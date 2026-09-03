import { Ionicons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import { useRouter } from "expo-router";
import { useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";

import { CircleButton, GlassSurface, ScanFrame, ScanLine } from "@/components/glass";
import { ErrorBanner, GlassInput, PrimaryButton, Screen, SecondaryButton, useTheme } from "@/components/ui";
import { extractPublicIdentifier } from "@/domain/qrPayload";
import { useAuth } from "@/state/AuthProvider";
import { useCheckout } from "@/state/CheckoutProvider";

export default function ScanScreen() {
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const { begin } = useCheckout();
  const [permission, requestPermission] = useCameraPermissions();
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [isManual, setIsManual] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const locked = useRef(false);

  async function onScan(raw: string) {
    if (locked.current || busy) {
      return;
    }
    locked.current = true;
    setBusy(true);
    setError(null);
    const extracted = extractPublicIdentifier(raw);
    if (!extracted.ok) {
      setError({ message: extracted.message });
      setBusy(false);
      locked.current = false;
      return;
    }
    const inspect = await api.inspectQr(extracted.publicIdentifier);
    if (!inspect.ok) {
      setError({ message: inspect.error.message, requestId: inspect.error.requestId });
      setBusy(false);
      locked.current = false;
      return;
    }
    const amount = inspect.data.qr_type === "dynamic" ? (inspect.data.amount ?? "") : "";
    begin(raw.trim(), inspect.data, amount);
    router.push("/customer/preview");
  }

  if (!permission) {
    return (
      <Screen>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 22 }}>Preparing scanner</Text>
        <Text style={{ color: theme.muted, marginTop: 8 }}>Checking camera permission…</Text>
      </Screen>
    );
  }

  if (!permission.granted) {
    return (
      <Screen>
        <Text style={{ color: theme.text, fontWeight: "800", fontSize: 22 }}>Camera access</Text>
        <Text style={{ color: theme.muted, marginVertical: 12 }}>
          Allow camera access or enter the code manually.
        </Text>
        <PrimaryButton label="Allow camera" onPress={() => void requestPermission()} />
        {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
        <GlassInput
          placeholder="Enter QR code"
          value={manualCode}
          autoCapitalize="characters"
          onChangeText={setManualCode}
        />
        <SecondaryButton label="Continue with code" onPress={() => void onScan(manualCode)} />
        <SecondaryButton label="Back" onPress={() => router.back()} />
      </Screen>
    );
  }

  return (
    <Screen padded={false} atmosphere={false}>
      <KeyboardAvoidingView
        style={styles.screen}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={Platform.OS === "ios" ? 10 : 0}
      >
        <View style={styles.header}>
          <CircleButton
            accessibilityLabel="Cancel scan"
            onPress={() => {
              if (isManual) {
                setIsManual(false);
              } else {
                router.back();
              }
            }}
          >
            <Ionicons name={isManual ? "arrow-back" : "close"} size={18} color="#f8fafc" />
          </CircleButton>
          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle}>{isManual ? "Manual Entry" : "Scan QR"}</Text>
            <Text style={styles.headerHint}>
              {isManual ? "Enter code directly. Camera unmounted." : "Hold steady. We verify with POMPO."}
            </Text>
          </View>
        </View>

        {isManual ? (
          <ScrollView
            contentContainerStyle={styles.manualScroll}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="interactive"
          >
            <View style={styles.manualCard}>
              <Text style={{ color: "#f8fafc", fontSize: 18, fontWeight: "800" }}>Enter QR Code</Text>
              <Text style={{ color: "#94a3b8", fontSize: 13, lineHeight: 18 }}>
                Type or paste the public identifier (e.g. QR78B2A91F0C) or universal link.
              </Text>
              {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
              <GlassInput
                placeholder="QR Code identifier"
                value={manualCode}
                autoCapitalize="characters"
                autoFocus
                onChangeText={setManualCode}
                accessibilityLabel="QR code"
              />
              <PrimaryButton
                label="Continue to payment"
                loading={busy}
                disabled={!manualCode.trim()}
                onPress={() => void onScan(manualCode)}
              />
              <SecondaryButton
                label="Switch back to camera"
                onPress={() => {
                  setError(null);
                  setIsManual(false);
                }}
              />
            </View>
          </ScrollView>
        ) : (
          <View style={{ flex: 1 }}>
            <View style={[styles.cameraWrap, { borderColor: busy ? "#34d399" : "rgba(147,197,253,0.55)" }]}>
              <CameraView
                style={StyleSheet.absoluteFill}
                barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
                onBarcodeScanned={busy ? undefined : (event) => void onScan(event.data)}
              />
              <View style={styles.dim} pointerEvents="none" />
              <ScanFrame />
              {!busy ? <ScanLine /> : null}
              {busy ? (
                <GlassSurface solid style={styles.detected}>
                  <Text style={{ color: theme.text, fontWeight: "800" }}>Code found</Text>
                </GlassSurface>
              ) : null}
            </View>

            {error ? (
              <View style={styles.errorWrap}>
                <ErrorBanner message={error.message} requestId={error.requestId} />
                <SecondaryButton
                  label="Scan again"
                  onPress={() => {
                    setError(null);
                    locked.current = false;
                    setBusy(false);
                  }}
                />
              </View>
            ) : (
              <View style={styles.manualWrap}>
                <Text style={styles.footerHint}>Align the code inside the frame</Text>
                <SecondaryButton
                  label="Enter code manually"
                  onPress={() => {
                    setError(null);
                    setIsManual(true);
                  }}
                />
              </View>
            )}
          </View>
        )}
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#020617" },
  header: {
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 8,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerTitle: { color: "#f8fafc", fontSize: 18, fontWeight: "800" },
  headerHint: { color: "#94a3b8", fontSize: 12, marginTop: 2 },
  cameraWrap: {
    flex: 1,
    marginHorizontal: 20,
    marginVertical: 12,
    borderRadius: 28,
    overflow: "hidden",
    backgroundColor: "#020617",
    borderWidth: 2,
  },
  dim: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    borderWidth: 48,
    borderColor: "rgba(2, 6, 23, 0.42)",
  },
  detected: { position: "absolute", bottom: 18, alignSelf: "center" },
  errorWrap: { paddingHorizontal: 20, paddingBottom: 20, gap: 10 },
  manualWrap: { paddingHorizontal: 20, paddingBottom: 20, gap: 10 },
  manualScroll: { flexGrow: 1, padding: 20, justifyContent: "center" },
  manualCard: {
    backgroundColor: "rgba(15, 23, 42, 0.8)",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.12)",
    padding: 20,
    gap: 16,
  },
  footerHint: {
    textAlign: "center",
    color: "#94a3b8",
    fontSize: 13,
    fontWeight: "600",
  },
});
