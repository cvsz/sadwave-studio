# Changelog

All notable changes to SadwaveStudio should be documented here.

## [Unreleased]

### Added

- Production Python/FastAPI runtime foundation
- PostgreSQL content-job repository and initial migration
- Content-job lifecycle state machine
- Idempotency enforcement and request-conflict detection
- Production API bearer authentication
- Docker and Compose runtime with dependency healthchecks
- Unit/API test suite
- Ruff formatting/linting and Python compile validation
- Dependency vulnerability audit
- SBOM generation

### Changed

- CI now validates the application runtime instead of only inherited template files.
- Production readiness documentation now distinguishes implemented runtime capabilities from the incomplete full platform.
- Compose credentials are required through environment injection rather than committed defaults.

### Security

- Removed the compromised Trivy GitHub Action from CI after GitHub Dependency Review identified advisory GHSA-69fq-xp46-6x23.
- Production/staging startup now fails closed without an API token.
- Production API mutations require bearer authentication and idempotency keys.
