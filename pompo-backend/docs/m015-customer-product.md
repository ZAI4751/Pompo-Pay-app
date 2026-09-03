# M015 Customer Product & Everyday Utility

POMPO remains a payment gateway. This milestone adds convenience around
merchant payments. It does **not** introduce wallets, stored customer
currency, top-ups, or a second payment engine.

## Product identity

A payment request is an instruction to pay a **merchant till**. Fulfillment
creates a new `Transaction` through `PaymentService → ProviderRegistry →
ProviderAdapter`. POMPO never holds the money.

## Phone verification (external dependency)

Customer self-registration uses the existing email/password JWT session.

`POST /customers/register` returns `phone_verification: "not_configured"`.

SMS OTP is **not implemented**. There is no SMS provider, no OTP table, and
no verification endpoint. Phone uniqueness is enforced when a phone is
supplied (`uq_users_phone_active`). Do not treat a stored phone as verified.

To add SMS later: keep the same registration contract, add an OTP issuer
behind configuration, and change `phone_verification` only when a real
provider is wired.

## Selected features

- Customer self-registration, login, logout, change password, logout-all
- Recent / favourite merchants from real successful payments
- Pay Again: new payment, never a copy of the old transaction
- Payment requests and bill splits as merchant-payment instructions
- Payment receipts labelled PAYMENT RECEIPT, not tax invoices
- In-app notifications (Celery delivery mark; no push vendor)
- Backend history search/filters
- Lightweight support requests (not a ticketing platform)
- Customer payment insights from completed transactions only
- Merchant daily success summary and activity search
- Offline-safe cached history view; payment initiation stays online

## Intentionally deferred

- Customer-to-customer P2P money movement (no customer wallet destination)
- Recurring payment requests, school-fee products, rent products
- Spending categories (the payment model has no reliable category field)
- Push / APNs / FCM
- SMS / WhatsApp delivery
- Full support ticketing / CRM
- Offline queued payments
- TNM, bank rails, POS expansion, major mobile visual redesign

## Architecture reuse

Registration uses `AuthService` session issuance.
Repeat pay and request pay use `PaymentService.create_payment`.
QR inspect/pay paths are unchanged.
Notification rows use a unique `event_key` for delivery idempotency.
Financial uniqueness remains PostgreSQL idempotency keys on payments.

## Authorization

Customer-owned rows are scoped to the authenticated user: payments they
initiated, their favorites, their requests, their notifications, their
support tickets. Public payment-request inspect is limited to safe
destination/amount/status fields. Cross-user mutation returns 403.
