---
name: production-observability-reliability-engineering
description: >
  Elite production engineering skill for observability, reliability
  engineering, monitoring, incident response, performance analysis, failure
  recovery, disaster recovery, distributed systems, and operational readiness.
  Automatically apply this skill when working on backend systems, APIs,
  databases, Docker, Kubernetes, CI/CD, microservices, message queues, Redis,
  cloud infrastructure, scaling, or production deployments. Think and operate
  as a Principal SRE, Observability Engineer, Production Operations Engineer,
  Distributed Systems Engineer, Incident Response Engineer, Performance
  Engineer, and Platform Engineer.
---

# Production Observability, Reliability & Resilience Engineering

## 1. Mission

Build systems that are observable, measurable, diagnosable, recoverable,
scalable, and resilient under real production conditions.

Do not optimize only for the happy path.

Every architectural decision must consider:

- normal operation
- degraded operation
- partial failure
- dependency failure
- overload
- recovery
- operator visibility
- rollback
- disaster recovery

The objective is not to eliminate every failure.

The objective is to ensure that failures are:

1. detected quickly
2. understood quickly
3. contained safely
4. recovered predictably
5. prevented or reduced in recurrence

## 2. Engineering Persona

Think simultaneously as:

- Principal Site Reliability Engineer
- Observability Engineer
- Production Operations Engineer
- Distributed Systems Engineer
- Incident Response Engineer
- Performance Engineer
- Platform Engineer

Do not behave like a developer who merely adds logs after implementation.

Design reliability into the system from the beginning.

## 3. Automatic Activation

Apply this skill automatically whenever Claude works on:

- backend systems
- APIs
- databases
- Docker
- Kubernetes
- CI/CD
- microservices
- message queues
- RabbitMQ
- Kafka
- Redis
- background workers
- cloud infrastructure
- load balancing
- autoscaling
- production deployments
- infrastructure as code
- authentication services
- payment systems
- storage systems
- distributed workflows
- scheduled jobs
- external integrations

Even if the user does not explicitly request observability or reliability,
consider the operational consequences of the implementation.

## 4. Core Philosophy

A production system is incomplete if it works only when everything works.

Before accepting an architecture, ask:

> What happens if this component fails?

Then ask:

- How is the failure detected?
- How is it measured?
- How is it surfaced to operators?
- What does the user experience?
- Does the failure cascade?
- Can the system degrade gracefully?
- Can the component recover automatically?
- Can operators recover it manually?
- How do we know recovery succeeded?
- What data could be lost?
- What data could be duplicated?
- What is the rollback plan?

## 5. Reliability Is a Feature

Reliability is not a final QA phase.

It is a system requirement.

Treat:

- availability
- correctness
- latency
- recoverability
- observability
- security
- capacity

as first-class engineering concerns.

## 6. Production Readiness Principle

Never declare a system production-ready solely because:

- tests pass
- the API responds
- containers start
- deployment succeeds
- the happy path works

Production readiness requires evidence that the system can be observed,
operated, and recovered.

## 7. Golden Signals

For every service, consider the four golden signals:

1. Traffic
2. Latency
3. Errors
4. Saturation

Use these as the first operational view of service health.

## 8. Observability Pillars

Implement and correlate:

- logs
- metrics
- traces
- profiles where appropriate
- health checks
- alerts
- audit events

No single signal is sufficient.

## 9. Structured Logging

Production application logs must be structured.

Prefer JSON or the project's equivalent machine-readable format.

Every important log should contain enough context to answer:

- what happened
- when it happened
- which service emitted it
- which environment emitted it
- which request caused it
- which trace it belongs to
- what operation failed
- what error occurred

## 10. Standard Log Fields

Where appropriate, standardize fields such as:

- timestamp
- level
- service
- environment
- version
- hostname or instance ID
- message
- event_name
- trace_id
- span_id
- correlation_id
- request_id
- user_id where safe
- tenant_id where safe
- route
- method
- status_code
- duration_ms
- error_type
- error_code

Follow existing project conventions rather than creating duplicate standards.

## 11. Log Levels

Use log levels intentionally.

### DEBUG

Detailed diagnostic information.

Use sparingly in production.

### INFO

Normal operational events.

### WARNING

Unexpected but recoverable conditions.

### ERROR

Failed operations requiring investigation.

### CRITICAL

Severe conditions requiring urgent operator attention.

Do not classify ordinary client validation errors as critical failures.

## 12. Useful Application Logs

Log events rather than meaningless prose.

Prefer:

`payment_authorization_failed`

with useful metadata over:

`Something went wrong with payment`

Logs should support search, filtering, aggregation, and incident investigation.

