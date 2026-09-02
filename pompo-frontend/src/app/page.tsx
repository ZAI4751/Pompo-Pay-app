import type { Metadata } from "next";
import { ExperienceChrome } from "@/components/experience/ExperienceChrome";
import { ExperienceHome } from "@/components/experience/ExperienceHome";

export const metadata: Metadata = {
  title: "Pompo Wallet",
  description: "Customer wallet preview for the Pompo payment platform.",
};

export default function WalletPage() {
  return (
    <ExperienceChrome>
      <ExperienceHome />
    </ExperienceChrome>
  );
}
