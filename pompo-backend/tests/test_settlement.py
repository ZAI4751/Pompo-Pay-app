"""M011 settlement ingestion, matching, and reconciliation tests."""

from __future__ import annotations

import json
import time
import uuid
import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    AuditLog,
    Branch,
    Merchant,
    PaymentAttempt,
    PaymentProvider,
    Permission,
    Role,
    RolePermission,
    Settlement,
    Till,
    Transaction,
    User,
)
from app.models.base import Base
from app.models.enums import (
    FeeType,
    MismatchCategory,
    PaymentAttemptStatus,
    ProviderCode,
    ReconciliationStatus,
    SettlementStatus,
    TransactionStatus,
)
from app.models.settlement import PricingSchedule
from app.payments.money import MoneyError, merchant_net, parse_money, percentage_of
from app.payments.pricing import apply_schedule, pricing_scope_key
from app.payments.webhooks import compute_mock_signature
from app.services.settlement import SettlementService, SettlementSignatureError

WEBHOOK_SECRET = "test-webhook-secret-value"
WEBHOOK_SECRET_ENV = "SIMULATED_WEBHOOK_SECRET"
GROSS = Decimal("100000.00")
PROVIDER_COST = Decimal("500.00")
POMPO_FEE = Decimal("1000.00")
NET = Decimal("98500.00")


@pytest.fixture(autouse=True)
def settlement_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_SIMULATED_WEBHOOK_SECRET_REF", WEBHOOK_SECRET_ENV)
    monkeypatch.setenv(WEBHOOK_SECRET_ENV, WEBHOOK_SECRET)


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


async def _seed(
    session: AsyncSession,
    *,
    amount: Decimal = GROSS,
    status: TransactionStatus = TransactionStatus.SUCCESS,
    extra_permissions: tuple[str, ...] = (),
) -> tuple[User, Transaction, PaymentProvider]:
    codes = {
        "settlements:read",
        "settlements:create",
        "reconciliation:read",
        "reconciliation:update",
        *extra_permissions,
    }
    perms = [Permission(code=code) for code in codes]
    role = Role(code=f"settlement_admin_{uuid.uuid4().hex}", name="Settlement admin")
    for perm in perms:
        role.permissions.append(RolePermission(permission=perm))
    merchant = Merchant(
        name="Merchant",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Main")
    till = Till(branch=branch, code="T1", name="Counter")
    actor = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Admin",
        hashed_password="hash",
    )
    provider = PaymentProvider(code=ProviderCode.SIMULATED, display_name="Simulated")
    session.add_all([*perms, role, merchant, branch, till, actor, provider])
    await session.flush()

    schedule = PricingSchedule(
        scope_key=pricing_scope_key(
            provider_id=str(provider.id), merchant_id=str(merchant.id), currency="MWK"
        ),
        provider_id=provider.id,
        merchant_id=merchant.id,
        currency="MWK",
        pompo_fee_type=FeeType.FIXED,
        pompo_fixed_amount=POMPO_FEE,
        provider_cost_type=FeeType.FIXED,
        provider_cost_fixed=PROVIDER_COST,
    )
    session.add(schedule)

    transaction = Transaction(
        merchant_id=merchant.id,
        branch_id=branch.id,
        till_id=till.id,
        cashier_id=actor.id,
        provider_id=provider.id,
        reference=f"PMP-{uuid.uuid4().hex[:16].upper()}",
        idempotency_key=f"order-{uuid.uuid4().hex}",
        request_fingerprint=uuid.uuid4().hex,
        amount=amount,
        currency="MWK",
        payment_method="mobile_money",
        status=status,
        completed_at=datetime.now(UTC) if status is TransactionStatus.SUCCESS else None,
    )
    attempt = PaymentAttempt(
        transaction=transaction,
        provider_id=provider.id,
        attempt_number=1,
        status=PaymentAttemptStatus.SUCCESS
        if status is TransactionStatus.SUCCESS
        else PaymentAttemptStatus.PENDING,
        provider_reference=f"simulated-{transaction.reference}",
        provider_response={"provider_transaction_id": f"simulated-{transaction.reference}"},
        initiated_at=datetime.now(UTC),
    )
    session.add_all([transaction, attempt])
    await session.commit()
    await session.refresh(transaction, attribute_names=["attempts"])
    return actor, transaction, provider


