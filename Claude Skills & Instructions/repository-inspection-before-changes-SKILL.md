---
name: repository-inspection-before-changes
description: >
  Enforces a repository-first engineering workflow. Before modifying, creating,
  deleting, refactoring, migrating, or configuring anything, Claude must inspect
  the existing repository, understand its architecture, conventions,
  dependencies, configuration, tests, infrastructure, and current state.
  Use automatically for software engineering work, especially backend systems,
  APIs, databases, Docker, Kubernetes, CI/CD, microservices, queues, Redis,
  cloud infrastructure, and production code.
---

# Repository Inspection Before Changes

## 1. Mission

Never modify a repository blindly.

Before making any code, configuration, infrastructure, database, dependency, or
architectural change, Claude must first inspect the repository and establish a
reliable understanding of the existing system.

The repository is the source of truth.

Do not assume:
- the framework
- the architecture
- the directory structure
- the database
- the dependency manager
- the deployment model
- the testing strategy
- the configuration system
- the coding conventions
- the intended implementation
- what previous agents have already implemented

Inspect first.

## 2. Core Principle

The required sequence is:

**Inspect → Understand → Plan → Verify assumptions → Change → Test → Review**

Never:

**Guess → Change → Hope**

## 3. Mandatory Activation

Apply this skill automatically whenever Claude is asked to:
- modify code
- add a feature
- fix a bug
- refactor code
- create an API
- modify a database
- create migrations
- change configuration
- add dependencies
- change Docker
- change Kubernetes
- modify CI/CD
- add queues
- modify Redis
- modify authentication
- modify payment logic
- change infrastructure
- improve performance
- add observability
- implement security changes
- restructure directories
- remove code
- replace an existing component
- integrate an external service

## 4. Absolute Rule

**Do not make repository changes until the repository has been inspected.**

The inspection must be proportional to the requested change.

A documentation change may require limited inspection. A backend architectural
change requires broad inspection.

## 5. First Action

When entering an unfamiliar repository, begin by inspecting the repository
rather than immediately writing code.

Determine:
- repository root
- project type
- primary language
- framework
- package manager
- application entry points
- major directories
- configuration files
- test directories
- infrastructure files
- documentation
- environment configuration
- version-control state

## 6. Git Inspection

Inspect version-control state before making changes.

Determine, where applicable:
- current branch
- working-tree status
- staged changes
- uncommitted changes
- recent commits
- relevant branches
- ignored files

Never overwrite existing user work.

## 7. Protect Existing Work

Uncommitted changes belong to the user unless explicitly instructed otherwise.

Never discard, reset, overwrite, revert, or "clean up" unrelated changes without
explicit authorization.

## 8. Project Identification

Identify whether the repository is a:
- monolith
- modular monolith
- microservice
- monorepo
- library
- CLI
- worker
- API
- frontend
- infrastructure repository
- full-stack application

Do not impose architecture before understanding what already exists.

## 9. Technology Stack

Inspect manifests and configuration to determine:
- programming language
- framework
- runtime
- package manager
- ORM
- database
- cache
- message broker
- testing framework
- linting
- formatting
- build system
- deployment platform

## 10. Directory Structure

Inspect the major directories before opening individual implementation files.

Identify patterns such as:
- `src`
- `app`
- `api`
- `domain`
- `services`
- `repositories`
- `models`
- `schemas`
- `workers`
- `tests`
- `migrations`
- `infra`
- `deploy`
- `docker`
- `k8s`
- `docs`

Do not assume directory names have standard meanings.

## 11. Documentation

Read the README and relevant documentation.

Extract:
- project purpose
- setup instructions
- architecture notes
- development commands
- testing commands
- deployment instructions
- known limitations

Verify documentation against the actual code.

## 12. Repository Instructions

Look for:
- `CLAUDE.md`
- `AGENTS.md`
- `CONTRIBUTING.md`
- `README.md`
- `.github`
- `.cursor`
- project skill files
- engineering documentation

Follow applicable repository instructions.

## 13. Instruction Scope

Determine which instructions apply to:
- the whole repository
- a directory
- a specific component

Respect more-specific instructions within their scope.

## 14. Configuration

Identify configuration sources:
- environment variables
- `.env.example`
- settings modules
- YAML
- TOML
- JSON
- secrets configuration
- deployment manifests
- ConfigMaps

Never expose secret values.

## 15. Dependencies

Determine existing dependencies before adding new ones.

Ask:
- Does the project already solve this?
- Is there an existing abstraction?
- Is a second library necessary?
- Is it compatible with the runtime?
- What operational complexity does it add?

Avoid duplicate libraries.

## 16. Entry Points

Find how the application starts.

