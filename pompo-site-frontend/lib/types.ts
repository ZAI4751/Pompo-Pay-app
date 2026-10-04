export interface Founder {
  name: string;
  role: string;
}

export interface ContactInfo {
  phones: string[];
  email: string;
  country: string;
}

export interface HomeSection {
  heading: string;
  body: string;
}

export interface HomeContent {
  title: string;
  description: string;
  sections: HomeSection[];
}

export interface AboutContent {
  summary: string;
  founders: Founder[];
}

export interface HowItWorksContent {
  flow: string[];
  steps: string[];
  clarification: string;
}

export interface SolutionItem {
  name: string;
  description: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface SeoMeta {
  site_name: string;
  title: string;
  description: string;
}

export interface SiteOverview {
  company_name: string;
  short_description: string;
  is_a_wallet: boolean;
  country: string;
  seo: SeoMeta;
  contact: ContactInfo;
}

export interface VisionResponse {
  vision: string;
}

export interface MissionResponse {
  mission: string;
}

export interface GoalsResponse {
  goals: string[];
}

export interface ContactSubmission {
  name: string;
  email: string;
  phone?: string | null;
  company?: string | null;
  subject: string;
  message: string;
}

export interface ContactResponse {
  status: "received";
  delivery_status: "sent" | "not_configured" | "failed";
  reference_id: string;
}

export interface ContactFormValues {
  name: string;
  email: string;
  phone: string;
  company: string;
  subject: string;
  message: string;
}

export type ContactFormStatus = "idle" | "submitting" | "success" | "error";
