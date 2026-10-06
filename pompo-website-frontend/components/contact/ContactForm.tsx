"use client";

import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import Button from "@/components/ui/Button";
import type { ContactFormValues } from "@/lib/types";
import { buildContactMailto } from "@/lib/contact";

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
  const [emailReady, setEmailReady] = useState(false);
  const [mailLink, setMailLink] = useState<string | null>(null);

  const update =
    (field: keyof ContactFormValues) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setValues((v) => ({ ...v, [field]: e.target.value }));
    };

  function validate(): boolean {
    const next: Partial<Record<keyof ContactFormValues, string>> = {};
    if (!values.name.trim()) next.name = "Please enter your name.";
    if (!values.email.trim()) next.email = "Please enter your email.";
    else if (!EMAIL_RE.test(values.email.trim())) next.email = "Please enter a valid email address.";
    if (!values.subject.trim()) next.subject = "Please add a subject.";
    if (!values.message.trim()) next.message = "Please add a message.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const href = buildContactMailto(values);
    setMailLink(href);
    setEmailReady(true);
    window.location.href = href;
  }

  if (emailReady && mailLink) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        role="status"
        className="rounded-2xl border border-slate-line bg-mist p-8 text-center"
      >
        <div aria-hidden className="mx-auto mb-4 h-10 w-10 rounded-full bg-brand-gradient" />
        <h3 className="font-display text-xl font-medium text-ink">Complete your message</h3>
        <p className="mt-3 text-[15px] text-slate-soft">
          Your email application should open with your message addressed to the POMPO team.
          Send the email there to complete delivery.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          <a
            href={mailLink}
            className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-gradient px-5 py-3 text-sm font-medium text-white"
          >
            Open email to send message
          </a>
          <Button
            variant="secondary"
            type="button"
            onClick={() => {
              setEmailReady(false);
              setMailLink(null);
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
          maxLength={5000}
          required
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

      <Button type="submit" variant="primary" className="w-full sm:w-auto">
        Send Message
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
        required={required}
        maxLength={id === "email" ? 254 : id === "subject" ? 150 : 120}
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
