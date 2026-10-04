import Hero from "@/components/home/Hero";
import WhatIsPompo from "@/components/home/WhatIsPompo";
import HowItWorksPreview from "@/components/home/HowItWorksPreview";
import WhoWeServe from "@/components/home/WhoWeServe";
import SolutionsPreview from "@/components/home/SolutionsPreview";
import VisionMissionPreview from "@/components/home/VisionMissionPreview";
import GoalsPreview from "@/components/home/GoalsPreview";
import ContactCTA from "@/components/home/ContactCTA";
import ApiErrorNotice from "@/components/ui/ApiErrorNotice";
import {
  getHomeContent,
  getHowItWorksContent,
  getSolutionsContent,
  getVisionContent,
  getMissionContent,
  getGoalsContent,
} from "@/lib/api/site";

export default async function HomePage() {
  try {
    const [home, howItWorks, solutions, vision, mission, goals] =
      await Promise.all([
        getHomeContent(),
        getHowItWorksContent(),
        getSolutionsContent(),
        getVisionContent(),
        getMissionContent(),
        getGoalsContent(),
      ]);

    return (
      <>
        <Hero title={home.title} description={home.description} />
        <WhatIsPompo sections={home.sections} />
        <HowItWorksPreview steps={howItWorks.steps} />
        <WhoWeServe />
        <SolutionsPreview solutions={solutions} />
        <VisionMissionPreview vision={vision.vision} mission={mission.mission} />
        <GoalsPreview goals={goals.goals} />
        <ContactCTA />
      </>
    );
  } catch (err) {
    return (
      <ApiErrorNotice
        title="Could not load homepage content"
        message={
          err instanceof Error
            ? err.message
            : "Failed to connect to the POMPO API. Please verify the backend is running."
        }
        retryHref="/"
      />
    );
  }
}
