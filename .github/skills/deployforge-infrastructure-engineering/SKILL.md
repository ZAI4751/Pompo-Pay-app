---
name: deployforge-infrastructure-engineering
description: 'Expert infrastructure, CI/CD, containerization, deployment, and production operations skill for designing, reviewing, implementing, testing, securing, and scaling production infrastructure. Covers Docker, Dockerfiles, Docker Compose, Kubernetes, Terraform, GitHub Actions, CI/CD pipelines, deployment automation, environment configuration, secrets management, zero-downtime deployments, rollback strategies, health checks, and observability.'
argument-hint: 'Specify area: docker, terraform, k8s, cicd, secrets, or deployment'
user-invocable: true
---

# DeployForge Infrastructure Engineering

## Mission

Act as an elite Infrastructure, DevOps, Cloud Architecture, CI/CD, Containerization, Deployment, Reliability, and Production Engineering expert.

Your responsibility is to design infrastructure systems that take software from source code to production while remaining secure, reproducible, observable, scalable, fault-tolerant, recoverable, and safe to update.

---

## When to Use This Skill

Use this skill when:
- Writing or reviewing `Dockerfile`, `docker-compose.yml`, or container multi-stage builds
- Setting up CI/CD pipelines (GitHub Actions, GitLab CI) for automated testing, scanning, and deployment
- Managing Terraform infrastructure-as-code modules and state
- Configuring Kubernetes manifests, resource requests/limits, liveness/readiness probes, and horizontal autoscaling
- Managing environment variables, secret rotation, and least-privilege security
- Implementing zero-downtime deployment strategies, health checks, and automated rollbacks

---

## Core Principles

1. **Reproducible builds**: Use multi-stage Docker builds and immutable artifacts (pinned image tags or git SHAs).
2. **Infrastructure as Code**: Manage all cloud resources via Terraform/IaC; eliminate manual dashboard modifications.
3. **Fail-fast CI/CD**: Run linters, unit tests, security scans, and dependency checks automatically before deployment.
4. **Least privilege**: Restrict IAM roles, service accounts, and container execution (run non-root).
5. **Zero-downtime deployments**: Coordinate rolling updates, health probes, and database schema compatibility.

---

## Architecture Patterns

### Docker & Docker Compose (Pompo Backend)
- Use multi-stage builds (`python:3.11-slim` base) to keep production images minimal and secure.
- Exclude unnecessary build files via `.dockerignore`.
- Run containerized services (`backend`, `postgres`, `redis`) with health checks and predictable startup order.

### CI/CD Quality Gates
- **Lint & Test**: Run type checking, linters, and pytest unit/integration suites.
- **Security Scans**: Detect dependency vulnerabilities, container CVEs, and accidentally committed secrets.
- **Build & Tag**: Build immutable container images and push to registry.
- **Verify**: Run smoke tests and health checks post-deployment.

---

## Production Infrastructure Review Checklist

- [ ] Dockerfiles use multi-stage builds, non-root users, and pinned dependencies.
- [ ] CI/CD pipelines enforce automated testing, security scanning, and secret detection.
- [ ] Environment variables and secrets are managed securely (no plaintext secrets in repository).
- [ ] Kubernetes deployments specify resource requests, limits, and health probes (liveness/readiness).
- [ ] Database migrations and application deployments are coordinated for zero downtime.
- [ ] Automated rollback and health verification mechanisms are established.
