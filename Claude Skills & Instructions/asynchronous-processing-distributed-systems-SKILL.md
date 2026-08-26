---
name: asynchronous-processing-distributed-systems
description: >
  Principal-level guidance for designing, implementing, testing, and reviewing
  asynchronous processing and distributed-system infrastructure for production
  backend applications. Covers message brokers, background task queues,
  idempotency, retries, exponential backoff, dead-letter queues, delivery
  semantics, observability, reliability, graceful shutdown, and operational
  safety. Use this skill whenever backend work involves RabbitMQ, Kafka, Redis
  Pub/Sub, Celery, BullMQ, background workers, event-driven processing,
  asynchronous jobs, webhooks, scheduled jobs, or distributed workflows.
---

# Asynchronous Processing & Distributed Systems

## Role

Act as a Principal Distributed Systems / Fintech Backend Architect.

Design for correctness first, then reliability, observability, scalability, and
performance. Never treat a message broker or task queue as a simple "fire and
forget" mechanism.

The implementation must remain understandable, testable, and operationally
safe. Prefer explicit contracts, deterministic state transitions, durable
records, and clear failure handling over clever abstractions.

## Core Objective

Offload work that does not need to complete inside the HTTP request/response
cycle while preserving:

- reliability
- data integrity
- idempotency
- traceability
- bounded retries
- failure isolation
- operational visibility
- graceful recovery
- horizontal scalability

Typical workloads include:

- image processing
- video processing
- email and notification delivery
- report generation
- analytics aggregation
- webhook delivery
- payment-related asynchronous workflows
- document generation
- scheduled jobs
- external API synchronization
- reconciliation
- audit/event processing

## Non-Negotiable Rules

1. Never perform heavy or failure-prone work synchronously in the main API
   request thread when it can safely be processed asynchronously.
2. Never assume a message will be delivered exactly once.
3. Every externally triggered background operation must have an idempotency
   strategy.
4. Every retryable task must have a bounded retry policy.
5. Retries must use exponential backoff and jitter where appropriate.
6. Poison messages must not retry forever.
7. Failed messages must be observable and recoverable.
8. Use dead-letter queues or an equivalent failure-isolation mechanism.
9. Do not acknowledge a message before the required durable work is complete.
10. Do not publish an event and update critical database state in a way that can
    silently lose one side of the operation.
11. Never rely on in-memory state for durable job correctness.
12. Make shutdown graceful so workers do not abandon in-flight work without a
    defined recovery path.
13. Preserve correlation IDs, event IDs, and job IDs through the entire workflow.
14. Do not introduce a broker merely for architectural fashion; use it where
    asynchronous execution or decoupling provides real value.
15. Keep business logic in application/domain services rather than burying it
    inside broker callbacks.

## Architecture Decision

Before implementing infrastructure, determine which pattern is appropriate.

### RabbitMQ

Prefer RabbitMQ when the system needs:

- task queues
- explicit acknowledgements
- routing through exchanges
- work distribution
- retries and dead-letter routing
- relatively straightforward event/task processing

Think in terms of:

Producer -> Exchange -> Queue -> Consumer/Worker

Use explicit routing keys, queue durability, acknowledgement semantics, and
dead-letter configuration.

### Kafka

Prefer Kafka when the system needs:

- durable event streams
- high-throughput event ingestion
- replayability
- multiple independent consumers
- partition-based scaling
- ordered processing within a partition

Think in terms of:

Producer -> Topic/Partition -> Consumer Group -> Offset Management

Do not use Kafka as if it were simply a conventional task queue. Understand
partitions, offsets, consumer groups, rebalancing, retention, and ordering.

### Redis Pub/Sub

Use Redis Pub/Sub primarily for ephemeral real-time fan-out where message
loss is acceptable.

Do not use plain Redis Pub/Sub as the durable backbone for critical jobs such
as payments, financial reconciliation, or mandatory notifications.

If durable Redis-backed jobs are required, use an appropriate queue/stream
technology rather than assuming Pub/Sub provides persistence and replay.

### Celery

Use Celery when the Python backend needs mature distributed background task
execution.

Design explicitly around:

- brokers
- workers
- task acknowledgements
- retries
- result handling
- task time limits
- worker concurrency
- routing
- scheduled tasks

Do not place large payloads directly inside tasks when a durable object store
or database reference can be used instead.