Understand:
- initialization
- dependency injection
- middleware
- lifecycle events
- configuration loading
- worker startup

## 17. Architecture Mapping

Map the major architectural layers.

For example:

API → application/service layer → domain → repositories → database

or:

API → queue → worker → external provider

Do not refactor architecture until it is understood.

## 18. Dependency Injection

Determine how dependencies are created and injected.

Preserve existing patterns unless there is a clear, demonstrated reason to
change them.

## 19. Database Inspection

If a database exists, determine:
- database technology
- ORM
- connection management
- models
- migrations
- repositories
- transaction boundaries
- indexes
- constraints

Understand transaction patterns before changing persistence logic.

## 20. Migration Inspection

Before changing schemas:
- inspect migration tooling
- inspect recent migrations
- inspect migration naming
- inspect dependencies
- determine reversibility
- determine deployment behavior

Never create a migration blindly.

## 21. API Inspection

Before modifying an endpoint, inspect:
- routing
- handlers/controllers
- schemas
- validation
- authentication
- authorization
- error handling
- response conventions
- versioning

Match the existing API style.

## 22. Authentication Inspection

Before modifying authentication or authorization, identify:
- authentication mechanism
- token handling
- middleware
- permissions
- roles
- session management
- security boundaries

Never assume conventional implementation.

## 23. Error Handling

Find the existing error strategy:
- custom exceptions
- error schemas
- HTTP mappings
- logging
- middleware
- retry behavior

Do not introduce a second incompatible error system.

## 24. Logging and Observability

Before adding telemetry, inspect:
- logger configuration
- structured logging
- log levels
- correlation IDs
- metrics
- tracing
- health checks
- Prometheus/OpenTelemetry
- dashboards
- alerts
- audit logs

Reuse existing infrastructure.

## 25. Background Processing

Determine whether the project uses:
- Celery
- BullMQ
- RabbitMQ
- Kafka
- Redis
- cron
- scheduled jobs
- workers

Understand current job patterns before adding another mechanism.

## 26. External Integrations

Identify integrations with:
- payment providers
- email
- SMS
- cloud storage
- identity providers
- third-party APIs
- webhooks

Understand existing client abstractions and failure handling.

## 27. Docker

If Docker exists, inspect:
- Dockerfiles
- `.dockerignore`
- Compose
- entrypoints
- health checks
- environment configuration
- ports
- process model

Do not replace working Docker architecture unnecessarily.

## 28. Kubernetes

If Kubernetes exists, inspect:
- Deployments
- Services
- ConfigMaps
- Secret references
- Ingress
- probes
- resource requests/limits
- autoscaling
- PodDisruptionBudgets
- namespaces
- Helm charts

Understand deployment assumptions before modifying manifests.

## 29. CI/CD

Inspect:
- GitHub Actions
- GitLab CI
- Jenkins
- deployment pipelines
- build scripts
- test workflows
- release workflows

Determine which commands are authoritative.

## 30. Testing

Find:
- unit tests
- integration tests
- end-to-end tests
- fixtures
- factories
- test configuration
- test databases
- mocks
- test scripts

Understand how the project expects changes to be verified.

## 31. Code Conventions

Determine conventions for:
- naming
- imports
- typing
- formatting
- error handling
- classes
- functions
- modules
- comments
- documentation

Match existing style unless explicitly instructed otherwise.

## 32. Similar Implementations

Before creating a new feature, find existing features with similar behavior.

Inspect their:
- structure
- tests
- dependency injection
- error handling
- configuration
- persistence

Reuse established patterns where appropriate.

## 33. Search Before Creating

Before creating a new:
- class
- function
- endpoint
- model
- service
- repository
- schema
- utility
- configuration key

search the repository for an existing equivalent.

## 34. Search Before Modifying

Before modifying a symbol, search for:
- definitions
- imports
- usages
- tests
- configuration references
- documentation references

Understand its dependency surface.

## 35. Trace Callers and Dependencies

For important code, determine:

**Who calls this?**

Then:

**What does it call?**

Understand both upstream and downstream effects.

## 36. Trace Data Flow

For important data, map:

input → validation → transformation → persistence → event/job →
external side effect → response

Do not modify one stage without understanding downstream consequences.

## 37. Trace Control Flow

Understand:
- synchronous paths
- asynchronous paths
- retries
- exceptions
- fallbacks
- state transitions

This is especially important for distributed systems.

## 38. Critical Paths

Identify business-critical workflows such as:
- authentication
- payment initiation
- payment confirmation
- settlement
- withdrawals
- order creation
- account creation
- data deletion

These require deeper inspection.

## 39. Side Effects

Identify:
- database writes
- messages
- emails
- payments
- external API calls
- file creation
- cache mutation
- audit events

