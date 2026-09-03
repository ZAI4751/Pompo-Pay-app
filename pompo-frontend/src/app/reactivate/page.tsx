"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authService } from "@/lib/api/services/auth";
import { useAuth } from "@/lib/auth/AuthContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { AnimatedPage } from "@/components/motion/AnimatedPage";

export default function ReactivatePage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function onRequest(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    setSubmitting(true);
    const result = await authService.requestAccountReactivation(email.trim());
    setSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    setNotice(
      "If a deactivated POMPO account matches that email, reactivation instructions have been sent.",
    );
  }

  async function onConfirm(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    setSubmitting(true);
    const result = await authService.reactivateAccount(token.trim(), password);
    setSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    const signedIn = await login(email.trim(), password);
    if (!signedIn.ok) {
      router.push("/login");
      return;
    }
    router.push("/dashboard");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <AnimatedPage className="w-full max-w-sm">
        <h1 className="text-lg font-semibold text-text">Your POMPO account is deactivated.</h1>
        <p className="mt-1 text-sm text-text-muted">
          Request a one-time token, then confirm with your password. Old sessions cannot restore access.
        </p>
        {notice ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-sm text-success">{notice}</p> : null}
        {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-sm text-error">{error}</p> : null}
        <form onSubmit={(event) => void onRequest(event)} className="mt-5 space-y-3">
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Button type="submit" className="w-full" loading={submitting}>
            Request reactivation
          </Button>
        </form>
        <form onSubmit={(event) => void onConfirm(event)} className="mt-6 space-y-3 border-t border-border pt-5">
          <Input
            label="Reactivation token"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            required
          />
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          <Button type="submit" className="w-full" loading={submitting} variant="secondary">
            Reactivate and sign in
          </Button>
        </form>
        <p className="mt-6 text-center text-sm text-text-muted">
          <Link href="/login" className="text-primary">
            Back to sign in
          </Link>
        </p>
      </AnimatedPage>
    </div>
  );
}