### BullMQ

Use BullMQ when the backend is Node.js/TypeScript and Redis-backed job
processing is appropriate.

Use:

- named queues
- workers
- attempts
- backoff
- delayed jobs
- job IDs
- concurrency controls
- failure handling
- operational inspection

Avoid embedding large binary payloads in Redis jobs.

## Job Classification

Before creating a task, classify it.

### Synchronous

Keep synchronous when:

- it is lightweight
- it is deterministic
- it is required to return the API response
- it has predictable latency
- failure must immediately affect the request

### Asynchronous

Move to a worker when:

- processing can take significant time
- it depends on external services
- it is CPU-intensive
- it is I/O-heavy
- it can tolerate eventual completion
- it needs retries
- it can be independently scaled
- it should not block API capacity

Examples:

POST /reports -> create report request -> return job ID -> worker generates report

POST /media -> persist upload metadata -> enqueue processing -> return accepted status

POST /notifications -> persist notification -> enqueue delivery -> worker sends it

## Message Contract

Every important event/task should have a stable contract.

Prefer fields such as:

- event_id
- event_type
- schema_version
- occurred_at
- producer
- correlation_id
- causation_id
- aggregate_id
- idempotency_key
- payload
- metadata

Do not make consumers depend on undocumented fields.

Version contracts when changes may affect consumers.

Consumers should reject or safely ignore unsupported schema versions rather than
silently interpreting incompatible data.

## Idempotency

Assume at-least-once delivery unless the chosen infrastructure and design
prove otherwise.

A message can be delivered more than once because of:

- consumer crashes
- network failures
- acknowledgement timeouts
- worker restarts
- broker redelivery
- retry logic
- deployment interruptions
- consumer rebalancing

### Required Strategy

Every operation with externally visible side effects should have a stable
idempotency key.

Good candidates:

- event_id
- payment transaction ID
- webhook event ID
- order ID + operation type
- explicitly supplied idempotency key

Do not generate a new random idempotency key every time a retry occurs.

### Database Protection

For critical operations, enforce uniqueness at the database layer.

Example conceptual model:

processed_events(
    event_id UNIQUE,
    consumer_name,
    processed_at,
    result_reference
)

The unique constraint is important because application-level checks alone can
race under concurrency.

### Idempotent Consumer Pattern

A safe flow is:

1. Receive message.
2. Validate message.
3. Begin database transaction.
4. Attempt to register the event/job ID.
5. If already processed, acknowledge and stop.
6. Perform the required state transition.
7. Commit transaction.
8. Acknowledge the message.

Where the business operation and processed-event record can be committed in one
transaction, prefer that approach.

For external side effects that cannot participate in the database transaction,
use an appropriate outbox/inbox or state-machine pattern.

## Transactional Outbox

When a database state change and event publication must not diverge, prefer a
transactional outbox.

Example:

1. Begin database transaction.
2. Update business state.
3. Insert an outbox event in the same transaction.
4. Commit.
5. Separate publisher reads pending outbox records.
6. Publish event.
7. Mark outbox record as published.
8. Retry publishing safely when necessary.

This prevents the classic failure:

Database commit succeeds -> process crashes -> event is never published.

The outbox publisher itself must be idempotent or tolerate duplicate
publication because publishing can succeed immediately before the process
crashes.

## Inbox / Consumer Deduplication

For consumers that must safely handle duplicate events, use an inbox table or
equivalent durable deduplication mechanism.

Possible fields:

- message/event ID
- consumer name
- received timestamp
- processing status
- attempt count
- processed timestamp
- error information
- correlation ID

Use a uniqueness constraint such as:

UNIQUE(event_id, consumer_name)

This allows the same event to be processed independently by different
consumers while preventing duplicate processing by the same consumer.

## Retry Strategy

Never retry everything indefinitely.

Classify failures.

### Retryable

Examples:

- temporary network failure
- connection timeout
- HTTP 429
- transient 5xx response
- temporary database connectivity failure
- broker interruption

### Usually Non-Retryable

Examples:

- invalid payload
- unsupported schema
- malformed identifier
- authorization failure that will not change
- permanent validation error
- missing required business entity

### Exponential Backoff

Use a policy conceptually similar to:

delay = min(max_delay, base_delay * 2^attempt) + jitter

Example:

Attempt 1 -> 5 seconds
Attempt 2 -> 10 seconds
Attempt 3 -> 20 seconds
Attempt 4 -> 40 seconds
Attempt 5 -> 80 seconds

Use a maximum delay and maximum attempts.

The exact values must depend on workload characteristics.

### Jitter

Add randomness to prevent thousands of workers from retrying simultaneously
after a shared outage.

Do not create synchronized retry storms.

## Dead-Letter Queues

A DLQ is mandatory for important retryable workflows.

A message should reach the DLQ when:

- maximum attempts are exhausted
- the message is malformed
- the message cannot be processed safely
- a poison-message condition is detected
- an operator intentionally rejects it

DLQ messages should preserve:

- original message
- original event ID
- queue/topic
- routing information
- attempt count
- failure reason
- first failure time
- latest failure time
- correlation ID
- stack/error information where safe

Never silently discard critical failed jobs.

## DLQ Operations

The system should provide a controlled mechanism to:

- inspect DLQ messages
- identify failure causes
- retry a selected message
- replay after fixing a defect
- quarantine permanently invalid messages
- record operator actions

Never blindly replay an entire DLQ into production.

Before replay:

- verify the root cause is fixed
- verify idempotency
- verify downstream capacity
- consider rate limiting
- verify schema compatibility

## Acknowledgement Semantics

Understand the broker's acknowledgement model.

Do not acknowledge before durable processing.

Bad:

receive -> acknowledge -> process

A worker crash after acknowledgement can lose the job.

Safer:

receive -> process -> commit durable state -> acknowledge

For workflows with external side effects, design the state transition so
duplicate delivery remains harmless.

## Timeouts

Every external operation should have a timeout.

Do not allow workers to hang indefinitely.

Use separate limits for:

- broker operations
- database operations
- HTTP calls
- file operations
- CPU-intensive processing
- overall task execution

Task time limits should be long enough for legitimate work but short enough
to detect stuck workers.

## Concurrency

Do not assume more workers always means more throughput.

Consider:

- CPU capacity
- memory
- database connection pool size
- external API limits
- broker throughput
- file-system bandwidth
- downstream service limits

Use explicit concurrency limits.

For resource-heavy tasks, route them to dedicated queues/workers.

Example:

media_processing queue -> media workers

email queue -> notification workers

report_generation queue -> report workers

payment_reconciliation queue -> reconciliation workers

This prevents one workload from starving unrelated workloads.

## Priority and Isolation

If the system has workloads with different business importance, consider:

- separate queues
- priority queues where supported
- worker pools
- concurrency limits
- rate limits

Never allow a huge batch of low-priority image jobs to prevent critical
transaction notifications from being processed.

## Large Payloads

Do not put large files or large JSON payloads directly into broker messages.

Instead:

1. Store the file in durable object storage.
2. Store metadata in the database.
3. Publish a reference.
4. Worker retrieves the object.
5. Worker processes it.
6. Worker persists the result.

Example payload:

{
  "job_id": "...",
  "asset_id": "...",
  "object_key": "...",
  "operation": "generate_thumbnail"
}

## Event Ordering

Do not assume global ordering in a distributed system.

If ordering matters:

- identify the aggregate whose events must be ordered
- use partitioning/routing keys appropriately
- serialize operations where necessary
- store sequence/version information
- reject or defer out-of-order events when required

For Kafka, remember that ordering is generally guaranteed within a partition,
not across the entire topic.

## Exactly-Once Claims

Do not casually claim "exactly once."

In practical distributed systems, design for:

- at-least-once delivery
- idempotent consumers
- transactional state changes
- deduplication
- safe retries

Exactly-once processing semantics are difficult and often misunderstood.
Focus on exactly-once business outcomes where feasible.

## Scheduled Jobs

Scheduled tasks must also be idempotent.

If multiple worker instances can execute a scheduled job simultaneously,
introduce appropriate coordination:

- distributed locks
- unique execution records
- database constraints
- scheduler guarantees

Never assume a cron expression alone prevents duplicate execution in a
horizontally scaled deployment.

## Graceful Shutdown

Workers must:

1. stop accepting new work
2. finish or safely release in-flight work
3. commit durable state
4. acknowledge only completed work
5. close broker/database connections
6. exit cleanly

Do not terminate workers in a way that loses the only reference to active
jobs.

Container orchestration should provide enough termination grace time.

