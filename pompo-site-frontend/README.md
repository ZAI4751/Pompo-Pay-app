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
cp .env.example .env.local   # then set NEXT_PUBLIC_WEBSITE_API_URL
npm run dev
```

## Verification

```bash
npm run typecheck
npm run lint
npm run build
```

**Note:** these commands were not run in the environment this project was generated in —
it has no network access to install dependencies. Run them yourself after `npm install`
and fix anything that surfaces; the code has been written carefully but hasn't been
compiled or type-checked by a real TypeScript/Next.js toolchain yet.

## Environment variables

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_WEBSITE_API_URL` | Base URL of the backend that exposes `POST /api/v1/contact`. Public/client-exposed — never put secrets here. |

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
  constants.ts        All site copy, nav, contact info, FAQs, goals — single source of truth
  types.ts            Shared TS types
public/               Logo assets (from the official uploaded asset), favicons, OG image
```

## Content notes

All copy on the site comes directly from the brief. Nothing about user counts, funding,
partnerships, certifications, or live provider integrations has been invented — see
`lib/constants.ts` to update copy as those facts change.
