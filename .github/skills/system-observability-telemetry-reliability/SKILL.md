---
name: system-observability-telemetry-reliability
description: 'Principal-level guidance for implementing production-grade observability, telemetry, reliability, structured logging, distributed tracing, metrics, health checks, alerting, and operational diagnostics in backend systems. Covers OpenTelemetry, Prometheus, Grafana, structured JSON logging, RED/USE metrics, liveness/readiness probes, and SLOs/SLIs.'
argument-hint: 'Specify area: logging, metrics, tracing, health, alerting, or slo'
user-invocable: true
---

# System Observability, Telemetry & Reliability

## Mission

Act as a Principal Site Reliability Engineer, Distributed Systems Architect, and Backend Observability Engineer.

Your objective is to build an observability architecture that allows engineers to answer quickly and reliably:
- What is happening?
- Who or what is affected?
- Where is the failure?
- Which dependency is responsible?
- Is the system healthy and ready for traffic?

---

## When to Use This Skill

Use this skill when:
- Adding or reviewing structured JSON logging, correlation IDs, and W3C Trace Context propagation
- Setting up OpenTelemetry tracing, custom spans, and sampling strategies
- Exposing Prometheus metrics (counters, gauges, histograms) using RED (Rate, Errors, Duration) and USE (Utilization, Saturation, Errors) methods
- Implementing decoupled `/health/live` (process health) and `/health/ready` (dependency readiness) endpoints
- Designing actionable alerts, SLOs, SLIs, error budgets, and Grafana operational dashboards
- Ensuring telemetry failure does not break business logic or expose sensitive data

---

## Core Principles

1. **Structured JSON Logging**: Every log entry includes level, timestamp, service, route, status code, duration, trace ID, and correlation ID.
2. **Strict Redaction**: Never log passwords, API keys, JWT tokens, credit card details, or PII.
3. **Decoupled Health Probes**: `/health/live` monitors process execution; `/health/ready` evaluates critical dependency availability.
4. **Bounded Metric Cardinality**: Never use raw user IDs, UUIDs, or un-normalized URLs as metric labels.
5. **Trace Propagation**: Propagate correlation and trace context across HTTP, gRPC, and asynchronous queue boundaries.

---

## Architecture Patterns

### Logging & Tracing
- **Request Tracing**: Assign a unique `trace_id` / `correlation_id` at the API boundary and pass it down to database queries and background tasks.
- **Span Boundaries**: Wrap external HTTP calls, database transactions, and message publishing in dedicated telemetry spans.

### Metrics & Health Checks
- **RED Method**: Measure Rate (requests/sec), Errors (4xx/5xx count), and Duration (p50/p95/p99 latency histograms).
- **Graceful Shutdown**: On termination signal, mark `/health/ready` as unready, drain pending requests, flush telemetry, and exit cleanly.

---

## Observability Review Checklist

- [ ] Production logs use structured JSON with trace and correlation context.
- [ ] Passwords, tokens, PII, and credentials are redacted at the logging layer.
- [ ] Metric labels maintain strictly bounded cardinality.
- [ ] `/health/live` and `/health/ready` probes are implemented and decoupled.
- [ ] Distributed trace IDs propagate across asynchronous worker boundaries.
- [ ] Telemetry failures fail-safe without breaking primary application workflows.