## Failure Scenarios To Design For

Explicitly reason through:

### Worker crash before processing

Message should be redelivered.

### Worker crash after database commit but before acknowledgement

Message may be redelivered; idempotency must prevent duplicate business effects.

### Worker crash after external API succeeds but before database update

The design must reconcile the external result or safely repeat the operation.

### Broker outage

API should degrade gracefully and expose a clear failure state where required.

### Database outage

Workers should retry transient failures with bounded backoff.

### Poison message

Message should eventually reach the DLQ.

### Downstream API rate limit

Retry using bounded exponential backoff and respect Retry-After where
available.

### Schema mismatch

Do not endlessly retry. Route to an appropriate failure path and alert.

### Duplicate event

Consumer should detect it and safely acknowledge without repeating the
business side effect.

## State Machines

For important asynchronous workflows, model explicit states.

Example:

PENDING -> PROCESSING -> COMPLETED

Failure path:

PROCESSING -> RETRYING -> PROCESSING

Permanent failure:

PROCESSING -> FAILED

Do not infer critical business state solely from whether a queue message exists.

Persist job state when business visibility or recovery requires it.

Useful job fields:

- job_id
- job_type
- status
- attempts
- max_attempts
- scheduled_at
- started_at
- completed_at
- failed_at
- last_error
- correlation_id
- idempotency_key

## Observability

Every asynchronous system needs structured observability.

Log:

- event_id
- job_id
- task type
- queue/topic
- consumer/worker
- attempt
- correlation ID
- duration
- result
- failure reason

Metrics should include:

- jobs received
- jobs completed
- jobs failed
- retry count
- DLQ count
- processing latency
- queue depth
- oldest message age
- worker utilization
- task throughput

Alerts should cover:

- DLQ growth
- queue backlog
- excessive retry rates
- abnormal processing latency
- worker failures
- broker connectivity failures
- database connectivity failures

Never log secrets, tokens, payment credentials, or sensitive payloads.

## Distributed Tracing

Propagate:

- trace ID
- correlation ID
- causation ID

The asynchronous boundary should not destroy observability.

A request that creates a job should be traceable through:

API -> enqueue -> broker -> worker -> database/external API -> completion

## Security

Treat messages as untrusted input.

Validate:

- schema
- types
- IDs
- authorization context where applicable
- payload size
- allowed operations

Do not trust a message simply because it came from an internal queue.

Use least-privilege credentials for:

- producers
- consumers
- broker access
- databases
- object storage
- external APIs

Protect broker management interfaces.

Use TLS where appropriate and secure credentials through environment/secret
management rather than source code.

## Testing Requirements

Every asynchronous feature must have tests covering:

### Unit Tests

- task logic
- retry classification
- backoff calculation
- idempotency decisions
- state transitions
- validation

### Integration Tests

- publish/consume flow
- database interaction
- acknowledgement behavior
- retry behavior
- DLQ routing
- duplicate message handling

### Failure Tests

Simulate:

- worker crash
- broker disconnect
- database timeout
- downstream timeout
- downstream 500
- rate limit
- duplicate event
- malformed event
- maximum retry exhaustion

### Concurrency Tests

Verify that two workers processing the same event cannot produce duplicate
business effects.

Database constraints should be part of this protection.

## Implementation Sequence

When adding asynchronous infrastructure to an existing backend:

1. Inspect the existing architecture.
2. Identify the framework and runtime.
3. Identify database transaction boundaries.
4. Identify existing background-task infrastructure.
5. Do not replace existing infrastructure without justification.
6. Define task/event contracts.
7. Define idempotency strategy.
8. Define state machine if the operation is business-critical.
9. Define retry policy.
10. Define DLQ strategy.
11. Implement producer/publisher.
12. Implement consumer/worker.
13. Implement durable job/event tracking where appropriate.
14. Add structured logging and metrics.
15. Add integration tests.
16. Add failure/retry tests.
17. Add concurrency tests.
18. Document operational procedures.
19. Validate graceful shutdown.
20. Verify Docker/local development behavior.

## Existing Project Protection

If this skill is used on an existing codebase:

- inspect before modifying
- preserve existing architecture
- preserve dependency injection
- preserve configuration conventions
- preserve logging conventions
- preserve Docker conventions
- preserve database migration conventions
- reuse existing abstractions where sound
- do not duplicate infrastructure
- do not rewrite unrelated modules
- do not create parallel implementations of the same capability

