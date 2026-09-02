# Authentication, API keys, and scopes

POS software authenticates as a machine client. Do not log in as a human user.

## API key

Format: `pompo_test_<hex>` (sandbox) or `pompo_live_<hex>` (live).

```http
POST /api/v1/integrations/payments
X-API-Key: pompo_test_…
```

Bearer tokens that start with `pompo_` are also accepted.

- The secret is shown **once** at create or rotate.
- POMPO stores only HMAC-SHA256(`SECRET_KEY`, raw key).
- Prefix (16 characters) is kept for operations.
- Optional `key_expires_at` on create, or `expires_at` on rotate.
- Revoke a key or disable/revoke the client to stop access immediately.

Never log or persist the full key. List and GET responses return prefixes only.

## Scopes

| Scope | Purpose |
|-------|---------|
| `payments:create` | Create payments |
| `payments:read` | Read payment status |
| `qr:create` | Create dynamic QR |
| `qr:read` | Read QR context |
| `transactions:read` | Alias of `payments:read` |
| `webhooks:read` | Read this client's outbound deliveries |

Never granted: `providers:manage`, `rbac:manage`, `settlements:manage`,
`reconciliation:manage`.

Human admins use RBAC `api_keys:read|create|revoke`.

## Merchant / branch / till

`merchant_pos` clients must be bound to merchant → branch → till. The server
derives that context from the client. Submitted `merchant_id` / `branch_id` /
`till_id` are consistency checks only.

A POS bound to Till 7 cannot create a payment on Till 999.

## Sandbox vs live

`environment=sandbox` issues `pompo_test_` keys. Production (`APP_ENV=production`)
requires HTTPS webhook destinations.
