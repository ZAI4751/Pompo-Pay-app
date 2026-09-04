"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, m } from "framer-motion";
import { Eye, EyeOff, FlaskConical } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { PompoMark } from "@/components/brand/PompoMark";
import { AnimatedPage } from "@/components/motion/AnimatedPage";
import { useAuth } from "@/lib/auth/AuthContext";
import { isDeactivatedLoginMessage } from "@/lib/auth/adminEligibility";
import { USE_MOCKS } from "@/lib/api/config";
import { messageIn } from "@/lib/motion";

export default function LoginPage() {
  const router = useRouter();
  const { login, enterDemoSession, status } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorReference, setErrorReference] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") router.replace("/dashboard");
  }, [status, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setErrorReference(null);
    const result = await login(email, password);
    setSubmitting(false);
    if (!result.ok) {
      if (result.httpStatus === 403 || result.kind === "forbidden") {
        if (isDeactivatedLoginMessage(result.error)) {
          setError("Your POMPO account is deactivated. Use reactivation to restore access.");
          setErrorReference(result.requestId ?? null);
          router.push("/reactivate");
          return;
        }
        setError(result.error ?? "This account cannot access Master Admin.");
        setErrorReference(result.requestId ?? null);
        return;
      }
      setError(result.error ?? "Sign in failed. Check your credentials and try again.");
      setErrorReference(result.requestId ?? null);
      return;
    }
    router.push("/dashboard");
  }

  function onEnterDemo() {
    setError(null);
    setErrorReference(null);
    const result = enterDemoSession();
    if (!result.ok) {
      setError(result.error ?? "Demo mode is unavailable.");
      return;
    }
    router.push("/dashboard");
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <aside className="relative hidden overflow-hidden bg-dark-blue text-white lg:flex lg:flex-col lg:justify-between">
        <div className="pompo-aurora pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="pompo-grid-bg pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
        <div className="relative flex h-full flex-col justify-between p-10">
          <div className="flex items-center gap-3">
            <PompoMark size={36} />
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">Pompo</p>
              <p className="text-sm text-white/70">Master Admin</p>
            </div>
          </div>
          <div className="max-w-md">
            <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">
              Payment infrastructure
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">
              The control plane for money in motion.
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-white/70">
              Operations, identity, and rail health for Malawi mobile money — designed for teams
              that move real value, not generic dashboards.
            </p>
          </div>
          <p className="text-xs text-white/45">Malawi · MWK · Authorized staff only</p>
        </div>
      </aside>

      <div className="relative flex min-h-screen items-center justify-center bg-background px-4 py-12 transition-colors duration-200">
        <div className="pompo-aurora pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="absolute right-4 top-4 z-10">
          <ThemeToggle />
        </div>

        <AnimatedPage className="relative z-10 w-full max-w-sm">
          <div className="mb-8 flex flex-col items-center gap-3 lg:items-start">
            <div className="lg:hidden">
              <PompoMark size={36} />
            </div>
            <div className="text-center lg:text-left">
              <h2 className="text-lg font-semibold text-text">Sign in</h2>
              <p className="text-sm text-text-muted">Restricted to authorized Pompo staff.</p>
              {!USE_MOCKS && (
                <p className="mt-2 text-xs text-text-subtle">
                  This form authenticates against the live API. For local development, use{" "}
                  <code className="font-mono">POMPO_ADMIN_EMAIL</code> and{" "}
                  <code className="font-mono">POMPO_ADMIN_PASSWORD</code> from{" "}
                  <code className="font-mono">pompo-backend/.env</code>.
                </p>
              )}
            </div>
          </div>

          {USE_MOCKS && (
            <div
              role="status"
              className="mb-4 rounded-2xl border border-warning/30 bg-warning-bg px-3 py-3 text-sm text-warning"
            >
              <p className="flex items-center gap-1.5 font-medium">
                <FlaskConical className="h-4 w-4 shrink-0" aria-hidden="true" />
                Demo mode for visual review
              </p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">
                Screens use mock data. This is not a production sign-in and does not call the
                backend. Set <code className="font-mono">NEXT_PUBLIC_USE_MOCKS=false</code> to
                authenticate against a running Pompo API.
              </p>
              <Button type="button" className="mt-3 w-full" onClick={onEnterDemo}>
                Continue with demo data
              </Button>
            </div>
          )}

          <form
            onSubmit={onSubmit}
            className="space-y-4 rounded-3xl border border-border bg-white p-6 card-depth pompo-glass dark:border-neutral-800 dark:bg-slate-900/80"
          >
            {USE_MOCKS && (
              <p className="text-xs text-text-subtle">
                The form below is the production login. In demo mode it also opens the mock
                workspace and never sends a password.
              </p>
            )}
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@pompo.mw"
            />

            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute right-3 top-[34px] text-text-subtle hover:text-text"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            <AnimatePresence>
              {error && (
                <m.div
                  role="alert"
                  className="rounded-sm border border-error/30 bg-error-bg px-3 py-2 text-sm text-error"
                  initial={messageIn.initial}
                  animate={messageIn.animate}
                  exit={messageIn.exit}
                  transition={messageIn.transition}
                >
                  <p className="break-words">{error}</p>
                  {errorReference && (
                    <p className="mt-1 truncate text-xs opacity-80">
                      Reference: <span className="font-mono">{errorReference}</span>
                    </p>
                  )}
                </m.div>
              )}
            </AnimatePresence>

            <Button
              type="submit"
              className="w-full"
              loading={submitting}
              variant={USE_MOCKS ? "secondary" : "primary"}
            >
              {submitting ? "Signing in" : USE_MOCKS ? "Open demo via sign-in form" : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-text-subtle lg:text-left">
            All activity is logged. Do not share credentials.
          </p>
        </AnimatedPage>
      </div>
    </div>
  );
}
