"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, ShieldHalf } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { useAuth } from "@/lib/auth/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorReference, setErrorReference] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setErrorReference(null);
    const result = await login(email, password);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error ?? "Sign in failed. Check your credentials and try again.");
      // Only server-side failures carry a correlation ID; a network failure
      // never reached the backend, so there is nothing to quote.
      setErrorReference(result.requestId ?? null);
      return;
    }
    router.push("/dashboard");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldHalf className="h-6 w-6" aria-hidden="true" />
          </div>
          <div className="text-center">
            <h1 className="text-lg font-semibold text-text">Pompo Master Admin</h1>
            <p className="text-sm text-text-muted">Sign in to continue</p>
          </div>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-border bg-surface p-6 shadow-sm">
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

          {error && (
            <div role="alert" className="rounded border border-error/30 bg-error-bg px-3 py-2 text-sm text-error">
              <p>{error}</p>
              {errorReference && (
                <p className="mt-1 text-xs opacity-80">
                  Reference: <span className="font-mono">{errorReference}</span>
                </p>
              )}
            </div>
          )}

          <Button type="submit" className="w-full" loading={submitting}>
            {submitting ? "Signing in" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-text-subtle">
          Access is restricted to authorized Pompo staff. All activity is logged.
        </p>
      </div>
    </div>
  );
}
