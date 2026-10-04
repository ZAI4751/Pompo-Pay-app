import { apiGet, RequestOptions } from "@/lib/api/client";
import {
  AboutContent,
  ContactInfo,
  FaqItem,
  GoalsResponse,
  HomeContent,
  HowItWorksContent,
  MissionResponse,
  SiteOverview,
  SolutionItem,
  VisionResponse,
} from "@/lib/types";

// Default revalidation time for public informational content (seconds)
const DEFAULT_REVALIDATE = 60;

function defaultOptions(options?: RequestOptions): RequestOptions {
  return {
    revalidate: DEFAULT_REVALIDATE,
    ...options,
  };
}

export function getHealth(options?: RequestOptions): Promise<{ status: string }> {
  return apiGet<{ status: string }>("/health", defaultOptions(options));
}

export function getSiteOverview(options?: RequestOptions): Promise<SiteOverview> {
  return apiGet<SiteOverview>("/api/v1/site", defaultOptions(options));
}

export function getHomeContent(options?: RequestOptions): Promise<HomeContent> {
  return apiGet<HomeContent>("/api/v1/site/home", defaultOptions(options));
}

export function getAboutContent(options?: RequestOptions): Promise<AboutContent> {
  return apiGet<AboutContent>("/api/v1/site/about", defaultOptions(options));
}

export function getHowItWorksContent(options?: RequestOptions): Promise<HowItWorksContent> {
  return apiGet<HowItWorksContent>("/api/v1/site/how-it-works", defaultOptions(options));
}

export function getSolutionsContent(options?: RequestOptions): Promise<SolutionItem[]> {
  return apiGet<SolutionItem[]>("/api/v1/site/solutions", defaultOptions(options));
}

export function getVisionContent(options?: RequestOptions): Promise<VisionResponse> {
  return apiGet<VisionResponse>("/api/v1/site/vision", defaultOptions(options));
}

export function getMissionContent(options?: RequestOptions): Promise<MissionResponse> {
  return apiGet<MissionResponse>("/api/v1/site/mission", defaultOptions(options));
}

export function getGoalsContent(options?: RequestOptions): Promise<GoalsResponse> {
  return apiGet<GoalsResponse>("/api/v1/site/goals", defaultOptions(options));
}

export function getFaqContent(options?: RequestOptions): Promise<FaqItem[]> {
  return apiGet<FaqItem[]>("/api/v1/site/faq", defaultOptions(options));
}

export function getContactInfo(options?: RequestOptions): Promise<ContactInfo> {
  return apiGet<ContactInfo>("/api/v1/site/contact", defaultOptions(options));
}
