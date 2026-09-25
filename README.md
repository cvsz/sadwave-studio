# SadwaveStudio

Production-grade, secure, observable, cost-controlled automation for YouTube content operations.

> **Status: Foundation / not production-ready.** The repository currently contains the hardened project baseline and architecture contract. Application capabilities are being implemented incrementally behind explicit readiness gates.

## Mission

SadwaveStudio is designed to continuously support:

- YouTube channel synchronization and intelligence
- content opportunity discovery and planning
- AI-assisted scripts, metadata, subtitles, translations, and thumbnails
- deterministic media processing and Shorts candidates
- approval-gated publishing and distribution
- analytics, experiments, anomaly detection, and recommendations
- community/comment intelligence
- provenance, auditability, security, and cost controls
- local-first AI with provider independence

## Safety model

High-risk operations use:

`validate → authorize → policy → idempotency → execute → verify → audit`

Publishing, deletion, replacement, public communication, credential changes, billing changes, copyright-sensitive actions, and policy-sensitive content require explicit approval unless an enabled autonomy policy permits them.

The system must never automate fake engagement, spam, credential abuse, CAPTCHA bypass, rate-limit bypass, or copyright circumvention.

## Architecture

See:

- [Architecture](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
- [AI Master Production Prompt](docs/AI_MASTER_PRODUCTION_PROMPT.md)
- [Security Model](docs/SECURITY_MODEL.md)
- [Production Readiness](docs/PRODUCTION_READINESS.md)

Target boundaries include API, dashboard, workers, domain/application services, provider adapters, persistence, queues, object storage, media processing, AI, publishing, distribution, analytics, and audit.

## Source of truth

`cvsz/ztemplate` is the architectural/reference baseline only. SadwaveStudio must adapt the template rather than modify or blindly copy it.

## Development contract

Read [AGENTS.md](AGENTS.md) before making changes.

Production readiness requires evidence, not generated files or documentation alone.

## License

MIT. See [LICENSE](LICENSE).
