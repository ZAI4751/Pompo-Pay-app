#!/usr/bin/env python3
"""Production QR smoke test for M009 hardening verification."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from decimal import Decimal

try:
    import httpx
except ImportError:
    print("ERROR: pip install httpx")
    sys.exit(1)

API_BASE = os.getenv(
    "POMPO_API_BASE", "https://pompo-api-production.up.railway.app/api/v1"
).rstrip("/")
ADMIN_EMAIL = os.getenv("POMPO_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("POMPO_ADMIN_PASSWORD")


class SmokeResult:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)


async def main() -> int:
    result = SmokeResult()
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        result.record(
            "credentials configured",
            False,
            "Set POMPO_ADMIN_EMAIL and POMPO_ADMIN_PASSWORD",
        )
        return 1

    async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
        live = await client.get(f"{API_BASE}/health/live")
        result.record("health live", live.status_code == 200, str(live.status_code))

        login = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        if login.status_code != 200:
            result.record("login", False, login.text[:120])
            return 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        result.record("login", True)

        merchants = await client.get(f"{API_BASE}/merchants", headers=headers)
        if merchants.status_code != 200 or not merchants.json():
            result.record("merchant context", False, merchants.text[:120])
            return 1
        merchant = merchants.json()[0]
        merchant_id = merchant["id"]

        branches = await client.get(
            f"{API_BASE}/branches", headers=headers, params={"merchant_id": merchant_id}
        )
        tills = await client.get(
            f"{API_BASE}/tills", headers=headers, params={"merchant_id": merchant_id}
        )
        if not branches.json() or not tills.json():
            result.record("branch/till context", False, "missing branch or till")
            return 1
        branch_id = branches.json()[0]["id"]
        till_id = tills.json()[0]["id"]
        result.record("branch/till context", True)

        static = await client.post(
            f"{API_BASE}/qr/static",
            headers=headers,
            json={"merchant_id": merchant_id, "branch_id": branch_id, "till_id": till_id},
        )
        result.record("static QR create", static.status_code == 201, static.text[:80])
        if static.status_code != 201:
            return 1
        static_body = static.json()
        static_id = static_body["public_identifier"]

        inspect_static = await client.get(f"{API_BASE}/qr/{static_id}")
        inspect_body = inspect_static.json()
        safe = {"merchant_id", "branch_id", "till_id", "encoded_payload", "payload"}.isdisjoint(
            inspect_body.keys()
        )
        result.record(
            "static QR inspect",
            inspect_static.status_code == 200 and safe,
            str(inspect_static.status_code),
        )

        dyn_key = f"prod-dyn-{uuid.uuid4().hex[:8]}"
        dynamic = await client.post(
            f"{API_BASE}/qr/dynamic",
            headers=headers,
            json={
                "merchant_id": merchant_id,
                "branch_id": branch_id,
                "till_id": till_id,
                "amount": "25.50",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": dyn_key,
            },
        )
        result.record("dynamic QR create", dynamic.status_code == 201, dynamic.text[:80])
        if dynamic.status_code != 201:
            return 1
        dynamic_body = dynamic.json()
        dynamic_id = dynamic_body["public_identifier"]
        dynamic_payload = dynamic_body["encoded_payload"]

        inspect_dynamic = await client.get(f"{API_BASE}/qr/{dynamic_id}")
        result.record(
            "dynamic QR inspect",
            inspect_dynamic.status_code == 200,
            str(inspect_dynamic.status_code),
        )

        revoke = await client.post(f"{API_BASE}/qr/{static_id}/revoke", headers=headers)
        result.record("QR revoke", revoke.status_code == 200, str(revoke.status_code))

        revoked_inspect = await client.get(f"{API_BASE}/qr/{static_id}")
        result.record(
            "revoked QR rejected",
            revoked_inspect.status_code == 422,
            str(revoked_inspect.status_code),
        )

        pay_dynamic = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=headers,
            json={"payload": dynamic_payload, "idempotency_key": f"scan-{dyn_key}"},
        )
        result.record(
            "QR payment initiate",
            pay_dynamic.status_code in {200, 201},
            str(pay_dynamic.status_code),
        )
        if pay_dynamic.status_code not in {200, 201}:
            return 1
        reference = pay_dynamic.json()["reference"]

        fetched = await client.get(f"{API_BASE}/payments/{reference}", headers=headers)
        result.record("payment fetch", fetched.status_code == 200, fetched.json().get("status", ""))

        processed = await client.post(
            f"{API_BASE}/payments/{reference}/process", headers=headers
        )
        result.record(
            "sandbox provider process",
            processed.status_code == 200,
            processed.json().get("status", processed.text[:80]),
        )

        replay = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=headers,
            json={"payload": dynamic_payload, "idempotency_key": f"scan-{dyn_key}"},
        )
        result.record(
            "terminal QR reuse blocked",
            replay.status_code == 422,
            str(replay.status_code),
        )

        idem_key = f"static-idem-{uuid.uuid4().hex[:8]}"
        static_payload = static_body["encoded_payload"]
        # Use a fresh static QR for idempotency (revoked above)
        static2 = await client.post(
            f"{API_BASE}/qr/static",
            headers=headers,
            json={"merchant_id": merchant_id, "branch_id": branch_id, "till_id": till_id},
        )
        sp2 = static2.json()
        first = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=headers,
            json={
                "payload": sp2["encoded_payload"],
                "idempotency_key": idem_key,
                "amount": "10.00",
                "provider_code": "simulated",
            },
        )
        second = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=headers,
            json={
                "payload": sp2["encoded_payload"],
                "idempotency_key": idem_key,
                "amount": "10.00",
                "provider_code": "simulated",
            },
        )
        same_id = (
            first.status_code in {200, 201}
            and second.status_code in {200, 201}
            and first.json()["id"] == second.json()["id"]
        )
        result.record("static idempotency replay", same_id, str(second.status_code))

    print("\nSummary:", "ALL PASSED" if result.passed else "FAILURES DETECTED")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