def _batch_payload(
    *,
    payment_reference: str,
    settlement_reference: str,
    gross: Decimal = GROSS,
    provider_fee: Decimal | None = PROVIDER_COST,
    batch_reference: str | None = None,
    provider_transaction_id: str | None = None,
) -> dict:
    record = {
        "settlement_reference": settlement_reference,
        "payment_reference": payment_reference,
        "provider_transaction_id": provider_transaction_id or f"simulated-{payment_reference}",
        "gross_amount": str(gross),
        "currency": "MWK",
        "settlement_date": date.today().isoformat(),
    }
    if provider_fee is not None:
        record["provider_fee"] = str(provider_fee)
    return {
        "batch_reference": batch_reference or f"SIM-BATCH-{uuid.uuid4().hex[:8]}",
        "settlement_date": date.today().isoformat(),
        "currency": "MWK",
        "records": [record],
    }


def _signed(payload: dict) -> tuple[bytes, dict[str, str]]:
    timestamp = str(int(time.time()))
    body = json.dumps(payload).encode()
    signature = compute_mock_signature(WEBHOOK_SECRET, timestamp, body)
    return body, {
        "X-Pompo-Signature": signature,
        "X-Pompo-Timestamp": timestamp,
        "Content-Type": "application/json",
    }


def test_parse_money_rejects_float_and_extra_scale() -> None:
    with pytest.raises(MoneyError):
        parse_money(1.25)  # type: ignore[arg-type]
    with pytest.raises(MoneyError):
        parse_money("100.001")
    assert parse_money("100000.00") == GROSS
    assert merchant_net(gross=GROSS, provider_fee=PROVIDER_COST, pompo_fee=POMPO_FEE) == NET
    assert percentage_of(GROSS, 150) == Decimal("1500.00")


def test_zero_schedule_passes_gross_through() -> None:
    breakdown = apply_schedule(GROSS, None, "MWK")
    assert breakdown.provider_cost == Decimal("0.00")
    assert breakdown.pompo_fee == Decimal("0.00")
    assert breakdown.merchant_net == GROSS


@pytest.mark.asyncio
async def test_settlement_model_unique_provider_reference(session: AsyncSession) -> None:
    actor, transaction, provider = await _seed(session)
    from app.models.settlement import SettlementBatch

    batch = SettlementBatch(
        public_identifier="BAT-AAA",
        provider_id=provider.id,
        external_batch_reference="batch-1",
        settlement_date=date.today(),
        currency="MWK",
    )
    session.add(batch)
    await session.flush()
    first = Settlement(
        public_identifier="SET-AAA",
        batch_id=batch.id,
        provider_id=provider.id,
        provider_settlement_reference="sim-1",
        gross_amount=GROSS,
        provider_fee=PROVIDER_COST,
        pompo_fee=POMPO_FEE,
        merchant_net=NET,
        currency="MWK",
        status=SettlementStatus.SETTLED,
        settlement_date=date.today(),
        received_at=datetime.now(UTC),
        transaction_id=transaction.id,
        merchant_id=actor.merchant_id,
    )
    duplicate = Settlement(
        public_identifier="SET-BBB",
        batch_id=batch.id,
        provider_id=provider.id,
        provider_settlement_reference="sim-1",
        gross_amount=GROSS,
        provider_fee=PROVIDER_COST,
        pompo_fee=POMPO_FEE,
        merchant_net=NET,
        currency="MWK",
        status=SettlementStatus.SETTLED,
        settlement_date=date.today(),
        received_at=datetime.now(UTC),
    )
    session.add(first)
    await session.commit()
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_matched_settlement_calculates_net(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    original_amount = transaction.amount
    original_status = transaction.status
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference, settlement_reference="sim-match-1"
    )
    batch, duplicate = await service.ingest_admin(actor, "simulated", payload)
    assert duplicate is False
    assert batch.record_count == 1
    assert batch.total_gross == GROSS
    assert batch.total_provider_fees == PROVIDER_COST
    assert batch.total_pompo_fees == POMPO_FEE
    assert batch.total_merchant_net == NET

    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    assert settlement.merchant_net == NET
    assert settlement.status is SettlementStatus.RECONCILED
    assert settlement.reconciliation is not None
    assert settlement.reconciliation.status is ReconciliationStatus.MATCHED
    await session.refresh(transaction)
    assert transaction.amount == original_amount
    assert transaction.status is original_status