Side effects require stronger verification.

## 40. State Transitions

For stateful workflows determine:
- valid states
- transitions
- terminal states
- retry behavior
- failure states

Do not bypass existing invariants.

## 41. Business Invariants

Find rules that must always remain true.

Examples:
- transaction IDs are unique
- balances cannot become negative
- completed payments cannot be completed again
- audit records cannot be silently removed

Preserve invariants during changes.

## 42. Database Constraints

Inspect:
- unique constraints
- foreign keys
- check constraints
- indexes
- nullability

Do not rely solely on application validation for data integrity.

## 43. Runtime Versions

Determine:
- language version
- framework version
- database version
- runtime version
- container base image
- package manager version where relevant

Do not use APIs unavailable in the actual runtime.

## 44. Lockfiles

Respect existing lockfiles:
- `poetry.lock`
- `uv.lock`
- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `go.sum`

Do not modify dependency resolution casually.

## 45. Build Scripts

Identify authoritative commands for:
- build
- test
- lint
- format
- type-check
- migration
- deployment

Use project-provided commands where possible.

## 46. Recent Changes

Review recent commits when useful.

Recent work may explain:
- current architecture
- partially completed features
- migrations
- workarounds
- known issues

Do not undo recent work without understanding why it exists.

## 47. Incomplete Work

Look for:
- TODO
- FIXME
- stubs
- placeholder implementations
- `pass`
- `NotImplemented`
- temporary flags

Do not fix unrelated incomplete work unless required.

## 48. Generated Files

Identify generated code and artifacts.

Modify the source generator rather than manually editing generated output when
applicable.

## 49. Vendor Code

Do not modify third-party vendor code or package-manager directories unless
explicitly required.

## 50. Secrets

Be alert for accidentally committed:
- API keys
- credentials
- certificates
- private keys
- tokens

Never reproduce secrets in responses.

If a serious exposure is discovered, report it without printing the secret.

## 51. Dangerous Operations

Before executing potentially destructive commands, stop and assess.

Examples:
- database reset
- recursive deletion
- force git reset
- destructive migrations
- dropping tables
- deleting containers with volumes
- removing cloud resources

Never execute destructive commands casually.

## 52. Plan Before Editing

After inspection, create a concise implementation plan covering:
- files likely to change
- affected components
- dependencies
- tests
- migrations
- deployment implications
- risks

## 53. Verify the Plan

Before editing ask:
- Does the plan match the existing architecture?
- Is there already an abstraction?
- Are there hidden consumers?
- Are database changes required?
- Are API contracts affected?
- Are background jobs affected?
- Are deployment changes required?

## 54. Minimal Change Principle

Change the smallest appropriate surface area.

Do not refactor unrelated code.

Do not rename unrelated files.

Do not rewrite stable infrastructure merely because another style looks cleaner.

## 55. Compatibility

Before changing public behavior determine:
- API consumers
- internal callers
- background jobs
- database compatibility
- external integrations

Prefer backward-compatible changes where practical.

## 56. Avoid Speculative Architecture

Do not create abstractions solely for hypothetical future requirements.

Architecture must be justified by actual requirements and repository patterns.

## 57. Avoid Duplicate Systems

Before adding logging, metrics, queues, repositories, service layers,
configuration frameworks, HTTP clients, or cache abstractions, verify that an
equivalent does not already exist.

## 58. Incremental Changes

Prefer small, verifiable changes.

After meaningful changes:
- inspect the diff
- run relevant tests
- check formatting
- check type errors
- validate behavior

## 59. Diff Review

Before completion, inspect exactly what changed.

Look for:
- accidental edits
- unrelated formatting
- debug code
- secrets
- incorrect imports
- unintended deletions
- generated artifacts

## 60. Test the Change

Run the narrowest relevant tests first, then expand verification as needed.

Typical order:
1. focused unit test
2. affected integration test
3. relevant full test suite
4. lint/type-check
5. build

## 61. Regression Testing

Do not test only the new behavior.

Check nearby existing behavior that could have been affected.

## 62. Database Verification

If database behavior changes:
- inspect migration
- validate schema
- test migration
- test rollback where supported
- test affected queries
- check constraints

## 63. API Verification

If API behavior changes:
- test validation
- test success response
- test error response
- test authentication
- test authorization
- test compatibility

## 64. Infrastructure Verification

For Docker, Kubernetes, cloud, or CI/CD changes validate:
- syntax
- configuration
- health checks
- startup
- shutdown
- deployment behavior

## 65. Observability Verification

If observability changes, verify:
- logs
- metrics
- traces
- correlation IDs
- health endpoints
- alerts where applicable

## 66. Verification Honesty

Never claim a command was run if it was not.

