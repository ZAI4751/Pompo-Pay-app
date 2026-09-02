import { Redirect, Stack } from "expo-router";

import { canUseMerchantMode } from "@/domain/roles";
import { useAuth } from "@/state/AuthProvider";

export default function MerchantLayout() {
  const { hydrated, user } = useAuth();
  if (hydrated && !user) {
    return <Redirect href="/login" />;
  }
  if (user && !canUseMerchantMode(user.role_code)) {
    return <Redirect href="/customer" />;
  }
  return <Stack screenOptions={{ headerShown: false, animation: "slide_from_right" }} />;
}
