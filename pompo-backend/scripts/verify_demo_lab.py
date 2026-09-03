"""Developer verification of the POMPO demonstration lab (API-level).

Not part of the human demonstration. Operators should follow DEMO-TESTING-GUIDE.md.

Exercises the same backend path the physical demo uses:
  health → login identities → merchant access isolation → QR inspect →
  customer pay (simulated) → merchant ledger → admin visibility →
  customer QR-create denial.

Usage:

    docker compose exec backend python scripts/verify_demo_lab.py
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx

from scripts.demo_lab import (
    DEMO_ADMIN_EMAIL,
    DEMO_ADMIN_PASSWORD,
    DEMO_CUSTOMER_EMAIL,
    DEMO_CUSTOMER_PASSWORD,
    DEMO_MERCHANT_EMAIL,
    DEMO_MERCHANT_PASSWORD,
)

API_BASE = os.getenv("POMPO_API_BASE", "http://localhost:8000/api/v1").rstrip("/")


class Check:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self.rows.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.rows)


def _login(client: httpx.Client, email: str, password: str) -> dict:
    resp = client.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    result = Check()
    with httpx.Client(timeout=30.0) as client:
        live = client.get(f"{API_BASE}/health/live")
        result.record("health live", live.status_code == 200, str(live.status_code))
        ready = client.get(f"{API_BASE}/health/ready")
        result.record("health ready", ready.status_code == 200, str(ready.status_code))

        try:
            admin_tokens = _login(client, DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD)
            result.record("demo admin login", True)
        except httpx.HTTPError as exc:
            result.record("demo admin login", False, str(exc)[:160])
            return 1

        try:
            merchant_tokens = _login(client, DEMO_MERCHANT_EMAIL, DEMO_MERCHANT_PASSWORD)
            result.record("demo merchant login", True)
        except httpx.HTTPError as exc:
            result.record("demo merchant login", False, str(exc)[:160])
            return 1

        try:
            customer_tokens = _login(client, DEMO_CUSTOMER_EMAIL, DEMO_CUSTOMER_PASSWORD)
            result.record("demo customer login", True)
        except httpx.HTTPError as exc:
            result.record("demo customer login", False, str(exc)[:160])
            return 1

        admin_h = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
        merchant_h = {"Authorization": f"Bearer {merchant_tokens['access_token']}"}
        customer_h = {"Authorization": f"Bearer {customer_tokens['access_token']}"}

        admin_me = client.get(f"{API_BASE}/auth/me", headers=admin_h)
        result.record(
            "admin is not a merchant",
            admin_me.status_code == 200 and admin_me.json().get("merchant_id") is None,
            str(admin_me.json().get("role_code")),
        )

        admin_access = client.get(f"{API_BASE}/organization/my-access", headers=admin_h)
        result.record(
            "admin merchant access denied",
            admin_access.status_code == 200 and admin_access.json().get("allowed") is False,
        )

        merch_access = client.get(f"{API_BASE}/organization/my-access", headers=merchant_h)
        merch_body = merch_access.json() if merch_access.status_code == 200 else {}
        result.record(
            "merchant access allowed with till",
            merch_access.status_code == 200
            and merch_body.get("allowed") is True
            and merch_body.get("can_generate_qr") is True
            and len(merch_body.get("tills") or []) >= 1,
        )

        cust_access = client.get(f"{API_BASE}/organization/my-access", headers=customer_h)
        result.record(
            "customer merchant access denied",
            cust_access.status_code == 200 and cust_access.json().get("allowed") is False,
        )

        merchant_id = merch_body.get("merchant", {}).get("id")
        branch_id = (merch_body.get("operating_branch_id") or (merch_body.get("branches") or [{}])[0].get("id"))
        till_id = (merch_body.get("operating_till_id") or (merch_body.get("tills") or [{}])[0].get("id"))

        deny_qr = client.post(
            f"{API_BASE}/qr/static",
            headers=customer_h,
            json={"merchant_id": merchant_id, "branch_id": branch_id, "till_id": till_id},
        )
        result.record("customer cannot create QR", deny_qr.status_code == 403, str(deny_qr.status_code))

        deny_ledger = client.get(f"{API_BASE}/payments", headers=customer_h)
        result.record(
            "customer cannot read merchant ledger",
            deny_ledger.status_code == 403,
            str(deny_ledger.status_code),
        )

        deny_settle = client.get(f"{API_BASE}/settlements/summary", headers=customer_h)
        result.record(
            "customer cannot read settlements",
            deny_settle.status_code == 403,
            str(deny_settle.status_code),
        )

        create_qr = client.post(
            f"{API_BASE}/qr/static",
            headers=merchant_h,
            json={"merchant_id": merchant_id, "branch_id": branch_id, "till_id": till_id},
        )
        result.record("merchant can create static QR", create_qr.status_code == 201, str(create_qr.status_code))
        if create_qr.status_code != 201:
            return 1 if not result.passed else 1
        qr = create_qr.json()
        public_id = qr["public_identifier"]
        result.record(
            "QR bound to demo merchant/till",
            qr.get("merchant_id") == merchant_id and qr.get("till_id") == till_id,
        )

        inspect = client.get(f"{API_BASE}/qr/{public_id}")
        inspect_ok = inspect.status_code == 200
        inspect_body = inspect.json() if inspect_ok else {}
        result.record(
            "public QR inspect",
            inspect_ok and inspect_body.get("merchant_name") == "POMPO Demo Merchant",
            inspect_body.get("merchant_name", str(inspect.status_code)),
        )

        pay = client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer_h,
            json={
                "public_identifier": public_id,
                "amount": "1500.00",
                "provider_code": "simulated",
                "idempotency_key": f"demo-lab-{uuid.uuid4().hex}",
            },
        )
        result.record("customer pay-from-qr", pay.status_code == 201, str(pay.status_code))
        if pay.status_code != 201:
            print(pay.text[:240])
            return 1
        payment = pay.json()
        reference = payment["reference"]

        processed = client.post(f"{API_BASE}/payments/{reference}/process", headers=customer_h)
        processed_ok = processed.status_code == 200
        processed_body = processed.json() if processed_ok else {}
        result.record(
            "simulated payment SUCCESS",
            processed_ok and processed_body.get("status") == "success",
            processed_body.get("status", str(processed.status_code)),
        )

        mine = client.get(f"{API_BASE}/payments/mine", headers=customer_h, params={"reference": reference})
        result.record(
            "customer history contains payment",
            mine.status_code == 200 and any(row.get("reference") == reference for row in mine.json()),
        )

        ledger = client.get(f"{API_BASE}/payments", headers=merchant_h, params={"reference": reference})
        result.record(
            "merchant ledger contains payment",
            ledger.status_code == 200 and any(row.get("reference") == reference for row in ledger.json()),
        )

        admin_tx = client.get(f"{API_BASE}/payments/{reference}", headers=admin_h)
        result.record(
            "admin can see payment",
            admin_tx.status_code == 200 and admin_tx.json().get("reference") == reference,
            str(admin_tx.status_code),
        )

        fail_pay = client.post(
            f"{API_BASE}/payments/from-qr",
            headers=customer_h,
            json={
                "public_identifier": public_id,
                "amount": "500.00",
                "provider_code": "simulated_failure",
                "idempotency_key": f"demo-lab-fail-{uuid.uuid4().hex}",
            },
        )
        if fail_pay.status_code == 201:
            fail_ref = fail_pay.json()["reference"]
            fail_proc = client.post(f"{API_BASE}/payments/{fail_ref}/process", headers=customer_h)
            result.record(
                "simulated payment FAILED",
                fail_proc.status_code == 200 and fail_proc.json().get("status") == "failed",
                fail_proc.json().get("status", str(fail_proc.status_code)) if fail_proc.status_code == 200 else str(fail_proc.status_code),
            )
        else:
            result.record("simulated payment FAILED", False, str(fail_pay.status_code))

        bogus = client.get(f"{API_BASE}/qr/NOT-A-POMPO-QR")
        result.record("invalid QR rejected", bogus.status_code in (404, 422), str(bogus.status_code))

    print()
    print("DEMO LAB API VERIFICATION:", "PASS" if result.passed else "FAIL")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
