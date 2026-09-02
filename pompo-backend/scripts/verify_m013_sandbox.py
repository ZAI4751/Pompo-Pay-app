#!/usr/bin/env python3
"""M013 POS sandbox against a live POMPO API.

Uses admin credentials from the environment. Never prints API keys, webhook
secrets, JWTs, or passwords. Creates a throwaway merchant tree, exercises the
integration payment/QR/idempotency/scope/revoke flow, then revokes the client.
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


def _code(payload: Any) -> str:
    if isinstance(payload, dict):
        return str(payload.get("code") or "")
    return ""


async def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return {}


async def main() -> int:
    result = Result()
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        result.record("credentials configured", False, "POMPO_ADMIN_EMAIL/PASSWORD must be set")
        return 1

    suffix = uuid.uuid4().hex[:8]
    async with httpx.AsyncClient(timeout=30.0) as client:
        live = await client.get(f"{API_BASE}/health/live")
        result.record("health live", live.status_code == 200, str(live.status_code))

        login = await client.post(
            f"{API_BASE}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        if login.status_code != 200:
            result.record("admin login", False, f"http_{login.status_code}")
            return 1 if result.checks else 1
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        result.record("admin login", True)

        merchant = await client.post(
            f"{API_BASE}/organization/merchants",
            headers=headers,
            json={
                "name": f"M013 Sandbox {suffix}",
                "contact_email": f"m013-{suffix}@example.com",
                "contact_phone": "+265991000000",
            },
        )
        if merchant.status_code != 201:
            result.record("create merchant", False, f"http_{merchant.status_code}")
            return 1
        merchant_id = merchant.json()["id"]
        branch = await client.post(
            f"{API_BASE}/organization/merchants/{merchant_id}/branches",
            headers=headers,
            json={"name": "Sandbox Branch"},
        )
        till = await client.post(
            f"{API_BASE}/organization/branches/{branch.json()['id']}/tills",
            headers=headers,
            json={"code": f"SBX-{suffix[:4].upper()}", "name": "Sandbox Till"},
        )
        result.record("merchant tree", till.status_code == 201, f"http_{till.status_code}")
        if till.status_code != 201:
            return 1
        branch_id = branch.json()["id"]
        till_id = till.json()["id"]

        created = await client.post(
            f"{API_BASE}/integrations/clients",
            headers=headers,
            json={
                "name": f"Sandbox POS {suffix}",
                "client_type": "merchant_pos",
                "environment": "sandbox",
                "merchant_id": merchant_id,
                "branch_id": branch_id,
                "till_id": till_id,
                "webhook_url": "https://example.com/pompo/hooks",
            },
        )
        body = await _json(created)
        raw_key = body.get("api_key") if isinstance(body, dict) else None
        result.record(
            "create api client",
            created.status_code == 201 and isinstance(raw_key, str) and raw_key.startswith("pompo_"),
            f"http_{created.status_code} prefix={str(raw_key)[:11]}…",
        )
        if not raw_key:
            return 1
        api_headers = {"X-API-Key": raw_key}
        client_id = body["id"]

        limited = await client.post(
            f"{API_BASE}/integrations/clients",
            headers=headers,
            json={
                "name": f"Read only {suffix}",
                "client_type": "developer",
                "merchant_id": merchant_id,
                "scopes": ["payments:read"],
            },
        )
        read_key = (await _json(limited)).get("api_key")
        result.record("create read-only client", limited.status_code == 201)

        denied = await client.post(
            f"{API_BASE}/integrations/payments",
            headers={"X-API-Key": read_key or "missing"},
            json={
                "amount": "10.00",
                "currency": "MWK",
                "payment_method": "mobile_money",
                "idempotency_key": f"denied-{suffix}",
                "generate_qr": False,
            },
        )
        result.record(
            "insufficient scope",
            denied.status_code == 403 and _code(await _json(denied)) == "insufficient_scope",
            f"http_{denied.status_code} code={_code(await _json(denied))}",
        )

        idempotency = f"m013-{suffix}"
        payment_body = {
            "amount": "25.00",
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": idempotency,
            "generate_qr": True,
            "provider_code": "simulated",
        }
        first = await client.post(
            f"{API_BASE}/integrations/payments", headers=api_headers, json=payment_body
        )
        pay = await _json(first)
        qr = pay.get("qr") if isinstance(pay, dict) else None
        payload = qr.get("encoded_payload") if isinstance(qr, dict) else None
        reference = pay.get("reference") if isinstance(pay, dict) else None
        result.record(
            "pos create payment+qr",
            first.status_code == 201
            and isinstance(payload, str)
            and payload.startswith("POMPO:1:dynamic:")
            and isinstance(reference, str),
            f"http_{first.status_code} status={pay.get('status') if isinstance(pay, dict) else ''}",
        )
        if not reference or not payload:
            return 1

        replay = await client.post(
            f"{API_BASE}/integrations/payments", headers=api_headers, json=payment_body
        )
        replay_body = await _json(replay)
        result.record(
            "idempotent duplicate payment",
            replay.status_code == 201 and replay_body.get("reference") == reference,
            f"same_reference={replay_body.get('reference') == reference}",
        )

        conflict = await client.post(
            f"{API_BASE}/integrations/payments",
            headers=api_headers,
            json={**payment_body, "amount": "30.00"},
        )
        result.record(
            "idempotency conflict",
            conflict.status_code == 409 and _code(await _json(conflict)) == "idempotency_conflict",
            f"http_{conflict.status_code}",
        )

        scanned = await client.post(
            f"{API_BASE}/payments/from-qr",
            headers=headers,
            json={"payload": payload, "idempotency_key": f"scan-{suffix}"},
        )
        result.record(
            "customer scan from-qr",
            scanned.status_code == 201,
            f"http_{scanned.status_code} status={(await _json(scanned)).get('status')}",
        )

        processed = await client.post(
            f"{API_BASE}/payments/{reference}/process",
            headers=headers,
        )
        processed_body = await _json(processed)
        result.record(
            "simulated provider process",
            processed.status_code == 200 and processed_body.get("status") in {"success", "pending"},
            f"http_{processed.status_code} status={processed_body.get('status')}",
        )

        status = await client.get(
            f"{API_BASE}/integrations/payments/{reference}", headers=api_headers
        )
        status_body = await _json(status)
        result.record(
            "pos retrieve final state",
            status.status_code == 200 and status_body.get("reference") == reference,
            f"status={status_body.get('status')}",
        )

        deliveries = await client.get(
            f"{API_BASE}/integrations/clients/{client_id}/deliveries",
            headers=headers,
        )
        rows = await _json(deliveries)
        event_ids = [row.get("public_event_id") for row in rows] if isinstance(rows, list) else []
        result.record(
            "outbound webhook events queued",
            deliveries.status_code == 200 and len(event_ids) >= 1,
            f"count={len(event_ids)}",
        )
        unique_ids = set(event_ids)
        result.record(
            "duplicate webhook identity unique",
            len(event_ids) == len(unique_ids),
            f"events={len(event_ids)} unique={len(unique_ids)}",
        )

        await client.post(f"{API_BASE}/integrations/clients/{client_id}/revoke", headers=headers)
        dead = await client.get(
            f"{API_BASE}/integrations/payments/{reference}", headers=api_headers
        )
        result.record(
            "revoked api key rejected",
            dead.status_code == 401
            and _code(await _json(dead)) in {"api_key_revoked", "api_key_inactive", "invalid_api_key"},
            f"http_{dead.status_code} code={_code(await _json(dead))}",
        )

        invalid = await client.get(
            f"{API_BASE}/integrations/payments/{reference}",
            headers={"X-API-Key": "not-a-key"},
        )
        result.record(
            "invalid api key rejected",
            invalid.status_code == 401 and _code(await _json(invalid)) == "invalid_api_key",
            f"http_{invalid.status_code}",
        )

    failed = sum(1 for _, ok, _ in result.checks if not ok)
    print(f"summary passed={len(result.checks) - failed}/{len(result.checks)} base={API_BASE}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
