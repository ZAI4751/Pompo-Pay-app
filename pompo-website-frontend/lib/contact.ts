import { CONTACT } from "@/lib/constants";
import type { ContactFormValues } from "@/lib/types";

export function buildContactMailto(values: ContactFormValues): string {
  const body = [
    `Name: ${values.name.trim()}`,
    `Email: ${values.email.trim()}`,
    values.phone.trim() ? `Phone: ${values.phone.trim()}` : null,
    values.company.trim() ? `Company: ${values.company.trim()}` : null,
    "",
    values.message.trim(),
  ]
    .filter((line): line is string => line !== null)
    .join("\n");

  return `mailto:${CONTACT.email}?subject=${encodeURIComponent(
    values.subject.trim(),
  )}&body=${encodeURIComponent(body)}`;
}
