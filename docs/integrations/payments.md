# Payments, dynamic QR, and idempotency

Reuse `PaymentService` and M009 QR. Do not sign QR payloads in the POS layer.

## Create payment (optional dynamic QR)

```bash
curl -sS -X POST "$API/integrations/payments" \
  -H "X-API-Key: $POMPO_API_KEY" \
  -H "Idempotency-Key: order-123" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "250.00",
    "currency": "MWK",
    "payment_method": "mobile_money",
    "idempotency_key": "order-123",
    "generate_qr": true
  }'
```

Response includes `reference`, `status`, `amount`, `currency`, timestamps, and
when requested a `qr` object: `public_identifier`, `encoded_payload`, `qr_type`,
`status`, `expires_at`.

Customer scan uses the existing mobile contract (`GET /qr/{id}`,
`POST /payments/from-qr`). Simulated provider completes the payment in sandbox.

## Status

```bash
curl -sS "$API/integrations/payments/$REFERENCE" \
  -H "X-API-Key: $POMPO_API_KEY"
```

Cross-merchant lookups return `404 payment_not_found`.

## Idempotency

PostgreSQL unique `(merchant_id, idempotency_key)` is authoritative.

| Same client + same key + same body | Same payment |
| Same client + same key + different body | `409 idempotency_conflict` |
| Same client + different key | New payment |
| Concurrent identical requests | One financial row |
