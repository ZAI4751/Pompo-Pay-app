#!/usr/bin/env python3
"""Live sandbox: enroll a test method, pay a QR, revoke, and prove idempotency.

Uses admin credentials from the environment. Never prints JWTs, passwords,
tokens, PANs, PINs, or CVVs.
"""

from __future__ import annotations

import os
import sys
import uuid
from typing import Any

try:
    import httpx
except ImportError:
    print("ERROR: pip install httpx")
    sys.exit(1)

API_BASE = os.getenv("POMPO_API_BASE", "http://127.0.0.1:8000/api/v1").rstrip("/")
ADMIN_EMAIL = os.getenv("POMPO_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("POMPO_ADMIN_PASSWORD")


class Result:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


async def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def main() -> int:
    result = Result()
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        result.record("credentials configured", False, "POMPO_ADMIN_EMAIL/PASSWORD must be set")
        return 1

    suffix = uuid.uuid4().hex[:8]
    customer_email = f"m016-{suffix}@sandbox.example"
    customer_password = f"sandbox-{suffix}-horse"
    async with httpx.AsyncClient(timeout=30.0) as client:
        live = await client.get(f"{API_BASE}/health/live")
        result.record("health live", live.status_code == 200, str(live.status_code))
        if live.status_code != 200:
            return 1

        login = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        if login.status_code != 200:
            result.record("admin login", False, f"http_{login.status_code}")
            return 1
        admin_token = login.json()["access_token"]
        admin = _auth(admin_token)
        result.record("admin login", True)

        merchant = await client.post(
            f"{API_BASE}/organization/merchants",
            headers=admin,
            json={
                "name": f"Chez Ntemba {suffix}",
                "contact_email": f"ntemba-{suffix}@example.com",
                "contact_phone": "+265991000000",
            },
        )
        if merchant.status_code != 201:
            result.record("create merchant", False, f"http_{merchant.status_code}")
            return 1
        merchant_id = merchant.json()["id"]
        branch = await client.post(
            f"{API_BASE}/organization/merchants/{merchant_id}/branches",
            headers=admin,
            json={"name": "Lilongwe"},
        )
        till = await client.post(
            f"{API_BASE}/organization/branches/{branch.json()['id']}/tills",
            headers=admin,
            json={"code": f"NT-{suffix[:4].upper()}", "name": "Counter 1"},
        )
        result.record("merchant tree", till.status_code == 201, f"http_{till.status_code}")
        if till.status_code != 201:
            return 1
        branch_id = branch.json()["id"]
        till_id = till.json()["id"]

        qr = await client.post(
            f"{API_BASE}/qr/static",
            headers=admin,
            json={
                "merchant_id": merchant_id,
                "branch_id": branch_id,
                "till_id": till_id,
            },
        )
        result.record("merchant qr", qr.status_code == 201, f"http_{qr.status_code}")
        if qr.status_code != 201:
            return 1
        payload = qr.json()["encoded_payload"]
        public_id = qr.json()["public_identifier"]

        registered = await client.post(
            f"{API_BASE}/customers/register",
            json={
                "email": customer_email,
                "password": customer_password,
                "full_name": "Sandbox Customer",
                "phone": f"+26599{suffix[:7]}",
            },
        )
        result.record("customer register", registered.status_code == 201, f"http_{registered.status_code}")
        if registered.status_code != 201:
            return 1

        customer_login = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": customer_email, "password": customer_password},
        )
        if customer_login.status_code != 200:
            result.record("customer login", False, f"http_{customer_login.status_code}")
            return 1
        customer = _auth(customer_login.json()["access_token"])
        result.record("customer login", True)

        catalog = await client.get(f"{API_BASE}/payment-methods/catalog", headers=customer)
        items = await _json(catalog) if catalog.status_code == 200 else []
        simulated_mm = next(
            (
                row
                for row in items
                if row.get("provider_code") == "simulated"
                and row.get("instrument_type") == "mobile_money"
                and row.get("available") is True
            ),
            None,
        )
        airtel = next(
            (row for row in items if row.get("provider_code") == "airtel_money"),
            None,
        )
        result.record(
            "catalog simulated enrollable",
            catalog.status_code == 200 and simulated_mm is not None,
            f"http_{catalog.status_code}",
        )
        result.record(
            "catalog airtel unavailable",
            airtel is not None and airtel.get("available") is False,
            str(airtel.get("reason") if airtel else "missing"),
        )

        pin_rejected = await client.post(
            f"{API_BASE}/payment-methods",
            headers=customer,
            json={
                "provider_code": "simulated",
                "instrument_type": "mobile_money",
                "msisdn": "0882211121",
                "pin": "1234",
            },
        )
        result.record("reject pin enroll", pin_rejected.status_code == 422, f"http_{pin_rejected.status_code}")

        enrolled = await client.post(
            f"{API_BASE}/payment-methods",
            headers=customer,
            json={
                "provider_code": "simulated",
                "instrument_type": "mobile_money",
                "msisdn": "0882211121",
                "make_default": True,
            },
        )
        method = await _json(enrolled)
        result.record(
            "enroll sandbox airtel-style method",
            enrolled.status_code == 201
            and method.get("is_sandbox") is True
            and "••" in str(method.get("masked_identifier", ""))
            and "token_reference" not in method,
            f"http_{enrolled.status_code} {method.get('masked_identifier')}",
        )
        if enrolled.status_code != 201:
            return 1
        method_id = method["id"]

        inspect = await client.get(f"{API_BASE}/qr/{public_id}")
        inspect_body = await _json(inspect)
        result.record(
            "scan merchant identified",
            inspect.status_code == 200 and "Chez Ntemba" in str(inspect_body.get("merchant_name", "")),
            inspect_body.get("merchant_name", ""),
        )

        mismatch = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer,
            json={
                "payload": payload,
                "idempotency_key": f"mismatch-{suffix}",
                "amount": "18500.00",
                "provider_code": "airtel_money",
                "payment_instrument_id": method_id,
            },
        )
        result.record("provider mismatch rejected", mismatch.status_code == 422, f"http_{mismatch.status_code}")

        paid = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer,
            json={
                "payload": payload,
                "idempotency_key": f"pay-{suffix}",
                "amount": "18500.00",
                "payment_instrument_id": method_id,
            },
        )
        payment = await _json(paid)
        result.record(
            "pay from scanned qr",
            paid.status_code == 201
            and payment.get("payment_instrument_id") == method_id
            and "token_reference" not in payment,
            f"http_{paid.status_code} {payment.get('reference')}",
        )
        if paid.status_code != 201:
            return 1
        reference = payment["reference"]

        processed = await client.post(f"{API_BASE}/payments/{reference}/process", headers=customer)
        processed_body = await _json(processed)
        result.record(
            "simulated provider success",
            processed.status_code == 200 and processed_body.get("status") == "success",
            f"http_{processed.status_code} {processed_body.get('status')}",
        )

        receipt = await client.get(f"{API_BASE}/payments/{reference}/receipt", headers=customer)
        receipt_body = await _json(receipt)
        result.record(
            "customer receipt",
            receipt.status_code == 200 and receipt_body.get("reference") == reference,
            f"http_{receipt.status_code}",
        )

        mine = await client.get(f"{API_BASE}/payments/mine", headers=customer)
        mine_rows = await _json(mine) if mine.status_code == 200 else []
        result.record(
            "customer activity",
            mine.status_code == 200 and any(row.get("reference") == reference for row in mine_rows),
            f"http_{mine.status_code}",
        )

        merchant_view = await client.get(f"{API_BASE}/payments/{reference}", headers=admin)
        merchant_body = await _json(merchant_view)
        result.record(
            "merchant/admin payment activity",
            merchant_view.status_code == 200 and merchant_body.get("status") == "success",
            f"http_{merchant_view.status_code}",
        )

        replay = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer,
            json={
                "payload": payload,
                "idempotency_key": f"pay-{suffix}",
                "amount": "18500.00",
                "payment_instrument_id": method_id,
            },
        )
        replay_body = await _json(replay)
        result.record(
            "duplicate idempotency one effect",
            replay.status_code == 201 and replay_body.get("reference") == reference,
            f"http_{replay.status_code}",
        )

        visa = await client.post(
            f"{API_BASE}/payment-methods",
            headers=customer,
            json={
                "provider_code": "simulated",
                "instrument_type": "visa",
                "card_last4": "4242",
            },
        )
        visa_body = await _json(visa)
        result.record(
            "enroll sandbox visa",
            visa.status_code == 201 and visa_body.get("is_sandbox") is True,
            visa_body.get("masked_identifier", ""),
        )
        if visa.status_code != 201:
            return 1

        manual = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer,
            json={
                "public_identifier": public_id,
                "idempotency_key": f"manual-{suffix}",
                "amount": "50.00",
                "payment_instrument_id": visa_body["id"],
            },
        )
        manual_body = await _json(manual)
        result.record(
            "manual qr code checkout",
            manual.status_code == 201 and manual_body.get("payment_method") == "card",
            f"http_{manual.status_code} {manual_body.get('detail')}",
        )

        revoked = await client.delete(f"{API_BASE}/payment-methods/{method_id}", headers=customer)
        result.record("revoke method", revoked.status_code in {200, 204}, f"http_{revoked.status_code}")

        rejected = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer,
            json={
                "public_identifier": public_id,
                "idempotency_key": f"revoked-{suffix}",
                "amount": "10.00",
                "payment_instrument_id": method_id,
            },
        )
        result.record("revoked method rejected", rejected.status_code == 422, f"http_{rejected.status_code}")

        admin_list = await client.get(f"{API_BASE}/payment-methods/admin", headers=admin)
        admin_rows = await _json(admin_list) if admin_list.status_code == 200 else []
        leaked = any("token_reference" in row for row in admin_rows if isinstance(row, dict))
        result.record(
            "admin masked list",
            admin_list.status_code == 200 and not leaked and any("••" in str(row.get("masked_identifier", "")) for row in admin_rows),
            f"http_{admin_list.status_code} count={len(admin_rows) if isinstance(admin_rows, list) else 0}",
        )

        openapi = await client.get(API_BASE.removesuffix("/api/v1") + "/openapi.json")
        paths = (await _json(openapi)).get("paths", {}) if openapi.status_code == 200 else {}
        result.record(
            "openapi payment-methods",
            "/api/v1/payment-methods" in paths and "/api/v1/payment-methods/catalog" in paths,
            f"http_{openapi.status_code}",
        )

    failed = [name for name, ok, _ in result.checks if not ok]
    if failed:
        print(f"FAILED: {len(failed)} checks")
        return 1
    print(f"PASSED: {len(result.checks)} checks")
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
