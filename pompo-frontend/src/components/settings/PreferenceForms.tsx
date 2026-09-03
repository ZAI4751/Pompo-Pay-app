"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useTheme } from "next-themes";
import { customersService, type NotificationPreferences } from "@/lib/api/services/customers";
import { useAuth } from "@/lib/auth/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { FormActions, SettingsPanel } from "./SettingPrimitives";
import type { ApiErrorKind } from "@/lib/types/common";

const PREF_FIELDS = [
  {
    key: "notify_payment_success" as const,
    label: "Payment succeeded",
    hint: "In-app notice when a payment you can see reaches success.",
  },
  {
    key: "notify_payment_failed" as const,
    label: "Payment failed",
    hint: "In-app notice when a payment fails.",
  },
  {
    key: "notify_payment_updates" as const,
    label: "Payment updates",
    hint: "In-app notice for intermediate payment status changes.",
  },
  {
    key: "notify_payment_requests" as const,
    label: "Payment requests",
    hint: "In-app notice when a payment request is created or updated.",
  },
];

export function NotificationPrefsForm() {
  const { isDemoSession } = useAuth();
  const { push } = useToast();
  const [loaded, setLoaded] = useState<NotificationPreferences | null>(null);
  const [draft, setDraft] = useState<NotificationPreferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<ApiErrorKind>("unknown");
  const [saving, setSaving] = useState(false);

  const load = () => {
    void customersService.preferences().then((result) => {
      if (result.status === "error") {
        setError(result.message);
        setKind(result.kind);
        return;
      }
      setError(null);
      setLoaded(result.data);
      setDraft(result.data);
    });
  };

  useEffect(() => {
    load();
  }, []);

  const dirty = useMemo(() => {
    if (!loaded || !draft) return false;
    return PREF_FIELDS.some((field) => loaded[field.key] !== draft[field.key]);
  }, [loaded, draft]);

  function cancel() {
    setDraft(loaded);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!draft || !dirty) return;
    setSaving(true);
    const result = await customersService.updatePreferences({
      notify_payment_success: draft.notify_payment_success,
      notify_payment_failed: draft.notify_payment_failed,
      notify_payment_updates: draft.notify_payment_updates,
      notify_payment_requests: draft.notify_payment_requests,
    });
    setSaving(false);
    if (result.status === "error") {
      push(result.message, "error");
      return;
    }
    setLoaded(result.data);
    setDraft(result.data);
    push("Notification preferences saved", "success");
  }

  if (error) {
    return (
      <ErrorState
        kind={kind}
        description={error}
        onRetry={kind === "unavailable" ? undefined : load}
      />
    );
  }

  if (!draft) {
    return <SkeletonCard />;
  }

  return (
    <SettingsPanel
      title="In-app notification flags"
      description="PATCH /api/v1/customers/me/preferences. These flags belong to the signed-in user. They are not a platform SMS, email, or push gateway."
    >
      <form onSubmit={onSubmit} className="space-y-1">
        {PREF_FIELDS.map((field) => (
          <label
            key={field.key}
            className="flex items-start justify-between gap-4 border-b border-border py-3 last:border-b-0"
          >
            <span>
              <span className="block text-sm font-medium text-text">{field.label}</span>
              <span className="block text-xs text-text-subtle">{field.hint}</span>
            </span>
            <input
              type="checkbox"
              className="mt-1 h-4 w-4 accent-primary"
              checked={draft[field.key]}
              disabled={isDemoSession}
              onChange={(event) =>
                setDraft({ ...draft, [field.key]: event.target.checked })
              }
            />
          </label>
        ))}
        <p className="pt-2 text-xs text-text-subtle">
          Phone verification: {draft.phone_verification}. Preferred mode: {draft.preferred_mode ?? "unset"}.
          Mode switching is a customer-product field and is not edited here.
        </p>
        <FormActions dirty={dirty} saving={saving} onCancel={cancel} />
      </form>
    </SettingsPanel>
  );
}

export function DisplayThemeForm() {
  const { theme, setTheme } = useTheme();
  const saved = theme ?? "system";
  const [draft, setDraft] = useState<string | null>(null);
  const value = draft ?? saved;
  const dirty = draft !== null && draft !== saved;

  function cancel() {
    setDraft(null);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTheme(value);
    setDraft(null);
  }

  return (
    <SettingsPanel
      title="Display theme"
      description="Stored in this browser by next-themes. It is not a backend setting and is not shared across operators."
    >
      <form onSubmit={onSubmit} className="space-y-3">
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-text">Theme</legend>
          {(
            [
              ["system", "Match the operating system"],
              ["light", "Light"],
              ["dark", "Dark"],
            ] as const
          ).map(([option, label]) => (
            <label key={option} className="flex items-center gap-2 text-sm text-text">
              <input
                type="radio"
                name="theme"
                value={option}
                checked={value === option}
                onChange={() => setDraft(option)}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <FormActions dirty={dirty} saving={false} onCancel={cancel} saveLabel="Apply on this device" />
      </form>
    </SettingsPanel>
  );
}
