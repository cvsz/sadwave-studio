# SadwaveStudio Implementation Plan

## Stage 0 — Foundation — Complete

- Establish repository-specific agent contract.
- Preserve ztemplate security/community baseline.
- Record the approved AI production contract.
- Replace generic template identity with SadwaveStudio identity.
- Add architecture, security, and readiness documentation.

## Stage 1 — Runtime foundation — Complete

- Select Python 3.12 + FastAPI runtime.
- Establish API boundary.
- Add validated configuration.
- Add request IDs and health/readiness/version endpoints.
- Add production bearer authentication.
- Add domain job lifecycle state machine.
- Add idempotent job creation.
- Add PostgreSQL repository and initial migration.
- Add unit/API tests.
- Add Ruff format/lint/compile gates.
- Add dependency audit and SBOM generation.
- Add production Docker/Compose healthchecks.

## Stage 2 — Persistence and jobs — In progress

- [x] Core content-job persistence
- [x] Lifecycle states
- [x] Idempotency key uniqueness
- [x] Durable audit events for creation, retry, failure, block, and lease recovery
- [x] Durable queue and worker lease model
- [x] Bounded retry and dead-letter handling
- [x] Expired lease recovery with stale-worker fencing
- [ ] Content processors and job execution
- [ ] Queue cancellation
- [ ] Transactional outbox where required
- [x] Focused PostgreSQL integration tests for idempotency, rate limits, retry/dead-letter, and leases
- [ ] Backup and restore verification

## Stage 3 — YouTube integration — Not started

- Verify authoritative API contracts.
- Implement OAuth credential lifecycle.
- Implement channel/video/playlist synchronization.
- Implement historical analytics snapshots.
- Implement approval-gated publishing and verification.

## Stage 4 — AI/media factory — Not started

- Provider interfaces and provenance.
- Local-first routing.
- Media validation and isolated FFmpeg workers.
- Transcription, subtitles, translation, thumbnails, metadata, and Shorts workflows.

## Stage 5 — Intelligence — Not started

- Opportunity engine.
- Content knowledge model.
- Analytics and anomaly detection.
- Experiment registry.
- Recommendation engine.
- Revenue intelligence.

## Stage 6 — Distribution/community — Not started

- Platform adapter framework.
- Comment classification and approval-gated drafts.
- Community-post drafts.
- Campaign scheduling.

## Stage 7 — Security/operations — In progress

- [x] Secret and dependency gates
- [x] SBOM generation
- [x] Production authentication baseline
- [x] Database-backed API rate limiting
- [ ] RBAC
- [ ] Container vulnerability scanning with a trusted current scanner
- [ ] Threat-model tests
- [ ] Backup/restore
- [ ] Disaster recovery
- [ ] Operational alerting

## Stage 8 — Production hardening — Not started

Validate duplicate requests, restarts, worker crashes, timeouts, 401/403/404/409/429/5xx, quota exhaustion, expired credentials, partial provider failures, database restart, storage failure, and rollback.

No stage may claim completion without validation evidence.
