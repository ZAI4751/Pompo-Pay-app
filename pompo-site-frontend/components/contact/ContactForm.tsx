"use client";

import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import Button from "@/components/ui/Button";
import { ContactFormStatus, ContactFormValues, ContactResponse } from "@/lib/types";
import { submitContact } from "@/lib/api/contact";
import { ApiClientError } from "@/lib/api/client";

const EMPTY: ContactFormValues = {
  name: "",
  email: "",
  phone: "",
  company: "",
  subject: "",
  message: "",
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ContactForm() {
  const [values, setValues] = useState<ContactFormValues>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<keyof ContactFormValues, string>>>({});
  const [status, setStatus] = useState<ContactFormStatus>("idle");
  const [serverError, setServerError] = useState<string | null>(null);
  const [apiResponse, setApiResponse] = useState<ContactResponse | null>(null);

  const update =
    (field: keyof ContactFormValues) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((v) => ({ ...v, [field]: e.target.value }));
    };

  function validate(): boolean {
    const next: Partial<Record<keyof ContactFormValues, string>> = {};
    if (!values.name.trim()) next.name = "Please enter your name.";
    if (!values.email.trim()) next.email = "Please enter your email.";
    else if (!EMAIL_RE.test(values.email)) next.email = "Please enter a valid email address.";
    if (!values.subject.trim()) next.subject = "Please add a subject.";
    if (!values.message.trim()) next.message = "Please add a message.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setServerError(null);

    if (!validate()) return;

    setStatus("submitting");

    try {
      const response = await submitContact({
        name: values.name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim() || null,
        company: values.company.trim() || null,
        subject: values.subject.trim(),
        message: values.message.trim(),
      });

      setApiResponse(response);
      setStatus("success");
      setValues(EMPTY);
    } catch (err) {
      setStatus("error");
      if (err instanceof ApiClientError) {
        if (err.status === 429) {
          setServerError("Too many contact requests. Please wait a minute before trying again.");
        } else if (err.status === 422) {
          setServerError(
            err.detail
              ? `Validation error: ${err.detail}`
              : "Please check your inputs and ensure all required fields are correctly filled."
          );
        } else if (err.status >= 500) {
          setServerError("The POMPO server encountered an issue processing your submission. Please try again shortly.");
        } else if (err.status === 0) {
          setServerError("Cannot connect to the POMPO API server. Please check your connection or verify the backend is running.");
        } else {
          setServerError(err.message || "An unexpected error occurred. Please try again.");
        }
      } else if (err instanceof Error) {
        setServerError(err.message);
      } else {
        setServerError("Something went wrong sending your message. Please try again.");
      }
    }
  }

  if (status === "success") {
    const isConfigured = apiResponse?.delivery_status === "sent";
    const refId = apiResponse?.reference_id;

    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        role="status"
        className="rounded-2xl border border-slate-line bg-mist p-8 text-center"
      >
        <div aria-hidden className="mx-auto mb-4 h-10 w-10 rounded-full bg-brand-gradient" />
        <h3 className="font-display text-xl font-medium text-ink">
          {isConfigured ? "Message sent" : "Message received"}
        </h3>
        {refId && (
          <p className="mt-1 text-xs font-mono text-slate-soft">
            Reference ID: {refId}
          </p>
        )}
        <p className="mt-3 text-[15px] text-slate-soft">
          {isConfigured
            ? "Thanks for reaching out — the POMPO team will get back to you shortly."
            : "Your message has been received and recorded by our system. Automated email delivery is currently not configured on this server, but the POMPO team has your inquiry on file."}
        </p>
        <div className="mt-6">
          <Button
            variant="secondary"
            type="button"
            onClick={() => {
              setStatus("idle");
              setApiResponse(null);
            }}
          >
            Send another message
          </Button>
        </div>
      </motion.div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <Field
          label="Name"
          id="name"
          value={values.name}
          onChange={update("name")}
          error={errors.name}
          autoComplete="name"
          required
        />
        <Field
          label="Email"
          id="email"
          type="email"
          value={values.email}
          onChange={update("email")}
          error={errors.email}
          autoComplete="email"
          required
        />
        <Field
          label="Phone"
          id="phone"
          type="tel"
          value={values.phone}
          onChange={update("phone")}
          autoComplete="tel"
        />
        <Field
          label="Company"
          id="company"
          value={values.company}
          onChange={update("company")}
          autoComplete="organization"
        />
      </div>

      <Field
        label="Subject"
        id="subject"
        value={values.subject}
        onChange={update("subject")}
        error={errors.subject}
        required
      />

      <div>
        <label htmlFor="message" className="mb-2 block text-sm font-medium text-ink">
          Message <span aria-hidden className="text-indigo-500">*</span>
        </label>
        <textarea
          id="message"
          rows={5}
          value={values.message}
          onChange={update("message")}
          aria-invalid={Boolean(errors.message)}
          aria-describedby={errors.message ? "message-error" : undefined}
          className={`w-full rounded-xl border bg-white px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-indigo-500 ${
            errors.message ? "border-red-400" : "border-slate-line"
          }`}
        />
        {errors.message && (
          <p id="message-error" className="mt-1.5 text-sm text-red-600">
            {errors.message}
          </p>
        )}
      </div>

      {status === "error" && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {serverError ?? "We couldn't send your message. Please try again."}
        </div>
      )}

      <Button type="submit" variant="primary" disabled={status === "submitting"} className="w-full sm:w-auto">
        {status === "submitting" ? "Sending…" : "Send Message"}
      </Button>
    </form>
  );
}

function Field({
  label,
  id,
  value,
  onChange,
  error,
  type = "text",
  autoComplete,
  required,
}: {
  label: string;
  id: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string;
  type?: string;
  autoComplete?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-medium text-ink">
        {label} {required && <span aria-hidden className="text-indigo-500">*</span>}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        className={`w-full rounded-xl border bg-white px-4 py-3 text-[15px] text-ink outline-none transition-colors focus:border-indigo-500 ${
          error ? "border-red-400" : "border-slate-line"
        }`}
      />
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}
