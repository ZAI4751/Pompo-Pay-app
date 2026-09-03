"use client";

import { useState, type FormEvent } from "react";
import { authService } from "@/lib/api/services/auth";
import { useAuth } from "@/lib/auth/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { FormActions, SettingsPanel } from "./SettingPrimitives";

const MIN_PASSWORD = 8;
const MAX_PASSWORD = 72;

export function PasswordChangeForm() {
  const { isDemoSession, logout } = useAuth();
  const { push } = useToast();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const dirty = Boolean(currentPassword || newPassword || confirmPassword);

  function reset() {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setErrors({});
  }

  function validate(): boolean {
    const next: Record<string, string> = {};
    if (!currentPassword) next.currentPassword = "Current password is required.";
    if (newPassword.length < MIN_PASSWORD) {
      next.newPassword = `New password must be at least ${MIN_PASSWORD} characters.`;
    }
    if (newPassword.length > MAX_PASSWORD) {
      next.newPassword = `New password must be at most ${MAX_PASSWORD} characters.`;
    }
    if (newPassword && newPassword === currentPassword) {
      next.newPassword = "New password must be different from the current password.";
    }
    if (confirmPassword !== newPassword) {
      next.confirmPassword = "Confirmation does not match the new password.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (isDemoSession) {
      push("Demo mode cannot change passwords.", "error");
      return;
    }
    if (!validate()) return;
    setConfirmOpen(true);
  }

  async function confirmChange() {
    setSaving(true);
    const result = await authService.changePassword(currentPassword, newPassword);
    setSaving(false);
    setConfirmOpen(false);
    if (result.status === "error") {
      if (result.kind === "unauthorized") {
        setErrors({ currentPassword: result.message });
      } else if (result.kind === "validation") {
        setErrors({ newPassword: result.message });
      } else {
        push(result.message, "error");
      }
      return;
    }
    push("Password changed. Sign in again — all sessions were revoked.", "success");
    reset();
    await logout();
  }

  return (
    <SettingsPanel
      title="Change password"
      description="POST /api/v1/auth/change-password. A successful change revokes every refresh session for this account, including this one."
    >
      <form onSubmit={onSubmit} className="space-y-3">
        <Input
          type="password"
          autoComplete="current-password"
          label="Current password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          error={errors.currentPassword}
          disabled={isDemoSession}
        />
        <Input
          type="password"
          autoComplete="new-password"
          label="New password"
          hint={`8–72 characters. Stored as a bcrypt hash; never logged.`}
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          error={errors.newPassword}
          disabled={isDemoSession}
        />
        <Input
          type="password"
          autoComplete="new-password"
          label="Confirm new password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={errors.confirmPassword}
          disabled={isDemoSession}
        />
        {isDemoSession && (
          <p className="text-sm text-warning">Sign in against the live API to change a password.</p>
        )}
        <FormActions dirty={dirty} saving={saving} onCancel={reset} saveLabel="Change password" />
      </form>
      <ConfirmationDialog
        open={confirmOpen}
        title="Change password and revoke sessions?"
        description="This updates the password hash and immediately revokes all refresh sessions. You will be signed out."
        confirmLabel="Change password"
        destructive
        loading={saving}
        onConfirm={() => void confirmChange()}
        onCancel={() => setConfirmOpen(false)}
      />
    </SettingsPanel>
  );
}

export function AccountLifecycleForm() {
  const { user, isDemoSession, logout } = useAuth();
  const { push } = useToast();
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const status = (user?.account_status ?? "active").toUpperCase();

  async function confirm() {
    setSaving(true);
    const result = await authService.deactivateAccount(password, confirmation.trim());
    setSaving(false);
    setOpen(false);
    if (result.status === "error") {
      push(result.message, "error");
      return;
    }
    push("Account deactivated. Sign in again to request reactivation.", "success");
    await logout();
  }

  return (
    <SettingsPanel
      title="Account lifecycle"
      description="POST /api/v1/auth/deactivate-account. Requires your current password and the confirmation word DEACTIVATE. Sessions are revoked. Payment history stays on file."
    >
      <p className="text-sm text-text">
        Status: <span className="font-semibold">{status}</span>
      </p>
      <p className="text-sm text-text-muted">
        Deactivating this account disables access, signs out every device, and stops payment use.
        Receipts and settlement records remain preserved.
      </p>
      <Input
        type="password"
        autoComplete="current-password"
        label="Current password"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={isDemoSession}
      />
      <Input
        label="Type DEACTIVATE to confirm"
        value={confirmation}
        onChange={(event) => setConfirmation(event.target.value)}
        disabled={isDemoSession}
      />
      <div className="flex justify-end border-t border-border pt-4">
        <Button
          type="button"
          variant="danger"
          size="sm"
          disabled={isDemoSession || !password || confirmation.trim() !== "DEACTIVATE"}
          onClick={() => setOpen(true)}
        >
          Deactivate account
        </Button>
      </div>
      <ConfirmationDialog
        open={open}
        title="Deactivate this POMPO account?"
        description="Account access will be disabled, active sessions will be revoked, and payment access will stop. Financial history remains preserved."
        confirmLabel="Deactivate account"
        destructive
        loading={saving}
        onConfirm={() => void confirm()}
        onCancel={() => setOpen(false)}
      />
    </SettingsPanel>
  );
}

export function SessionRevokeForm() {
  const { isDemoSession, logout } = useAuth();
  const { push } = useToast();
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  async function confirm() {
    setSaving(true);
    const result = await authService.logoutAll();
    setSaving(false);
    setOpen(false);
    if (result.status === "error") {
      push(result.message, "error");
      return;
    }
    push("All sessions revoked. Sign in again.", "success");
    await logout();
  }

  return (
    <SettingsPanel
      title="Active sessions"
      description="POST /api/v1/auth/logout-all revokes every refresh token for this user. There is no session-list API, so individual devices cannot be inspected or revoked one-by-one."
    >
      <p className="text-sm text-text-muted">
        Use this after a suspected compromise. Access tokens already issued remain valid until
        they expire; refresh is blocked immediately.
      </p>
      <div className="flex justify-end border-t border-border pt-4">
        <Button
          type="button"
          variant="danger"
          size="sm"
          disabled={isDemoSession}
          onClick={() => setOpen(true)}
        >
          Revoke all sessions
        </Button>
      </div>
      <ConfirmationDialog
        open={open}
        title="Revoke every session?"
        description="Every refresh session for this account will be revoked. You will be signed out of this console."
        confirmLabel="Revoke all sessions"
        destructive
        loading={saving}
        onConfirm={() => void confirm()}
        onCancel={() => setOpen(false)}
      />
    </SettingsPanel>
  );
}
