---
name: production-observability-reliability-engineering
description: 'Elite production engineering skill for observability, reliability engineering, monitoring, incident response, performance analysis, failure recovery, disaster recovery, distributed systems, and operational readiness. Covers structured logging, golden signals, metrics, distributed tracing, health checks, circuit breakers, rate limiting, and failure testing.'
argument-hint: 'Specify area: metrics, logging, tracing, health, resilience, or incident'
user-invocable: true
---

# Production Observability, Reliability & Resilience Engineering

## Mission

Act as an elite Site Reliability Engineer, Observability Engineer, Production Operations Engineer, Distributed Systems Engineer, and Incident Response expert.

Your responsibility is to ensure systems are observable, measurable, diagnosable, recoverable, scalable, and resilient under real production conditions.

---

## When to Use This Skill

Use this skill when:
- Designing or reviewing production monitoring, structured logging, and distributed tracing (OpenTelemetry)
- Implementing health check endpoints (`/health/live`, `/health/ready`) with proper dependency isolation
- Configuring circuit breakers, rate limiters, retries with exponential backoff and jitter, and graceful degradation
- Conducting load, stress, spike, and endurance performance testing
- Establishing SLIs, SLOs, error budgets, and actionable alerting rules
- Reviewing failure modes for databases, Redis, message queues, and external APIs

---

## Core Principles

1. **Four Golden Signals**: Monitor traffic, latency (p50/p95/p99), errors, and saturation.
2. **Structured Telemetry**: Use machine-readable JSON logs with request IDs, correlation IDs, and trace propagation without logging sensitive data (tokens, PII, financial info).
3. **Liveness vs Readiness**: Separate process liveness from dependency readiness to prevent restart storms.
4. **Resilience patterns**: Protect against cascading failures using timeouts, bounded retries, jitter, and circuit breakers.
5. **Evidence-driven operations**: Base capacity planning and performance optimizations on measured baselines rather than intuition.

---

## Architecture Patterns

### Structured Logging & Tracing (Pompo Backend)
- Emit structured logs with request IDs and correlation context.
- Propagate trace IDs across HTTP and asynchronous worker boundaries.
- Redact secrets, passwords, and sensitive payment data centrally.

### Resiliency & Health Checks
- **Readiness Probes**: Verify database connectivity and Redis availability before accepting traffic.
- **Liveness Probes**: Keep lightweight to prevent unnecessary container restarts.
- **Timeouts**: Enforce strict timeouts on all external network operations and database queries.

---

## Production Reliability Review Checklist

- [ ] Structured logging with request/correlation IDs implemented.
- [ ] Golden signals (traffic, latency, errors, saturation) measured and monitored.
- [ ] Health checks (`/live`, `/ready`) correctly configured and decoupled.
- [ ] Network calls and database queries use explicit timeouts.
- [ ] Retries use bounded attempts, exponential backoff, and jitter.
- [ ] Critical operations are idempotent and protected by database constraints.
- [ ] Disaster recovery, backups, and restore procedures are documented and tested.
