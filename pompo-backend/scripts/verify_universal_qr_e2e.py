#!/usr/bin/env python3
"""POMPO Universal QR & Zero-Install Web Checkout E2E Verification Script.

Runs against live database session to verify the real merchant QR creation,
universal HTTPS URL resolution, public web inspection, customer payment initiation,
provider simulation, and terminal consumption.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database.engine import create_engine, dispose_engine
from app.models import Branch, Merchant, Permission, Role, RolePermission, Till, User
from app.models.enums import QRStatus, TransactionStatus
from app.payments.catalog import seed_provider_catalog
from app.qr.payload import extract_public_identifier
from app.services.payment import PaymentService
from app.services.qr import QRInvalidError, QRService


async def get_or_create_permission(session, code: str) -> Permission:
    p = await session.scalar(select(Permission).where(Permission.code == code))
    if p is None:
        p = Permission(code=code)
        session.add(p)
        await session.flush()
    return p


async def main() -> int:
    print("============================================================")
    print("POMPO UNIVERSAL QR + WEB PAYMENT ENTRY E2E TEST")
    print("============================================================")

    from app.core.config.base import get_settings

    settings = get_settings()
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with factory() as session:
        await seed_provider_catalog(session)

        # 1. Setup Merchant Context
        merchant = Merchant(
            name="Lilongwe Fresh Mart E2E",
            contact_email=f"freshmart_{uuid.uuid4().hex[:6]}@example.com",
            contact_phone="+265999000111",
        )
        branch = Branch(merchant=merchant, name="City Centre Branch")
        till = Till(branch=branch, name="Main Counter Till 01", code=f"T01-{uuid.uuid4().hex[:4]}")

        # Merchant Cashier
        cashier_role = Role(code=f"cashier_{uuid.uuid4().hex[:6]}", name="Cashier")
        for perm in ("qr:create", "qr:read", "qr:revoke", "transactions:create", "transactions:read", "transactions:update"):
            p = await get_or_create_permission(session, perm)
            cashier_role.permissions.append(RolePermission(permission=p))

        cashier = User(
            email=f"cashier_{uuid.uuid4().hex[:6]}@freshmart.mw",
            hashed_password="hash",
            full_name="Kondwani Phiri",
            merchant=merchant,
            branch=branch,
            role=cashier_role,
            is_active=True,
        )

        # Customer User
        cust_role = Role(code=f"cust_{uuid.uuid4().hex[:6]}", name="Customer")
        for perm in ("transactions:create", "transactions:read"):
            p = await get_or_create_permission(session, perm)
            cust_role.permissions.append(RolePermission(permission=p))

        customer = User(
            email=f"cust_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="hash",
            full_name="Alice Chimwemwe",
            phone=f"+265888{uuid.uuid4().int % 1000000:06d}",
            role=cust_role,
            is_active=True,
        )

        session.add_all([merchant, branch, till, cashier_role, cashier, cust_role, customer])
        await session.commit()
        await session.refresh(cashier, attribute_names=["merchant", "branch", "role"])
        await session.refresh(customer, attribute_names=["role"])

        qr_service = QRService(session)
        payment_service = PaymentService(session)

        print("[OK] Test merchant and customer accounts seeded.")

        # 2. Generate Universal Dynamic QR
        dyn_qr = await qr_service.create_dynamic_qr(
            cashier,
            {
                "merchant_id": merchant.id,
                "branch_id": branch.id,
                "till_id": till.id,
                "amount": Decimal("15000.00"),
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": f"e2e-dyn-{uuid.uuid4().hex}",
                "expires_in_seconds": 900,
            },
        )
        universal_url = f"https://pay.pompo.mw/p/{dyn_qr.public_identifier}"
        print(f"[OK] Generated Dynamic QR: {dyn_qr.public_identifier}")
        print(f"     Universal HTTPS URL: {universal_url}")
        print(f"     Amount: {dyn_qr.amount} {dyn_qr.currency}")

        # 3. Simulate Android Native Camera / Google Lens Scan (URL detection)
        detected_id = extract_public_identifier(universal_url)
        assert detected_id == dyn_qr.public_identifier, "Camera/Lens failed to extract identifier"
        print(f"[OK] Camera / Google Lens extracted: {detected_id}")

        # 4. Simulate POMPO Mobile Scanner (Direct QR recognition)
        scanned_id = extract_public_identifier(f"pompo://pay.pompo.mw/p/{dyn_qr.public_identifier}")
        assert scanned_id == dyn_qr.public_identifier, "POMPO mobile scanner failed to extract identifier"
        print(f"[OK] POMPO Mobile scanner extracted: {scanned_id}")

        # 5. Public Inspection without authentication (Browser Web Checkout Entry)
        inspect_res = await qr_service.inspect_qr(detected_id)
        assert inspect_res.merchant.name == "Lilongwe Fresh Mart E2E"
        assert inspect_res.amount == Decimal("15000.00")
        assert inspect_res.status == QRStatus.ACTIVE
        print(f"[OK] Web Checkout Inspection: Paying {inspect_res.merchant.name} (MWK {inspect_res.amount})")

        # 6. Customer Web Payment Initiation
        txn = await qr_service.initiate_payment_from_qr(
            customer,
            {
                "public_identifier": detected_id,
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "customer_phone": "+265888777666",
                "idempotency_key": f"pay-{uuid.uuid4().hex}",
            },
        )
        print(f"[OK] Payment Initiated: Reference={txn.reference}, Status={txn.status.value}")

        # 7. Process simulated payment
        processed_txn = await payment_service.process_payment(cashier, txn.reference)
        print(f"[OK] Payment Processed: Reference={processed_txn.reference}, Status={processed_txn.status.value}")
        assert processed_txn.status == TransactionStatus.SUCCESS, "Payment must succeed"

        # 8. Dynamic QR Consumption Check
        await session.refresh(dyn_qr)
        assert dyn_qr.status == QRStatus.CONSUMED, "Dynamic QR must be marked consumed"
        print(f"[OK] QR Code marked CONSUMED: status={dyn_qr.status.value}")

        # Verify duplicate attempt is rejected
        try:
            await qr_service.initiate_payment_from_qr(
                customer,
                {
                    "public_identifier": detected_id,
                    "payment_method": "mobile_money",
                    "idempotency_key": f"pay-dup-{uuid.uuid4().hex}",
                },
            )
            print("[FAIL] Re-use of consumed QR was not blocked!")
            return 1
        except QRInvalidError:
            print("[OK] Duplicate payment attempt correctly rejected.")

        # 9. Static QR Test
        static_qr = await qr_service.create_static_qr(
            cashier,
            {
                "merchant_id": merchant.id,
                "branch_id": branch.id,
                "till_id": till.id,
            },
        )
        static_url = f"https://pay.pompo.mw/p/{static_qr.public_identifier}"
        print(f"[OK] Generated Static QR: {static_qr.public_identifier}")
        print(f"     Universal HTTPS URL: {static_url}")

        static_inspect = await qr_service.inspect_qr(static_qr.public_identifier)
        assert static_inspect.amount is None
        print(f"[OK] Static QR inspected: Amount is null (customer enters amount)")

        static_txn = await qr_service.initiate_payment_from_qr(
            customer,
            {
                "public_identifier": static_qr.public_identifier,
                "amount": Decimal("4500.00"),
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": f"pay-static-{uuid.uuid4().hex}",
            },
        )
        print(f"[OK] Static Payment Initiated: Ref={static_txn.reference}, Amount={static_txn.amount}")
        processed_static = await payment_service.process_payment(cashier, static_txn.reference)
        assert processed_static.status == TransactionStatus.SUCCESS
        print(f"[OK] Static Payment Processed: Status={processed_static.status.value}")

        print("============================================================")
        print("ALL REAL-WORLD UNIVERSAL QR CHECKS PASSED SUCCESSFULLY!")
        print("============================================================")

    await dispose_engine()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
