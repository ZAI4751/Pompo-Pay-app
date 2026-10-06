export interface HomeSection {
  heading: string;
  body: string;
}

export interface SolutionItem {
  name: string;
  description: string;
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface ContactFormValues {
  name: string;
  email: string;
  phone: string;
  company: string;
  subject: string;
  message: string;
}
