import { messageFromApiPayload, GENERIC_VALIDATION_DETAIL } from "@/api/errors";
import { validateCustomerRegistrationInput } from "@/domain/registration";

describe("messageFromApiPayload", () => {
  const fallback = "Some of those values are not valid.";

  it("maps field-level 422 errors instead of the generic validation detail", () => {
    expect(
      messageFromApiPayload(
        {
          detail: GENERIC_VALIDATION_DETAIL,
          errors: [{ loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" }],
        },
        fallback,
      ),
    ).toBe("Email address is invalid");
  });

  it("maps password and missing-field errors", () => {
    expect(
      messageFromApiPayload(
        {
          detail: GENERIC_VALIDATION_DETAIL,
          errors: [
            { loc: ["body", "password"], msg: "String should have at least 8 characters", type: "string_too_short" },
          ],
        },
        fallback,
      ),
    ).toBe("Password does not meet requirements");
    expect(
      messageFromApiPayload(
        {
          detail: GENERIC_VALIDATION_DETAIL,
          errors: [{ loc: ["body", "full_name"], msg: "Field required", type: "missing" }],
        },
        fallback,
      ),
    ).toBe("Full name is required");
  });

  it("uses a useful backend detail when no field errors are present", () => {
    expect(messageFromApiPayload({ detail: "An account with these details already exists" }, fallback)).toBe(
      "An account with these details already exists",
    );
  });

  it("does not use the generic validation sentence as the displayed message", () => {
    expect(messageFromApiPayload({ detail: GENERIC_VALIDATION_DETAIL }, fallback)).toBe(fallback);
  });
});

describe("validateCustomerRegistrationInput", () => {
  const valid = {
    full_name: "Chikondi Banda",
    email: "chikondi@gmail.com",
    password: "Password123",
  };

  it("accepts a valid customer payload", () => {
    expect(validateCustomerRegistrationInput(valid)).toBeNull();
  });

  it("rejects invalid email, short password, and missing name", () => {
    expect(validateCustomerRegistrationInput({ ...valid, email: "not-an-email" })).toBe("Email address is invalid");
    expect(validateCustomerRegistrationInput({ ...valid, password: "short" })).toBe(
      "Password does not meet requirements",
    );
    expect(validateCustomerRegistrationInput({ ...valid, full_name: "  " })).toBe("Full name is required");
  });
});