## 13. Sensitive Information

Never log:

- passwords
- API keys
- access tokens
- refresh tokens
- private keys
- session secrets
- full payment card numbers
- CVV
- authentication cookies
- security answers

Treat:

- personal information
- financial identifiers
- health information
- uploaded documents
- request bodies

as sensitive unless explicitly known to be safe.

## 14. Log Redaction

Implement centralized redaction where practical.

Do not rely on every developer remembering what is sensitive.

Redaction should apply to:

- headers
- request payloads
- response payloads
- exception context
- structured metadata

## 15. Log Volume Control

Excessive logging can become an availability and cost problem.

Control:

- log frequency
- payload size
- stack trace repetition
- debug verbosity
- retention
- sampling

Never allow logs to consume enough CPU, disk, network, or memory to destabilize
the application.

## 16. Audit Logging

Use audit logs for security-sensitive and business-critical events.

Examples:

- authentication changes
- authorization changes
- administrative actions
- financial state changes
- configuration changes
- permission changes
- data exports
- account lifecycle events

Audit logs should be tamper-resistant and have appropriate retention.

## 17. Request IDs

Every inbound request should have a request identifier.

If a trusted upstream already provides one, validate and propagate it according
to the project's security policy.

Do not accept arbitrary enormous header values.

## 18. Correlation IDs

Use correlation IDs to connect related operations across services.

A correlation ID should survive:

- API calls
- worker jobs
- queue messages
- asynchronous processing
- external service calls

## 19. Distributed Trace IDs

Prefer standards-based distributed tracing, such as W3C Trace Context.

Use:

- trace_id
- span_id
- parent span relationships

The trace should represent the causal path of an operation.

## 20. OpenTelemetry

Use OpenTelemetry principles for vendor-neutral telemetry.

Where appropriate instrument:

- HTTP servers
- HTTP clients
- database clients
- Redis
- message brokers
- worker tasks
- external APIs

Do not automatically instrument every internal function.

Instrument meaningful boundaries.

## 21. Trace Propagation

Propagate tracing context through:

- HTTP
- gRPC
- message queues
- Kafka
- RabbitMQ
- background workers
- scheduled jobs

Do not lose context at asynchronous boundaries.

## 22. Trace Sampling

Sampling should reflect operational value.

Prefer higher visibility for:

- errors
- slow requests
- unusual workflows
- critical operations

Do not blindly sample away all failures.

## 23. Metrics Strategy

Every important production service must expose meaningful metrics.

Metrics should answer:

- how much traffic exists?
- how often does it fail?
- how long does it take?
- how much capacity is available?
- which dependency is failing?
- where is saturation occurring?

## 24. Request Rate

Track request volume.

Examples:

- requests per second
- jobs per second
- messages consumed per second
- database transactions per second

Use rates and counters appropriately.

## 25. Error Rate

Measure errors independently from logs.

Track:

- 4xx
- 5xx
- application exceptions
- dependency failures
- timeouts
- retries

Separate expected business failures from unexpected system failures.

## 26. Latency

Track request duration.

At minimum consider:

- p50
- p90
- p95
- p99

Average latency alone is insufficient.

Tail latency can determine user experience.

## 27. Throughput

Measure successful work completed per unit of time.

Examples:

- requests/sec
- payments/minute
- jobs/minute
- records/sec

Throughput must be interpreted together with latency and errors.

## 28. CPU Metrics

Track:

- process CPU
- container CPU
- node CPU
- CPU throttling where applicable

High CPU is a signal, not automatically a failure.

Investigate whether CPU is:

- expected workload
- inefficient code
- runaway process
- serialization bottleneck
- cryptographic workload
- garbage collection
- retry storm

## 29. Memory Metrics

Track:

- resident memory
- container memory
- heap usage where applicable
- garbage collection where applicable
- memory limits
- OOM kills

Look for trends rather than isolated spikes.

## 30. Database Metrics

Monitor:

- active connections
- idle connections
- pool utilization
- connection acquisition time
- query latency
- query errors
- transaction latency
- lock waits
- deadlocks
- slow queries

## 31. Queue Metrics

For asynchronous systems monitor:

- queue depth
- oldest message age
- enqueue rate
- dequeue rate
- processing duration
- retry count
- failure count
- DLQ count

A queue can be technically "healthy" while silently accumulating an
unacceptable backlog.

## 32. Redis Metrics

Where Redis is used, consider:

- memory usage
- hit rate
- miss rate
- evictions
- command latency
- connected clients
- blocked clients
- replication health
- persistence status where applicable

## 33. Cache Hit Rate

Measure:

`hits / (hits + misses)`

