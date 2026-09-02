# POMPO Integrations

Machine clients (merchant POS, partners, developers) authenticate with API keys
and call the existing payment, QR, and webhook systems. This is not a second
payment engine.

| Topic | Document |
|-------|----------|
| API keys, scopes, merchant/till binding | [authentication.md](authentication.md) |
| Create payment, dynamic QR, status, idempotency | [payments.md](payments.md) |
| Outbound webhooks, signing, retries | [webhooks.md](webhooks.md) |
| Error codes | [errors.md](errors.md) |

Sandbox example: `pompo-backend/scripts/pos_simulator.py`.

Live verifier (never prints secrets): `pompo-backend/scripts/verify_m013_sandbox.py`.