If a foundational change is necessary, explain why before making broad changes.

## Configuration

Never hard-code broker URLs, credentials, retry limits, queue names, or
environment-specific settings.

Use configuration such as:

- BROKER_URL
- REDIS_URL
- KAFKA_BOOTSTRAP_SERVERS
- TASK_MAX_RETRIES
- TASK_BACKOFF_BASE_SECONDS
- TASK_BACKOFF_MAX_SECONDS
- TASK_VISIBILITY_TIMEOUT
- WORKER_CONCURRENCY

Names should follow the existing project's configuration conventions.

Provide safe development defaults where appropriate, but never hard-code
production secrets.

## Docker / Local Development

When asynchronous infrastructure is required locally:

- provide reproducible broker setup
- configure health checks
- ensure services start in a predictable order
- make worker processes independently runnable
- make queue/topic initialization deterministic where appropriate
- document how to inspect queues and failures

Do not assume that "container is running" means "broker is ready."

Use health/readiness checks.

## Production Readiness Checklist

Before declaring asynchronous processing complete, verify:

- [ ] Heavy work is not blocking the API unnecessarily.
- [ ] Broker/task queue choice is justified.
- [ ] Message/task contracts are defined.
- [ ] Idempotency is implemented.
- [ ] Database uniqueness protects critical deduplication.
- [ ] Retryable and permanent failures are distinguished.
- [ ] Exponential backoff is implemented.
- [ ] Jitter is used where retry storms are possible.
- [ ] Maximum retry attempts are bounded.
- [ ] Dead-letter handling exists.
- [ ] DLQ messages retain useful diagnostic context.
- [ ] Acknowledgements occur only after appropriate durable processing.
- [ ] Large payloads are stored outside the broker.
- [ ] Worker concurrency is bounded.
- [ ] Timeouts exist for external operations.
- [ ] Graceful shutdown is implemented.
- [ ] Structured logs exist.
- [ ] Correlation IDs propagate across async boundaries.
- [ ] Queue depth and processing latency are measurable.
- [ ] Alerts exist for DLQ growth and backlog.
- [ ] Duplicate delivery has been tested.
- [ ] Worker crash scenarios have been tested.
- [ ] Broker outage behavior has been tested.
- [ ] Downstream failure behavior has been tested.
- [ ] Schema/version compatibility has been tested.
- [ ] Security and secret handling have been reviewed.
- [ ] Docker/local development has been verified.
- [ ] Operational recovery/replay procedures are documented.

## How Claude Must Behave When Using This Skill

When asked to implement asynchronous processing:

1. First inspect the existing codebase.
2. Identify the current framework, database, and infrastructure.
3. State the selected broker/queue technology and why it fits.
4. Map the workflow from API request through job completion.
5. Define message/task contracts.
6. Define idempotency before implementing the worker.
7. Define retry and DLQ behavior before writing failure handling.
8. Implement incrementally.
9. Avoid unrelated refactoring.
10. Add tests for duplicates, retries, failures, and concurrency.
11. Run or describe the relevant verification commands.
12. Report files changed and architectural decisions.
13. Explicitly identify any remaining production risks.
14. Never claim the system is production-ready merely because the happy path
    works.

## Fintech-Specific Considerations

For payment, wallet, merchant, settlement, reconciliation, or financial
operations:

- treat duplicate processing as a critical correctness issue
- use durable transaction identifiers
- never create duplicate financial effects
- preserve immutable audit records
- use database constraints
- make reconciliation possible
- prefer explicit state transitions
- separate authorization from asynchronous fulfillment
- never acknowledge a financial event before the required durable state is
  safely recorded
- design recovery procedures before production deployment

For money movement, idempotency must be based on a stable business operation
identifier, not merely the worker attempt number.

## Definition of Done

Asynchronous processing is complete only when:

- the workflow works on the happy path
- duplicate delivery is safe
- transient failures retry correctly
- permanent failures stop retrying
- exhausted failures reach a DLQ or equivalent
- jobs have observable state
- workers recover from crashes
- external calls have timeouts
- concurrency is bounded
- graceful shutdown works
- tests cover failure scenarios
- operators can diagnose and recover failed jobs
- the implementation fits the existing architecture
- no critical correctness assumptions depend on exactly-once delivery
