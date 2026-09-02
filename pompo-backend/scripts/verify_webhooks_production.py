#!/usr/bin/env python3
"""Production webhook verification for M010."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid

try:
    import httpx
except ImportError:
    print("ERROR: httpx required")
    raise SystemExit(1)

from app.payments.webhooks import compute_mock_signature


async def main() -> int:
    parser = argparse.ArgumentParser(description="Verify M010 webhooks in production")
    parser.add_argument(
        "--api-base",
        default="https://pompo-api-production.up.railway.app/api/v1",
        help="Production API base URL",
    )
    parser.add_argument(
        "--webhook-secret",
        required=True,
        help="Simulated provider webhook signing secret value",
    )
    parser.add_argument(
        "--admin-token",
        help="Optional bearer token for admin webhook list verification",
    )
    args = parser.parse_args()
    base = args.api_base.rstrip("/")
    failures = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        health = await client.get(f"{base}/health")
        print("health", health.status_code, health.text[:200])
        if health.status_code != 200:
            failures += 1

        bad = await client.post(
            f"{base}/webhooks/simulated",
            content=b"{}",
            headers={"Content-Type": "application/json"},
        )
        print("invalid_signature", bad.status_code, bad.text[:200])
        if bad.status_code != 401:
            failures += 1

        event_id = f"prod-verify-{uuid.uuid4().hex[:12]}"
        payload = {
            "event_id": event_id,
            "event_type": "payment.success",
            "event_version": "1",
            "payment_reference": "PMP-NONEXISTENT",
            "outcome": "success",
        }
        body = json.dumps(payload).encode()
        timestamp = str(int(time.time()))
        signature = compute_mock_signature(args.webhook_secret, timestamp, body)
        headers = {
            "Content-Type": "application/json",
            "X-Pompo-Signature": signature,
            "X-Pompo-Timestamp": timestamp,
        }
        accepted = await client.post(f"{base}/webhooks/simulated", content=body, headers=headers)
        print("accepted_or_rejected", accepted.status_code, accepted.text[:200])
        if accepted.status_code not in {200, 422}:
            failures += 1

        duplicate = await client.post(f"{base}/webhooks/simulated", content=body, headers=headers)
        print("duplicate", duplicate.status_code, duplicate.text[:200])
        if duplicate.status_code != 200 or duplicate.json().get("duplicate") is not True:
            failures += 1

        if args.admin_token:
            listed = await client.get(
                f"{base}/webhooks",
                headers={"Authorization": f"Bearer {args.admin_token}"},
            )
            print("admin_list", listed.status_code, listed.text[:200])
            if listed.status_code != 200:
                failures += 1

    print("failures", failures)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
