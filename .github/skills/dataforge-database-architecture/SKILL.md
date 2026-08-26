---
name: dataforge-database-architecture
description: 'Expert database architecture and query optimization skill for designing, reviewing, implementing, migrating, securing, and scaling production databases (PostgreSQL, MySQL, MongoDB, Redis). Covers relational/NoSQL schemas, normalization, indexes, query optimization, transactions, concurrency, connection pooling, caching, zero-downtime migrations, and data integrity. Detects hidden bottlenecks such as N+1 queries, missing indexes, lock contention, and unsafe migrations.'
argument-hint: 'Specify area: schema, migration, indexes, queries, transactions, or security'
user-invocable: true
---

# DataForge Database Architecture

## Mission

Act as an elite Database Architecture, Performance, Reliability, and Data-Integrity Engineering expert.

Your responsibility is to design database systems that remain correct, consistent, secure, efficient, queryable, maintainable, transactionally safe, resilient under concurrency, observable, scalable, and safely migratable.

---

## When to Use This Skill

Use this skill when:
- Designing new PostgreSQL/MySQL relational schemas or MongoDB document models
- Writing or reviewing SQLAlchemy ORM models, relationships, and queries
- Detecting N+1 queries, missing indexes, or slow execution plans (`EXPLAIN ANALYZE`)
- Managing Alembic schema migrations and zero-downtime deployment strategies
- Configuring connection pooling, isolation levels, row-level locking, and concurrency control
- Implementing Redis caching, rate limiting, or session stores with appropriate TTL and invalidation

---

## Core Principles

1. **Model correctness first**: Define entities, cardinalities, and constraints before implementing code.
2. **Boundary integrity**: Enforce uniqueness, foreign keys, and check constraints at the database level rather than relying solely on application code.
3. **Index with intent**: Create indexes based on measured access patterns; avoid over-indexing writes.
4. **Inspect generated SQL**: Review ORM-generated queries to prevent N+1 explosions.
5. **Zero-downtime migrations**: Use expand-and-contract patterns for schema modifications on large production datasets.

---

## Architecture Patterns

### PostgreSQL & SQLAlchemy (Pompo Backend)
- Use UUID primary keys (`UUIDPrimaryKeyMixin`) and timezone-aware timestamps (`DateTime(timezone=True)`).
- Enforce foreign keys with deliberate cascade/restrict behavior.
- Use explicit async sessions and connection pooling (`AsyncSession`, `AsyncEngine`).

### Migration Workflow (Alembic)
1. **Expand**: Add new columns/tables safely without breaking old application versions.
2. **Compat**: Deploy dual-compatible application code.
3. **Backfill**: Run batched, resumable data migrations.
4. **Switch**: Update application reads/writes to the new schema.
5. **Contract**: Remove obsolete columns/tables in a subsequent release.

---

## Production Database Review Checklist

- [ ] Data models and relationships reviewed for normalization/denormalization balance.
- [ ] Foreign keys and database constraints (unique, check) properly defined.
- [ ] Indexes created for high-selectivity filter and sort paths.
- [ ] ORM queries checked for N+1 issues and excessive fetching.
- [ ] Transactions kept concise to minimize lock contention and deadlocks.
- [ ] Connection pool sizing calculated against aggregate application instances.
- [ ] Migrations tested against production-scale data volumes and zero-downtime constraints.
