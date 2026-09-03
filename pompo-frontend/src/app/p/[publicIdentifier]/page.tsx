"use client";

import { use, useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  CreditCard,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  WifiOff,
} from "lucide-react";
import { CheckoutShell, CheckoutStatusCard } from "@/components/checkout/CheckoutShell";
import { qrService } from "@/lib/api/services/qr";
import { paymentsService } from "@/lib/api/services/payments";
import { instrumentsService, type PaymentMethodCatalogItem } from "@/lib/api/services/instruments";
import { authService } from "@/lib/api/services/auth";
import { setAccessToken } from "@/lib/api/session";
import { useAuth } from "@/lib/auth/AuthContext";
import type { QRInspect } from "@/lib/types/qr";
import type { Payment } from "@/lib/types/payment";
import type { AuthenticatedUser } from "@/lib/types/auth";
import {
  type CheckoutPhase,
  catalogMethodPresentation,
  checkoutPhaseFromPayment,
  formatMoney,
  formatReceiptTimestamp,
  humanizeCustomerError,
  isTerminalPaymentStatus,
  paymentCtaLabel,
  sanitizeAmountInput,
  shouldShowAppInvitation,
  validateStaticAmount,
} from "@/lib/checkout/publicCheckout";

interface PageProps {
  params: Promise<{ publicIdentifier: string }>;
}

const FALLBACK_PAY = "Payment could not be completed. Please try again.";
const FALLBACK_NETWORK = "Could not reach POMPO. Check your connection and try again.";

