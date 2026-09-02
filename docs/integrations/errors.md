# Integration error contract

```json
{ "detail": "Invalid API key", "code": "invalid_api_key", "request_id": "…" }
```

No stack traces or database details.

| Code | HTTP |
|------|------|
| `invalid_api_key` | 401 |
| `revoked_api_key` | 401 |
| `expired_api_key` | 401 |
| `api_key_inactive` | 401 |
| `insufficient_scope` | 403 |
| `invalid_merchant_context` | 422 |
| `invalid_branch_context` | 422 |
| `invalid_till_context` | 422 |
| `idempotency_conflict` | 409 |
| `payment_not_found` | 404 |
| `rate_limited` | 429 |
| `invalid_amount` | 422 |
| `unsupported_currency` | 422 |
| `invalid_request` | 422 |

Rate-limit responses include `Retry-After` and `X-RateLimit-*`. Invalid keys are
throttled per IP. Valid clients may also have a per-client `rate_limit_requests`.
