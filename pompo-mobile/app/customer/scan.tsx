import { CameraView, useCameraPermissions } from "expo-camera";
import { useRouter } from "expo-router";
import { useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { ErrorBanner, PrimaryButton, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
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
        <Title>Camera</Title>
      </Screen>
    );
  }

  if (!permission.granted) {
    return (
      <Screen>
        <Title>Camera access</Title>
        <Text style={{ color: theme.muted, marginVertical: 12 }}>
          POMPO needs the camera to scan merchant QR codes.
        </Text>
        <PrimaryButton label="Allow camera" onPress={() => void requestPermission()} />
        <SecondaryButton label="Back" onPress={() => router.back()} />
      </Screen>
    );
  }

  return (
    <Screen padded={false}>
      <View style={styles.header}>
        <Title>Scan QR</Title>
        <Text style={{ color: theme.muted }}>Point at a POMPO code. We verify it with the server.</Text>
      </View>
      <View style={styles.cameraWrap}>
        <CameraView
          style={StyleSheet.absoluteFill}
          barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
          onBarcodeScanned={busy ? undefined : (event) => void onScan(event.data)}
        />
        <View style={styles.frame} />
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
      ) : null}
      <View style={styles.footer}>
        <SecondaryButton label="Cancel" onPress={() => router.back()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { paddingHorizontal: 20, paddingTop: 12, gap: 6 },
  cameraWrap: { flex: 1, margin: 20, borderRadius: 24, overflow: "hidden" },
  frame: {
    ...StyleSheet.absoluteFill,
    borderWidth: 3,
    borderColor: "rgba(37,99,235,0.9)",
    borderRadius: 24,
  },
  errorWrap: { paddingHorizontal: 20, gap: 10 },
  footer: { padding: 20 },
});