export default function PublicWebCheckoutPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const rawPublicId = resolvedParams.publicIdentifier;
  const publicId = rawPublicId.replace(/^.*\/p\//, "").replace(/[/?#].*$/, "").toUpperCase();

  const { user } = useAuth();
  const [authCustomer, setAuthCustomer] = useState<AuthenticatedUser | null>(null);
  const effectiveUser = user || authCustomer;

  const [phase, setPhase] = useState<CheckoutPhase>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [qr, setQr] = useState<QRInspect | null>(null);
  const [catalog, setCatalog] = useState<PaymentMethodCatalogItem[]>([]);
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethodCatalogItem | null>(null);

  const [amountInput, setAmountInput] = useState("");
  const [phoneInput, setPhoneInput] = useState("");
  const [amountError, setAmountError] = useState("");

  const [authMode, setAuthMode] = useState<"register" | "login">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authPhone, setAuthPhone] = useState("");
  const [authError, setAuthError] = useState("");
  const [authSubmitting, setAuthSubmitting] = useState(false);
  const [authNotice, setAuthNotice] = useState("");

  const [paymentResult, setPaymentResult] = useState<Payment | null>(null);
  const [submittingPayment, setSubmittingPayment] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function init() {
      try {
        const qrRes = await qrService.inspect(publicId, true);
        if (!active) return;

        if (qrRes.status === "error") {
          if (qrRes.kind === "not_found") {
            setPhase("not_found");
            return;
          }
          if (qrRes.kind === "network") {
            setPhase("network_error");
            setErrorMessage(humanizeCustomerError(qrRes.message, FALLBACK_NETWORK));
            return;
          }
          const msg = (qrRes.message || "").toLowerCase();
          if (msg.includes("expired")) {
            setPhase("expired");
            return;
          }
          if (msg.includes("revoked")) {
            setPhase("revoked");
            return;
          }
          if (msg.includes("already been used") || msg.includes("consumed") || qrRes.kind === "conflict") {
            setPhase("consumed");
            return;
          }
          setPhase("failure");
          setErrorMessage(humanizeCustomerError(qrRes.message, FALLBACK_PAY));
          return;
        }

        const qrData = qrRes.data;
        setQr(qrData);

        if (qrData.status === "expired") {
          setPhase("expired");
          return;
        }
        if (qrData.status === "revoked") {
          setPhase("revoked");
          return;
        }
        if (qrData.status === "consumed") {
          setPhase("consumed");
          return;
        }
        if (qrData.status !== "active") {
          setPhase("failure");
          setErrorMessage("This QR code cannot accept payments right now.");
          return;
        }

        if (qrData.qr_type === "dynamic" && qrData.amount) {
          setAmountInput(qrData.amount);
        }

        const catRes = await instrumentsService.catalog();
        if (!active) return;
        if (catRes.status === "success" && catRes.data) {
          setCatalog(catRes.data);
          const firstAvailable = catRes.data.find((method) => catalogMethodPresentation(method).selectable);
          if (firstAvailable) {
            setSelectedMethod(firstAvailable);
          }
        }

        setPhase("ready");
      } catch {
        if (!active) return;
        setPhase("network_error");
        setErrorMessage(FALLBACK_NETWORK);
      }
    }

    void init();
    return () => {
      active = false;
    };
  }, [publicId, refreshKey]);

  const handleRetry = () => {
    setPhase("loading");
    setErrorMessage("");
    setRefreshKey((key) => key + 1);
  };

  const displayedAmount = qr?.qr_type === "dynamic" ? qr.amount : amountInput || null;
  const displayedCurrency = qr?.currency || "MWK";

  const executePayment = async () => {
    if (!qr) return;

    if (qr.qr_type === "static") {
      const invalid = validateStaticAmount(amountInput);
      if (invalid) {
        setAmountError(invalid);
        return;
      }
    }

    if (!selectedMethod || !catalogMethodPresentation(selectedMethod).selectable) {
      setErrorMessage("Choose an available payment method.");
      setPhase("unsupported_method");
      return;
    }

    setSubmittingPayment(true);
    setPhase("processing");
    setErrorMessage("");

    try {
      const idempotencyKey = `webpay-${crypto.randomUUID()}`;
      const payload = {
        public_identifier: qr.public_identifier,
        idempotency_key: idempotencyKey,
        amount: qr.qr_type === "static" ? Number(amountInput).toFixed(2) : undefined,
        payment_method: selectedMethod.instrument_type,
        provider_code: selectedMethod.provider_code,
        customer_phone: phoneInput.trim() || undefined,
        description: `Web QR payment to ${qr.merchant_name}`,
      };

      const initiateRes = await qrService.payFromQR(payload);
      if (initiateRes.status === "error") {
        setSubmittingPayment(false);
        setErrorMessage(humanizeCustomerError(initiateRes.message, FALLBACK_PAY));
        setPhase("failure");
        return;
      }

      let currentPayment = initiateRes.data;
      setPaymentResult(currentPayment);

      if (!isTerminalPaymentStatus(currentPayment.status)) {
        const processRes = await paymentsService.process(currentPayment.reference);
        if (processRes.status === "success") {
          currentPayment = processRes.data;
          setPaymentResult(currentPayment);
        } else {
          setSubmittingPayment(false);
          setErrorMessage(humanizeCustomerError(processRes.message, FALLBACK_PAY));
          setPhase("failure");
          return;
        }
      }

      if (!isTerminalPaymentStatus(currentPayment.status)) {
        for (let attempt = 0; attempt < 8; attempt += 1) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          const pollRes = await paymentsService.getByReference(currentPayment.reference);
          if (pollRes.status === "success") {
            currentPayment = pollRes.data;
            setPaymentResult(currentPayment);
            if (isTerminalPaymentStatus(currentPayment.status)) {
              break;
            }
          }
        }
      }

      setSubmittingPayment(false);
      const nextPhase = checkoutPhaseFromPayment(currentPayment.status);
      if (nextPhase === "failure") {
        setErrorMessage(
          humanizeCustomerError(currentPayment.failure_reason, "Payment could not be completed. Please try again."),
        );
      }
      setPhase(nextPhase);
    } catch {
      setSubmittingPayment(false);
      setErrorMessage(FALLBACK_NETWORK);
      setPhase("network_error");
    }
  };

  const handleProceedClick = () => {
    if (qr?.qr_type === "static") {
      const invalid = validateStaticAmount(amountInput);
      if (invalid) {
        setAmountError(invalid);
        return;
      }
    }
    if (!effectiveUser) {
      setAuthError("");
      setAuthNotice("");
      setPhase("auth_required");
      return;
    }
    void executePayment();
  };

  const applyAuthenticatedUser = async (accessToken: string) => {
    setAccessToken(accessToken);
    const meRes = await authService.me(accessToken);
    if (meRes.status === "success") {
      setAuthCustomer(meRes.data);
      if (meRes.data.is_email_verified === false) {
        setPhase("verify_email");
        return false;
      }
    }
    return true;
  };

  const handleAuthSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthError("");
    setAuthSubmitting(true);

    try {
      if (authMode === "register") {
        if (!authName.trim()) {
          setAuthError("Enter your full name.");
          setAuthSubmitting(false);
          return;
        }
        if (!authPhone.trim()) {
          setAuthError("Enter your phone number.");
          setAuthSubmitting(false);
          return;
        }
        const res = await authService.registerCustomer({
          full_name: authName.trim(),
          phone: authPhone.trim(),
          email: authEmail.trim(),
          password: authPassword,
        });

        if (res.status === "success") {
          const canPay = await applyAuthenticatedUser(res.data.access_token);
          if (canPay) {
            setPhase("ready");
            setTimeout(() => {
              void executePayment();
            }, 100);
          }
        } else {
          setAuthError(humanizeCustomerError(res.message, "Could not create your account. Please try again."));
        }
      } else {
        const res = await authService.login({
          email: authEmail.trim(),
          password: authPassword,
        });

        if (res.status === "success") {
          const canPay = await applyAuthenticatedUser(res.data.access_token);
          if (canPay) {
            setPhase("ready");
            setTimeout(() => {
              void executePayment();
            }, 100);
          }
        } else {
          setAuthError(humanizeCustomerError(res.message, "Could not sign in. Check your email and password."));
        }
      }
    } catch {
      setAuthError("Could not reach POMPO. Please try again.");
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleForgotPassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthError("");
    setAuthNotice("");
    setAuthSubmitting(true);
    try {
      const res = await authService.forgotPassword(authEmail.trim());
      if (res.status === "success") {
        setAuthNotice(
          humanizeCustomerError(
            res.data.detail,
            "If an account matches that email, password reset instructions have been sent.",
          ),
        );
      } else {
        setAuthError(humanizeCustomerError(res.message, "Could not request a password reset."));
      }
    } catch {
      setAuthError(FALLBACK_NETWORK);
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleRequestVerification = async () => {
    setAuthError("");
    setAuthNotice("");
    setAuthSubmitting(true);
    try {
      const res = await authService.requestEmailVerification(effectiveUser?.email || authEmail.trim());
      if (res.status === "success") {
        setAuthNotice(
          humanizeCustomerError(
            res.data.detail,
            "If an unverified account matches, verification instructions have been sent.",
          ),
        );
      } else {
        setAuthError(humanizeCustomerError(res.message, "Could not send verification instructions."));
      }
    } catch {
      setAuthError(FALLBACK_NETWORK);
    } finally {
      setAuthSubmitting(false);
    }
  };

  const selectedPresentation = selectedMethod ? catalogMethodPresentation(selectedMethod) : null;

  return (
    <CheckoutShell>
      {phase === "loading" && (
        <CheckoutStatusCard
          tone="neutral"
          icon={<div className="h-7 w-7 rounded-full border-2 border-primary border-t-transparent animate-spin" />}
          title="Finding this payment"
        >
          <p>Loading merchant and amount…</p>
        </CheckoutStatusCard>
      )}

      {phase === "expired" && (
        <CheckoutStatusCard tone="warning" icon={<Clock className="h-7 w-7 text-warning" />} title="This QR has expired">
          <p>
            Ask {qr?.merchant_name || "the merchant"} for a new POMPO QR. Expired codes cannot be paid.
          </p>
          <RetryButton onClick={handleRetry} />
        </CheckoutStatusCard>
      )}

      {phase === "revoked" && (
        <CheckoutStatusCard
          tone="error"
          icon={<ShieldAlert className="h-7 w-7 text-error" />}
          title="This QR is no longer valid"
        >
          <p>{qr?.merchant_name || "The merchant"} revoked this code. It cannot accept payments.</p>
        </CheckoutStatusCard>
      )}

      {phase === "consumed" && (
        <CheckoutStatusCard
          tone="success"
          icon={<CheckCircle2 className="h-7 w-7 text-success" />}
          title="Already paid"
        >
          <p>This payment request has already been completed.</p>
          {qr?.payment_reference ? (
            <p className="mt-3 font-mono text-xs text-text">{qr.payment_reference}</p>
          ) : null}
        </CheckoutStatusCard>
      )}

      {phase === "not_found" && (
        <CheckoutStatusCard
          tone="neutral"
          icon={<AlertCircle className="h-7 w-7 text-text-subtle" />}
          title="Not a valid POMPO QR"
        >
          <p>Scan an official POMPO plate. This link is not a live payment request.</p>
        </CheckoutStatusCard>
      )}

      {phase === "network_error" && (
        <CheckoutStatusCard tone="error" icon={<WifiOff className="h-7 w-7 text-error" />} title="Connection problem">
          <p>{errorMessage || FALLBACK_NETWORK}</p>
          <RetryButton onClick={handleRetry} />
        </CheckoutStatusCard>
      )}

      {phase === "unsupported_method" && (
        <CheckoutStatusCard
          tone="warning"
          icon={<CreditCard className="h-7 w-7 text-warning" />}
          title="That payment method is not available"
        >
          <p>{errorMessage || "Choose a method POMPO can complete for this merchant."}</p>
          <button
            type="button"
            onClick={() => setPhase("ready")}
            className="mt-5 w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground"
          >
            Choose another method
          </button>
        </CheckoutStatusCard>
      )}

      {phase === "processing" && (
        <CheckoutStatusCard
          tone="info"
          icon={<div className="h-7 w-7 rounded-full border-2 border-primary border-t-transparent animate-spin" />}
          title="Processing payment"
        >
          <p>Confirming with {selectedMethod?.label || "your payment method"}…</p>
          <p className="mt-3 text-xs text-text-subtle">Keep this page open.</p>
        </CheckoutStatusCard>
      )}

      {phase === "pending" && (
        <CheckoutStatusCard tone="info" icon={<Clock className="h-7 w-7 text-info" />} title="Payment is still processing">
          <p>POMPO has not received a final result yet. This is not a failure.</p>
          {paymentResult?.reference ? (
            <p className="mt-3 font-mono text-xs text-text">{paymentResult.reference}</p>
          ) : null}
          <button
            type="button"
            onClick={() => {
              if (!paymentResult?.reference) return;
              setPhase("processing");
              void paymentsService.getByReference(paymentResult.reference).then((res) => {
                if (res.status === "success") {
                  setPaymentResult(res.data);
                  const next = checkoutPhaseFromPayment(res.data.status);
                  if (next === "failure") {
                    setErrorMessage(
                      humanizeCustomerError(res.data.failure_reason, FALLBACK_PAY),
                    );
                  }
                  setPhase(next);
                } else {
                  setPhase("pending");
                }
              });
            }}
            className="mt-5 w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground"
          >
            Check status
          </button>
        </CheckoutStatusCard>
      )}

      {phase === "success" && (
        <section className="card-depth my-auto rounded-2xl border border-success/30 bg-surface p-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success-bg text-success">
            <CheckCircle2 className="h-9 w-9" />
          </div>
          <h1 className="mt-4 text-center text-2xl font-semibold tracking-tight text-text">Payment successful</h1>
          <p className="mt-1 text-center text-sm text-success">The merchant can see this payment.</p>

          <dl className="mt-6 space-y-3 rounded-xl bg-surface-inset px-4 py-4 text-sm">
            <ReceiptRow label="Merchant" value={paymentResult?.merchant_name || qr?.merchant_name} />
            <ReceiptRow
              label="Amount"
              value={formatMoney(paymentResult?.amount || displayedAmount, paymentResult?.currency || displayedCurrency)}
            />
            {formatReceiptTimestamp(paymentResult?.completed_at || paymentResult?.created_at) ? (
              <ReceiptRow
                label="Date"
                value={formatReceiptTimestamp(paymentResult?.completed_at || paymentResult?.created_at) ?? undefined}
              />
            ) : null}
            {paymentResult?.reference ? <ReceiptRow label="Reference" value={paymentResult.reference} mono /> : null}
            {paymentResult?.status ? <ReceiptRow label="Status" value={paymentResult.status} /> : null}
            {selectedMethod?.label ? <ReceiptRow label="Method" value={selectedMethod.label} /> : null}
          </dl>

          {shouldShowAppInvitation(phase) ? (
            <p className="mt-6 text-center text-xs leading-relaxed text-text-subtle">
              Get the POMPO app for faster payments next time. Installation is optional.
            </p>
          ) : null}
        </section>
      )}

      {phase === "failure" && (
        <CheckoutStatusCard tone="error" icon={<AlertCircle className="h-7 w-7 text-error" />} title="Payment could not be completed">
          <p>{errorMessage || "Please try again."}</p>
          <button
            type="button"
            onClick={() => {
              setErrorMessage("");
              setPhase("ready");
            }}
            className="mt-5 w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground"
          >
            Try again
          </button>
        </CheckoutStatusCard>
      )}

      {phase === "ready" && qr && (
        <div className="flex flex-1 flex-col">
          <p className="text-[11px] font-semibold uppercase tracking-brand text-text-subtle">You&apos;re paying</p>
          <h1 className="mt-1 text-[1.65rem] font-semibold leading-tight tracking-tight text-text">
            {qr.merchant_name}
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            {qr.branch_name}
            {qr.till_name ? ` · ${qr.till_name}` : ""}
          </p>

          <section className="card-depth mt-5 rounded-2xl border border-border bg-surface px-4 py-5">
            {qr.qr_type === "dynamic" ? (
              <div>
                <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-brand text-text-subtle">
                  <span>Amount</span>
                  <span>Set by merchant</span>
                </div>
                <p className="mt-2 text-4xl font-semibold tabular-nums tracking-tight text-text">
                  {formatMoney(qr.amount, qr.currency)}
                </p>
              </div>
            ) : (
              <div>
                <label htmlFor="amount-input" className="text-[11px] font-semibold uppercase tracking-brand text-text-subtle">
                  Amount
                </label>
                <div className="relative mt-2">
                  <span className="pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 text-lg font-semibold text-text-muted">
                    {qr.currency}
                  </span>
                  <input
                    id="amount-input"
                    inputMode="decimal"
                    autoComplete="off"
                    enterKeyHint="done"
                    placeholder="0.00"
                    value={amountInput}
                    onChange={(event) => {
                      setAmountInput(sanitizeAmountInput(event.target.value));
                      if (amountError) setAmountError("");
                    }}
                    className={`w-full border-0 border-b bg-transparent py-2 pl-16 pr-2 text-4xl font-semibold tabular-nums tracking-tight text-text outline-none placeholder:text-text-subtle ${
                      amountError ? "border-error" : "border-border-strong focus:border-primary"
                    }`}
                  />
                </div>
                {amountError ? <p className="mt-2 text-xs font-medium text-error">{amountError}</p> : null}
              </div>
            )}
          </section>

          <section className="mt-5">
            <h2 className="text-[11px] font-semibold uppercase tracking-brand text-text-subtle">Payment method</h2>
            <div className="mt-2 space-y-2">
              {catalog.map((method) => {
                const presentation = catalogMethodPresentation(method);
                const isSelected =
                  selectedMethod?.provider_code === method.provider_code &&
                  selectedMethod?.instrument_type === method.instrument_type;
                return (
                  <button
                    key={`${method.provider_code}-${method.instrument_type}`}
                    type="button"
                    disabled={!presentation.selectable}
                    onClick={() => setSelectedMethod(method)}
                    className={`flex w-full items-center justify-between rounded-2xl border px-3.5 py-3 text-left ${
                      !presentation.selectable
                        ? "cursor-not-allowed border-border bg-surface-inset opacity-70"
                        : isSelected
                          ? "border-primary bg-primary-light"
                          : "border-border bg-surface"
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-surface-inset text-text-muted">
                        {method.instrument_type === "mobile_money" ? (
                          <Smartphone className="h-4 w-4" />
                        ) : (
                          <CreditCard className="h-4 w-4" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-text">{method.label}</p>
                        <p className="mt-0.5 text-[11px] uppercase tracking-wide text-text-subtle">
                          {presentation.badges.join(" · ")}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`h-4 w-4 shrink-0 rounded-full border ${
                        isSelected && presentation.selectable ? "border-primary bg-primary" : "border-border-strong"
                      }`}
                    />
                  </button>
                );
              })}
            </div>

            {selectedMethod?.instrument_type === "mobile_money" && selectedPresentation?.selectable ? (
              <label className="mt-3 block text-sm text-text-muted">
                Mobile money number <span className="text-text-subtle">(optional)</span>
                <input
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="0888 000 000"
                  value={phoneInput}
                  onChange={(event) => setPhoneInput(event.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
                />
              </label>
            ) : null}
          </section>

          {effectiveUser ? (
            <div className="mt-4 flex items-center gap-2 rounded-xl bg-success-bg px-3 py-2 text-xs text-success">
              <ShieldCheck className="h-4 w-4 shrink-0" />
              <span className="min-w-0 truncate">
                Paying as {effectiveUser.full_name || effectiveUser.email}
                {effectiveUser.is_email_verified === false ? " · verification recommended" : ""}
              </span>
            </div>
          ) : null}

          <div className="sticky bottom-0 mt-auto bg-gradient-to-t from-background via-background to-transparent pt-6">
            <button
              type="button"
              disabled={submittingPayment || !selectedPresentation?.selectable}
              onClick={handleProceedClick}
              className="w-full rounded-2xl bg-primary py-4 text-base font-semibold text-primary-foreground disabled:opacity-50"
            >
              {paymentCtaLabel({
                authenticated: Boolean(effectiveUser),
                currency: displayedCurrency,
                amount: displayedAmount,
                qrType: qr.qr_type,
              })}
            </button>
          </div>
        </div>
      )}

      {phase === "auth_required" && (
        <section className="card-depth my-auto rounded-2xl border border-border bg-surface p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-text">Sign in to pay</h2>
              <p className="mt-1 text-sm text-text-muted">Use your POMPO account. No new account system.</p>
            </div>
            <button type="button" onClick={() => setPhase("ready")} className="text-xs font-semibold text-text-muted">
              Back
            </button>
          </div>

          <div className="mt-4 grid grid-cols-2 rounded-xl bg-surface-inset p-1">
            <button
              type="button"
              onClick={() => setAuthMode("login")}
              className={`rounded-lg py-2 text-xs font-semibold ${authMode === "login" ? "bg-surface text-text" : "text-text-muted"}`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => setAuthMode("register")}
              className={`rounded-lg py-2 text-xs font-semibold ${authMode === "register" ? "bg-surface text-text" : "text-text-muted"}`}
            >
              Create account
            </button>
          </div>

          {authError ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{authError}</p> : null}

          <form onSubmit={handleAuthSubmit} className="mt-4 space-y-3">
            {authMode === "register" ? (
              <>
                <Field label="Full name" value={authName} onChange={setAuthName} autoComplete="name" />
                <Field label="Phone" value={authPhone} onChange={setAuthPhone} type="tel" autoComplete="tel" />
              </>
            ) : null}
            <Field label="Email" value={authEmail} onChange={setAuthEmail} type="email" autoComplete="email" />
            <Field
              label="Password"
              value={authPassword}
              onChange={setAuthPassword}
              type="password"
              autoComplete={authMode === "login" ? "current-password" : "new-password"}
            />
            {authMode === "login" ? (
              <button
                type="button"
                onClick={() => {
                  setAuthError("");
                  setAuthNotice("");
                  setPhase("forgot_password");
                }}
                className="text-xs font-semibold text-primary"
              >
                Forgot password?
              </button>
            ) : null}
            <button
              type="submit"
              disabled={authSubmitting}
              className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              {authSubmitting ? "Please wait…" : authMode === "register" ? "Create account and continue" : "Sign in and continue"}
            </button>
          </form>
        </section>
      )}

      {phase === "forgot_password" && (
        <section className="card-depth my-auto rounded-2xl border border-border bg-surface p-5">
          <h2 className="text-lg font-semibold text-text">Reset password</h2>
          <p className="mt-1 text-sm text-text-muted">We will use the same POMPO account recovery as the app.</p>
          {authNotice ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-xs text-success">{authNotice}</p> : null}
          {authError ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{authError}</p> : null}
          <form onSubmit={handleForgotPassword} className="mt-4 space-y-3">
            <Field label="Email" value={authEmail} onChange={setAuthEmail} type="email" autoComplete="email" />
            <button
              type="submit"
              disabled={authSubmitting}
              className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
            >
              {authSubmitting ? "Please wait…" : "Send reset instructions"}
            </button>
          </form>
          <button type="button" onClick={() => setPhase("auth_required")} className="mt-3 w-full text-xs font-semibold text-text-muted">
            Back to sign in
          </button>
        </section>
      )}

      {phase === "verify_email" && (
        <section className="card-depth my-auto rounded-2xl border border-border bg-surface p-5 text-center">
          <ShieldCheck className="mx-auto h-8 w-8 text-primary" />
          <h2 className="mt-3 text-lg font-semibold text-text">Verify your email</h2>
          <p className="mt-2 text-sm text-text-muted">
            Your POMPO account is signed in. Email verification is still outstanding.
          </p>
          {authNotice ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-xs text-success">{authNotice}</p> : null}
          {authError ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{authError}</p> : null}
          <button
            type="button"
            disabled={authSubmitting}
            onClick={() => void handleRequestVerification()}
            className="mt-5 w-full rounded-xl border border-border py-3 text-sm font-semibold text-text disabled:opacity-50"
          >
            Send verification instructions
          </button>
          <button
            type="button"
            onClick={() => {
              setPhase("ready");
              setTimeout(() => {
                void executePayment();
              }, 100);
            }}
            className="mt-2 w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground"
          >
            Continue to payment
          </button>
        </section>
      )}
    </CheckoutShell>
  );
}

function ReceiptRow({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-text-subtle">{label}</dt>
      <dd className={`text-right font-medium text-text ${mono ? "break-all font-mono text-xs" : ""}`}>{value}</dd>
    </div>
  );
}

function RetryButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground"
    >
      <RefreshCw className="h-4 w-4" />
      Try again
    </button>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block text-xs font-medium text-text-muted">
      {label}
      <input
        type={type}
        required
        autoComplete={autoComplete}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
      />
    </label>
  );
}