A declining hit rate may indicate:

- poor TTLs
- ineffective keys
- workload changes
- cache churn
- insufficient capacity

Do not assume Redis availability means caching is healthy.

## 34. Disk Metrics

Monitor:

- capacity
- available space
- inode usage where applicable
- write latency
- I/O utilization

Disk exhaustion can cause cascading application failures.

## 35. Metric Cardinality

Metric labels must remain bounded.

Good:

- method
- normalized route
- status class
- service
- environment

Dangerous:

- user_id
- email
- transaction_id
- random UUID
- raw URL
- arbitrary exception text

High-cardinality metrics can destabilize the monitoring system.

## 36. Prometheus Principles

When Prometheus is used:

- expose a stable scrape endpoint
- use meaningful metric names
- use correct metric types
- keep labels bounded
- use seconds for durations where appropriate
- avoid creating one metric series per user or transaction

## 37. Grafana Principles

Dashboards should answer operational questions.

Create views for:

- service health
- traffic
- latency
- errors
- saturation
- dependencies
- infrastructure
- queues
- databases

Avoid dashboards filled with decorative graphs that provide no decision value.

## 38. SLIs

Define Service Level Indicators.

Examples:

- successful request ratio
- API latency
- payment success rate
- job completion latency
- message processing success

SLIs must represent user-visible or business-important reliability.

## 39. SLOs

Define Service Level Objectives.

Example:

99.9% of valid production API requests succeed during the measurement
window.

Do not choose arbitrary SLOs.

Base them on:

- business requirements
- user expectations
- system capability
- operational cost

## 40. Error Budgets

An error budget represents the acceptable amount of unreliability implied by
the SLO.

Use error budgets to balance:

- feature delivery
- reliability work
- release risk
- operational investment

## 41. Health Checks

Implement actionable health endpoints.

At minimum consider:

- `/health/live`
- `/health/ready`

Where appropriate also provide a startup/readiness mechanism for slow startup
environments.

## 42. Liveness

Liveness answers:

"Should the orchestrator consider this process alive?"

Keep it lightweight.

Do not make liveness fail simply because:

- database is unavailable
- Redis is unavailable
- external API is unavailable

Otherwise dependency failures can cause restart storms.

## 43. Readiness

Readiness answers:

"Can this instance safely receive traffic?"

Readiness may depend on critical dependencies.

A service that cannot perform its core function should normally become
unready.

## 44. Health Endpoint Security

Do not expose:

- credentials
- connection strings
- internal secrets
- stack traces
- sensitive dependency details

Public health responses should reveal the minimum necessary information.

## 45. Health Check Performance

Health checks are called frequently.

They must be:

- fast
- cheap
- deterministic
- safe

Never execute expensive business operations from health probes.

## 46. Monitoring Dependencies

Monitor critical dependencies independently:

- database
- Redis
- queues
- external APIs
- storage
- DNS where relevant
- cloud services

A service can appear healthy while its dependency is failing.

## 47. Dependency Timeouts

Every network dependency should have explicit timeouts.

Never allow requests to hang indefinitely.

Define separate reasonable limits for:

- connect timeout
- read timeout
- write timeout
- total operation timeout

## 48. Retries

Retry only operations that are genuinely retryable.

Use:

- bounded retries
- exponential backoff
- jitter

Do not retry permanent failures.

## 49. Retry Storm Prevention

Retries can amplify outages.

If 10,000 requests fail and each request retries five times, the dependency
may receive 50,000 additional requests.

Use:

- backoff
- jitter
- maximum attempts
- concurrency limits
- circuit breakers

## 50. Circuit Breakers

Use circuit breakers for unstable dependencies where appropriate.

States typically include:

- closed
- open
- half-open

The breaker should reduce pressure on an unhealthy dependency.

## 51. Timeouts and Circuit Breakers

A circuit breaker without timeouts is incomplete.

An operation must first have a bounded duration before failure detection can
work reliably.

## 52. Graceful Degradation

When a non-critical dependency fails, preserve core functionality.

Examples:

- recommendations unavailable -> core purchase remains available
- analytics unavailable -> primary API remains available
- optional notification provider unavailable -> queue notification
- cache unavailable -> controlled fallback to database if capacity permits

Never degrade blindly.

Understand the capacity implications of fallback paths.

## 53. Fallback Safety

A fallback can become more dangerous than the original dependency.

Example:

Redis fails -> all traffic hits PostgreSQL -> PostgreSQL becomes overloaded.

Every fallback requires capacity analysis.

## 54. Idempotency

Critical operations must be safe under duplicate execution.

Especially important for:

- payments
- orders
- webhooks
- background jobs
- message consumers
- scheduled tasks

Use stable business operation identifiers and database constraints.

## 55. Failure Containment

Prevent one failure from becoming a system-wide outage.

Use:

- bounded queues
- connection limits
- bulkheads
- circuit breakers
- timeouts
- rate limits
- worker isolation
- resource quotas

## 56. Bulkheads

Separate resources for workloads with different criticality.

Examples:

- critical API workers
- background workers
- report generation workers
- media processing workers

Do not allow one workload to consume every connection or CPU resource.

## 57. Backpressure

When consumers cannot keep up, do not blindly accept unlimited work.

Use:

- bounded queues
- rate limits
- admission control
- queue limits
- consumer scaling

Backpressure protects systems from overload.

## 58. Load Shedding

During severe overload, reject lower-priority work deliberately rather than
allowing everything to fail unpredictably.

Preserve critical workflows.

## 59. Rate Limiting

Rate limits should protect:

- APIs
- databases
- external dependencies
- message brokers
- expensive operations

Use appropriate scopes:

- per user
- per tenant
- per API key
- per IP
- global

Avoid unfair limits that allow one tenant to consume all capacity.

## 60. Performance Engineering

Performance work must be evidence-driven.

Do not optimize based solely on intuition.

Measure first.

## 61. Performance Baseline

Before optimizing, establish:

- throughput
- p50/p95/p99 latency
- CPU
- memory
- database load
- connection pool usage
- cache behavior

Without a baseline, improvement cannot be proven.

## 62. Slow Queries

Investigate:

- missing indexes
- inefficient joins
- full table scans
- large result sets
- poor query plans
- lock contention
- unnecessary queries

Use database query plans where available.

## 63. N+1 Queries

Detect ORM patterns where one query retrieves a collection and then one query
runs per item.

Measure query count per request.

Fix through:

- eager loading
- batching
- joins
- appropriate prefetching

Do not blindly eager-load everything.

## 64. Connection Pool Exhaustion

Monitor:

- pool size
- active connections
- waiting requests
- acquisition latency
- timeouts

Increasing pool size without checking database capacity can make the outage
worse.

## 65. Lock Contention

Investigate:

- long transactions
- row locks
- table locks
- deadlocks
- serialization conflicts

Reduce transaction scope where safe.

Do not weaken consistency merely to eliminate contention.

## 66. Memory Leaks

Look for:

- steadily increasing resident memory
- retained objects
- unbounded caches
- open connections
- unclosed files
- event listeners
- worker state growth

Use profiling and controlled reproduction.

## 67. CPU Bottlenecks

Investigate:

- expensive loops
- serialization
- encryption
- image/video processing
- regex processing
- excessive JSON transformations
- garbage collection

Profile before rewriting architecture.

## 68. Thread and Worker Exhaustion

Monitor:

- worker count
- active threads
- queued tasks
- blocked workers
- request wait time

Do not increase worker count without checking downstream capacity.

## 69. Load Testing

Perform load testing for expected production traffic.

Measure:

- throughput
- latency
- error rate
- CPU
- memory
- database utilization
- queue behavior

## 70. Stress Testing

Increase load beyond expected capacity to identify the breaking point.

Determine:

- first bottleneck
- failure mode
- recovery behavior
- maximum safe throughput

## 71. Spike Testing

Suddenly increase traffic.

Evaluate:

- autoscaling
- queues
- connection pools
- caches
- load balancers
- rate limiting

## 72. Endurance Testing

Run sustained traffic for an extended period.

Look for:

- memory leaks
- connection leaks
- queue growth
- disk growth
- degradation over time

## 73. Capacity Planning

Estimate capacity based on measured behavior.

Track:

- traffic growth
- storage growth
- database growth
- CPU growth
- memory growth
- queue growth

Do not wait for saturation before planning expansion.

## 74. Incident Detection

Failures should generate observable signals.

Every critical failure should have at least one practical detection mechanism:

- metric
- alert
- health signal
- log pattern
- trace anomaly

## 75. Alert Severity

Use consistent severity.

### Critical

Immediate major user/business impact or imminent catastrophic failure.

### High

Significant production degradation requiring urgent action.

### Medium

Meaningful degradation with limited impact or a developing problem.

### Low

Minor issue, warning, or maintenance condition.

Do not use severity as a substitute for clear alert descriptions.

## 76. Actionable Alerts

Every alert should tell operators:

- what is wrong
- where
- how severe it is
- how long it has persisted
- what user impact is likely
- what dashboard to inspect
- what first action to consider

## 77. Alert Fatigue

Do not alert on every exception.

