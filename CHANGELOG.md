# Changelog

All notable changes to SadwaveStudio should be documented here.

## [Unreleased]

### Added

- SadwaveStudio production automation master contract
- Domain architecture and trust-boundary documentation
- Implementation plan and production-readiness gates
- Security threat model and mutation safety contract

### Changed

- Replaced generic template agent guidance with SadwaveStudio-specific engineering rules
- Replaced placeholder task commands with repository validation and security checks
- Added explicit local-first, dry-run, autonomy, and cost-lock configuration examples
- Replaced the generic Docker placeholder with a fail-closed foundation image

### Fixed

- Removed generic template identity from the main project documentation

### Security

- Added explicit controls for prompt injection, malicious media, OAuth secrets, webhook replay, unauthorized publishing, and uncontrolled paid-provider fallback
