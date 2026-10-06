# POMPO Website

The official public informational website for POMPO Pay App — a standalone Next.js
frontend with no dependency on any other POMPO codebase.

## Stack

- Next.js 14 (App Router) + TypeScript
- Tailwind CSS
- Framer Motion

## Getting started

```bash
npm install
npm run dev
```

## Verification

```bash
npm run typecheck
npm run lint
npm run build
```

The public website pages are self-contained and do not require backend environment
variables. The contact form opens the visitor's email application with a message addressed
to `admin@pompo.com`; the visitor sends it from that application.

## Structure

```
app/                 Routes (App Router) — one folder per page
components/
  layout/            Navbar, MobileNav, Footer
  ui/                Button, Container, Logo, Reveal, SectionHeading
  home/               Homepage sections (Hero, previews, CTA)
  how-it-works/       FlowDiagram (shared by home preview + full page)
  solutions/          SolutionCard
  faq/                FaqAccordion
  contact/            ContactForm
lib/
constants.ts        Site metadata, navigation, contact details
content.ts          Public pages' copy and FAQs
types.ts            Shared TS types
public/               Logo assets (from the official uploaded asset), favicons, OG image
```

## Content notes

All copy on the site comes directly from the brief. Nothing about user counts, funding,
partnerships, certifications, or live provider integrations has been invented — see
`lib/constants.ts` to update copy as those facts change.
