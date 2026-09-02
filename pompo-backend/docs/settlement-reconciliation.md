# M011 — Settlement and Reconciliation

PAYMENT, webhook, settlement, and reconciliation are related but distinct.

```text
Payment (expected POMPO outcome)
    ≠
Webhook (asynchronous provider notification)
    ≠
Settlement (what the provider reports as financially settled)
    ≠
Reconciliation (comparison of expected vs actual)
```

PostgreSQL is the financial source of truth. Settlement ingestion never
mutates payment history. Discrepancies are preserved as reconciliation
records.

## Identity

- Settlement uniqueness: `(provider_id, provider_settlement_reference)`
- Batch uniqueness: `(provider_id, external_batch_reference)`
- One reconciliation record per settlement
- Duplicate ingestion returns the existing batch/record with no second
  financial effect

## Matching (never fuzzy)

1. Exact POMPO payment reference
2. Exact provider transaction reference on `PaymentAttempt`
3. Explicit settlement→transaction link
4. Otherwise `UNMATCHED` or `INVESTIGATION`

## Fees

`pricing_schedules` is a small forward-compatible structure (zero / fixed /
percentage, optional min/max, provider-specific and merchant-specific
rows). There is no hardcoded platform percentage.

```text
merchant net = gross − provider cost − POMPO fee
```

## Manual resolution

`POST /api/v1/reconciliation/{id}/resolve` records an auditable resolution
note and marks the comparison `resolved`. It does **not** rewrite
settlement amounts or payment rows. A later reconciliation run attaches the
existing missing-settlement record to the new run but will not revert a
resolved status.

Append-only financial adjustments (GL-style correction records) are
deferred until a later milestone. Operators must not delete settlement or
reconciliation rows to “fix” a mismatch.

Reconciliation runs and settlement batches are platform-admin operational
tools because a provider file can contain multiple merchants. Merchant users
can inspect their own settlement and reconciliation rows; they cannot read
another merchant’s financial rows or provider-wide batch/run aggregates.

## Simulated provider

The simulated adapter accepts a deterministic JSON settlement batch for
tests and sandbox operations. It is not a real Airtel/TNM/bank settlement
file.
