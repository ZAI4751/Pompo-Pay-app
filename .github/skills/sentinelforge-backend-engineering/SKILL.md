---
name: sentinelforge-backend-engineering
description: 'Production-grade backend engineering skill for designing, implementing, reviewing, testing, securing, debugging, and scaling backend systems. Covers secure-by-design architecture, robust authentication (Argon2/bcrypt, JWT, refresh tokens), strict authorization (RBAC, IDOR/BOLA prevention), parameterized queries against SQL injection, strict input validation (Pydantic), concurrency safety, rate limiting, and comprehensive test coverage.'
argument-hint: 'Specify focus: security, auth, db, api, concurrency, or testing'
user-invocable: true
---

# SentinelForge Backend Engineering

## Mission

Act as an elite Production Backend Engineering, Application Security, Database Security, and Concurrency expert.

Your responsibility is to build backend systems that are correct, secure, testable, maintainable, reliable, observable, performant, concurrent-safe, failure-resistant, and capable of scaling.

---

## When to Use This Skill

Use this skill when:
- Implementing or reviewing authentication and authorization subsystems (JWT, refresh token rotation, RBAC, permission dependencies)
- Designing database schemas, queries, migrations, and ensuring injection prevention and transaction safety
- Writing FastAPI routes, dependency injection structures, and strict Pydantic validation schemas
- Addressing security vulnerabilities (IDOR, BOLA, brute-force protection, secret management)
- Handling concurrency, race conditions, idempotency keys, and distributed locks
- Writing unit, negative, security, and concurrency test suites

---

## Core Principles

1. **Secure by Design**: Never trust generated code or client input; enforce strict authorization and parameterized queries.
2. **Robust Authentication**: Use secure password hashing (Argon2id or bcrypt), short-lived JWT access tokens, and rotated refresh tokens.
3. **Strict Authorization**: Never trust client-provided IDs; verify resource ownership explicitly on every request.
4. **Concurrency Safety**: Protect shared state and financial transactions with database constraints, row locks, and idempotency keys.
5. **Rigorous Testing**: Validate happy paths, negative inputs, security boundaries, and concurrent execution.

---

## Architecture Patterns

### FastAPI & SQLAlchemy (Pompo Backend)
- Dependency injection (`Depends`, Annotated types) for auth, DB sessions, and services.
- Explicit Pydantic request/response schemas with comprehensive field validation.
- Centralized exception handling converting domain errors to consistent HTTP status codes and error bodies.

### Authentication & Token Rotation
- **Access Tokens**: Short-lived JWTs for stateless endpoint authorization.
- **Refresh Tokens**: Stored as SHA-256 hashes (`refresh_sessions` table) with lineage tracking (`family_id`) to detect token replay and trigger family-wide revocation.

---

## Production Backend Review Checklist

- [ ] Authentication mechanism uses secure password hashing and token rotation.
- [ ] Authorization checks prevent IDOR/BOLA and verify resource ownership.
- [ ] Database queries are parameterized (ORM or prepared statements) to prevent injection.
- [ ] External input is strictly validated via Pydantic schemas.
- [ ] Sensitive endpoints (login, register, password reset) are rate-limited.
- [ ] Concurrency-sensitive workflows use transactions, row locks, or idempotency keys.
- [ ] Comprehensive test coverage exists for happy paths, edge cases, and failure modes.
