# Changelog

All notable changes to SadwaveStudio should be documented here.

## [Unreleased]

### Added

- Production Python/FastAPI runtime foundation
- PostgreSQL content-job repository and migrations
- Content-job lifecycle state machine
- Durable PostgreSQL job queue with leases and recovery
- Lease-token fencing and transactional worker state/audit/queue updates
- Bounded retry and dead-letter handling
- Terminal retry and lease-recovery outcomes update content-job state and audit in the same transaction
- Unhandled jobs are blocked and dead-lettered instead of being marked planned without processing
- Content-job API requests are limited to 1 MiB
- Immutable application audit-event persistence
- Atomic idempotent job creation and audit persistence
- Versioned startup migrations with restricted runtime database role
- Database-backed API rate limiting
- Dedicated production worker service
- Production API bearer authentication
- Docker and Compose runtime with dependency healthchecks
- Unit/API test suite
- Ruff formatting/linting and Python compile validation
- Dependency vulnerability audit
- SBOM generation

### Changed

- CI now validates the application runtime instead of only inherited template files.
- CI third-party actions are pinned to immutable commit SHAs where implemented.
- Production readiness documentation now distinguishes the production-core gate from the incomplete full platform.
- Compose credentials are required through environment injection rather than committed defaults.
- Worker execution refuses unsupported workflow states instead of guessing behavior.
- Worker handles SIGINT/SIGTERM and interrupts idle polling for prompt graceful shutdown.
- Add an on-demand PostgreSQL custom-archive backup utility with credential-safe subprocess handling and a disposable restore runbook.

### Security

- Removed the compromised Trivy GitHub Action from CI after Dependency Review identified advisory GHSA-69fq-xp46-6x23.
- Production/staging startup now fails closed without an API token.
- Production/staging API tokens must be at least 32 non-whitespace characters; cost budgets reject NaN and infinity values.
- Migrations reject an existing runtime database role that still owns database objects.
- Production API mutations require bearer authentication and idempotency keys.
- Production API traffic receives security response headers and database-backed rate limiting.
- API and worker database access no longer uses the PostgreSQL administrator role.
- Dependency versions were upgraded to remove current pip, pytest, and Starlette advisories.
- CodeQL and CI action references are pinned to immutable commits to reduce workflow supply-chain risk.

### Release status

This is an unreleased production-core hardening increment. The full YouTube automation platform is not declared production-ready until the remaining integration, security, recovery, observability, and operational gates in `docs/PRODUCTION_READINESS.md` are evidenced in the target runtime.
