import { useRouter } from "expo-router";
import { useState } from "react";
import { Text, View } from "react-native";

import { Card, ErrorBanner, GlassInput, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function SecurityScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { user, api, logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyToken, setVerifyToken] = useState("");
  const [verifyStatus, setVerifyStatus] = useState<string | null>(null);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 12 }}>
        <Title>Account security</Title>
        <Text style={{ color: theme.muted }}>
          Manage your credentials, email verification, and active sessions.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        {done ? <Text style={{ color: theme.success, fontWeight: "600" }}>{done}</Text> : null}

        {/* Email Verification Section */}
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700" }}>Email verification</Text>
          <Text style={{ color: user?.is_email_verified ? theme.success : "#f59e0b", fontSize: 13, fontWeight: "600" }}>
            Status: {user?.is_email_verified ? "Verified ✓" : "Unverified"}
          </Text>
          {verifyStatus ? (
            <Text style={{ color: theme.subtle, fontSize: 12 }}>{verifyStatus}</Text>
          ) : null}
          {!user?.is_email_verified ? (
            <View style={{ gap: 8, marginTop: 4 }}>
              <GlassInput
                placeholder="Enter verification token"
                value={verifyToken}
                autoCapitalize="none"
                onChangeText={setVerifyToken}
              />
              <PrimaryButton
                label="Confirm token"
                loading={verifying}
                disabled={!verifyToken.trim()}
                onPress={async () => {
                  setError(null);
                  setVerifying(true);
                  const res = await api.verifyEmail(verifyToken.trim());
                  setVerifying(false);
                  if (!res.ok) {
                    setError(res.error.message);
                    return;
                  }
                  setDone("Email verified successfully! Refreshing session…");
                  setVerifyToken("");
                }}
              />
              <SecondaryButton
                label="Resend verification email"
                onPress={async () => {
                  setError(null);
                  const res = await api.requestEmailVerification(user?.email);
                  if (res.ok) {
                    setVerifyStatus("Verification email requested. Check your inbox.");
                  } else {
                    setError(res.error.message);
                  }
                }}
              />
            </View>
          ) : null}
        </Card>

        {/* MFA Backend Gap Transparency */}
        <Card style={{ opacity: 0.85 }}>
          <Text style={{ color: theme.text, fontWeight: "700" }}>Multi-factor authentication (MFA)</Text>
          <Text style={{ color: theme.muted, fontSize: 13, lineHeight: 18 }}>
            Hardware / TOTP multi-factor authentication is not yet supported by the POMPO backend. This capability will be enabled once backend TOTP endpoints are provisioned.
          </Text>
        </Card>

        {/* Change Password Section */}
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700" }}>Change password</Text>
          <GlassInput secureTextEntry placeholder="Current password" value={current} onChangeText={setCurrent} />
          <GlassInput secureTextEntry placeholder="New password (8+ characters)" value={next} onChangeText={setNext} />
          <GlassInput secureTextEntry placeholder="Confirm new password" value={confirm} onChangeText={setConfirm} />
          <PrimaryButton
            label="Update password"
            loading={busy}
            onPress={async () => {
              setError(null);
              setDone(null);
              if (next.length < 8) {
                setError("New password must be at least 8 characters.");
                return;
              }
              if (next !== confirm) {
                setError("Confirmation does not match the new password.");
                return;
              }
              setBusy(true);
              const result = await api.changePassword(current, next);
              setBusy(false);
              if (!result.ok) {
                setError(result.error.message);
                return;
              }
              await logout();
              router.replace("/login");
            }}
          />
        </Card>
        <SecondaryButton
          label="Log out all sessions"
          onPress={async () => {
            await api.logoutAll();
            await logout();
            router.replace("/login");
          }}
        />
      </View>
    </Screen>
  );
}