@pytest.mark.asyncio
async def test_match_by_provider_reference(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference="",
        settlement_reference="sim-pref-1",
        provider_transaction_id=f"simulated-{transaction.reference}",
    )
    payload["records"][0]["payment_reference"] = None
    batch, _ = await service.ingest_admin(actor, "simulated", payload)
    settlement = (await session.scalars(select(Settlement))).one()
    assert settlement.transaction_id == transaction.id
    assert batch.record_count == 1


@pytest.mark.asyncio
async def test_amount_discrepancy_does_not_mutate_payment(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference,
        settlement_reference="sim-disc-1",
        gross=Decimal("99000.00"),
        provider_fee=Decimal("500.00"),
    )
    await service.ingest_admin(actor, "simulated", payload)
    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    recon = settlement.reconciliation
    assert recon is not None
    assert recon.status is ReconciliationStatus.DISCREPANCY
    assert recon.mismatch_category is MismatchCategory.AMOUNT_MISMATCH
    assert recon.expected_amount == GROSS
    assert recon.actual_amount == Decimal("99000.00")
    assert recon.variance == Decimal("-1000.00")
    await session.refresh(transaction)
    assert transaction.amount == GROSS
    assert transaction.status is TransactionStatus.SUCCESS


@pytest.mark.asyncio
async def test_fee_discrepancy_is_partial_match(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference,
        settlement_reference="sim-fee-1",
        provider_fee=Decimal("800.00"),
    )
    await service.ingest_admin(actor, "simulated", payload)
    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    assert settlement.reconciliation.status is ReconciliationStatus.PARTIAL_MATCH
    assert settlement.reconciliation.mismatch_category is MismatchCategory.FEE_MISMATCH
    assert settlement.merchant_net == Decimal("98200.00")


@pytest.mark.asyncio
async def test_missing_pompo_payment_is_unmatched(session: AsyncSession) -> None:
    actor, _, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference="PMP-DOES-NOT-EXIST",
        settlement_reference="sim-miss-1",
    )
    await service.ingest_admin(actor, "simulated", payload)
    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    assert settlement.reconciliation.status is ReconciliationStatus.UNMATCHED
    assert settlement.reconciliation.mismatch_category is MismatchCategory.MISSING_POMPO_TRANSACTION


@pytest.mark.asyncio
async def test_duplicate_ingestion_has_no_duplicate_financial_effect(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference,
        settlement_reference="sim-dup-1",
        batch_reference="SIM-BATCH-DUP",
    )
    first, dup1 = await service.ingest_admin(actor, "simulated", payload)
    second, dup2 = await service.ingest_admin(actor, "simulated", payload)
    assert dup1 is False
    assert dup2 is True
    assert first.id == second.id
    count = (await session.scalar(select(func.count(Settlement.id)))) or 0
    total_net = await session.scalar(select(func.coalesce(func.sum(Settlement.merchant_net), 0)))
    assert count == 1
    assert parse_money(total_net) == NET


@pytest.mark.asyncio
async def test_duplicate_settlement_different_reference_is_discrepancy(
    session: AsyncSession,
) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference,
            settlement_reference="sim-first",
            batch_reference="batch-a",
        ),
    )
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference,
            settlement_reference="sim-second",
            batch_reference="batch-b",
        ),
    )
    settlements = list((await session.scalars(select(Settlement))).all())
    assert len(settlements) == 2
    statuses = []
    for item in settlements:
        await session.refresh(item, attribute_names=["reconciliation"])
        statuses.append(item.reconciliation.status)
    assert ReconciliationStatus.DISCREPANCY in statuses


