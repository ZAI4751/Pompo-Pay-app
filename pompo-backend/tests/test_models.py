"""Domain model tests: schema creation, relationships, and soft-delete behavior.

These run against an in-memory SQLite engine rather than PostgreSQL so they
stay fast and dependency-free in CI. They validate ORM wiring (relationships,
constraints, cascades) — not PostgreSQL-specific behavior, which belongs in
the (future) database integration test suite that runs against a real
Postgres service container.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Branch,
    Merchant,
    PaymentAttempt,
    PaymentProvider,
    QRCode,
    Receipt,
    Role,
    Till,
    Transaction,
    User,
)
from app.models.base import Base
from app.models.enums import PaymentAttemptStatus, ProviderCode, QRStatus, QRType, TransactionStatus


@pytest.fixture
async def session() -> AsyncSession:
    """Fresh in-memory SQLite database per test."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _seed_checkout(session: AsyncSession) -> Transaction:
    """Build a merchant -> branch -> till -> user -> transaction chain."""
    role = Role(code="cashier", name="Cashier")
    merchant = Merchant(
        name="Chikondi General Store",
        contact_email="owner@chikondi.mw",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="Area 47 Branch")
    till = Till(branch=branch, code="T1", name="Front Counter")
    cashier = User(
        merchant=merchant,
        branch=branch,
        role=role,
        email="cashier@chikondi.mw",
        full_name="Grace Banda",
        hashed_password="hashed",
    )
    provider = PaymentProvider(
        code=ProviderCode.SIMULATED, display_name="Simulated Provider", is_simulated=True
    )
    txn = Transaction(
        merchant=merchant,
        branch=branch,
        till=till,
        cashier=cashier,
        reference=f"TXN-{uuid.uuid4().hex[:10]}",
        amount=Decimal("2500.00"),
        currency="MWK",
        status=TransactionStatus.CREATED,
    )
    session.add_all([role, merchant, branch, till, cashier, provider, txn])
    await session.flush()
    return txn


@pytest.mark.asyncio
async def test_checkout_chain_persists_with_relationships(session: AsyncSession) -> None:
    txn = await _seed_checkout(session)
    await session.commit()

    fetched = await session.get(Transaction, txn.id)
    assert fetched is not None
    assert fetched.merchant.name == "Chikondi General Store"
    assert fetched.branch.name == "Area 47 Branch"
    assert fetched.till.code == "T1"
    assert fetched.cashier.email == "cashier@chikondi.mw"
    assert fetched.status == TransactionStatus.CREATED


@pytest.mark.asyncio
async def test_transaction_reference_must_be_unique(session: AsyncSession) -> None:
    txn = await _seed_checkout(session)
    await session.commit()

    duplicate = Transaction(
        merchant_id=txn.merchant_id,
        branch_id=txn.branch_id,
        till_id=txn.till_id,
        reference=txn.reference,
        amount=Decimal("100.00"),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_payment_attempt_and_qr_and_receipt_link_to_transaction(
    session: AsyncSession,
) -> None:
    txn = await _seed_checkout(session)
    provider = (await session.execute(PaymentProvider.__table__.select())).first()

    attempt = PaymentAttempt(
        transaction_id=txn.id,
        provider_id=provider.id,
        attempt_number=1,
        status=PaymentAttemptStatus.INITIATED,
        initiated_at=datetime.now(timezone.utc),
    )
    qr = QRCode(
        public_identifier=f"QR{uuid.uuid4().hex[:12].upper()}",
        merchant_id=txn.merchant_id,
        branch_id=txn.branch_id,
        till_id=txn.till_id,
        qr_type=QRType.DYNAMIC,
        status=QRStatus.ACTIVE,
        version=1,
        transaction_id=txn.id,
        payment_reference=txn.reference,
        amount=txn.amount,
        currency=txn.currency,
        payload="POMPO:1:dynamic:QRTEST000000:250000:MWK:9999999999:REF:abcdefghijklmnopqr",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    receipt = Receipt(
        transaction_id=txn.id,
        receipt_number=f"RCPT-{uuid.uuid4().hex[:8]}",
        issued_at=datetime.now(timezone.utc),
    )
    session.add_all([attempt, qr, receipt])
    await session.commit()

    fetched = await session.get(Transaction, txn.id)
    await session.refresh(fetched, attribute_names=["attempts", "qr_code", "receipt"])
    assert len(fetched.attempts) == 1
    assert fetched.qr_code.payload.startswith("POMPO:")
    assert fetched.receipt.receipt_number == receipt.receipt_number


@pytest.mark.asyncio
async def test_soft_delete_hides_row_from_active_query(session: AsyncSession) -> None:
    from app.repositories.base import BaseRepository

    class MerchantRepository(BaseRepository[Merchant]):
        model = Merchant

    merchant = Merchant(
        name="Temp Vendor", contact_email="temp@pompo.mw", contact_phone="+265990000001"
    )
    session.add(merchant)
    await session.flush()

    repo = MerchantRepository(session)
    assert await repo.get_active_by_id(merchant.id) is not None

    await repo.soft_delete(merchant)
    await session.commit()

    assert merchant.is_deleted is True
    assert await repo.get_active_by_id(merchant.id) is None
    # Row still exists when queried without the soft-delete filter.
    assert await repo.get_by_id(merchant.id) is not None
