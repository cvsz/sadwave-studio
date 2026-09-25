# SadwaveStudio Architecture

## Status

The current runtime implements a FastAPI API, PostgreSQL job and queue storage, a dedicated worker, versioned migrations, and audit events. YouTube, AI, media, object storage, dashboard, and publishing adapters remain planned capabilities.

## Architectural principles

1. Domain logic is independent of external providers.
2. Adapters isolate YouTube, AI, media, storage, notification, and distribution integrations.
3. External input is untrusted.
4. Mutations are authorized, policy checked, idempotent, verified, and audited.
5. Workers are stateless and recoverable.
6. Large media uses streaming/object storage rather than unbounded memory.
7. Historical analytics is append-oriented; snapshots are not overwritten.
8. Paid services are opt-in and budget constrained.
9. Human approval is mandatory for configured high-risk actions.
10. Observability is part of the application contract.

## Current runtime topology

```text
API ─────┐
         ├── PostgreSQL: content jobs, queue, audit events, rate limits
Worker ──┘
```

Dashboard/CLI, provider adapters, and object storage are not implemented yet.

## Proposed repository shape

```text
apps/
  api/
  dashboard/
  workers/

packages/
  domain/
  application/
  infrastructure/
  youtube/
  analytics/
  ai/
  media/
  publishing/
  distribution/
  moderation/
  observability/

workflows/
  content/
  analytics/
  publishing/
  shorts/
  distribution/

infrastructure/
  docker/
  terraform/
  kubernetes/
  monitoring/

docs/
tests/
scripts/
```

This is a target boundary, not a license to create empty scaffolding. Add a directory when there is an implemented capability that requires it.

## Core entities

Channel, Video, Short, Playlist, Artist, Song, Album, Release, MediaAsset, ContentIdea, ContentPlan, ContentJob, PublishingJob, DistributionJob, ThumbnailCandidate, SubtitleTrack, Translation, Comment, AudienceSegment, AnalyticsSnapshot, Experiment, RevenueRecord, CopyrightRisk, ModerationDecision, AuditEvent, ProviderCredential, WorkflowExecution.

Every entity needs stable identity, timestamps, lifecycle state, validation, ownership/tenant boundaries where applicable, and audit/idempotency strategy.

## Trust boundaries

- YouTube/API responses: untrusted data.
- Comments, titles, descriptions, transcripts, web pages: untrusted content.
- Uploaded media: untrusted executable-adjacent input.
- AI output: untrusted generated data.
- Webhooks: untrusted until authenticated and replay-protected.
- CI pull requests and dependencies: untrusted supply-chain inputs.

## High-risk mutation boundary

No public mutation may bypass:

`validate → authorize → policy → idempotency → execute → verify → audit`.

## Analytics

Historical measurements should be retained by time window and population. Derived metrics must identify their window and input population. Observed data must never be presented as model inference.

## Resilience

External failures are classified as:

- RETRYABLE
- NON_RETRYABLE
- AUTHENTICATION
- AUTHORIZATION
- QUOTA
- VALIDATION
- DEPENDENCY
- SECURITY

Workers must support timeout, retry, dead-letter, cancellation, heartbeat, lease/recovery, and duplicate-request protection.

## Cost controls

Runtime configuration will support cost locks and explicit limits. Exceeding a configured limit pauses relevant work and emits an alert; it does not silently select a paid provider.
