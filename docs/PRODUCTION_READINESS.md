# Production Readiness

This file is the authoritative checklist for declaring SadwaveStudio production-ready.

## Current status

**NOT PRODUCTION-READY. Runtime hardening is implemented; release evidence and major platform capabilities remain outstanding.**

The repository implements a durable PostgreSQL-backed queue, lease fencing and recovery, bounded retries, transactional audit writes, atomic idempotency, database-backed API rate limiting, common request/error handling, versioned migrations, production Compose topology, and pinned CI actions. The worker has no content processors; queued work is explicitly blocked and dead-lettered with an audit event. These capabilities still require hosted CI and operational evidence before release claims.

The complete YouTube automation platform is **not yet production-ready** because YouTube OAuth/synchronization, provider contracts, media isolation, AI execution, dashboard/RBAC, backup/restore evidence, and full integration/E2E/recovery evidence are still outstanding.

## Implemented capability checklist

### Application

- [x] Application runtime foundation
- [x] Configuration validation
- [x] Health/version/readiness endpoints
- [x] Domain job state machine
- [x] Idempotency enforcement
- [x] PostgreSQL persistence adapter
- [x] Restricted PostgreSQL runtime role with administrator-only migrations
- [x] Migration runner rejects an existing runtime role that owns database objects
- [x] Durable queue persistence
- [x] Worker claim/lease model
- [x] Unhandled jobs transition to BLOCKED and are dead-lettered with an audit event
- [x] Expired-worker lease recovery
- [x] Retry with bounded attempts
- [x] Dead-letter state
- [x] Durable audit events
- [x] Database-backed API rate limiting
- [ ] Dashboard implementation
- [ ] Full domain model
- [ ] Approval workflow persistence
- [ ] RBAC and operator identity

### Data and infrastructure

- [x] Initial database migration
- [x] Production Docker image
- [x] Docker healthcheck
- [x] Compose PostgreSQL dependency health
- [x] Dedicated worker service
- [ ] Object storage
- [ ] Backup
- [ ] Restore verification
- [ ] Production resource limits and runtime isolation
- [ ] Migration rollback policy

### Integrations

- [ ] YouTube API contract validation
- [ ] OAuth credential lifecycle
- [ ] Channel/video/playlist synchronization
- [ ] Historical analytics snapshots
- [ ] AI provider contracts
- [ ] AI model routing
- [ ] Media/FFmpeg isolation
- [ ] Publishing adapter with verification
- [ ] Notification/distribution adapters

### Security

- [x] Production API authentication
- [x] Bounded content-job API request bodies
- [x] Secret configuration gate
- [x] Dependency audit
- [x] SBOM generation
- [x] Database-backed rate limiting
- [x] Security response headers
- [x] CI third-party action SHA pinning
- [x] CodeQL workflow SHA pinning
- [ ] RBAC/authorization model
- [ ] CSRF/CORS policy appropriate to deployed UI
- [ ] Container vulnerability scan with a currently trusted scanner
- [ ] Threat-model tests
- [ ] Prompt-injection defenses at provider boundaries
- [ ] Malicious-media isolation
- [ ] Webhook signature/replay protection
- [ ] Secret rotation procedure

### Validation

- [x] Formatting gate configured
- [x] Lint gate configured
- [x] Type/compile gate configured
- [x] Unit/API test gate configured
- [x] Idempotency test coverage
- [x] Dependency audit gate
- [x] Focused PostgreSQL integration tests for idempotency, rate limits, and lease fencing
- [x] Retry/dead-letter and terminal expired-lease behavior tests against PostgreSQL
- [x] Worker process crash/restart recovery test against disposable PostgreSQL
- [ ] Provider contract tests
- [ ] Media tests
- [ ] Security tests
- [ ] E2E tests
- [x] Retry/dead-letter tests against disposable PostgreSQL
- [ ] Backup/restore test

### Operations

- [x] Worker crash lease-recovery mechanism
- [x] Worker graceful SIGINT/SIGTERM shutdown and interruptible idle polling
- [x] Bounded retry/dead-letter behavior
- [ ] Structured production logs
- [ ] Metrics
- [ ] Traces
- [ ] Alerts
- [ ] Cost accounting
- [ ] Backup/restore runbook
- [ ] RPO/RTO defined and tested
- [ ] Rollback tested
- [ ] Manual approval gates verified
- [ ] Production deployment evidence

## Validation evidence for this change

- **PASS — Local tests:** 45 tests passed with Python 3.12 and disposable PostgreSQL 17.6. The worker crash/restart test killed a process after it claimed a job, then verified that a production-mode worker recovered the lease, blocked the unhandled job, and wrote both recovery and block audit events.
- **PASS — Local code checks:** Ruff 0.13.1 format check, Ruff lint, and Python compilation.
- **PASS — Local repository checks:** `make validate`, `make security`, `git diff --check`, and Compose configuration validation with synthetic placeholders.
- **PASS with scope limit — Dependency audit:** `pip-audit` reported no known vulnerabilities; the local `sadwave-studio` distribution was skipped because it is not published on PyPI, while its installed dependencies were audited.
- **PASS — Hosted PR checks:** application, container, dependency-review, CodeQL, and Analyze GitHub Actions passed for worker crash/restart test commit `8bae250`.
- **PENDING — Production/external gates:** deployment and crash/restart evidence in the target runtime, backup/restore, rollback, provider-contract, full security, and end-to-end validation.

A production claim requires evidence for every applicable gate. A code path or checklist item is not complete merely because it exists; it must be validated in the target runtime.
