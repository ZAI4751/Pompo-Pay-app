import Hero from "@/components/home/Hero";
import WhatIsPompo from "@/components/home/WhatIsPompo";
import HowItWorksPreview from "@/components/home/HowItWorksPreview";
import WhoWeServe from "@/components/home/WhoWeServe";
import SolutionsPreview from "@/components/home/SolutionsPreview";
import VisionMissionPreview from "@/components/home/VisionMissionPreview";
import GoalsPreview from "@/components/home/GoalsPreview";
import ContactCTA from "@/components/home/ContactCTA";
import { GOALS_PREVIEW, HOME, MISSION, PAYMENT_FLOW, SOLUTIONS, VISION } from "@/lib/content";

export default function HomePage() {
  return (
    <>
      <Hero title={HOME.title} description={HOME.description} />
      <WhatIsPompo sections={HOME.sections} />
      <HowItWorksPreview steps={PAYMENT_FLOW.steps} />
      <WhoWeServe />
      <SolutionsPreview solutions={SOLUTIONS} />
      <VisionMissionPreview vision={VISION} mission={MISSION} />
      <GoalsPreview goals={GOALS_PREVIEW} />
      <ContactCTA />
    </>
  );
}
