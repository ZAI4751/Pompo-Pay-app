---
name: system-observability-telemetry-reliability
description: >
  Principal-level guidance for implementing production-grade observability,
  telemetry, reliability, structured logging, distributed tracing, metrics,
  health checks, alerting, and operational diagnostics in backend systems.
  Use this skill whenever Claude is asked to add or review logging, metrics,
  tracing, health endpoints, Prometheus, Grafana, OpenTelemetry, service
  monitoring, reliability instrumentation, readiness/liveness probes,
  performance telemetry, or production observability.
---

# System Observability, Telemetry & Reliability

## Role

Act as a Principal Site Reliability Engineer, Distributed Systems Architect,
and Backend Observability Engineer.

The objective is not merely to "add logs."

Build an observability system that allows engineers to answer, quickly and
reliably:

- What is happening?
- Who or what is affected?
- When did it start?
- Where is the failure?
- How many requests are affected?
- Which dependency is responsible?
- Is the system healthy?
- Is the system becoming unhealthy?
- Can the issue be reproduced from telemetry?
- Can operators diagnose the problem without attaching a debugger?

Observability must be designed as part of the architecture rather than added
after implementation.

## Core Pillars

Treat these as complementary signals:

1. Logs — detailed event records and diagnostic context.
2. Metrics — aggregated numerical measurements and trends.
3. Traces — request-level and cross-service execution paths.
4. Health checks — machine-readable service health and dependency readiness.
5. Alerts — actionable notifications based on meaningful failure conditions.
6. Reliability signals — availability, latency, errors, saturation, and
   capacity.

Do not rely on any single signal.

## Non-Negotiable Rules

1. Use structured JSON logging in production.
2. Every request must have a correlation/trace context.
3. Propagate trace context across service boundaries.
4. Never log passwords, API keys, authentication tokens, payment credentials,
   private keys, or unnecessary sensitive information.
5. Health endpoints must distinguish liveness from readiness.
6. Liveness must not fail merely because a dependency is temporarily down.
7. Readiness must reflect whether the instance can safely receive traffic.
8. Metrics must use bounded labels/cardinality.
9. Never put raw user IDs, transaction IDs, URLs with arbitrary parameters,
   email addresses, or other unbounded values into metric labels.
10. Instrument external dependencies separately from application latency.
11. Errors must be measurable, not merely logged.
12. Logs must be searchable by correlation ID.
13. Production telemetry must not depend on local console output alone.
14. Observability must have controlled overhead.
15. Do not claim a system is production-ready without testing telemetry failure
    modes and operational behavior.

## Observability Architecture

A typical architecture should resemble:

Client
  |
  v
API Gateway / Load Balancer
  |
  v
Service
  |---- structured logs ----> Log Collector / Log Platform
  |
  |---- metrics -----------> Prometheus
  |                              |
  |                              v
  |                           Grafana
  |
  |---- traces ------------> OpenTelemetry Collector
                                 |
                                 +--> Trace Backend

The exact products may differ, but the separation of concerns should remain.

## Structured JSON Logging

Production logs should be machine-readable JSON.

Prefer fields such as:

- timestamp
- level
- service
- environment
- version
- logger
- message
- trace_id
- span_id
- correlation_id
- request_id
- method
- route
- status_code
- duration_ms
- user_id where safe and appropriate
- tenant_id where safe and appropriate
- error_type
- error_code
- stack_trace for unexpected server errors
- event_name

Example conceptual record:

{
  "timestamp": "2026-08-22T19:00:00Z",
  "level": "INFO",
  "service": "payment-api",
  "environment": "production",
  "trace_id": "abc123",
  "span_id": "def456",
  "correlation_id": "abc123",
  "method": "POST",
  "route": "/payments",
  "status_code": 202,
  "duration_ms": 84,
  "message": "Payment request accepted"
}

Do not create logs that require parsing human prose to understand important
fields.

## Log Levels

Use levels consistently.

### DEBUG

Detailed diagnostic information useful during development or targeted
troubleshooting.

Do not enable high-volume DEBUG logging indefinitely in production.

### INFO

Normal significant lifecycle events.

Examples:

- application started
- worker started
- request completed
- job accepted
- configuration loaded without exposing secrets

### WARNING

Unexpected but recoverable situations.

Examples:

- retry occurred
- dependency degraded
- approaching resource threshold
- non-critical configuration fallback

### ERROR

An operation failed and requires attention or investigation.

Examples:

- request failed unexpectedly
- external dependency failure
- background task permanently failed

### CRITICAL

The service has experienced a severe condition requiring immediate operator
attention.

Do not use CRITICAL for ordinary request errors.

## Correlation IDs

Every incoming request must receive or inherit a correlation context.

Use a standard trace context where possible, such as W3C Trace Context.

The system should support:

- trace_id
- span_id
- correlation_id
- request_id where the architecture requires it

Prefer using the distributed trace ID as the primary cross-service correlation
identifier.

If a trusted upstream provides trace context, validate and propagate it rather
than blindly accepting arbitrary values.

## Trace Propagation

For service-to-service communication, propagate tracing context through:

- HTTP headers
- asynchronous messages
- task queues
- Kafka records
- RabbitMQ messages
- scheduled jobs where applicable

Do not lose trace context at asynchronous boundaries.

Example conceptual flow:

Client
 -> API trace/span
 -> Service A span
 -> Service B span
 -> Database span
 -> External API span

Operators should be able to inspect one trace and understand the complete
request path.

## OpenTelemetry

When practical, prefer OpenTelemetry for standardized instrumentation.

Use it for:

- traces
- metrics where appropriate
- context propagation
- automatic instrumentation
- custom spans
- exporter integration

Do not blindly instrument every function.

Create custom spans around meaningful boundaries such as:

- database operations
- external API calls
- message publication
- message consumption
- file processing
- significant business operations

Avoid high-volume spans that add cost without diagnostic value.

## Trace Sampling

Tracing can become expensive at scale.

Use an appropriate sampling strategy.

Possible approaches:

- head-based sampling
- tail-based sampling
- higher sampling for errors
- higher sampling for slow requests
- lower sampling for routine successful traffic

Errors and unusual latency should be easier to investigate than ordinary
successful requests.

Do not sample away all evidence of critical failures.

## HTTP Request Instrumentation

Capture:

- HTTP method
- normalized route
- status code
- duration
- request/response size where useful
- trace ID
- service name

Use normalized route templates.

Prefer:

/users/{id}

over:

/users/928371

This prevents high-cardinality metric names and labels.

## Sensitive HTTP Data

Never automatically log:

- Authorization headers
- cookies
- access tokens
- refresh tokens
- passwords
- credit card numbers
- CVV
- private keys
- session secrets

Be cautious with:

- request bodies
- response bodies
- query parameters
- uploaded documents
- identity information

If payload logging is necessary for a specific debugging workflow, use explicit
redaction and controlled sampling.

## Metrics

Metrics should answer operational questions.

At minimum track:

### Request Metrics

- request count
- successful request count
- error count
- request duration
- request rate

### Infrastructure Metrics

- CPU usage
- memory usage
- disk usage
- network throughput
- process restarts
- file descriptor usage where relevant

### Database Metrics

- connection pool utilization
- query latency
- active connections
- connection failures
- transaction failures
- slow query counts where available

### Queue Metrics

- queue depth
- oldest message age
- processing rate
- failure rate
- retry count
- dead-letter count

### External Dependency Metrics

For each important dependency:

- request count
- latency
- timeout count
- error count
- rate-limit responses
- availability

## Prometheus Metrics

When Prometheus is used, expose a scrape endpoint such as:

/metrics

Do not protect it in a way that prevents the configured monitoring system from
accessing it, but do not expose sensitive operational data publicly.

Typical metric families include:

http_requests_total
http_request_duration_seconds
http_requests_in_flight
process_cpu_seconds_total
process_resident_memory_bytes

Use counters, gauges, histograms, and summaries appropriately.

Prefer histograms for request latency when percentile analysis is required.

## Metric Naming

Use consistent names and units.

Prefer:

http_request_duration_seconds

rather than:

request_time

Use seconds for durations when following Prometheus conventions.

Use counters for cumulative events:

http_requests_total

Use gauges for values that can move up and down:

active_connections

Use histograms for distributions:

http_request_duration_seconds

## Metric Labels

Labels must have bounded cardinality.

Good:

method="GET"
route="/users/{id}"
status_code="200"
environment="production"

Dangerous:

user_id="928371"
email="person@example.com"
transaction_id="random-value"
raw_url="/users/928371?token=..."

High-cardinality labels can overload Prometheus and make the monitoring
system itself unreliable.

## RED Method

For APIs and services, track:

### Rate

How many requests are being processed?

### Errors

How many requests are failing?

### Duration

How long do requests take?

These should be available by service and useful route categories.

## USE Method

