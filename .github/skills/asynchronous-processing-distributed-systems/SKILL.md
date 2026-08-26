---
name: asynchronous-processing-distributed-systems
description: 'Principal-level guidance for designing, implementing, testing, and reviewing asynchronous processing and distributed-system infrastructure for production backend applications. Covers message brokers, background task queues, idempotency, retries, exponential backoff, dead-letter queues, delivery semantics, observability, reliability, graceful shutdown, and operational safety. Use this skill whenever backend work involves RabbitMQ, Kafka, Redis Pub/Sub, Celery, BullMQ, background workers, event-driven processing, asynchronous jobs, webhooks, scheduled jobs, or distributed workflows.'
argument-hint: 'Specify component: broker, celery, idempotency, retries, dlq, or testing'
user-invocable: true
---

# Asynchronous Processing & Distributed Systems

## Role

Act as a Principal Distributed Systems / Fintech Backend Architect.

Design for correctness first, then reliability, observability, scalability, and performance. Never treat a message broker or task queue as a simple "fire and forget" mechanism.

The implementation must remain understandable, testable, and operationally safe. Prefer explicit contracts, deterministic state transitions, durable records, and clear failure handling over clever abstractions.

---

## When to Use This Skill

Use this skill when:
- Designing or implementing asynchronous workers (Celery, background queues)
- Integrating message brokers (RabbitMQ, Kafka, Redis)
- Implementing idempotency and deduplication (Inbox/Outbox patterns)
- Configuring retries, exponential backoff, jitter, and Dead-Letter Queues (DLQ)
- Building financial reconciliation, payment webhooks, or scheduled jobs
- Ensuring graceful shutdown, concurrency control, and distributed tracing across async boundaries

---

## Core Principles

1. **Never block the request thread**: Offload heavy or failure-prone work outside the HTTP cycle.
2. **At-least-once delivery**: Assume messages can be delivered multiple times.
3. **Strict idempotency**: Every background operation must have an idempotency strategy and database-level uniqueness enforcement.
4. **Bounded retries with backoff**: Use exponential backoff and jitter; never retry indefinitely.
5. **Dead-letter isolation**: Poison messages must be routed to a DLQ with full diagnostic context.
6. **Durable acknowledgements**: Never acknowledge a message before durable state is committed.
7. **Traceability**: Propagate correlation IDs, causation IDs, and trace IDs across asynchronous boundaries.

---

## Architecture Patterns

### Celery & Redis (Python / FastAPI)
- Use Celery with Redis for distributed background task execution in Pompo backend.
- Keep task payloads small: store objects in database/storage and pass references (UUIDs/keys).
- Configure time limits, worker concurrency, and explicit queues (`media`, `notifications`, `reconciliation`, `default`).

### Idempotency & Deduplication
- **Outbox Pattern**: Commit business state and outbox events in a single database transaction.
- **Inbox Pattern / Unique Constraints**: Enforce uniqueness at the database level (`UNIQUE(event_id, consumer_name)`).

### Retry & Dead-Letter Configuration
- **Exponential Backoff**: `delay = min(max_delay, base_delay * 2^attempt) + jitter`
- **DLQ Routing**: Maximum attempts exhausted or malformed payloads route to DLQ for manual inspection and replay.

---

## Production Readiness Checklist

- [ ] Heavy work is offloaded from HTTP request threads.
- [ ] Broker choice and queue routing are explicitly defined.
- [ ] Idempotency keys and database uniqueness constraints are implemented.
- [ ] Exponential backoff with jitter prevents retry storms.
- [ ] Dead-letter queues (DLQ) capture failed and poison messages.
- [ ] Acknowledgements occur only after durable state commit.
- [ ] Structured logging preserves correlation IDs.
- [ ] Workers support graceful shutdown and signal handling.
- [ ] Integration tests cover duplicate delivery, crashes, and retry exhaustion.
