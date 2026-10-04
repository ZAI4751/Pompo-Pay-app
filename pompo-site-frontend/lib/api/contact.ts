import { apiPost } from "@/lib/api/client";
import { ContactResponse, ContactSubmission } from "@/lib/types";

/**
 * Submit contact form payload to FastAPI backend POST /api/v1/contact.
 * Uncached, no-store request.
 */
export function submitContact(data: ContactSubmission): Promise<ContactResponse> {
  return apiPost<ContactResponse, ContactSubmission>("/api/v1/contact", data, {
    cache: "no-store",
    revalidate: false,
  });
}
