import type { FaqItem, HomeSection, SolutionItem } from "@/lib/types";

export const HOME = {
  title: "Connecting payments. Simplifying commerce.",
  description:
    "POMPO connects merchants to local payment providers through a single digital payment gateway, making payments simpler for businesses and customers in Malawi.",
  sections: [
    {
      heading: "One payment gateway",
      body: "Connect customers, merchants, and supported payment providers through one digital payment gateway.",
    },
    {
      heading: "A clear payment flow",
      body: "Keep each payment moving through a clear request, provider response, and confirmation.",
    },
    {
      heading: "Built for commerce",
      body: "Give businesses and customers a simpler way to make and accept digital payments.",
    },
  ] satisfies HomeSection[],
};

export const ABOUT_SUMMARY =
  "POMPO Pay App is a Malawi-focused technology company building digital payment infrastructure. POMPO connects merchants, customers, and supported payment providers through a single digital payment gateway.";

export const PAYMENT_FLOW = {
  flow: ["Customer", "POMPO", "Payment provider", "Merchant"],
  steps: [
    "A customer scans a merchant's POMPO QR code and reviews the payment details.",
    "The customer chooses an available payment method and confirms the payment.",
    "POMPO routes the request to the explicitly selected, supported payment provider.",
    "The provider returns a payment result through the POMPO payment flow.",
    "The customer and merchant can review the payment confirmation.",
  ],
  clarification:
    "POMPO is a payment gateway, not a wallet or a place to store funds. Payments are processed by the selected supported payment provider.",
};

export const SOLUTIONS: SolutionItem[] = [
  {
    name: "For merchants",
    description:
      "Accept digital payments and review transaction activity through POMPO's merchant tools.",
  },
  {
    name: "For customers",
    description:
      "Scan a POMPO QR code, choose an available payment method, and view payment confirmation.",
  },
  {
    name: "For developers",
    description:
      "Connect business systems with POMPO's payment APIs and integration tools.",
  },
  {
    name: "For payment providers",
    description:
      "Connect supported payment services to a shared payment gateway experience.",
  },
];

export const VISION =
  "A simpler, more connected digital payment experience for businesses and customers in Malawi.";

export const MISSION =
  "Build payment infrastructure that connects merchants, customers, and supported providers through a clear, reliable payment gateway.";

export const GOALS = [
  "Make it easier for merchants to accept digital payments.",
  "Keep the customer payment journey clear, from QR scan through payment confirmation.",
  "Expand supported payment integrations as provider access becomes available.",
  "Continue strengthening the security and reliability of the payment platform.",
];

export const FAQ_ITEMS: FaqItem[] = [
  {
    question: "What is POMPO?",
    answer:
      "POMPO is a digital payment gateway that connects customers, merchants, and supported payment providers. It is not a wallet and does not store customer funds.",
  },
  {
    question: "How do I pay with a POMPO QR code?",
    answer:
      "Scan or open the merchant's POMPO QR code, review the merchant and amount, choose an available payment method, and follow the prompts to complete payment.",
  },
  {
    question: "Which payment methods can I use?",
    answer:
      "Available methods depend on the merchant and the payment providers currently enabled for the transaction. The checkout page shows the methods you can select.",
  },
  {
    question: "How can I confirm a payment?",
    answer:
      "POMPO shows the payment result and reference after processing. Keep the reference with your receipt if you need help with a transaction.",
  },
  {
    question: "How do I contact the POMPO team?",
    answer:
      "Use the contact form or email admin@pompo.com. The contact form opens your email application with your message addressed to the POMPO team.",
  },
];

export const GOALS_PREVIEW = GOALS.slice(0, 4);
