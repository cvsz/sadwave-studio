# Production Readiness

This file is the authoritative checklist for declaring SadwaveStudio production-ready.

## Current status

**PRODUCTION-CORE HARDENING COMPLETE — FULL PLATFORM RELEASE REMAINS GATED.**

The repository now has a durable PostgreSQL-backed queue, worker leases and recovery, retry/dead-letter handling, immutable audit-event persistence, database-backed API rate limiting, security response headers, production Compose worker topology, and CI action supply-chain hardening.

The complete YouTube automation platform is **not yet production-ready** because YouTube OAuth/synchronization, provider contracts, media isolation, AI execution, dashboard/RBAC, backup/restore evidence, and full integration/E2E/recovery evidence are still outstanding.

## Completed evidence-backed gates

### Application

- [x] Application runtime foundation
- [x] Configuration validation
- [x] Health/version/readiness endpoints
- [x] Domain job state machine
- [x] Idempotency enforcement
- [x] PostgreSQL persistence adapter
- [x] Durable queue persistence
- [x] Worker claim/lease model
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
- [ ] Migration rollback/versioning policy

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
- [ ] Integration tests against PostgreSQL
- [ ] Queue tests
- [ ] Provider contract tests
- [ ] Media tests
- [ ] Security tests
- [ ] E2E tests
- [ ] Retry/dead-letter tests against real PostgreSQL
- [ ] Crash/restart recovery tests
- [ ] Backup/restore test

### Operations

- [x] Worker crash lease-recovery mechanism
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

A production claim requires evidence for every applicable gate. A code path or checklist item is not considered complete merely because it exists; it must be validated in the target runtime.
