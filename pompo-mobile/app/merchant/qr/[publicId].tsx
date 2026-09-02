import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Share, Text } from "react-native";
import QRCode from "react-native-qrcode-svg";

import { Card, ErrorBanner, Screen, SecondaryButton, Title, useTheme } from "@/components/ui";
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
        <Card style={{ alignItems: "center" }}>
          <QRCode value={qr.encoded_payload} size={180} />
          <Text style={{ color: theme.text, fontWeight: "700" }}>{qr.public_identifier}</Text>
          <Text style={{ color: theme.muted }}>
            {qr.qr_type} · {qr.status}
          </Text>
          <SecondaryButton
            label="Share"
            onPress={() => void Share.share({ message: qr.encoded_payload })}
          />
        </Card>
      ) : null}
      <SecondaryButton label="Back" onPress={() => router.back()} />
    </Screen>
  );
}