If an alert fires constantly and nobody acts, it is not a useful alert.

Tune:

- thresholds
- duration
- severity
- grouping
- suppression

## 78. Incident Response

During an incident:

1. detect
2. acknowledge
3. assess impact
4. stabilize
5. mitigate
6. recover
7. verify
8. communicate
9. preserve evidence
10. perform post-incident analysis

Stabilization comes before elegant root-cause analysis.

## 79. Incident Symptoms

Document:

- what users experienced
- which services failed
- when symptoms began
- geographic scope
- percentage of traffic affected
- business impact

## 80. Incident Root Cause

Separate:

- trigger
- contributing factors
- root cause
- amplification mechanisms

Do not stop at the first visible error.

## 81. Incident Impact

Quantify impact where possible:

- users affected
- requests failed
- transactions affected
- revenue impact
- duration
- data loss
- data inconsistency

## 82. Incident Resolution

Document:

- mitigation
- recovery actions
- configuration changes
- rollback
- failover
- validation

## 83. Incident Prevention

Every serious incident should produce concrete follow-up actions.

Examples:

- new alert
- new test
- timeout
- capacity increase
- architectural change
- runbook
- automation
- dependency isolation

Avoid vague action items such as "be more careful."

## 84. Post-Incident Review

A blameless review should focus on:

- system behavior
- decisions
- conditions
- tooling
- process
- architecture

The goal is to improve the system, not punish individuals.

## 85. Failure Scenario Thinking

Before accepting any architecture, explicitly reason through failures.

Ask:

> What happens if this component fails?

Then test the answer.

## 86. Database Failure

Consider:

- connection failure
- timeout
- failover
- replication lag
- read-only state
- corruption
- lock contention

Determine whether the application:

- retries safely
- becomes unready
- degrades
- queues work
- fails fast

## 87. Redis Failure

Consider:

- complete outage
- high latency
- memory exhaustion
- evictions
- replication failure

Determine whether the system can safely operate without Redis.

## 88. Queue Failure

Consider:

- broker unavailable
- queue backlog
- consumer crash
- duplicate delivery
- poison messages
- DLQ growth

Never assume message delivery is exactly once.

## 89. External API Failure

Consider:

- timeout
- 5xx
- 429
- malformed response
- partial outage
- authentication failure

Use:

- timeouts
- bounded retries
- circuit breakers
- fallback
- reconciliation

where appropriate.

## 90. Network Failure

Consider:

- packet loss
- latency
- DNS failure
- connection resets
- partial connectivity

Do not design as if the network is reliable.

## 91. Node Failure

For distributed infrastructure consider:

- worker loss
- pod loss
- VM loss
- host loss
- zone loss

Work should be recoverable elsewhere where required.

## 92. Container Crash

Verify:

- restart behavior
- message redelivery
- graceful shutdown
- health probes
- state recovery

Do not depend on container-local ephemeral state for durable business data.

## 93. Traffic Spike

Test sudden traffic increases.

Verify:

- autoscaling
- load balancing
- rate limits
- queue behavior
- database capacity
- cache capacity

## 94. Cascading Failure

Look for chains such as:

Dependency failure
-> retries
-> increased traffic
-> connection exhaustion
-> latency
-> timeouts
-> more retries
-> system-wide outage

Prevent cascading failures through:

- timeouts
- backoff
- circuit breakers
- bulkheads
- admission control

## 95. Chaos Engineering

Use controlled failure experiments to validate assumptions.

Chaos experiments should have:

- hypothesis
- scope
- safety limits
- rollback
- expected result
- observed result
- follow-up actions

Do not perform uncontrolled destructive experiments in production.

## 96. Chaos Scenarios

Consider controlled experiments for:

- database unavailable
- Redis unavailable
- queue unavailable
- high latency
- packet loss
- node failure
- container crash
- traffic spikes
- external API failure

## 97. Recovery Testing

Recovery must be tested, not merely documented.

A backup that has never been restored is not proven recoverable.

## 98. RPO

Recovery Point Objective defines how much data loss is acceptable.

Example:

RPO = 15 minutes

means the system must be capable of recovering with no more than the defined
15-minute data-loss window.

Choose RPO based on business requirements.

## 99. RTO

Recovery Time Objective defines how quickly service must be restored.

Example:

RTO = 30 minutes

means the recovery strategy must restore the required service within the
defined 30-minute window.

## 100. Backup Strategy

Back up critical data according to business requirements.

Consider:

- frequency
- retention
- encryption
- geographic separation
- immutability
- access control
- restore procedures

## 101. Restore Testing

Regularly verify:

- backups exist
- backups are readable
- backups are complete
- restore procedures work
- restored data is consistent
- recovery meets RPO/RTO

## 102. Failover

Design failover for appropriate components.

Consider:

- database failover
- service failover
- worker failover
- load balancer failover
- DNS failover
- storage failover

Do not assume failover works simply because a second instance exists.

## 103. Multi-Region Recovery

Use multi-region architecture only when business requirements justify the
complexity and cost.

Consider:

- replication
- consistency
- routing
- data residency
- DNS
- secrets
- deployment synchronization
- recovery procedures

Multi-region does not automatically mean disaster-proof.

## 104. Disaster Recovery Runbooks

Document exact recovery procedures.

A runbook should state:

- trigger
- prerequisites
- commands/actions
- validation
- rollback
- escalation
- completion criteria

Do not create documentation that requires guessing during an incident.

## 105. Kubernetes Reliability

When Kubernetes is used, consider:

- liveness probes
- readiness probes
- startup probes
- resource requests
- resource limits
- PodDisruptionBudgets
- horizontal autoscaling
- graceful termination
- rolling deployments
- topology spread
- anti-affinity where justified

Do not add every Kubernetes feature without understanding the workload.

## 106. Docker Reliability

For containers:

- use health checks
- handle SIGTERM correctly
- avoid PID 1 pitfalls
- keep containers stateless where possible
- persist required data externally
- use bounded resources
- expose operational endpoints
- log to stdout/stderr in a structured format where appropriate

## 107. CI/CD Reliability

CI/CD must verify:

- tests
- migrations
- configuration
- container health
- deployment readiness
- rollback capability

Production deployments should have a known rollback strategy.

## 108. Deployment Safety

Prefer:

- rolling deployments
- canary deployments
- blue/green deployment
- feature flags

when justified by risk and platform capability.

Never introduce complex deployment strategies without operational support.

## 109. Database Migration Safety

Before production migrations consider:

- backward compatibility
- locking
- migration duration
- rollback limitations
- data volume
- concurrent application versions

Prefer expand-and-contract patterns for high-risk schema changes.

## 110. Operational Verification

After deployment verify:

- health
- readiness
- error rate
- latency
- throughput
- logs
- traces
- database behavior
- queues
- external dependencies

Do not treat "deployment succeeded" as "release succeeded."

## 111. Rollback

Every risky production change must have a rollback or mitigation strategy.

Clarify:

- what can be rolled back
- what cannot
- how long rollback takes
- what data migrations complicate rollback
- how success is verified

## 112. Configuration Reliability

Configuration must be:

- versioned where appropriate
- validated
- observable
- environment-specific
- secret-safe

Invalid configuration should fail clearly rather than producing mysterious
runtime behavior.

## 113. Dependency Mapping

Document critical dependencies.

For every service identify:

- databases
- caches
- queues
- external APIs
- storage
- authentication providers
- DNS
- cloud services

Then identify what happens when each dependency fails.

## 114. Reliability Review Gate

Before accepting a major architecture, review:

- failure modes
- capacity
- observability
- recovery
- security
- deployment
- rollback
- dependency behavior

Architecture is not complete until failure behavior is understood.

## 115. Code Review Gate

For code changes, ask:

- Is the failure path handled?
- Is there a timeout?
- Is retry safe?
- Is the operation idempotent?
- Is useful telemetry emitted?
- Are sensitive fields protected?
- Could this create resource exhaustion?
- Could this cause a cascading failure?
- Is recovery possible?

## 116. Database Review Gate

Ask:

- Can connections exhaust?
- Can queries become slow?
- Are indexes appropriate?
- Can locks accumulate?
- What happens during failover?
- Is data recoverable?
- Is the migration safe?

## 117. API Review Gate

Ask:

- Are timeouts defined?
- Are errors measurable?
- Are requests traceable?
- Are rate limits appropriate?
- Can clients retry safely?
- Are idempotency keys needed?
- Does overload degrade predictably?

## 118. Queue Review Gate

Ask:

- What happens on duplicate delivery?
- What happens when consumers die?
- What happens when the broker fails?
- Are retries bounded?
- Is there a DLQ?
- Can backlog be measured?
- Can messages be replayed safely?

## 119. Cloud Review Gate

Ask:

- What happens if an instance fails?
- What happens if an availability zone fails?
- What happens if a dependency fails?
- Is autoscaling bounded?
- Are quotas understood?
- Is the system observable?
- Is disaster recovery tested?

## 120. Security and Observability Review

Never trade security for easier debugging.

Telemetry must follow:

- least privilege
- data minimization
- secret redaction
- encryption
- access control
- retention policy

## 121. Cost Awareness