For infrastructure/resources, track:

### Utilization

How much of the resource is being used?

### Saturation

How much work is queued or waiting?

### Errors

How often is the resource failing?

Apply this to:

- CPU
- memory
- disk
- network
- database pools
- worker pools

## Latency Percentiles

Average latency alone is insufficient.

Track meaningful percentiles such as:

- p50
- p90
- p95
- p99

Tail latency matters because a small percentage of very slow requests can
represent a serious user-facing problem.

Do not blindly choose percentile thresholds without understanding the workload.

## Error Rates

Measure errors numerically.

Track at least:

- total requests
- 4xx responses
- 5xx responses
- dependency failures
- timeout failures
- application exceptions

Distinguish client errors from server errors.

A spike in 404 responses is not equivalent to a spike in database failures.

## Health Checks

Implement two separate concepts.

### /health/live

Answers:

"Is this process alive enough that restarting it might be appropriate?"

Liveness should generally check only the local process/runtime.

Do not make liveness depend on:

- database availability
- Redis
- Kafka
- RabbitMQ
- external APIs

Otherwise a dependency outage can cause every instance to be restarted,
making the outage worse.

### /health/ready

Answers:

"Can this instance safely receive production traffic?"

Readiness may check critical dependencies such as:

- database connectivity
- required cache connectivity
- message broker connectivity
- essential configuration
- migration state where appropriate

If the service cannot perform its core responsibility, it should become
unready.

## Health Check Response

Use a machine-readable response.

Conceptually:

{
  "status": "ok",
  "service": "payment-api",
  "version": "1.4.2",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}

Do not expose:

- credentials
- connection strings
- internal secrets
- sensitive infrastructure details
- raw exception traces

Public-facing health endpoints should expose even less information.

## Health Check Failure Semantics

Do not make health checks unnecessarily expensive.

A readiness probe may execute a lightweight dependency check.

Do not run expensive queries or complex business workflows on every health
probe.

Cloud load balancers and orchestrators can call health endpoints frequently.

Design accordingly.

## Startup Health

Distinguish:

- application starting
- application alive
- application ready

A process may be alive but not ready during:

- database initialization
- cache warmup
- configuration loading
- migration validation
- dependency connection establishment

Use startup/readiness mechanisms appropriate to the deployment environment.

## Kubernetes / Cloud Integration

Health endpoints should map cleanly to orchestration systems.

Typical mapping:

livenessProbe -> /health/live

readinessProbe -> /health/ready

If the environment supports startup probes, use them for slow initialization.

The service should be removed from load-balancer traffic before being
terminated.

## Graceful Shutdown

Observability must remain coherent during shutdown.

On shutdown:

1. stop accepting new traffic
2. mark readiness as failed/unready
3. drain in-flight requests
4. finish or safely release background work
5. flush telemetry where appropriate
6. close connections
7. exit

Do not allow the load balancer to continue sending traffic to an instance
that is already terminating.

## Alerting

Alerts must be actionable.

Avoid alerting on every error.

Good alerts include:

- sustained high 5xx rate
- critical latency degradation
- service unavailable
- readiness failures across instances
- database connection exhaustion
- queue backlog exceeding safe limits
- DLQ growth
- worker crash loops
- memory pressure
- disk exhaustion
- certificate expiry
- unusual dependency failure rates

Each alert should have:

- clear condition
- severity
- affected service
- likely impact
- useful dashboard
- suggested investigation path
- owner/on-call routing where applicable

## Alert Fatigue

Do not create alerts that nobody can act on.

A warning that fires hundreds of times per day without intervention becomes
background noise.

Prefer symptoms that indicate real user or system impact.

Use warning-level dashboards for trends and alerts for conditions requiring
action.

## SLOs and SLIs

For important production systems, define:

### SLI

What is being measured?

Examples:

- successful request percentage
- request latency
- payment processing success
- report completion time

### SLO

What reliability target is expected?

Example:

99.9% of valid API requests succeed over a defined measurement window.

Do not choose arbitrary SLOs. Base them on business requirements and realistic
system capability.

## Error Budgets

When SLOs are established, calculate the allowed failure budget.

This can guide decisions about:

- release risk
- reliability work
- incident response
- feature velocity

Do not treat 100% availability as a practical default.

## Reliability Signals

Use the four golden signals where applicable:

1. Latency
2. Traffic
3. Errors
4. Saturation

Correlate these signals rather than examining them independently.

Example:

Traffic rises -> CPU rises -> p99 latency rises -> 5xx errors rise.

