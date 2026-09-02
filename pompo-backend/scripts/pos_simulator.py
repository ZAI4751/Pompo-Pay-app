"""Sandbox POS client against live POMPO integration APIs.

Usage (after creating a client in Master Admin):

    python scripts/pos_simulator.py \
        --base-url http://localhost:8000/api/v1 \
        --api-key pompo_test_… \
        --webhook-secret whsec_…

This calls real endpoints. It does not invent a payment UI.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from urllib.request import Request, urlopen

from app.payments.webhooks import compute_mock_signature, constant_time_compare, validate_mock_timestamp


def _request(method: str, url: str, *, api_key: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request) as response:
        payload = json.loads(response.read().decode())
        return response.status, payload


def verify_webhook(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    if not validate_mock_timestamp(timestamp):
        return False
    expected = compute_mock_signature(secret, timestamp, body)
    return constant_time_compare(signature, expected)


def main() -> int:
    parser = argparse.ArgumentParser(description="POMPO POS sandbox client")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--webhook-secret", default="")
    parser.add_argument("--amount", default="100.00")
    args = parser.parse_args()
    if args.api_key.lower() in {"pompo_test_example", "changeme"}:
        print("Refusing placeholder API key", file=sys.stderr)
        return 2

    idempotency = f"pos-sim-{uuid.uuid4().hex}"
    status, created = _request(
        "POST",
        f"{args.base_url.rstrip('/')}/integrations/payments",
        api_key=args.api_key,
        body={
            "amount": args.amount,
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": idempotency,
            "generate_qr": True,
        },
    )
    print(f"create={status} reference={created.get('reference')} qr={created.get('qr', {}).get('public_identifier')}")
    replay_status, replay = _request(
        "POST",
        f"{args.base_url.rstrip('/')}/integrations/payments",
        api_key=args.api_key,
        body={
            "amount": args.amount,
            "currency": "MWK",
            "payment_method": "mobile_money",
            "idempotency_key": idempotency,
            "generate_qr": True,
        },
    )
    print(f"idempotent_replay={replay_status} same={replay.get('reference') == created.get('reference')}")
    reference = created["reference"]
    _, current = _request(
        "GET",
        f"{args.base_url.rstrip('/')}/integrations/payments/{reference}",
        api_key=args.api_key,
    )
    print(f"status={current.get('status')}")
    if args.webhook_secret:
        body = json.dumps({"event_id": "demo", "event_type": "payment.pending"}).encode()
        timestamp = str(int(time.time()))
        signature = compute_mock_signature(args.webhook_secret, timestamp, body)
        print(f"webhook_signature_ok={verify_webhook(args.webhook_secret, timestamp, body, signature)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