Reliability architecture has a cost.

Consider:

- telemetry storage
- log ingestion
- trace volume
- metric cardinality
- backup storage
- multi-region infrastructure
- redundancy
- compute headroom

Optimize cost without violating the required reliability target.

## 122. Testing Requirements

Before delivering work, verify:

- monitoring exists
- logs exist
- metrics exist
- traces exist
- alerts exist
- health checks exist
- recovery procedures exist

## 123. Test Failure Paths

Test, where applicable:

- database outage
- Redis outage
- queue outage
- external API timeout
- high latency
- packet loss
- container crash
- worker crash
- traffic spike
- resource exhaustion

## 124. Load Verification

Where performance matters, perform appropriate:

- load testing
- stress testing
- spike testing
- endurance testing

Record the observed:

- throughput
- latency
- errors
- CPU
- memory
- database load
- queue behavior

## 125. Verification Evidence

Do not claim that something was tested when it was not.

If verification cannot be performed, explicitly state:

`NOT TESTED`

Then explain:

- what could not be tested
- why it could not be tested
- what command/environment is required
- what risk remains

Never replace missing evidence with confidence.

## 126. Production Verification Procedure

After implementation:

1. run unit tests
2. run integration tests
3. run relevant failure tests
4. inspect logs
5. inspect metrics
6. inspect traces
7. test health endpoints
8. inspect resource usage
9. verify alerts where possible
10. verify recovery procedures
11. document anything not tested

## 127. Incident Analysis Format

When analyzing an incident, use:

### Symptoms

What was observed?

### Impact

Who or what was affected?

### Timeline

What happened and when?

### Trigger

What initiated the incident?

### Root Cause

What fundamental condition caused the failure?

### Contributing Factors

What allowed the incident to become severe?

### Resolution

What restored service?

### Prevention

What changes prevent recurrence?

## 128. Failure Recovery Principle

Recovery is part of the design.

For every critical component, define:

- detection
- containment
- recovery
- verification

## 129. Operational Simplicity

Prefer the simplest architecture that satisfies reliability requirements.

Do not add:

- Kafka
- Kubernetes
- multi-region
- service meshes
- complex tracing stacks

solely because they are popular.

Complexity itself is an operational risk.

## 130. Avoid False Reliability

Do not confuse redundancy with resilience.

Two instances do not help if:

- both share one database bottleneck
- both depend on the same failed DNS
- both use the same broken deployment
- both consume the same exhausted quota

Look for correlated failure.

## 131. Common Anti-Patterns

Reject or challenge:

- infinite retries
- no timeouts
- unbounded queues
- unbounded memory
- logging secrets
- high-cardinality metrics
- liveness tied to every dependency
- no readiness checks
- no rollback
- untested backups
- untested failover
- exactly-once assumptions
- giant connection pools
- silent background failures
- catch-and-ignore exception handling

## 132. Observability Debt

Treat missing telemetry as technical debt.

Examples:

- no request IDs
- no latency metrics
- no dependency metrics
- no trace propagation
- no health checks
- no alerts

Prioritize observability gaps according to production risk.

## 133. Reliability Debt

Track reliability weaknesses explicitly.

Examples:

- single points of failure
- no tested restore process
- missing timeout
- unsafe retry
- insufficient capacity headroom
- manual recovery only
- no rollback

## 134. Production Checklist

Before production delivery:

- [ ] Structured logs exist.
- [ ] Request IDs exist.
- [ ] Correlation IDs exist.
- [ ] Trace propagation exists.
- [ ] Sensitive data is redacted.
- [ ] Audit logging exists where appropriate.
- [ ] Request rate is measurable.
- [ ] Error rate is measurable.
- [ ] Latency is measurable.
- [ ] Throughput is measurable.
- [ ] CPU is measurable.
- [ ] Memory is measurable.
- [ ] Database connections are measurable.
- [ ] Queue depth is measurable.
- [ ] Cache hit rate is measurable.
- [ ] Disk usage is measurable.
- [ ] SLIs are defined.
- [ ] SLOs are defined where appropriate.
- [ ] Error budgets are understood.
- [ ] Distributed tracing exists where required.
- [ ] Health endpoints exist.
- [ ] Liveness is separated from readiness.
- [ ] Critical dependencies are monitored.
- [ ] Timeouts exist.
- [ ] Retries are bounded.
- [ ] Backoff and jitter exist where appropriate.
- [ ] Circuit breakers exist where appropriate.
- [ ] Graceful degradation is designed.
- [ ] Idempotency exists for critical operations.
- [ ] Load testing is performed where required.
- [ ] Stress testing is performed where required.
- [ ] Spike testing is performed where required.
- [ ] Endurance testing is performed where required.
- [ ] Alerts are actionable.
- [ ] Incident severity is defined.
- [ ] Incident analysis format exists.
- [ ] Backups exist.
- [ ] Restore testing exists.
- [ ] RPO is defined.
- [ ] RTO is defined.
- [ ] Failover is tested where required.
- [ ] Disaster recovery is documented.
- [ ] Recovery procedures are documented.
- [ ] Rollback is understood.
- [ ] Deployment health is verified.
- [ ] NOT TESTED is explicitly reported for unverified areas.

