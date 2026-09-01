"""End-to-end Merchant → Branch → Till → Provider → Payment chain."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Branch,
    Merchant,
    Permission,
    Role,
    RolePermission,
    Till,
    User,
)
from app.models.base import Base
from app.models.enums import TransactionStatus
from app.payments.catalog import seed_provider_catalog
from app.services.organization import OrganizationService
from app.services.payment import PaymentForbiddenError, PaymentInvalidError, PaymentService


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_operational_payment_chain_creates_attempt_and_succeeds(
    session: AsyncSession,
) -> None:
    permissions = [
        Permission(code=code)
        for code in (
            "merchants:create",
            "merchants:read",
            "branches:create",
            "branches:read",
            "tills:create",
            "tills:read",
            "transactions:create",
            "transactions:read",
            "transactions:update",
        )
    ]
    role = Role(code="platform_admin", name="Platform administrator")
    role.permissions.extend(RolePermission(permission=permission) for permission in permissions)
    actor = User(
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Platform Administrator",
        hashed_password="hash",
        is_active=True,
    )
    session.add_all([*permissions, role, actor])
    await session.commit()

    created = await seed_provider_catalog(session)
    await session.commit()
    assert created >= 1

    organization = OrganizationService(session)
    merchant = await organization.create_merchant(
        actor,
        {
            "name": "Chain Merchant",
            "contact_email": f"{uuid.uuid4().hex}@example.com",
            "contact_phone": "+265991000000",
        },
    )
    branch = await organization.create_branch(actor, merchant.id, {"name": "Lilongwe"})
    till = await organization.create_till(actor, branch.id, {"code": "POS-1", "name": "Counter 1"})

    payments = PaymentService(session)
    payment = await payments.create_payment(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("25.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": "chain-1",
        },
    )
    replayed = await payments.create_payment(
        actor,
        {
            "merchant_id": merchant.id,
            "branch_id": branch.id,
            "till_id": till.id,
            "amount": Decimal("25.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": "chain-1",
        },
    )
    processed = await payments.process_payment(actor, payment.reference)

    assert replayed.id == payment.id
    assert processed.status is TransactionStatus.SUCCESS
    assert processed.till_id == till.id
    assert processed.attempts[0].provider_reference == f"simulated-{payment.reference}"
    fetched = await payments.get_payment(actor, payment.reference)
    assert fetched.reference == payment.reference


@pytest.mark.asyncio
async def test_payment_rejects_inactive_placeholder_provider(session: AsyncSession) -> None:
    permissions = [
        Permission(code=code)
        for code in ("transactions:create", "merchants:create", "branches:create", "tills:create")
    ]
    role = Role(code="platform_admin", name="Platform administrator")
    role.permissions.extend(RolePermission(permission=permission) for permission in permissions)
    actor = User(
        role=role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Admin",
        hashed_password="hash",
        is_active=True,
    )
    merchant = Merchant(
        name="M",
        contact_email=f"{uuid.uuid4().hex}@example.com",
        contact_phone="+265991000000",
    )
    branch = Branch(merchant=merchant, name="B")
    till = Till(branch=branch, code="T1", name="Till")
    session.add_all([*permissions, role, actor, merchant, branch, till])
    await session.commit()
    await seed_provider_catalog(session)
    await session.commit()

    payments = PaymentService(session)
    with pytest.raises(PaymentInvalidError):
        await payments.create_payment(
            actor,
            {
                "merchant_id": merchant.id,
                "branch_id": branch.id,
                "till_id": till.id,
                "amount": Decimal("10.00"),
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "airtel_money",
                "idempotency_key": "no-live-rail",
            },
        )


@pytest.mark.asyncio
async def test_cross_tenant_payment_identifiers_are_rejected(session: AsyncSession) -> None:
    permissions = [
        Permission(code=code)
        for code in (
            "merchants:create",
            "branches:create",
            "tills:create",
            "transactions:create",
        )
    ]
    admin_role = Role(code="platform_admin", name="Platform administrator")
    admin_role.permissions.extend(
        RolePermission(permission=permission) for permission in permissions
    )
    owner_role = Role(code=f"owner_{uuid.uuid4().hex}", name="Owner")
    owner_role.permissions.extend(
        RolePermission(permission=permission) for permission in permissions
    )
    admin = User(
        role=admin_role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Admin",
        hashed_password="hash",
        is_active=True,
    )
    session.add_all([*permissions, admin_role, owner_role, admin])
    await session.commit()
    await seed_provider_catalog(session)
    await session.commit()

    organization = OrganizationService(session)
    first = await organization.create_merchant(
        admin,
        {
            "name": "First",
            "contact_email": f"{uuid.uuid4().hex}@example.com",
            "contact_phone": "+265991000000",
        },
    )
    second = await organization.create_merchant(
        admin,
        {
            "name": "Second",
            "contact_email": f"{uuid.uuid4().hex}@example.com",
            "contact_phone": "+265991000001",
        },
    )
    first_branch = await organization.create_branch(admin, first.id, {"name": "A"})
    second_branch = await organization.create_branch(admin, second.id, {"name": "B"})
    first_till = await organization.create_till(
        admin, first_branch.id, {"code": "T1", "name": "One"}
    )
    second_till = await organization.create_till(
        admin, second_branch.id, {"code": "T2", "name": "Two"}
    )
    owner = User(
        merchant_id=first.id,
        role=owner_role,
        email=f"{uuid.uuid4().hex}@example.com",
        full_name="Owner",
        hashed_password="hash",
        is_active=True,
    )
    session.add(owner)
    await session.commit()

    payments = PaymentService(session)
    with pytest.raises(PaymentForbiddenError):
        await payments.create_payment(
            owner,
            {
                "merchant_id": second.id,
                "branch_id": second_branch.id,
                "till_id": second_till.id,
                "amount": Decimal("10.00"),
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": "cross-tenant",
            },
        )
    with pytest.raises(PaymentInvalidError):
        await payments.create_payment(
            owner,
            {
                "merchant_id": first.id,
                "branch_id": first_branch.id,
                "till_id": second_till.id,
                "amount": Decimal("10.00"),
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": "wrong-till-uuid",
            },
        )
    payment = await payments.create_payment(
        owner,
        {
            "merchant_id": first.id,
            "branch_id": first_branch.id,
            "till_id": first_till.id,
            "amount": Decimal("10.00"),
            "currency": "MWK",
            "payment_method": "mobile_money",
            "provider_code": "simulated",
            "idempotency_key": "own-till",
        },
    )
    assert payment.till_id == first_till.id
