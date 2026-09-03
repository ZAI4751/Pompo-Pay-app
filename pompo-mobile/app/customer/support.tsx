import { useState } from "react";
import { Pressable, Text, View } from "react-native";

import { BottomNav } from "@/components/nav";
import { Card, ErrorBanner, GlassInput, PrimaryButton, Screen, Title, useTheme } from "@/components/ui";
import { useAuth } from "@/state/AuthProvider";

const CATEGORIES = [
  { value: "payment_problem", label: "Payment problem" },
  { value: "report_transaction", label: "Report a payment" },
  { value: "reference_lookup", label: "Reference lookup" },
  { value: "other", label: "Other" },
] as const;

export default function SupportScreen() {
  const theme = useTheme();
  const { api } = useAuth();
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]["value"]>("payment_problem");
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
        {done ? (
          <Card>
            <Text style={{ color: theme.success, fontWeight: "800" }}>Request recorded</Text>
            <Text style={{ color: theme.muted, marginTop: 6 }}>{done}</Text>
          </Card>
        ) : null}
        <Card>
          <Text style={{ color: theme.text, fontWeight: "700", marginBottom: 8 }}>Category</Text>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 }}>
            {CATEGORIES.map((item) => {
              const selected = category === item.value;
              return (
                <Pressable
                  key={item.value}
                  onPress={() => setCategory(item.value)}
                  style={{
                    borderRadius: 999,
                    paddingHorizontal: 12,
                    paddingVertical: 6,
                    borderWidth: 1,
                    borderColor: selected ? theme.primary : theme.border,
                    backgroundColor: selected ? theme.surfaceRaised : theme.surface,
                  }}
                >
                  <Text style={{ color: selected ? theme.primary : theme.muted, fontWeight: "700", fontSize: 12 }}>
                    {item.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
          <GlassInput placeholder="Subject" value={subject} onChangeText={setSubject} />
          <GlassInput placeholder="Payment reference (optional)" value={reference} onChangeText={setReference} />
          <GlassInput placeholder="What happened?" value={message} onChangeText={setMessage} />
          <PrimaryButton
            label="Send"
            loading={loading}
            onPress={async () => {
              setError(null);
              setDone(null);
              if (!subject.trim() || !message.trim()) {
                setError("Subject and message are required.");
                return;
              }
              setLoading(true);
              const result = await api.createSupportRequest({
                category,
                subject: subject.trim(),
                message: message.trim(),
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