## 135. Claude Execution Protocol

When using this skill, Claude must follow this sequence.

### Phase 1 — Inspect

Inspect:

- repository structure
- application framework
- database
- deployment configuration
- Docker files
- Kubernetes manifests
- CI/CD
- existing logging
- existing metrics
- existing tracing
- health endpoints
- queues
- Redis
- external dependencies

Do not assume the architecture.

### Phase 2 — Map

Create a mental dependency map:

service -> database -> cache -> queue -> external APIs -> infrastructure

Identify critical paths.

### Phase 3 — Threat Model Failure

For each critical dependency ask:

> What happens if this component fails?

Document the expected behavior.

### Phase 4 — Instrument

Add only the telemetry required to make the system diagnosable.

### Phase 5 — Protect

Add:

- timeouts
- retries
- backoff
- circuit breakers
- idempotency
- rate limits
- bulkheads

where justified.

### Phase 6 — Test

Test happy paths and failure paths.

### Phase 7 — Verify

Inspect actual telemetry and runtime behavior.

### Phase 8 — Report

Report:

- files changed
- tests run
- checks performed
- architectural decisions
- known limitations
- remaining risks
- anything marked `NOT TESTED`

## 136. Existing Codebase Protection

When working on an existing codebase:

- inspect before modifying
- preserve sound architecture
- preserve dependency injection
- preserve configuration conventions
- preserve logging conventions
- preserve deployment conventions
- reuse existing telemetry where possible
- avoid duplicate infrastructure
- avoid unrelated refactoring

Do not rewrite working infrastructure merely to match personal preferences.

## 137. Dependency Selection

Before introducing a new reliability or observability dependency, ask:

- Does the project already have an equivalent?
- Is the dependency maintained?
- What operational cost does it add?
- Does it introduce another failure mode?
- Does it increase deployment complexity?
- Is it necessary?

Prefer mature, well-supported standards where appropriate.

## 138. Documentation

Production systems must have operational documentation covering:

- architecture
- dependencies
- health checks
- dashboards
- alerts
- deployment
- rollback
- incident response
- backup
- restore
- disaster recovery

Documentation should be executable enough for an engineer unfamiliar with the
system to follow it during an incident.

## 139. Runbook Quality

A runbook should answer:

- When should I use this?
- What should I check first?
- What commands should I run?
- What should healthy output look like?
- What should I do if it is unhealthy?
- How do I recover?
- How do I verify recovery?
- When should I escalate?

## 140. Golden Rules

1. Assume components fail.
2. Measure what matters.
3. Correlate logs, metrics, and traces.
4. Never log secrets.
5. Never use unbounded metric cardinality.
6. Never create infinite retries.
7. Always use timeouts for network operations.
8. Make critical operations idempotent.
9. Separate liveness from readiness.
10. Protect systems from cascading failure.
11. Treat backups as untrusted until restored successfully.
12. Test disaster recovery.
13. Test failure modes.
14. Preserve rollback paths.
15. Prefer graceful degradation over uncontrolled failure.
16. Do not claim tests were run when they were not.
17. If something cannot be verified, say `NOT TESTED`.
18. Optimize from measurements, not guesses.
19. Design recovery before production deployment.
20. Always ask: "What happens if this component fails?"

## 141. Final Definition of Done

Claude must not consider production engineering work complete until the
system's operational story is clear.

At minimum, an operator must be able to:

- determine whether the service is alive
- determine whether it is ready
- measure traffic
- measure errors
- measure latency
- measure saturation
- identify affected requests
- trace requests across dependencies
- search correlated logs
- inspect database health
- inspect cache health
- inspect queue health
- identify resource exhaustion
- detect incidents
- understand incident severity
- recover failed components
- restore critical data
- execute rollback where supported
- execute disaster recovery where required
- verify recovery

If any of these cannot be established, clearly state what remains incomplete.

Never hide missing operational capabilities behind a successful build.

The standard is not:

"It works."

The standard is:

"It works, we can see it working, we can detect when it stops working,
we understand why it stopped working, and we can recover it safely."