@pytest.mark.asyncio
async def test_currency_discrepancy(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference, settlement_reference="sim-cur-1"
    )
    payload["records"][0]["currency"] = "USD"
    await service.ingest_admin(actor, "simulated", payload)
    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    assert settlement.reconciliation.status is ReconciliationStatus.DISCREPANCY
    assert settlement.reconciliation.mismatch_category is MismatchCategory.CURRENCY_MISMATCH


@pytest.mark.asyncio
async def test_pending_payment_is_partial_timing(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session, status=TransactionStatus.PENDING)
    service = SettlementService(session)
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference, settlement_reference="sim-timing-1"
        ),
    )
    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    assert settlement.reconciliation.status is ReconciliationStatus.PARTIAL_MATCH
    assert settlement.reconciliation.mismatch_category is MismatchCategory.TIMING_DISCREPANCY


@pytest.mark.asyncio
async def test_resolve_does_not_change_settlement_amounts(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference,
            settlement_reference="sim-res-1",
            gross=Decimal("99000.00"),
        ),
    )
    settlement = (await session.scalars(select(Settlement))).one()
    await session.refresh(settlement, attribute_names=["reconciliation"])
    original_net = settlement.merchant_net
    resolved = await service.resolve(
        actor, settlement.reconciliation.id, note="Investigated; provider file accepted"
    )
    assert resolved.status is ReconciliationStatus.RESOLVED
    await session.refresh(settlement)
    assert settlement.merchant_net == original_net
    await session.refresh(transaction)
    assert transaction.amount == GROSS
    actions = list((await session.scalars(select(AuditLog.action))).all())
    assert "discrepancy_created" in actions
    assert "resolution_recorded" in actions


@pytest.mark.asyncio
async def test_reconciliation_run_finds_missing_settlement(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    now = datetime.now(UTC)
    run = await service.create_run(
        actor,
        provider_code="simulated",
        window_start=now - timedelta(hours=1),
        window_end=now + timedelta(hours=1),
    )
    assert run.unmatched_count >= 1
    assert run.records_examined >= 1
    from app.models.settlement import ReconciliationRecord

    missing = (
        await session.scalars(
            select(ReconciliationRecord).where(
                ReconciliationRecord.transaction_id == transaction.id,
                ReconciliationRecord.settlement_id.is_(None),
            )
        )
    ).one()
    assert missing.mismatch_category is MismatchCategory.MISSING_SETTLEMENT


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_ingest(session: AsyncSession) -> None:
    from app.services.settlement import SettlementForbiddenError

    _, transaction, _ = await _seed(session)
    cashier_role = Role(code=f"cashier_{uuid.uuid4().hex}", name="Cashier")
    cashier = User(
        role=cashier_role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Cashier",
        hashed_password="hash",
    )
    session.add_all([cashier_role, cashier])
    await session.commit()
    service = SettlementService(session)
    with pytest.raises(SettlementForbiddenError):
        await service.ingest_admin(
            cashier,
            "simulated",
            _batch_payload(
                payment_reference=transaction.reference, settlement_reference="sim-unauth"
            ),
        )


@pytest.mark.asyncio
async def test_signed_ingest_rejects_bad_signature(session: AsyncSession) -> None:
    _, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference, settlement_reference="sim-sig-1"
    )
    body, headers = _signed(payload)
    headers["X-Pompo-Signature"] = "sha256=deadbeef"
    with pytest.raises(SettlementSignatureError):
        await service.ingest_signed("simulated", headers=headers, body=body)


@pytest.mark.asyncio
async def test_signed_ingest_rejects_inactive_provider(session: AsyncSession) -> None:
    from app.services.settlement import SettlementInvalidError

    _, transaction, provider = await _seed(session)
    provider.is_active = False
    await session.commit()
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference, settlement_reference="sim-inactive-1"
    )
    body, headers = _signed(payload)
    with pytest.raises(SettlementInvalidError, match="not active"):
        await service.ingest_signed("simulated", headers=headers, body=body)


