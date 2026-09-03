"""Safe, controlled test and demonstration environment seeder.

Provisions clearly identifiable test data and identities for physical
and browser demonstration:
  - POMPO Demo Merchant, Branch, and Till (DEMO-TILL-01)
  - Test Platform Admin (demo.admin@pompo.mw / PompoDemoAdmin2026!)
  - Test Merchant Owner (demo.merchant@pompo.mw / PompoDemoMerch2026!)
  - Test Customer (demo.customer@pompo.mw / PompoDemoCust2026!)
  - Pre-enrolled simulated payment instruments (Airtel & TNM Sandbox)
  - Pre-generated static and dynamic demo QR codes

Idempotent: safe to run multiple times without corrupting data or duplicating users.
Refuses to run against production database unless explicitly confirmed.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config.base import get_settings
from app.core.security.password import PasswordHasher
from app.database.engine import create_engine, dispose_engine
from app.models import Branch, Merchant, Role, Till, User
from app.models.customer import CustomerPreference
from app.models.enums import PaymentInstrumentStatus, PaymentInstrumentType, ProviderCode, QRStatus
from app.models.payment import PaymentInstrument, PaymentProvider, QRCode
from app.payments.catalog import seed_provider_catalog
from scripts.demo_lab import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    DEMO_BRANCH_NAME,
    DEMO_CUSTOMER_EMAIL,
    DEMO_CUSTOMER_PASSWORD,
    DEMO_MERCHANT_EMAIL,
    DEMO_MERCHANT_NAME,
    DEMO_MERCHANT_PASSWORD,
    DEMO_TILL_CODE,
    DEMO_TILL_NAME,
    DemoLabRefused,
    require_demo_lab_allowed,
)
from scripts.seed_rbac import seed_rbac_session
from app.services.qr import QRService

hasher = PasswordHasher()


async def seed_demo_environment() -> None:
    settings = get_settings()
    require_demo_lab_allowed(settings.app_env)
    engine = create_engine(settings)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        print("[1/6] Seeding RBAC permissions and roles...")
        await seed_rbac_session(session)

        print("[2/6] Seeding provider catalog (including all simulated providers)...")
        await seed_provider_catalog(session)

        # Retrieve roles
        admin_role = await session.scalar(select(Role).where(Role.code == "platform_admin"))
        merchant_role = await session.scalar(select(Role).where(Role.code == "merchant_owner"))
        customer_role = await session.scalar(select(Role).where(Role.code == "customer"))

        if not admin_role or not merchant_role or not customer_role:
            raise RuntimeError("Required system roles are missing after RBAC seed")

        print("[3/6] Setting up POMPO Demo Merchant organization hierarchy...")
        demo_merchant = await session.scalar(
            select(Merchant).where(Merchant.name == DEMO_MERCHANT_NAME)
        )
        if demo_merchant is None:
            demo_merchant = Merchant(
                name=DEMO_MERCHANT_NAME,
                registration_number="DEMO-REG-001",
                contact_email=DEMO_MERCHANT_EMAIL,
                contact_phone="+265999000100",
                is_active=True,
            )
            session.add(demo_merchant)
            await session.flush()
        else:
            demo_merchant.is_active = True

        demo_branch = await session.scalar(
            select(Branch).where(
                Branch.merchant_id == demo_merchant.id,
                Branch.name == DEMO_BRANCH_NAME,
            )
        )
        if demo_branch is None:
            demo_branch = Branch(
                merchant_id=demo_merchant.id,
                name=DEMO_BRANCH_NAME,
                address="Lilongwe City Centre, Malawi",
                is_active=True,
            )
            session.add(demo_branch)
            await session.flush()
        else:
            demo_branch.is_active = True

        demo_till = await session.scalar(
            select(Till).where(
                Till.branch_id == demo_branch.id,
                Till.code == DEMO_TILL_CODE,
            )
        )
        if demo_till is None:
            demo_till = Till(
                branch_id=demo_branch.id,
                name=DEMO_TILL_NAME,
                code=DEMO_TILL_CODE,
                is_active=True,
            )
            session.add(demo_till)
            await session.flush()
        else:
            demo_till.is_active = True

        print("[4/6] Creating controlled test identities...")
        # A. Platform Admin: platform_admin access, merchant_id=None (proves admin does not imply merchant)
        demo_admin = await session.scalar(select(User).where(User.email == DEMO_ADMIN_EMAIL))
        if demo_admin is None:
            demo_admin = User(
                email=DEMO_ADMIN_EMAIL,
                hashed_password=hasher.hash(DEMO_ADMIN_PASSWORD),
                full_name="POMPO Demo Platform Admin",
                phone="+265999000001",
                role_id=admin_role.id,
                merchant_id=None,
                branch_id=None,
                is_active=True,
                is_email_verified=True,
                email_verified_at=datetime.now(UTC),
            )
            session.add(demo_admin)
        else:
            demo_admin.hashed_password = hasher.hash(DEMO_ADMIN_PASSWORD)
            demo_admin.role_id = admin_role.id
            demo_admin.merchant_id = None
            demo_admin.is_active = True
            demo_admin.is_email_verified = True

        # B. Test Merchant: authorized merchant membership, branch, till, and QR capability
        demo_merchant_user = await session.scalar(
            select(User).where(User.email == DEMO_MERCHANT_EMAIL)
        )
        if demo_merchant_user is None:
            demo_merchant_user = User(
                email=DEMO_MERCHANT_EMAIL,
                hashed_password=hasher.hash(DEMO_MERCHANT_PASSWORD),
                full_name="POMPO Demo Merchant Owner",
                phone="+265999000002",
                role_id=merchant_role.id,
                merchant_id=demo_merchant.id,
                branch_id=demo_branch.id,
                is_active=True,
                is_email_verified=True,
                email_verified_at=datetime.now(UTC),
            )
            session.add(demo_merchant_user)
        else:
            demo_merchant_user.hashed_password = hasher.hash(DEMO_MERCHANT_PASSWORD)
            demo_merchant_user.role_id = merchant_role.id
            demo_merchant_user.merchant_id = demo_merchant.id
            demo_merchant_user.branch_id = demo_branch.id
            demo_merchant_user.is_active = True
            demo_merchant_user.is_email_verified = True

        # C. Test Customer: verified customer account, merchant_id=None
        demo_customer = await session.scalar(
            select(User).where(User.email == DEMO_CUSTOMER_EMAIL)
        )
        if demo_customer is None:
            demo_customer = User(
                email=DEMO_CUSTOMER_EMAIL,
                hashed_password=hasher.hash(DEMO_CUSTOMER_PASSWORD),
                full_name="POMPO Demo Customer",
                phone="+265999000999",
                role_id=customer_role.id,
                merchant_id=None,
                branch_id=None,
                is_active=True,
                is_email_verified=True,
                email_verified_at=datetime.now(UTC),
            )
            session.add(demo_customer)
            await session.flush()
        else:
            demo_customer.hashed_password = hasher.hash(DEMO_CUSTOMER_PASSWORD)
            demo_customer.role_id = customer_role.id
            demo_customer.merchant_id = None
            demo_customer.is_active = True
            demo_customer.is_email_verified = True
            demo_customer.email_verified_at = demo_customer.email_verified_at or datetime.now(UTC)
            await session.flush()

        prefs = await session.scalar(
            select(CustomerPreference).where(CustomerPreference.user_id == demo_customer.id)
        )
        if prefs is None:
            session.add(
                CustomerPreference(
                    user_id=demo_customer.id,
                    preferred_mode="customer",
                )
            )

        # Simulated Provider for instruments
        sim_provider = await session.scalar(
            select(PaymentProvider).where(PaymentProvider.code == ProviderCode.SIMULATED)
        )
        if not sim_provider:
            raise RuntimeError("Simulated provider is missing from catalog")

        print("[5/6] Enrolling test customer simulated payment methods...")
        # Instrument 1: Airtel Money Sandbox (Default)
        airtel_inst = await session.scalar(
            select(PaymentInstrument).where(
                PaymentInstrument.customer_id == demo_customer.id,
                PaymentInstrument.masked_identifier == "...0999",
                PaymentInstrument.status != PaymentInstrumentStatus.REVOKED,
            )
        )
        if airtel_inst is None:
            airtel_inst = PaymentInstrument(
                customer_id=demo_customer.id,
                provider_id=sim_provider.id,
                public_identifier=f"INST-AIRTEL-{uuid.uuid4().hex[:12].upper()}",
                instrument_type=PaymentInstrumentType.MOBILE_MONEY,
                display_name="Airtel Money Sandbox",
                masked_identifier="...0999",
                token_reference=f"tok_sim_airtel_{uuid.uuid4().hex}",
                provider_customer_reference="+265999000999",
                status=PaymentInstrumentStatus.ACTIVE,
                is_default=True,
                is_sandbox=True,
                safe_metadata={"carrier": "Airtel Malawi", "simulated": True},
            )
            session.add(airtel_inst)
        else:
            airtel_inst.is_default = True
            airtel_inst.status = PaymentInstrumentStatus.ACTIVE

        # Instrument 2: TNM Mpamba Sandbox
        tnm_inst = await session.scalar(
            select(PaymentInstrument).where(
                PaymentInstrument.customer_id == demo_customer.id,
                PaymentInstrument.masked_identifier == "...0888",
                PaymentInstrument.status != PaymentInstrumentStatus.REVOKED,
            )
        )
        if tnm_inst is None:
            tnm_inst = PaymentInstrument(
                customer_id=demo_customer.id,
                provider_id=sim_provider.id,
                public_identifier=f"INST-TNM-{uuid.uuid4().hex[:12].upper()}",
                instrument_type=PaymentInstrumentType.MOBILE_MONEY,
                display_name="TNM Mpamba Sandbox",
                masked_identifier="...0888",
                token_reference=f"tok_sim_tnm_{uuid.uuid4().hex}",
                provider_customer_reference="+265888000888",
                status=PaymentInstrumentStatus.ACTIVE,
                is_default=False,
                is_sandbox=True,
                safe_metadata={"carrier": "TNM Mpamba", "simulated": True},
            )
            session.add(tnm_inst)
        else:
            tnm_inst.status = PaymentInstrumentStatus.ACTIVE

        await session.flush()

        print("[6/6] Ensuring active static & dynamic demo QR codes exist on till...")
        active_static_qr = await session.scalar(
            select(QRCode).where(
                QRCode.till_id == demo_till.id,
                QRCode.status == QRStatus.ACTIVE,
                QRCode.amount.is_(None),
            )
        )
        qr_svc = QRService(session)
        if active_static_qr is None:
            active_static_qr = await qr_svc.create_static_qr(
                demo_merchant_user,
                {
                    "merchant_id": demo_merchant.id,
                    "branch_id": demo_branch.id,
                    "till_id": demo_till.id,
                },
            )
            print(f"  Created Static QR: {active_static_qr.public_identifier}")
        else:
            print(f"  Existing Static QR: {active_static_qr.public_identifier}")

        active_dyn_qr = await session.scalar(
            select(QRCode).where(
                QRCode.till_id == demo_till.id,
                QRCode.status == QRStatus.ACTIVE,
                QRCode.amount.is_not(None),
            )
        )
        if active_dyn_qr is None:
            active_dyn_qr = await qr_svc.create_dynamic_qr(
                demo_merchant_user,
                {
                    "merchant_id": demo_merchant.id,
                    "branch_id": demo_branch.id,
                    "till_id": demo_till.id,
                    "amount": Decimal("2500.00"),
                    "currency": "MWK",
                    "payment_method": "mobile_money",
                    "provider_code": "simulated",
                    "idempotency_key": f"demo-dyn-{uuid.uuid4().hex}",
                    "description": "POMPO Demo Checkout Item",
                },
            )
            print(f"  Created Dynamic QR: {active_dyn_qr.public_identifier} (MWK 2500.00)")
        else:
            print(f"  Existing Dynamic QR: {active_dyn_qr.public_identifier} (MWK {active_dyn_qr.amount})")

        await session.commit()

        checkout_base = settings.public_checkout_base_url.rstrip("/")
        print("\n" + "=" * 70)
        print("POMPO SAFE TEST & DEMONSTRATION ENVIRONMENT READY")
        print("=" * 70)
        print(f"Merchant:   {DEMO_MERCHANT_NAME}")
        print(f"Branch:     {DEMO_BRANCH_NAME}")
        print(f"Till:       {DEMO_TILL_NAME} (Code: {DEMO_TILL_CODE})")
        print("-" * 70)
        print("IDENTITIES FOR HUMAN OPERATOR TESTING:")
        print("  1. Platform Admin (Master Admin web app):")
        print(f"     Email:    {DEMO_ADMIN_EMAIL}")
        print(f"     Password: {DEMO_ADMIN_PASSWORD}")
        print("     Role:     platform_admin (access to Master Admin, no merchant mode)")
        print()
        print("  2. Merchant Owner (POMPO Mobile App - Merchant Mode):")
        print(f"     Email:    {DEMO_MERCHANT_EMAIL}")
        print(f"     Password: {DEMO_MERCHANT_PASSWORD}")
        print("     Role:     merchant_owner (authorized for Demo Merchant, Branch & Till)")
        print()
        print("  3. Customer (POMPO Mobile App & Web Checkout):")
        print(f"     Email:    {DEMO_CUSTOMER_EMAIL}")
        print(f"     Password: {DEMO_CUSTOMER_PASSWORD}")
        print("     Role:     customer (pre-enrolled Airtel & TNM simulated methods)")
        print("-" * 70)
        print("DEMONSTRATION QR CODES:")
        print(f"  Static QR Public ID:  {active_static_qr.public_identifier}")
        print(f"  Static QR URL:        {checkout_base}/p/{active_static_qr.public_identifier}")
        print()
        print(f"  Dynamic QR Public ID: {active_dyn_qr.public_identifier}")
        print(f"  Dynamic QR URL:       {checkout_base}/p/{active_dyn_qr.public_identifier}")
        print("=" * 70 + "\n")

    await dispose_engine()


if __name__ == "__main__":
    try:
        asyncio.run(seed_demo_environment())
    except DemoLabRefused as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
