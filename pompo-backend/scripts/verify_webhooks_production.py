#!/usr/bin/env python3
"""Production webhook verification for M010 (simulated sandbox provider only)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx required")
    raise SystemExit(1)

from app.payments.webhooks import compute_mock_signature

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _load_secret() -> str:
    secret = os.environ.get("SIMULATED_WEBHOOK_SECRET")
    if secret:
        return secret
    local = ROOT / ".env.webhook.local"
    if local.exists():
        for line in local.read_text(encoding="utf-8").splitlines():
            if line.startswith("SIMULATED_WEBHOOK_SECRET="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("SIMULATED_WEBHOOK_SECRET is not configured")


class Result:
    def __init__(self) -> None:
        self.failed = 0

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            self.failed += 1
        print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


async def main() -> int:
    parser = argparse.ArgumentParser(description="Verify M010 webhooks in production")
    parser.add_argument(
        "--api-base",
        default="https://pompo-api-production.up.railway.app/api/v1",
        help="Production API base URL",
    )
    parser.add_argument("--webhook-secret", help="Simulated webhook signing secret")
    parser.add_argument("--admin-token", help="Optional bearer token")
    args = parser.parse_args()

    _load_dotenv(ROOT / ".env")
    secret = args.webhook_secret or _load_secret()
    base = args.api_base.rstrip("/")
    result = Result()

    async with httpx.AsyncClient(timeout=30.0) as client:
        live = await client.get(f"{base}/health/live")
        result.record("health live", live.status_code == 200, str(live.status_code))
        ready = await client.get(f"{base}/health/ready")
        ready_ok = ready.status_code == 200 and ready.json().get("ready") is True
        result.record("health ready", ready_ok, str(ready.status_code))
        health = await client.get(f"{base}/health")
        health_json = health.json() if health.status_code == 200 else {}
        components = health_json.get("components") or {}
        result.record("health overall", health_json.get("status") == "healthy", health_json.get("status", str(health.status_code)))
        result.record("database healthy", (components.get("database") or {}).get("healthy") is True)
        result.record("redis healthy", (components.get("redis") or {}).get("healthy") is True)
        result.record(
            "celery healthy",
            (components.get("celery") or {}).get("healthy") is True,
            str((components.get("celery") or {}).get("details")),
        )

        token = args.admin_token
        if not token:
            login = await client.post(
                f"{base}/auth/login",
                json={
                    "email": os.environ.get("POMPO_ADMIN_EMAIL"),
                    "password": os.environ.get("POMPO_ADMIN_PASSWORD"),
                },
            )
            if login.status_code != 200:
                result.record("login", False, str(login.status_code))
                print("failures", result.failed)
                return 1
            token = login.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        result.record("login", True)

        provider = await client.get(f"{base}/providers/simulated", headers=auth)
        row = provider.json() if provider.status_code == 200 else {}
        result.record(
            "simulated provider configured",
            provider.status_code == 200
            and row.get("is_active") is True
            and row.get("is_simulated") is True
            and (row.get("capabilities") or {}).get("supports_webhooks") is True
            and (row.get("configuration") or {}).get("signing_configured") is True,
            f"status={provider.status_code} active={row.get('is_active')} signing={(row.get('configuration') or {}).get('signing_configured')}",
        )

        merchants = await client.get(f"{base}/organization/merchants", headers=auth)
        if merchants.status_code != 200:
            result.record("merchant context", False, merchants.text[:120])
            print("failures", result.failed)
            return 1
        merchant_rows = merchants.json()
        if not merchant_rows:
            created_merchant = await client.post(
                f"{base}/organization/merchants",
                headers=auth,
                json={
                    "name": "M010 Verification Merchant",
                    "contact_email": "m010-verify@example.com",
                    "contact_phone": "+265991000010",
                },
            )
            if created_merchant.status_code != 201:
                result.record("merchant context", False, created_merchant.text[:160])
                print("failures", result.failed)
                return 1
            merchant_rows = [created_merchant.json()]
        merchant_id = merchant_rows[0]["id"]
        branches = await client.get(
            f"{base}/organization/merchants/{merchant_id}/branches", headers=auth
        )
        if branches.status_code != 200:
            result.record("branch/till context", False, branches.text[:120])
            print("failures", result.failed)
            return 1
        branch_rows = branches.json()
        if not branch_rows:
            created_branch = await client.post(
                f"{base}/organization/merchants/{merchant_id}/branches",
                headers=auth,
                json={"name": "M010 Verification Branch"},
            )
            if created_branch.status_code != 201:
                result.record("branch/till context", False, created_branch.text[:160])
                print("failures", result.failed)
                return 1
            branch_rows = [created_branch.json()]
        branch_id = branch_rows[0]["id"]
        tills = await client.get(
            f"{base}/organization/branches/{branch_id}/tills", headers=auth
        )
        if tills.status_code != 200:
            result.record("branch/till context", False, tills.text[:120])
            print("failures", result.failed)
            return 1
        till_rows = tills.json()
        if not till_rows:
            created_till = await client.post(
                f"{base}/organization/branches/{branch_id}/tills",
                headers=auth,
                json={"code": "M010T1", "name": "M010 Verification Till"},
            )
            if created_till.status_code != 201:
                result.record("branch/till context", False, created_till.text[:160])
                print("failures", result.failed)
                return 1
            till_rows = [created_till.json()]
        till_id = till_rows[0]["id"]
        result.record("merchant context", True)

        payment = await client.post(
            f"{base}/payments",
            headers=auth,
            json={
                "merchant_id": merchant_id,
                "branch_id": branch_id,
                "till_id": till_id,
                "amount": "25.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "provider_code": "simulated",
                "idempotency_key": f"m010-webhook-{uuid.uuid4().hex}",
                "description": "M010 simulated webhook verification",
            },
        )
        if payment.status_code != 201:
            result.record("create payment", False, payment.text[:160])
            print("failures", result.failed)
            return 1
        reference = payment.json()["reference"]
        initial_status = payment.json()["status"]
        result.record("create payment", True, f"{reference} status={initial_status}")

        timestamp = str(int(time.time()))
        event_id = f"prod-verify-{uuid.uuid4().hex[:12]}"
        payload = {
            "event_id": event_id,
            "event_type": "payment.success",
            "event_version": "1",
            "payment_reference": reference,
            "provider_transaction_id": f"simulated-{reference}",
            "outcome": "success",
        }
        body = json.dumps(payload).encode()

        invalid = await client.post(
            f"{base}/webhooks/simulated",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Pompo-Signature": "sha256=deadbeef",
                "X-Pompo-Timestamp": timestamp,
            },
        )
        result.record("invalid signature rejected", invalid.status_code == 401, str(invalid.status_code))
        after_invalid = await client.get(f"{base}/payments/{reference}", headers=auth)
        result.record(
            "payment unchanged after invalid signature",
            after_invalid.status_code == 200 and after_invalid.json()["status"] == initial_status,
            after_invalid.json().get("status") if after_invalid.status_code == 200 else str(after_invalid.status_code),
        )

        signature = compute_mock_signature(secret, timestamp, body)
        accepted = await client.post(
            f"{base}/webhooks/simulated",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Pompo-Signature": signature,
                "X-Pompo-Timestamp": timestamp,
            },
        )
        accepted_json = accepted.json() if accepted.status_code == 200 else {}
        result.record(
            "valid signed webhook accepted",
            accepted.status_code == 200 and accepted_json.get("duplicate") is not True,
            f"{accepted.status_code} {accepted.text[:120]}",
        )

        processed = None
        final_payment = None
        for _ in range(20):
            listed = await client.get(
                f"{base}/webhooks",
                headers=auth,
                params={"payment_reference": reference, "limit": 10},
            )
            events = listed.json() if listed.status_code == 200 else []
            processed = next((item for item in events if item.get("provider_event_id") == event_id), None)
            final_payment = await client.get(f"{base}/payments/{reference}", headers=auth)
            if (
                processed
                and processed.get("processing_status") in {"processed", "duplicate", "failed", "reconciliation"}
                and final_payment.status_code == 200
            ):
                break
            time.sleep(1)

        result.record("webhook persisted", processed is not None)
        if processed:
            result.record(
                "celery processed event",
                processed.get("processing_status") == "processed" and processed.get("processed") is not False,
                str(processed.get("processing_status")),
            )
            result.record(
                "webhook marked processed",
                processed.get("processing_status") == "processed",
                str(processed.get("processing_status")),
            )
        payment_status = final_payment.json()["status"] if final_payment and final_payment.status_code == 200 else None
        result.record(
            "payment updated through payment engine",
            payment_status == "success",
            str(payment_status),
        )
        result.record(
            "audit implied by processed webhook + payment transition",
            payment_status == "success" and (processed or {}).get("processing_status") == "processed",
        )

        duplicate = await client.post(
            f"{base}/webhooks/simulated",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Pompo-Signature": signature,
                "X-Pompo-Timestamp": timestamp,
            },
        )
        dup_json = duplicate.json() if duplicate.status_code == 200 else {}
        result.record(
            "duplicate acknowledged",
            duplicate.status_code == 200 and dup_json.get("duplicate") is True,
            f"{duplicate.status_code} {duplicate.text[:120]}",
        )
        after_dup = await client.get(f"{base}/payments/{reference}", headers=auth)
        result.record(
            "duplicate has no extra financial effect",
            after_dup.status_code == 200 and after_dup.json()["status"] == "success",
            after_dup.json().get("status") if after_dup.status_code == 200 else str(after_dup.status_code),
        )

    print("failures", result.failed)
    return 1 if result.failed else 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