That tells a more useful story than any single graph.

## Dashboards

Create dashboards for:

### Service Overview

- request rate
- success/error rate
- p50/p95/p99 latency
- CPU
- memory
- instance count

### Dependencies

- database latency
- database errors
- cache performance
- external API latency
- external API errors

### Async Processing

- queue depth
- processing latency
- retries
- failures
- DLQ count

### Infrastructure

- CPU
- memory
- disk
- network
- container restarts

Avoid dashboards containing dozens of decorative graphs with no operational
purpose.

## Incident Investigation Workflow

When an issue occurs:

1. Identify affected service.
2. Check request rate and error rate.
3. Check latency percentiles.
4. Check saturation.
5. Identify when the degradation began.
6. Inspect traces for representative failures.
7. Search logs using trace/correlation IDs.
8. Inspect dependency metrics.
9. Check recent deployments/configuration changes.
10. Check queues and background workers.
11. Determine whether the issue is isolated or systemic.
12. Mitigate first when user impact is severe.
13. Preserve evidence.
14. Perform root-cause analysis after stabilization.

## Logging and Tracing Correlation

A trace should allow an operator to move from:

Dashboard -> metric anomaly -> trace -> log entries -> dependency failure

Every layer should preserve enough context to make that transition possible.

## Asynchronous Boundaries

When a request creates a background job:

API request
 -> trace/span
 -> enqueue job
 -> worker receives job
 -> worker creates/continues trace context
 -> processing
 -> completion

Persist correlation identifiers when a job may need investigation later.

Do not assume the original HTTP request still exists when the worker runs.

## Database Observability

Instrument database interactions carefully.

Track:

- connection pool utilization
- connection acquisition time
- query duration
- transaction duration
- failures
- deadlocks
- timeout counts

Do not log every SQL statement in production unless there is a specific
controlled diagnostic reason.

When SQL logging is enabled for debugging, protect credentials and sensitive
query parameters.

## External API Observability

For each critical external API, track:

- request count
- success count
- failure count
- timeout count
- latency
- rate-limit responses
- circuit-breaker state where applicable

Do not expose secrets in request/response telemetry.

## Resource Monitoring

Track CPU and memory at the process/container/service level.

Memory requires particular attention because leaks often appear as gradual
growth rather than immediate failure.

Alert on sustained abnormal resource consumption rather than tiny temporary
spikes.

## Reliability Under Telemetry Failure

The application must not become unavailable merely because telemetry is down.

If:

- Prometheus is unavailable
- trace exporter is unavailable
- log collector is temporarily unavailable

the business service should continue operating where safely possible.

Use bounded buffers, non-blocking exporters, batching, and backpressure
appropriate to the telemetry stack.

Never allow telemetry exporters to consume unbounded memory.

## Privacy and Data Protection

Observability data can contain highly sensitive information.

Apply:

- field redaction
- data minimization
- retention policies
- access control
- encryption
- environment separation

Do not use logs as an unrestricted database of user information.

For financial systems, never log:

- full payment card numbers
- CVV
- authentication secrets
- private cryptographic keys
- raw access tokens

Mask or tokenize other sensitive identifiers where appropriate.

## Cost Control

Observability has a cost.

Control:

- log volume
- trace volume
- metric cardinality
- retention periods
- high-frequency scraping
- verbose debug logging

Optimize for useful signal, not maximum data volume.

## Testing Requirements

Observability must be tested.

### Logging Tests

Verify:

- logs are valid JSON
- required fields exist
- correlation IDs appear
- secrets are redacted
- exceptions contain useful context

### Trace Tests

Verify:

- incoming trace context is recognized
- outgoing requests propagate context
- asynchronous jobs preserve correlation context
- spans close correctly after failures

### Metrics Tests

Verify:

- counters increment correctly
- latency histograms record observations
- error metrics distinguish failures correctly
- labels remain bounded

### Health Tests

Verify:

- /health/live succeeds when dependencies are down
- /health/ready fails when critical dependencies are unavailable
- health responses contain no secrets
- health checks remain fast
- startup and shutdown states behave correctly

### Failure Tests

Simulate:

- database outage
- cache outage
- broker outage
- external API timeout
- telemetry collector outage
- high CPU
- high memory
- worker failure

The service should degrade predictably.

## Implementation Sequence

When adding observability to an existing backend:

1. Inspect the existing framework and architecture.
2. Identify current logging.
3. Identify current metrics.
4. Identify current tracing.
5. Identify existing health endpoints.
6. Identify deployment/orchestration platform.
7. Preserve existing conventions where sound.
8. Establish correlation/trace context.
9. Implement structured logging.
10. Instrument HTTP requests.
11. Instrument database and dependency boundaries.
12. Add metrics.
13. Add /health/live.
14. Add /health/ready.
15. Add tracing.
16. Add dashboards/alert definitions where applicable.
17. Add security/redaction.
18. Add tests.
19. Test degraded dependencies.
20. Verify production configuration.
21. Document operational usage.

## Existing Project Protection

When working in an existing codebase:

- inspect before modifying
- do not replace logging frameworks without justification
- do not introduce duplicate telemetry systems
- reuse existing middleware
- reuse existing dependency injection
- preserve configuration conventions
- preserve Docker/deployment conventions
- preserve existing health endpoints unless they are inadequate
- avoid unrelated refactoring
- do not instrument every function indiscriminately

If an architectural change is required, explain the reason and impact.

## Configuration

Never hard-code production telemetry configuration.

Use environment/configuration for values such as:

- LOG_LEVEL
- OTEL_EXPORTER_OTLP_ENDPOINT
- OTEL_SERVICE_NAME
- OTEL_TRACES_SAMPLER
- PROMETHEUS_ENABLED
- METRICS_PORT
- HEALTH_CHECK_TIMEOUT
- ENVIRONMENT
- SERVICE_VERSION

Follow the existing project's configuration naming conventions.

Never store telemetry credentials in source code.

## Production Readiness Checklist

Before declaring observability complete:

- [ ] Production logs are structured JSON.
- [ ] Every request has correlation/trace context.
- [ ] Trace context propagates across services.
- [ ] Async jobs preserve useful correlation context.
- [ ] Secrets and sensitive data are redacted.
- [ ] HTTP request metrics exist.
- [ ] Latency percentiles are measurable.
- [ ] Error rates are measurable.
- [ ] Throughput is measurable.
- [ ] CPU usage is measurable.
- [ ] Memory usage is measurable.
- [ ] Database health/performance is observable.
- [ ] External dependencies are observable.
- [ ] Queue/worker metrics exist where applicable.
- [ ] /health/live exists.
- [ ] /health/ready exists.
- [ ] Liveness does not depend on external services.
- [ ] Readiness reflects critical dependency availability.
- [ ] Health endpoints are lightweight.
- [ ] Health endpoints expose no secrets.
- [ ] Prometheus scraping is configured where applicable.
- [ ] Grafana dashboards exist where applicable.
- [ ] Alerts are actionable.
- [ ] Metric labels have bounded cardinality.
- [ ] Telemetry failure does not unnecessarily break the application.
- [ ] Graceful shutdown updates readiness correctly.
- [ ] Failure scenarios have been tested.
- [ ] Observability retention and cost are understood.
- [ ] SLOs/SLIs exist for critical production workflows where appropriate.

## How Claude Must Behave When Using This Skill

When asked to implement observability:

1. Inspect the existing project before changing anything.
2. Identify the framework, runtime, deployment environment, and existing
   telemetry stack.
3. Reuse existing observability infrastructure when appropriate.
4. Establish correlation and trace propagation first.
5. Implement structured logging.
6. Instrument important request and dependency boundaries.
7. Add meaningful metrics with bounded labels.
8. Implement liveness and readiness separately.
9. Add distributed tracing where appropriate.
10. Add dashboards and alerts only for meaningful operational signals.
11. Add redaction and privacy safeguards.
12. Add tests for normal and degraded operation.
13. Verify that telemetry failures do not take down the business service.
14. Run or describe the relevant verification commands.
15. Report files changed.
16. Explain important architectural decisions.
17. Explicitly identify remaining observability gaps and production risks.
18. Never claim production readiness merely because logs and a /metrics
    endpoint exist.

## Definition of Done

Observability is complete only when an operator can:

- determine whether the service is alive
- determine whether the service is ready
- measure traffic
- measure errors
- measure latency
- measure saturation
- identify affected requests
- follow a request across service boundaries
- correlate traces with logs
- inspect dependency failures
- detect resource exhaustion
- investigate asynchronous processing
- distinguish transient from persistent failures
- receive actionable alerts
- operate the service without relying on guesswork

The goal is not to collect the maximum amount of telemetry.

The goal is to collect the right telemetry, preserve enough context to explain
system behavior, and make failures diagnosable and recoverable.
