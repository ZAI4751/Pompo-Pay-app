"use client";

import { use, useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  CreditCard,
  Lock,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Store,
  WifiOff,
} from "lucide-react";
import { qrService } from "@/lib/api/services/qr";
import { paymentsService } from "@/lib/api/services/payments";
import { instrumentsService, type PaymentMethodCatalogItem } from "@/lib/api/services/instruments";
import { authService } from "@/lib/api/services/auth";
import { setAccessToken } from "@/lib/api/session";
import { useAuth } from "@/lib/auth/AuthContext";
import type { QRInspect } from "@/lib/types/qr";
import type { Payment } from "@/lib/types/payment";
import type { AuthenticatedUser } from "@/lib/types/auth";

interface PageProps {
  params: Promise<{ publicIdentifier: string }>;
}

type CheckoutPhase =
  | "loading"
  | "ready"
  | "auth_required"
  | "processing"
  | "success"
  | "failure"
  | "expired"
  | "revoked"
  | "consumed"
  | "not_found"
  | "network_error";

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

  // Form inputs
  const [amountInput, setAmountInput] = useState("");
  const [phoneInput, setPhoneInput] = useState("");
  const [amountError, setAmountError] = useState("");

  // Inline auth state
  const [authMode, setAuthMode] = useState<"register" | "login">("register");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authPhone, setAuthPhone] = useState("");
  const [authError, setAuthError] = useState("");
  const [authSubmitting, setAuthSubmitting] = useState(false);

  // Payment result
  const [paymentResult, setPaymentResult] = useState<Payment | null>(null);
  const [submittingPayment, setSubmittingPayment] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function init() {
      try {
        // 1. Inspect QR (allow inactive so we can display exact expired/revoked/consumed status)
        const qrRes = await qrService.inspect(publicId, true);
        if (!active) return;

        if (qrRes.status === "error") {
          if (qrRes.kind === "not_found") {
            setPhase("not_found");
            return;
          }
          if (qrRes.kind === "network") {
            setPhase("network_error");
            setErrorMessage(qrRes.message);
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
          setErrorMessage(qrRes.message);
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
          setErrorMessage(`This QR code is currently ${qrData.status}.`);
          return;
        }

        if (qrData.qr_type === "dynamic" && qrData.amount) {
          setAmountInput(qrData.amount);
        }

        const catRes = await instrumentsService.catalog();
        if (!active) return;
        if (catRes.status === "success" && catRes.data) {
          setCatalog(catRes.data);
          const firstAvailable = catRes.data.find((m) => m.available);
          if (firstAvailable) {
            setSelectedMethod(firstAvailable);
          }
        }

        setPhase("ready");
      } catch {
        if (!active) return;
        setPhase("network_error");
        setErrorMessage("Could not connect to the POMPO payment network. Please check your connection.");
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
    setRefreshKey((k) => k + 1);
  };

  // Amount validation
  const validateAmount = (val: string): boolean => {
    setAmountError("");
    const cleaned = val.trim();
    if (!cleaned) {
      setAmountError("Amount is required.");
      return false;
    }
    const num = Number(cleaned);
    if (isNaN(num) || num <= 0) {
      setAmountError("Please enter a valid amount greater than 0.");
      return false;
    }
    if (num < 1) {
      setAmountError("Minimum payment is MWK 1.00.");
      return false;
    }
    if (num > 50000000) {
      setAmountError("Amount exceeds maximum limit of MWK 50,000,000.");
      return false;
    }
    return true;
  };

  // Payment execution
  const executePayment = async () => {
    if (!qr) return;

    // Validate amount for static QR
    if (qr.qr_type === "static") {
      if (!validateAmount(amountInput)) {
        return;
      }
    }

    if (!selectedMethod) {
      setErrorMessage("Please select an available payment method.");
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

      // 1. Create payment from QR via backend
      const initiateRes = await qrService.payFromQR(payload);
      if (initiateRes.status === "error") {
        setSubmittingPayment(false);
        setErrorMessage(initiateRes.message);
        setPhase("failure");
        return;
      }

      let currentPayment = initiateRes.data;
      setPaymentResult(currentPayment);

      // 2. Real provider processing through backend
      const isTerminal = (st: string) => st === "success" || st === "failed" || st === "cancelled";

      if (!isTerminal(currentPayment.status)) {
        const processRes = await paymentsService.process(currentPayment.reference);
        if (processRes.status === "success") {
          currentPayment = processRes.data;
          setPaymentResult(currentPayment);
        } else {
          setSubmittingPayment(false);
          setErrorMessage(processRes.message);
          setPhase("failure");
          return;
        }
      }

      // 3. Poll until terminal state if pending (up to 8 attempts)
      if (!isTerminal(currentPayment.status)) {
        for (let i = 0; i < 8; i++) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          const pollRes = await paymentsService.getByReference(currentPayment.reference);
          if (pollRes.status === "success") {
            currentPayment = pollRes.data;
            setPaymentResult(currentPayment);
            if (isTerminal(currentPayment.status)) {
              break;
            }
          }
        }
      }

      setSubmittingPayment(false);

      if (currentPayment.status === "success") {
        setPhase("success");
      } else {
        setErrorMessage(currentPayment.failure_reason || `Payment finished with status: ${currentPayment.status}`);
        setPhase("failure");
      }
    } catch {
      setSubmittingPayment(false);
      setErrorMessage("An unexpected network error occurred while processing the payment.");
      setPhase("failure");
    }
  };

  // Continue to Pay button action
  const handleProceedClick = () => {
    if (qr?.qr_type === "static" && !validateAmount(amountInput)) {
      return;
    }
    // Check if customer is authenticated
    if (!effectiveUser) {
      setAuthError("");
      setPhase("auth_required");
      return;
    }
    void executePayment();
  };

  // Inline Auth Handler
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError("");
    setAuthSubmitting(true);

    try {
      if (authMode === "register") {
        if (!authName.trim()) {
          setAuthError("Full name is required.");
          setAuthSubmitting(false);
          return;
        }
        if (!authPhone.trim()) {
          setAuthError("Phone number is required.");
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
          setAccessToken(res.data.access_token);
          const meRes = await authService.me(res.data.access_token);
          if (meRes.status === "success") {
            setAuthCustomer(meRes.data);
          }
          setPhase("ready");
          setTimeout(() => {
            void executePayment();
          }, 100);
        } else {
          setAuthError(res.message);
        }
      } else {
        // Login mode
        const res = await authService.login({
          email: authEmail.trim(),
          password: authPassword,
        });

        if (res.status === "success") {
          setAccessToken(res.data.access_token);
          const meRes = await authService.me(res.data.access_token);
          if (meRes.status === "success") {
            setAuthCustomer(meRes.data);
          }
          setPhase("ready");
          setTimeout(() => {
            void executePayment();
          }, 100);
        } else {
          setAuthError(res.message);
        }
      }
    } catch {
      setAuthError("Authentication service error. Please try again.");
    } finally {
      setAuthSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070d18] text-[#f8fafc] flex flex-col justify-between selection:bg-blue-500/30">
      {/* Top Header */}
      <header className="border-b border-white/10 bg-[#0b1324]/80 backdrop-blur-md sticky top-0 z-30 px-4 py-3 sm:px-6">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 font-black text-white text-base tracking-wider">
              P
            </div>
            <span className="font-extrabold tracking-tight text-lg text-white">POMPO</span>
            <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Web Pay
            </span>
          </div>

          <div className="flex items-center gap-1 text-xs text-slate-400">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>256-bit Secure</span>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-md w-full mx-auto p-4 sm:p-6 flex flex-col justify-center">
        {/* State: Loading */}
        {phase === "loading" && (
          <div className="rounded-2xl border border-white/10 bg-[#0f192e]/90 p-8 text-center backdrop-blur-xl shadow-2xl">
            <div className="w-12 h-12 rounded-full border-2 border-blue-500 border-t-transparent animate-spin mx-auto mb-4" />
            <h2 className="text-lg font-bold text-white">Resolving POMPO QR</h2>
            <p className="text-sm text-slate-400 mt-1">Connecting to payment gateway…</p>
          </div>
        )}

        {/* State: Expired */}
        {phase === "expired" && (
          <div className="rounded-2xl border border-amber-500/30 bg-[#14151b] p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mx-auto mb-4">
              <Clock className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">QR Code Expired</h2>
            <p className="text-sm text-slate-400 mt-2">
              This dynamic payment request has expired for your security. Please ask{" "}
              <strong className="text-slate-200">{qr?.merchant_name || "the merchant"}</strong> to generate a fresh QR code.
            </p>
            <div className="mt-6">
              <button
                type="button"
                onClick={handleRetry}
                className="w-full py-3 px-4 rounded-xl font-semibold bg-white/10 hover:bg-white/15 text-white transition-colors flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Check Again
              </button>
            </div>
          </div>
        )}

        {/* State: Revoked */}
        {phase === "revoked" && (
          <div className="rounded-2xl border border-red-500/30 bg-[#161214] p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mx-auto mb-4">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">QR Code Revoked</h2>
            <p className="text-sm text-slate-400 mt-2">
              This QR code was revoked by {qr?.merchant_name || "the merchant"} and cannot accept payments.
            </p>
          </div>
        )}

        {/* State: Consumed / Already Used */}
        {phase === "consumed" && (
          <div className="rounded-2xl border border-emerald-500/30 bg-[#0f191b] p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">Already Paid</h2>
            <p className="text-sm text-slate-400 mt-2">
              This dynamic payment request has already been completed. Dynamic QR codes cannot be paid more than once.
            </p>
            {qr?.payment_reference && (
              <div className="mt-4 p-3 rounded-lg bg-black/40 border border-white/5 text-xs font-mono text-slate-300">
                Ref: {qr.payment_reference}
              </div>
            )}
          </div>
        )}

        {/* State: Not Found / Invalid */}
        {phase === "not_found" && (
          <div className="rounded-2xl border border-white/10 bg-[#0f192e] p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">QR Code Not Found</h2>
            <p className="text-sm text-slate-400 mt-2">
              The identifier <code className="text-blue-400">{publicId}</code> is not a valid POMPO QR code. Please check that you scanned an official POMPO QR plate.
            </p>
          </div>
        )}

        {/* State: Network Error */}
        {phase === "network_error" && (
          <div className="rounded-2xl border border-rose-500/20 bg-[#161218] p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto mb-4">
              <WifiOff className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">Network Connection Error</h2>
            <p className="text-sm text-slate-400 mt-2">
              {errorMessage || "Unable to reach the POMPO backend. Please check your data connection and retry."}
            </p>
            <div className="mt-6">
              <button
                type="button"
                onClick={handleRetry}
                className="w-full py-3 px-4 rounded-xl font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30"
              >
                <RefreshCw className="w-4 h-4" />
                Retry
              </button>
            </div>
          </div>
        )}

        {/* State: Processing */}
        {phase === "processing" && (
          <div className="rounded-2xl border border-blue-500/30 bg-[#0f192e] p-8 text-center shadow-2xl">
            <div className="w-14 h-14 rounded-full border-3 border-blue-500 border-t-transparent animate-spin mx-auto mb-5" />
            <h2 className="text-xl font-bold text-white">Processing Payment</h2>
            <p className="text-sm text-slate-300 mt-2">
              Authorizing transaction with {selectedMethod?.label || "payment provider"}…
            </p>
            <p className="text-xs text-slate-500 mt-4">Do not close or refresh this window.</p>
          </div>
        )}

        {/* State: Success */}
        {phase === "success" && (
          <div className="rounded-2xl border border-emerald-500/40 bg-[#0c1a17] p-6 text-center shadow-2xl">
            <div className="w-16 h-16 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <h2 className="text-2xl font-black text-white tracking-tight">Payment Successful!</h2>
            <p className="text-xs uppercase tracking-wider text-emerald-400 font-bold mt-1">Transaction Completed</p>

            {/* Receipt Summary */}
            <div className="mt-6 p-4 rounded-xl bg-black/40 border border-white/5 text-left space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Paid to</span>
                <span className="font-semibold text-white">{qr?.merchant_name}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Till / Branch</span>
                <span className="text-slate-300">{qr?.till_name} · {qr?.branch_name}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Amount</span>
                <span className="font-bold text-emerald-400 text-base">
                  MWK {paymentResult?.amount || amountInput}
                </span>
              </div>
              <div className="flex justify-between items-center text-sm border-t border-white/10 pt-3">
                <span className="text-slate-400">Reference</span>
                <span className="font-mono text-xs text-blue-300 font-semibold">
                  {paymentResult?.reference || qr?.payment_reference || "CONFIRMED"}
                </span>
              </div>
            </div>

            {/* Invitation to get POMPO App */}
            <div className="mt-6 p-4 rounded-xl bg-gradient-to-br from-blue-900/30 to-indigo-900/20 border border-blue-500/30 text-left">
              <div className="flex items-start gap-3">
                <Smartphone className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-white">Get the POMPO App</h4>
                  <p className="text-xs text-slate-300 mt-1">
                    Store receipts, view transaction history, and pay faster with 1-tap offline security.
                  </p>
                  <a
                    href={`pompo://customer`}
                    className="inline-flex items-center gap-1.5 mt-3 text-xs font-bold text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    Open POMPO App <ArrowRight className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* State: Failure */}
        {phase === "failure" && (
          <div className="rounded-2xl border border-red-500/30 bg-[#181114] p-6 text-center shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-bold text-white">Payment Failed</h2>
            <p className="text-sm text-slate-300 mt-2">
              {errorMessage || "The payment could not be processed. Your funds were not debited."}
            </p>
            <div className="mt-6 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => setPhase("ready")}
                className="w-full py-3 px-4 rounded-xl font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* State: Ready (Checkout Entry Point) */}
        {phase === "ready" && qr && (
          <div className="space-y-4">
            {/* Merchant Identity Card */}
            <div className="rounded-2xl border border-white/10 bg-[#0f192e]/90 p-5 backdrop-blur-xl shadow-xl">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
                  <Store className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Paying</p>
                  <h1 className="text-lg font-black text-white tracking-tight">{qr.merchant_name}</h1>
                  <p className="text-xs text-slate-400">{qr.branch_name} · {qr.till_name}</p>
                </div>
              </div>

              {/* Amount Display or Entry */}
              <div className="mt-5 pt-4 border-t border-white/10">
                {qr.qr_type === "dynamic" ? (
                  <div>
                    <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                      <span>Total Amount</span>
                      <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-semibold">
                        <Lock className="w-3 h-3" /> Fixed Request
                      </span>
                    </div>
                    <div className="text-3xl font-extrabold text-white tracking-tight">
                      <span className="text-lg text-blue-400 mr-1.5 font-bold">{qr.currency}</span>
                      {qr.amount ? Number(qr.amount).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
                    </div>
                  </div>
                ) : (
                  <div>
                    <label htmlFor="amount-input" className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-1.5">
                      Enter Amount (MWK)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 font-bold text-slate-400 text-sm">
                        MWK
                      </span>
                      <input
                        id="amount-input"
                        type="number"
                        step="0.01"
                        min="1"
                        placeholder="0.00"
                        value={amountInput}
                        onChange={(e) => {
                          setAmountInput(e.target.value);
                          if (amountError) setAmountError("");
                        }}
                        className={`w-full pl-16 pr-4 py-3 rounded-xl bg-black/40 border text-xl font-bold text-white focus:outline-none transition-colors ${
                          amountError ? "border-rose-500" : "border-white/15 focus:border-blue-500"
                        }`}
                      />
                    </div>
                    {amountError ? (
                      <p className="text-xs text-rose-400 font-medium mt-1.5">{amountError}</p>
                    ) : null}

                    {/* Quick Amount Pills */}
                    <div className="flex gap-2 mt-2.5">
                      {[500, 1000, 2500, 5000].map((quick) => (
                        <button
                          key={quick}
                          type="button"
                          onClick={() => {
                            setAmountInput(String(quick));
                            setAmountError("");
                          }}
                          className="flex-1 py-1 px-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-semibold text-slate-300 border border-white/5 transition-colors"
                        >
                          +{quick}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Payment Method Selection */}
            <div className="rounded-2xl border border-white/10 bg-[#0f192e]/90 p-5 backdrop-blur-xl shadow-xl">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center justify-between">
                <span>Select Payment Method</span>
                <span className="text-[10px] text-slate-400 font-normal">Backed by POMPO Core</span>
              </h3>

              <div className="space-y-2">
                {catalog.map((method) => {
                  const isSelected =
                    selectedMethod?.provider_code === method.provider_code &&
                    selectedMethod?.instrument_type === method.instrument_type;

                  return (
                    <button
                      key={`${method.provider_code}-${method.instrument_type}`}
                      type="button"
                      disabled={!method.available}
                      onClick={() => setSelectedMethod(method)}
                      className={`w-full p-3.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                        !method.available
                          ? "opacity-50 bg-white/[0.02] border-white/5 cursor-not-allowed"
                          : isSelected
                            ? "bg-blue-600/15 border-blue-500 shadow-sm shadow-blue-500/20"
                            : "bg-white/[0.04] border-white/10 hover:border-white/20"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                          method.instrument_type === "mobile_money"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-indigo-500/10 text-indigo-400"
                        }`}>
                          {method.instrument_type === "mobile_money" ? (
                            <Smartphone className="w-4 h-4" />
                          ) : (
                            <CreditCard className="w-4 h-4" />
                          )}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-sm text-white">{method.label}</span>
                            {method.is_sandbox && (
                              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                                Sandbox
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400 mt-0.5">
                            {method.available
                              ? "Available for instant checkout"
                              : method.reason || "Currently unavailable"}
                          </p>
                        </div>
                      </div>

                      <div className="w-5 h-5 rounded-full border border-white/20 flex items-center justify-center shrink-0">
                        {isSelected && <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />}
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Mobile Phone Input if Mobile Money selected */}
              {selectedMethod?.instrument_type === "mobile_money" && (
                <div className="mt-4 pt-3 border-t border-white/10">
                  <label htmlFor="customer-phone" className="block text-xs font-semibold text-slate-300 mb-1">
                    Mobile Money Phone Number (Optional)
                  </label>
                  <input
                    id="customer-phone"
                    type="tel"
                    placeholder="+265 991 000 000"
                    value={phoneInput}
                    onChange={(e) => setPhoneInput(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              )}
            </div>

            {/* Authenticated Customer Banner */}
            {effectiveUser ? (
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 px-4 py-2.5 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-emerald-400">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Paying as <strong>{effectiveUser.full_name || effectiveUser.email}</strong></span>
                </div>
                <span className="text-slate-400 text-[11px]">Authorized</span>
              </div>
            ) : null}

            {/* Action Button */}
            <div>
              <button
                type="button"
                disabled={submittingPayment || !selectedMethod?.available}
                onClick={handleProceedClick}
                className="w-full py-4 px-6 rounded-xl font-bold text-base bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white shadow-xl shadow-blue-600/30 transition-all flex items-center justify-center gap-2"
              >
                <span>
                  {effectiveUser
                    ? `Pay ${qr.qr_type === "dynamic" ? `${qr.currency} ${qr.amount}` : amountInput ? `MWK ${amountInput}` : "Now"}`
                    : "Continue to Pay"}
                </span>
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>

            {/* Open in POMPO App Option */}
            <div className="text-center pt-2">
              <a
                href={`pompo://p/${publicId}`}
                className="text-xs text-slate-400 hover:text-blue-400 inline-flex items-center gap-1 transition-colors"
              >
                <span>Have the POMPO app? Open in App</span>
              </a>
            </div>
          </div>
        )}

        {/* Modal / Sheet: Auth Required */}
        {phase === "auth_required" && (
          <div className="rounded-2xl border border-white/15 bg-[#0f192e] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">Payment Authorization</h3>
                <p className="text-xs text-slate-400 mt-0.5">Sign in or quick-register to authorize payment</p>
              </div>
              <button
                type="button"
                onClick={() => setPhase("ready")}
                className="text-slate-400 hover:text-white text-xs font-semibold px-2 py-1"
              >
                Cancel
              </button>
            </div>

            {/* Auth Mode Toggle */}
            <div className="flex p-1 rounded-xl bg-black/40 border border-white/10">
              <button
                type="button"
                onClick={() => setAuthMode("register")}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                  authMode === "register" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Quick Register
              </button>
              <button
                type="button"
                onClick={() => setAuthMode("login")}
                className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-colors ${
                  authMode === "login" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                Sign In
              </button>
            </div>

            {authError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-3">
              {authMode === "register" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Full Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Kondwani Banda"
                      value={authName}
                      onChange={(e) => setAuthName(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">Phone Number</label>
                    <input
                      type="tel"
                      required
                      placeholder="+265 991 000 000"
                      value={authPhone}
                      onChange={(e) => setAuthPhone(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
                <input
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
                <input
                  type="password"
                  required
                  minLength={8}
                  placeholder="••••••••"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-black/40 border border-white/10 text-sm text-white focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={authSubmitting}
                  className="w-full py-3 px-4 rounded-xl font-bold bg-blue-600 hover:bg-blue-500 text-white transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {authSubmitting ? (
                    <div className="w-5 h-5 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  ) : (
                    <span>{authMode === "register" ? "Create Account & Pay" : "Sign In & Pay"}</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="py-4 px-6 border-t border-white/5 text-center text-xs text-slate-500">
        <p>© 2026 POMPO Payment Platform · Bank of Malawi Regulatory Compliance · Zero PAN/PIN Storage</p>
      </footer>
    </div>
  );
}