Never claim tests passed if they were not executed.

If something cannot be verified, explicitly state:

**NOT TESTED**

Then explain why and what remains at risk.

## 67. Final Repository Review

Before finishing:
- inspect git diff
- inspect changed files
- run relevant tests
- verify no accidental files changed
- verify no secrets were introduced
- verify documentation if required

## 68. Final Report

Report:

### Changed
What was modified.

### Why
Why the change was made.

### Verified
What was actually tested or checked.

### NOT TESTED
What could not be verified and why.

### Risks
Remaining technical or operational risks.

## 69. When to Ask Questions

Do not ask questions when repository inspection can answer them.

Ask only when:
- requirements are genuinely ambiguous
- destructive action requires authorization
- required credentials/access are unavailable
- materially different interpretations remain
- business intent cannot safely be inferred

## 70. When to Stop

Stop before changing anything if:
- requirements conflict
- destructive action is necessary but unauthorized
- repository instructions conflict
- the change would violate a critical invariant
- required access is unavailable
- architecture is materially ambiguous and inspection cannot resolve it

## 71. Production Systems

For production systems, increase inspection depth.

Inspect:
- deployment
- rollback
- health checks
- observability
- migrations
- dependencies
- scaling
- failure modes
- backups
- recovery procedures

## 72. Financial Systems

For payment or financial systems inspect especially carefully:
- transaction identifiers
- idempotency
- state transitions
- ledger behavior
- database constraints
- audit trails
- reconciliation
- retries
- provider behavior

Never modify money-moving logic based on a superficial reading.

## 73. Security-Critical Systems

For authentication, authorization, secrets, cryptography, or identity changes,
inspect:
- trust boundaries
- middleware
- token lifecycle
- permission checks
- audit events
- existing security controls

Do not weaken security for convenience.

## 74. Distributed Systems

For distributed systems inspect:
- service boundaries
- message contracts
- delivery semantics
- retries
- idempotency
- timeouts
- circuit breakers
- tracing
- recovery

Never assume exactly-once execution.

## 75. Performance Work

Before optimizing:
1. inspect architecture
2. identify the suspected bottleneck
3. measure it
4. establish a baseline
5. change the smallest relevant area
6. measure again

Do not optimize from intuition alone.

## 76. Refactoring

Before refactoring:
- identify all consumers
- inspect tests
- inspect configuration
- inspect deployment
- inspect public interfaces

Preserve behavior unless behavior change is explicitly requested.

## 77. Dependency Upgrades

Before upgrading:
- inspect current version
- inspect lockfile
- inspect usage
- inspect compatibility
- inspect breaking changes
- run tests
- inspect resulting diff

Do not upgrade unrelated dependencies opportunistically.

## 78. File Creation

Before creating a file:
- search for an existing appropriate location
- inspect neighboring files
- match naming conventions
- determine whether a new abstraction is actually necessary

## 79. File Deletion

Before deleting a file:
- search for references
- inspect imports
- inspect deployment references
- inspect CI references
- inspect documentation
- confirm safe removal

## 80. Directory Restructuring

Do not restructure directories for aesthetics.

Directory changes can affect:
- imports
- deployment
- packaging
- tooling
- tests
- documentation
- CI/CD

Restructure only when justified.

## 81. Documentation Changes

When documenting behavior, inspect the relevant implementation.

Never document behavior that the code does not actually provide.

## 82. Generated Configuration

If configuration is generated, find its source and modify the source rather
than the generated output.

## 83. Monorepos

For monorepos determine:
- workspace boundaries
- shared packages
- service ownership
- local instructions
- package dependencies
- build graph

Do not assume root-level changes apply uniformly.

## 84. Microservices

For microservices inspect:
- service contracts
- API consumers
- event consumers
- deployment dependencies
- shared infrastructure

A local change can have distributed consequences.

## 85. Final Golden Rule

**Never change what you have not inspected.**

The repository is not a blank canvas. It already contains architecture, history,
conventions, dependencies, invariants, users, and operational assumptions.

Claude must understand those realities before modifying the system.

## 86. Mandatory Completion Gate

Before delivering any repository change, Claude must be able to answer:

1. What existed before the change?
2. Why was this implementation chosen?
3. Which files changed?
4. What dependencies are affected?
5. What tests were run?
6. What was not tested?
7. Could the change break an existing workflow?
8. How was that risk checked?
9. Does deployment require additional work?
10. Are there remaining risks?

If these questions cannot be answered, the work is not fully verified.

## 87. Final Standard

**Inspect deeply enough to understand.  
Change minimally enough to remain safe.  
Test enough to establish evidence.  
Report honestly what was and was not verified.**

Never optimize for speed at the expense of repository correctness.
