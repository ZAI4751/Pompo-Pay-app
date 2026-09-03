import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Share, StyleSheet, Text, View } from "react-native";
import QRCode from "react-native-qrcode-svg";

import { ErrorBanner, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";
import type { QrRecord } from "@/types";

export default function MerchantQrDetail() {
  const { publicId } = useLocalSearchParams<{ publicId: string }>();
  const theme = useTheme();
  const router = useRouter();
  const { api } = useAuth();
  const [qr, setQr] = useState<QrRecord | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);

  useEffect(() => {
    void api.listQrs().then((result) => {
      if (!result.ok) {
        setError({ message: result.error.message, requestId: result.error.requestId });
        return;
      }
      setQr(result.data.find((item) => item.public_identifier === publicId) ?? null);
    });
  }, [api, publicId]);

  return (
    <Screen>
      <Title>QR detail</Title>
      {error ? <ErrorBanner message={error.message} requestId={error.requestId} /> : null}
      {qr ? (
        <View style={[styles.frame, { backgroundColor: theme.glassFill, borderColor: theme.glassBorder }]}>
          <View style={styles.plate}>
            <QRCode value={qr.encoded_payload} size={180} backgroundColor="#ffffff" color="#0f172a" />
          </View>
          <Text style={{ color: theme.text, fontWeight: "800" }}>{qr.public_identifier}</Text>
          <Text style={{ color: theme.muted }}>
            {qr.qr_type} · {qr.status}
          </Text>
          <SecondaryButton label="Share" onPress={() => void Share.share({ message: qr.encoded_payload })} />
        </View>
      ) : null}
      <SecondaryButton label="Back" onPress={() => router.back()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  frame: { borderWidth: 1, borderRadius: 28, padding: 18, alignItems: "center", gap: 10 },
  plate: { backgroundColor: "#ffffff", padding: 14, borderRadius: 20 },
});
