/** Client-side checks that match POST /customers/register. Backend remains authoritative. */

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateCustomerRegistrationInput(input: {
  full_name: string;
  email: string;
  password: string;
  phone?: string;
}): string | null {
  if (!input.full_name.trim()) {
    return "Full name is required";
  }
  if (!input.email.trim()) {
    return "Email address is required";
  }
  if (!EMAIL_PATTERN.test(input.email.trim())) {
    return "Email address is invalid";
  }
  if (input.password.length < 8 || input.password.length > 72) {
    return "Password does not meet requirements";
  }
  if (input.phone && input.phone.length > 32) {
    return "Phone number is invalid";
  }
  return null;
}