@pytest.mark.asyncio
async def test_signed_ingest_match(session: AsyncSession) -> None:
    _, transaction, _ = await _seed(session)
    service = SettlementService(session)
    payload = _batch_payload(
        payment_reference=transaction.reference, settlement_reference="sim-signed-1"
    )
    body, headers = _signed(payload)
    batch, duplicate = await service.ingest_signed("simulated", headers=headers, body=body)
    assert duplicate is False
    assert batch.total_merchant_net == NET


@pytest.mark.asyncio
async def test_rbac_list_requires_permission(session: AsyncSession) -> None:
    from app.services.settlement import SettlementForbiddenError

    actor, _, _ = await _seed(session)
    cashier_role = Role(code=f"cashier_{uuid.uuid4().hex}", name="Cashier")
    cashier = User(
        role=cashier_role,
        merchant_id=actor.merchant_id,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Cashier",
        hashed_password="hash",
    )
    session.add_all([cashier_role, cashier])
    await session.commit()
    service = SettlementService(session)
    with pytest.raises(SettlementForbiddenError):
        await service.list_settlements(cashier)


@pytest.mark.asyncio
async def test_merchant_cannot_read_another_merchant_settlement(session: AsyncSession) -> None:
    from app.services.settlement import SettlementForbiddenError

    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference, settlement_reference="sim-tenant-1"
        ),
    )
    settlement = (await session.scalars(select(Settlement))).one()

    read_perm = await session.scalar(select(Permission).where(Permission.code == "settlements:read"))
    recon_perm = await session.scalar(select(Permission).where(Permission.code == "reconciliation:read"))
    assert read_perm is not None and recon_perm is not None
    other_role = Role(code=f"owner_{uuid.uuid4().hex}", name="Other owner")
    other_role.permissions.extend(
        [RolePermission(permission=read_perm), RolePermission(permission=recon_perm)]
    )
    other_merchant = Merchant(
        name="Other Merchant",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000001",
    )
    other_user = User(
        merchant=other_merchant,
        role=other_role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Other",
        hashed_password="hash",
    )
    session.add_all([other_role, other_merchant, other_user])
    await session.commit()

    visible = await service.list_settlements(other_user)
    assert visible == []
    with pytest.raises(SettlementForbiddenError):
        await service.get_settlement(other_user, settlement.id)
    await session.refresh(settlement, attribute_names=["reconciliation"])
    with pytest.raises(SettlementForbiddenError):
        await service.get_reconciliation(other_user, settlement.reconciliation.id)


@pytest.mark.asyncio
async def test_rerun_does_not_unresolve_missing_settlement(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    now = datetime.now(UTC)
    first = await service.create_run(
        actor,
        provider_code="simulated",
        window_start=now - timedelta(hours=1),
        window_end=now + timedelta(hours=1),
    )
    from app.models.settlement import ReconciliationRecord

    missing = (
        await session.scalars(
            select(ReconciliationRecord).where(
                ReconciliationRecord.transaction_id == transaction.id,
                ReconciliationRecord.settlement_id.is_(None),
            )
        )
    ).one()
    resolved = await service.resolve(actor, missing.id, note="Accepted as timing lag")
    assert resolved.status is ReconciliationStatus.RESOLVED
    second = await service.create_run(
        actor,
        provider_code="simulated",
        window_start=now - timedelta(hours=1),
        window_end=now + timedelta(hours=1),
    )
    await session.refresh(missing)
    assert missing.status is ReconciliationStatus.RESOLVED
    assert first.id != second.id


@pytest.mark.asyncio
async def test_summary_and_openapi_paths(session: AsyncSession) -> None:
    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference, settlement_reference="sim-sum-1"
        ),
    )
    summary = await service.reconciliation_summary(actor)
    assert summary["total_settlements"] == 1
    assert parse_money(summary["total_merchant_net"]) == NET
    assert summary["matched"] == 1

    from fastapi import FastAPI

    from app.api.v1.router import api_v1_router

    app = FastAPI()
    app.include_router(api_v1_router, prefix="/api/v1")
    paths = app.openapi()["paths"]
    assert "/api/v1/settlements" in paths
    assert "/api/v1/settlements/ingest/{provider_code}" in paths
    assert "/api/v1/reconciliation" in paths
    assert "/api/v1/reconciliation/{record_id}/resolve" in paths
    assert "/api/v1/reconciliation/runs" in paths
    assert "get" in paths["/api/v1/settlements"]
    assert "post" in paths["/api/v1/settlements"]
    get_settlements = paths["/api/v1/settlements"]["get"]
    assert get_settlements.get("tags") == ["Settlements"]


