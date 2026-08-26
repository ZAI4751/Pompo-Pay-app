---
name: repository-inspection-before-changes
description: 'Enforces a repository-first engineering workflow. Before modifying, creating, deleting, refactoring, migrating, or configuring anything, inspects the existing repository, architecture, conventions, dependencies, configuration, tests, and infrastructure. Use automatically before any software engineering work, backend code changes, database migrations, or infrastructure updates.'
argument-hint: 'Specify scope: arch, database, api, tests, or config'
user-invocable: true
---

# Repository Inspection Before Changes

## Mission

Never modify a repository blindly.

Before making any code, configuration, infrastructure, database, dependency, or architectural change, inspect the repository and establish a reliable understanding of the existing system. The repository is the source of truth.

---

## When to Use This Skill

Use this skill automatically before:
- Modifying backend code, APIs, or database models
- Creating or applying database migrations (Alembic)
- Adding new dependencies or changing configuration
- Modifying Dockerfiles, Docker Compose, or Kubernetes manifests
- Adding or refactoring background workers (Celery)
- Modifying authentication, authorization, or payment logic

---

## Core Principles

1. **Inspect before acting**: Follow the mandatory sequence: `Inspect → Understand → Plan → Verify assumptions → Change → Test → Review`.
2. **Protect existing work**: Never discard, reset, or overwrite uncommitted changes in the user's workspace.
3. **Search before creating**: Search the repository for existing equivalents before introducing new classes, functions, endpoints, or abstractions.
4. **Trace dependencies & data flows**: Understand upstream callers, downstream consumers, database transaction boundaries, and side effects.
5. **Verify with evidence**: Run relevant unit/integration tests and explicitly report what was tested versus what remains `NOT TESTED`.

---

## Inspection Checklist

- [ ] Repository root, project type, language, and package manager identified.
- [ ] Version-control state and uncommitted changes reviewed.
- [ ] Directory structure and architectural layers mapped.
- [ ] Configuration sources and environment requirements inspected.
- [ ] Existing dependencies reviewed to avoid duplication.
- [ ] Database models, connection handling, and migration history examined.
- [ ] Test suite structure and verification commands identified.
