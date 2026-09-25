# Production Readiness

This file is the authoritative checklist for declaring SadwaveStudio production-ready.

## Current status

**BLOCKED — foundation only.**

The repository was created from the generic `ztemplate` baseline and currently does not contain the complete SadwaveStudio application implementation. This status is intentional and prevents documentation from overstating readiness.

## Gates

### Application

- [ ] API implementation complete
- [ ] Dashboard implementation complete
- [ ] Worker implementation complete
- [ ] Domain model implemented
- [ ] State machines implemented
- [ ] Idempotency implemented
- [ ] Audit implementation complete

### Data and infrastructure

- [ ] Database schema and migrations
- [ ] Queue implementation
- [ ] Object storage
- [ ] Backup
- [ ] Restore verification
- [ ] Production Docker images
- [ ] Resource limits
- [ ] Health/readiness endpoints

### Integrations

- [ ] YouTube contract validated
- [ ] OAuth lifecycle validated
- [ ] AI provider contracts validated
- [ ] Media pipeline validated
- [ ] Notification adapters validated
- [ ] Distribution adapters validated

### Security

- [ ] Authentication
- [ ] RBAC
- [ ] Input/output validation
- [ ] Rate limiting
- [ ] CSRF/CORS/security headers where applicable
- [ ] Secret scanning
- [ ] Dependency scanning
- [ ] SAST
- [ ] Container scanning
- [ ] SBOM
- [ ] Threat-model tests
- [ ] Prompt-injection defenses
- [ ] Malicious-media isolation

### Validation

- [ ] Formatting
- [ ] Lint
- [ ] Typecheck
- [ ] Unit tests
- [ ] Integration tests
- [ ] API tests
- [ ] Queue tests
- [ ] Provider contract tests
- [ ] Media tests
- [ ] Security tests
- [ ] E2E tests
- [ ] Retry tests
- [ ] Idempotency tests
- [ ] Crash/restart recovery tests

### Operations

- [ ] Structured logs
- [ ] Metrics
- [ ] Traces
- [ ] Alerts
- [ ] Cost controls
- [ ] DR documentation
- [ ] RPO/RTO defined
- [ ] Rollback tested
- [ ] Manual approval gates verified

A production claim requires evidence for every applicable gate.