@pytest.mark.asyncio
async def test_admin_api_lists_settlements_and_rejects_anonymous(session: AsyncSession) -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.api import deps
    from app.api.v1.settlements import get_settlement_service, settlement_router

    actor, transaction, _ = await _seed(session)
    service = SettlementService(session)
    await service.ingest_admin(
        actor,
        "simulated",
        _batch_payload(
            payment_reference=transaction.reference, settlement_reference="sim-http-1"
        ),
    )

    app = FastAPI()
    app.include_router(settlement_router, prefix="/api/v1")

    async def override_user() -> User:
        return actor

    async def override_session():
        yield session

    app.dependency_overrides[deps.get_current_user] = override_user
    app.dependency_overrides[deps.get_db_session] = override_session
    app.dependency_overrides[get_settlement_service] = lambda: SettlementService(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/settlements")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["payment_reference"] == transaction.reference
        assert body[0]["merchant_net"] in ("98500.00", 98500.0, "98500.0")

    anonymous = FastAPI()
    anonymous.include_router(settlement_router, prefix="/api/v1")
    anonymous.dependency_overrides[deps.get_db_session] = override_session
    transport = ASGITransport(app=anonymous)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unauth = await client.get("/api/v1/settlements")
        assert unauth.status_code == 401


@pytest.mark.asyncio
async def test_http_ingest_duplicate_flag(session: AsyncSession) -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.api.v1.settlements import get_settlement_service, settlement_router

    _, transaction, _ = await _seed(session)
    payload = _batch_payload(
        payment_reference=transaction.reference,
        settlement_reference="sim-http-dup",
        batch_reference="SIM-HTTP-DUP",
    )
    body, headers = _signed(payload)

    app = FastAPI()
    app.include_router(settlement_router, prefix="/api/v1")
    app.dependency_overrides[get_settlement_service] = lambda: SettlementService(session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/settlements/ingest/simulated", content=body, headers=headers
        )
        second = await client.post(
            "/api/v1/settlements/ingest/simulated", content=body, headers=headers
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True
        assert first.json()["record_count"] == 1


@pytest.mark.asyncio
async def test_concurrent_duplicate_ingestion() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///file:m011settlement?mode=memory&cache=shared&uri=true"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as setup:
        actor, transaction, _ = await _seed(setup)
        actor_id = actor.id
        reference = transaction.reference
    payload = _batch_payload(
        payment_reference=reference,
        settlement_reference="sim-conc-1",
        batch_reference="SIM-CONC-BATCH",
    )

    async def _ingest() -> object:
        last: Exception | None = None
        for _ in range(8):
            try:
                async with factory() as worker:
                    user = await worker.get(User, actor_id)
                    assert user is not None
                    return await SettlementService(worker).ingest_admin(
                        user, "simulated", payload
                    )
            except Exception as exc:
                last = exc
                await asyncio.sleep(0.05)
        raise last if last is not None else RuntimeError("concurrent ingest failed")

    results = await asyncio.gather(_ingest(), _ingest(), return_exceptions=True)
    successes = [item for item in results if not isinstance(item, Exception)]
    async with factory() as check:
        count = (await check.scalar(select(func.count(Settlement.id)))) or 0
        total_net = await check.scalar(select(func.coalesce(func.sum(Settlement.merchant_net), 0)))
        assert count == 1, [repr(item) for item in results]
        assert parse_money(total_net) == NET
    assert len(successes) >= 1
    await engine.dispose()
