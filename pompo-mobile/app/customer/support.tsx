import { useState } from "react";
import { Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, GlassInput, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

export default function SupportScreen() {
  const theme = useTheme();
  const { api } = useAuth();
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [reference, setReference] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <Screen padded={false}>
      <View style={{ flex: 1, paddingHorizontal: 20, paddingTop: 8, gap: 12 }}>
        <Title>Support</Title>
        <Text style={{ color: theme.muted }}>
          Report a payment problem. Include the payment reference. We do not expose internal logs.
        </Text>
        {error ? <ErrorBanner message={error} /> : null}
        {done ? <Text style={{ color: theme.success }}>{done}</Text> : null}
        <Card>
          <GlassInput placeholder="Subject" value={subject} onChangeText={setSubject} />
          <GlassInput placeholder="Payment reference (optional)" value={reference} onChangeText={setReference} />
          <GlassInput placeholder="What happened?" value={message} onChangeText={setMessage} />
          <PrimaryButton
            label="Send"
            loading={loading}
            onPress={async () => {
              setError(null);
              setLoading(true);
              const result = await api.createSupportRequest({
                category: "payment_problem",
                subject,
                message,
                payment_reference: reference.trim() || undefined,
              });
              setLoading(false);
              if (!result.ok) {
                setError(result.error.message);
                return;
              }
              setDone(`Support request ${result.data.public_identifier} was recorded.`);
              setSubject("");
              setMessage("");
              setReference("");
            }}
          />
        </Card>
      </View>
      <BottomNav active="profile" />
    </Screen>
  );
}
