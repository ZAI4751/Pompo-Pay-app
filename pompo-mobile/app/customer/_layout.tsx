import { Redirect, Stack } from "expo-router";

import { useAuth } from "@/state/AuthProvider";

export default function CustomerLayout() {
  const { hydrated, user } = useAuth();
  if (hydrated && !user) {
    return <Redirect href="/login" />;
  }
  return <Stack screenOptions={{ headerShown: false, animation: "slide_from_right" }} />;
}
