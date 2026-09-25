# Changelog

All notable changes to SadwaveStudio should be documented here.

## [Unreleased]

### Added

- Production Python/FastAPI runtime foundation
- PostgreSQL content-job repository and migrations
- Content-job lifecycle state machine
- Durable PostgreSQL job queue with leases and recovery
- Bounded retry and dead-letter handling
- Immutable application audit-event persistence
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

### Security

- Removed the compromised Trivy GitHub Action from CI after Dependency Review identified advisory GHSA-69fq-xp46-6x23.
- Production/staging startup now fails closed without an API token.
- Production API mutations require bearer authentication and idempotency keys.
- Production API traffic receives security response headers and database-backed rate limiting.
- CodeQL and CI action references are pinned to immutable commits to reduce workflow supply-chain risk.

### Release status

This is an unreleased production-core hardening increment. The full YouTube automation platform is not declared production-ready until the remaining integration, security, recovery, observability, and operational gates in `docs/PRODUCTION_READINESS.md` are evidenced in the target runtime.
