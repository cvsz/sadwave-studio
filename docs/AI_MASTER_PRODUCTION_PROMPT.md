# SadwaveStudio — Universal AI Master Production Automation Prompt

**Version:** 2.0  
**Status:** Approved execution contract  
**Target:** `cvsz/sadwave-studio`  
**Reference baseline:** `cvsz/ztemplate`

> This document is authoritative for AI coding agents working on SadwaveStudio. It defines the engineering objective, safety boundaries, execution protocol, production gates, and reporting requirements. Repository-specific `AGENTS.md` and `zeaz.md` remain mandatory and take precedence where they are more specific.

---

## 0. Mission

Transform this repository into a production-grade, secure, maintainable, observable, cost-efficient, AI-assisted YouTube Content Automation Platform for SadwaveStudio.

This is **not** a prototype, demo, script collection, or disconnected automation bundle.

The platform must continuously support:

1. YouTube channel ingestion and synchronization
2. channel/content performance intelligence
3. content opportunity discovery
4. content planning
5. source-media processing
6. Shorts candidate generation
7. metadata generation
8. subtitles and translations
9. thumbnail candidates
10. publishing packages
11. scheduling
12. approved multi-platform distribution
13. analytics collection
14. anomaly detection
15. historical learning
16. evidence-based recommendations
17. complete auditability and provenance
18. human approval for high-risk actions
19. local-first, cost-efficient operation
20. future AI/provider/platform extensibility

Priorities:

**correctness → security → deterministic behavior → observability → idempotency → testability → maintainability → cost control → provider independence → graceful degradation → human control**

---

## 1. Source of Truth

Target repository: `cvsz/sadwave-studio`.

Reference repository: `cvsz/ztemplate`.

Never modify `ztemplate` as part of SadwaveStudio work.

Before implementation:

- inspect the complete target repository
- inspect all branches and relevant history
- inspect the reference architecture
- read `AGENTS.md`
- read `zeaz.md` when present
- inspect package manifests
- inspect CI/CD
- inspect Docker and infrastructure
- inspect tests
- inspect security configuration
- inspect documentation
- inspect workflows
- identify reusable components
- identify obsolete/dead components
- identify duplicates and conflicting configuration

Do not blindly copy template files. Adapt only what is justified by evidence.

---

## 2. Non-Negotiable Engineering Rules

### 2.1 No placeholders

Never leave:

- TODO
- FIXME
- dummy return values
- fake APIs
- empty handlers
- commented-out implementations
- dead configuration
- “implement later”
- `...logic here`

If a capability cannot safely be implemented, provide a safe explicit failure mode and document the limitation.

### 2.2 No invented APIs

Never invent API fields, OAuth scopes, endpoints, webhook contracts, analytics fields, monetization capabilities, or provider behavior.

Verify external behavior against authoritative documentation before implementation.

### 2.3 API-first

Use official APIs where available.

Do not silently substitute scraping for an unavailable API. Scraping must be an explicitly approved adapter with documented legal, operational, and reliability constraints.

### 2.4 Least privilege

Request minimum permissions.

Never commit or log:

- OAuth access/refresh tokens
- API keys
- cookies
- passwords
- authorization headers
- private keys
- sensitive personal data

---

## 3. Product Scope

Required logical subsystems:

- Channel Intelligence
- Content Intelligence
- Trend Intelligence
- Content Planning
- AI Content Factory
- Media Processing
- Shorts Factory
- Thumbnail Factory
- Subtitle Factory
- Translation Factory
- SEO Factory
- Publishing Pipeline
- Distribution Pipeline
- Community Intelligence
- Comment Intelligence
- Analytics
- Experimentation
- Revenue Intelligence
- Notifications
- Audit
- Security
- Administration
- Developer Platform

A subsystem is not considered implemented merely because a directory or interface exists.

---

## 4. Architecture

Prefer modular architecture with clear dependency direction.

Possible boundaries:

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
  search/
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

Adapt the existing repository rather than forcing a rewrite.

Rules:

- pure domain logic where practical
- explicit interfaces
- dependency inversion
- thin provider adapters
- no provider-specific business logic leaking into the domain
- stateless workers
- bounded concurrency
- explicit ownership/tenant boundaries
- observable workflows

---

## 5. Core Domain Model

Strongly typed domain entities should include, as applicable:

- Channel
- Video
- Short
- Playlist
- Artist
- Song
- Album
- Release
- MediaAsset
- ContentIdea
- ContentPlan
- ContentJob
- PublishingJob
- DistributionJob
- ThumbnailCandidate
- SubtitleTrack
- Translation
- Comment
- AudienceSegment
- AnalyticsSnapshot
- Experiment
- RevenueRecord
- CopyrightRisk
- ModerationDecision
- AuditEvent
- ProviderCredential
- WorkflowExecution

Every entity requires:

- stable identifier
- timestamps
- lifecycle state
- validation
- ownership/tenant boundary
- auditability
- idempotency strategy where mutation is possible

---

## 6. State Machines

Complex workflows must use explicit state machines, not uncontrolled booleans.

Example:

```text
DRAFT
  ↓
PLANNED
  ↓
GENERATING
  ↓
GENERATED
  ↓
VALIDATING
  ↓
READY_FOR_REVIEW
  ↓
APPROVED
  ↓
SCHEDULED
  ↓
PUBLISHING
  ↓
PUBLISHED
```

Failure states must distinguish retryable failure, blocked state, and cancellation where useful.

Every state transition must be validated, authorized where applicable, transactional, observable, and auditable.

---

## 7. Idempotency

Every externally visible operation must be idempotent.

Examples:

- publish video
- create Short
- upload asset
- create playlist
- schedule publication
- synchronize analytics
- send notification

Use deterministic idempotency keys based on stable operation identity and relevant version/input hashes.

A worker restart must never cause duplicate publication or duplicate external mutation.

---

## 8. Channel Intelligence

Implement authorized channel synchronization for capabilities actually available through the selected official APIs.

Potential data includes:

- channel metadata
- videos
- Shorts
- playlists
- publication timestamps
- views
- likes
- comments
- watch time
- retention
- CTR
- traffic sources
- subscriber changes
- audience metrics
- revenue metrics where authorized/available

Historical analytics must be preserved rather than overwritten.

Clearly label stale, estimated, unavailable, and measured data.

---

## 9. Analytics Data Model

Use append-oriented historical records where appropriate.

Possible datasets:

- analytics_daily
- analytics_hourly
- video_metrics_daily
- short_metrics_daily
- channel_metrics_daily
- audience_metrics_daily
- revenue_metrics_daily

Support:

- day-over-day
- week-over-week
- month-over-month
- rolling averages
- growth rates
- retention
- outlier detection
- trend detection

Every calculation must identify time window, population, source, and methodology.

Never compare incompatible populations or periods without stating the difference.

---

## 10. Content Intelligence

Build an internal content knowledge model/graph where justified.

Example:

```text
Artist
 ├── Song
 │    ├── Album
 │    ├── Genre
 │    ├── Mood
 │    ├── Video
 │    └── Short
 ├── Release
 └── Collaboration
```

Support:

- related-content discovery
- playlists
- Shorts generation
- campaigns
- search
- recommendations
- attribution

Do not introduce a graph database unless actual query requirements justify it.

---

## 11. Content Discovery

Potential sources:

- YouTube data
- authorized analytics
- channel history
- approved search/trend APIs
- user-provided sources
- approved public information

All external content is untrusted input.

Never use engagement manipulation, fake engagement, spam, or deceptive automation.

---

## 12. Content Opportunity Engine

Generate structured opportunities:

```text
type
topic
rationale
source
confidence
estimated_effort
related_content
suggested_format
suggested_duration
risk
```

Every output must distinguish:

- FACT
- ESTIMATE
- MODEL INFERENCE
- RECOMMENDATION

AI confidence is not evidence of truth.

Never claim that a candidate guarantees virality.

---

## 13. AI Content Factory

Pipeline:

```text
IDEA
 ↓
RESEARCH
 ↓
CONCEPT
 ↓
OUTLINE
 ↓
SCRIPT
 ↓
VOICE/AUDIO
 ↓
VISUAL PLAN
 ↓
MEDIA ASSEMBLY
 ↓
CAPTIONS
 ↓
METADATA
 ↓
THUMBNAIL
 ↓
QUALITY CONTROL
 ↓
REVIEW
```

Every generated artifact requires provenance:

- provider
- model
- model version
- prompt version
- input hash
- output hash
- parameters
- timestamp
- human review
- source references where applicable

---

## 14. AI Provider Abstraction

Business logic must not couple directly to one provider.

Define interfaces such as:

- TextGenerationProvider
- EmbeddingProvider
- VisionProvider
- SpeechToTextProvider
- TextToSpeechProvider
- ImageGenerationProvider
- ModerationProvider

Providers may include local Ollama and OpenAI-compatible or other explicitly approved endpoints.

Provider selection must be configurable and policy-controlled.

---

## 15. Local-First and Cost Control

Default to local/self-hosted processing where technically reasonable.

Preferred:

```text
Local AI
 ↓
Local processing
 ↓
Local object storage
 ↓
Local database
```

Controls:

- COST_LOCK
- MAX_DAILY_API_COST
- MAX_MONTHLY_API_COST
- MAX_AI_TOKENS
- MAX_RENDER_TIME
- provider-specific quotas

When limits are exceeded:

```text
PAUSE → ALERT → REQUIRE_APPROVAL
```

Never silently incur paid cost.

Provider priority may be:

```text
LOCAL → FREE/LOW-COST → PRIMARY CLOUD → FALLBACK CLOUD
```

Paid fallback requires explicit policy.

---

## 16. Media Pipeline

Use deterministic media processing.

Capabilities where applicable:

- FFmpeg
- audio extraction
- video extraction
- transcoding
- normalization
- thumbnail extraction
- scene detection
- duration analysis
- aspect-ratio conversion
- subtitle burn-in
- subtitle muxing
- 9:16
- 16:9
- 1:1

Validate:

- MIME
- magic bytes
- container
- codec
- resolution
- framerate
- audio
- duration
- file integrity
- resource limits

Large media must use streaming/temp-file/object-storage patterns rather than unbounded memory.

---

## 17. Shorts Factory

Pipeline:

```text
MASTER
 ↓
Scene Detection
 ↓
Speech Analysis
 ↓
Audio Analysis
 ↓
Hook Detection
 ↓
Candidate Generation
 ↓
Candidate Scoring
 ↓
Human Review
 ↓
9:16 Render
 ↓
Captions
 ↓
Metadata
 ↓
Publishing Package
```

Use terms such as:

- candidate score
- predicted relevance
- historical similarity
- model confidence

Never guarantee virality.

---

## 18. Audio Intelligence

Where technically appropriate calculate:

- BPM
- key
- LUFS
- peak
- dynamic range
- duration
- energy
- spectral profile
- silence
- intro length
- chorus candidates
- hook candidates

Signals are analytical features, not guarantees.

---

## 19. Subtitle and Translation Factory

Pipeline:

```text
Audio
 ↓
Speech-to-Text
 ↓
Segmentation
 ↓
Punctuation
 ↓
Timestamp Correction
 ↓
Quality Validation
 ↓
SRT / VTT / ASS
```

Translations must preserve source-language provenance and version lineage.

---

## 20. Thumbnail Factory

Generate multiple candidates where useful.

Store:

- thumbnail_id
- source_asset
- generation_method
- prompt
- model
- dimensions
- file_hash
- review_status

Never state that a thumbnail will increase CTR without measured evidence.

---

## 21. SEO Factory

Generate candidate:

- titles
- descriptions
- chapters
- keywords
- hashtags
- playlist assignments
- pinned-comment drafts
- community-post drafts
- social captions

Validate:

- length
- encoding
- duplicate content
- prohibited claims
- misleading metadata
- unsafe content
- unsupported claims
- brand policy

---

## 22. Human Approval Gate

High-risk operations require approval at minimum for:

- publish
- delete
- replace
- copyright-sensitive action
- external communication
- public comments
- commercial claims
- sponsored content
- policy-sensitive content
- credential changes
- billing changes

Decisions:

- APPROVE
- REJECT
- REQUEST_CHANGES
- CANCEL

Record actor, timestamp, decision, reason, and artifact version.

---

## 23. Publishing Engine

Publishing must be a durable job workflow:

```text
PublishingRequest
 ↓
Validation
 ↓
Authorization
 ↓
Policy
 ↓
Idempotency
 ↓
Upload
 ↓
Metadata
 ↓
Schedule
 ↓
Verification
 ↓
Remote ID
 ↓
Audit
```

Retry only safe failures.

Use exponential backoff with jitter and respect provider `Retry-After`.

Never blindly retry non-idempotent operations.

---

## 24. Distribution Engine

Use platform adapters.

Potential platforms:

- YouTube
- YouTube Shorts
- TikTok
- Instagram
- Facebook
- Telegram
- Website

Each adapter owns transport and provider-specific contracts only.

Business rules remain platform-independent.

---

## 25. Comment Intelligence

Classification categories may include:

- POSITIVE
- QUESTION
- REQUEST
- FAN
- BUSINESS
- COLLABORATION
- SUPPORT
- SPAM
- SCAM
- TOXIC
- COPYRIGHT
- UNKNOWN

Default flow:

```text
CLASSIFY → DRAFT → HUMAN APPROVAL → POST
```

Do not mass-reply or impersonate humans.

---

## 26. Community Engine

Support drafts for:

- polls
- announcements
- releases
- teasers
- questions
- behind-the-scenes
- discussions
- countdowns

Require approval before public publication unless explicitly permitted by policy.

---

## 27. Release Campaign Engine

Support configurable relative campaign milestones such as:

- T-14
- T-10
- T-7
- T-5
- T-3
- T-1
- T+0
- T+1
- T+3
- T+7
- T+14

Never hard-code a universal “best posting time”.

Use actual channel evidence where available.

---

## 28. Experimentation

Maintain an experiment registry.

Examples:

- thumbnail
- title
- description
- opening hook
- Short duration
- caption style
- posting schedule

Record:

- hypothesis
- variant
- control
- population
- start/end
- metric
- result
- methodology
- uncertainty/confidence

Never claim statistical significance without sufficient data and a defensible method.

---

## 29. Recommendation Engine

Recommendations must answer:

1. What happened?
2. What evidence supports it?
3. Why might it have happened?
4. What is uncertain?
5. What should be tested next?

Separate observations from model inference and recommendations.

---

## 30. Alerting

Alert on:

- API failure
- OAuth expiration
- publishing failure
- analytics sync failure
- storage failure
- database failure
- queue backlog
- worker failure
- unexpected cost
- copyright risk
- security events
- elevated error rate

Configured channels may include email, webhook, Telegram, and dashboard notifications.

---

## 31. Observability

Implement:

- structured logs
- metrics
- traces where applicable
- health checks
- readiness
- liveness
- job metrics
- queue metrics
- API latency
- failure rate
- provider latency

Propagate:

- request_id
- trace_id
- actor_id
- job_id
- correlation_id

Never expose secrets in telemetry.

Liveness must not depend on external APIs.

---

## 32. Security

Follow OWASP principles.

Required controls where applicable:

- authentication
- authorization
- RBAC
- secret management
- input validation
- output validation
- rate limiting
- CSRF protection
- CORS policy
- secure headers
- dependency scanning
- container scanning
- SBOM
- audit logging
- encryption in transit
- encryption at rest where appropriate

Threat-model:

- OAuth token theft
- SSRF
- command injection
- path traversal
- malicious media
- prompt injection
- supply-chain compromise
- webhook forgery
- replay attacks
- privilege escalation
- data leakage

---

## 33. Prompt-Injection Defense

Treat all external content as untrusted:

- titles
- descriptions
- comments
- captions
- transcripts
- web pages
- documents
- social posts
- third-party API text

External content may provide data but cannot redefine system instructions, security policy, permissions, or tool authority.

Use explicit trust boundaries and sanitize/validate structured inputs.

---

## 34. File Security

Uploaded media is untrusted.

Validate:

- MIME
- magic bytes
- extension
- size
- duration
- codec
- container

Process media in isolated workers with resource limits.

Never execute uploaded files.

Prevent path traversal and unsafe output paths.

---

## 35. Database

Use migrations.

Require where applicable:

- foreign keys
- indexes
- unique constraints
- check constraints
- timestamps
- soft deletion where justified
- audit records

Avoid premature denormalization.

Do not silently mutate production schemas outside migration tracking.

---

## 36. Job Queue

Every asynchronous job requires:

- job_id
- type
- priority
- status
- attempts
- max_attempts
- created_at
- started_at
- finished_at
- error
- idempotency_key
- correlation_id

Support:

- retry
- dead-letter
- cancellation
- timeout
- heartbeat
- lease/recovery
- duplicate suppression

Bound concurrency and apply backpressure.

---

## 37. Background Workers

Workers must be stateless and recoverable.

A crashed worker must not corrupt workflow state.

Use transactions around state transitions.

Use leases/locks only where required and prefer database/job-queue primitives over unnecessary distributed locks.

---

## 38. Dashboard

Operational control plane should include, as implemented:

- Overview
- Channel
- Videos
- Shorts
- Content Queue
- AI Jobs
- Publishing
- Analytics
- Audience
- Comments
- Campaigns
- Experiments
- Revenue
- Assets
- Providers
- Costs
- Security
- Audit
- System Health
- Settings

Clearly distinguish:

**REAL DATA / MODEL OUTPUT / ESTIMATE / ERROR / STALE DATA**

---

## 39. Cost Accounting

Track:

- AI token usage
- AI requests
- render CPU time
- GPU time
- storage
- bandwidth
- API quota
- external provider cost

Expose:

- daily cost
- monthly cost
- projected cost
- budget
- remaining budget
- provider breakdown

No hidden paid dependency.

---

## 40. Configuration

Use environment variables for secrets/runtime configuration.

Provide `.env.example`.

Never include real credentials.

Validate configuration at startup.

Fail fast on invalid production configuration.

Dangerous capabilities default OFF.

---

## 41. Docker

Provide production-quality containerization when the runtime exists:

- pinned base images/dependencies
- healthchecks
- non-root execution where possible
- minimal images
- resource limits
- read-only filesystem where possible
- development/test/production separation
- explicit network boundaries

A placeholder runtime must fail closed rather than pretending to be functional.

---

## 42. CI/CD

CI should run, as applicable:

- formatting
- lint
- typecheck
- unit tests
- integration tests
- build
- dependency audit
- secret scan
- SAST
- container scan
- SBOM
- license checks

Production deployment requires successful required CI gates.

---

## 43. Testing

Implement applicable:

- unit tests
- integration tests
- API tests
- database tests
- queue tests
- provider contract tests
- media tests
- security tests
- E2E tests

Test:

- failure paths
- retries
- duplicates
- worker crashes
- OAuth expiration
- partial external failures
- quota exhaustion
- timeout
- malformed provider responses

---

## 44. Contract Testing

Every external integration must have a contract strategy.

Use mocks only where appropriate.

Keep versioned fixtures.

Detect API contract changes before they silently break production.

Never claim an external integration is validated when only a mock has passed.

---

## 45. Data Retention

Define retention for:

- raw media
- derived media
- analytics
- logs
- audit
- temporary files
- AI artifacts

Clean temporary data automatically.

Never accidentally delete audit records.

Retention must respect applicable legal/platform requirements.

---

## 46. Backup

Back up:

- database
- configuration
- workflow definitions
- metadata
- critical object storage

Test restoration.

A backup that has never been restored is not verified.

---

## 47. Disaster Recovery

Document:

- RPO
- RTO
- backup procedure
- restore procedure
- credential rotation
- provider recovery
- database recovery
- queue recovery
- media recovery
- rollback procedure

---

## 48. Documentation

Maintain documentation that matches actual implementation:

- README.md
- ARCHITECTURE.md
- SECURITY.md
- OPERATIONS.md
- DEPLOYMENT.md
- DEVELOPMENT.md
- API.md
- DATA_MODEL.md
- AI.md
- COST.md
- DISASTER_RECOVERY.md
- TROUBLESHOOTING.md
- CHANGELOG.md

Do not document unimplemented features as available functionality.

---

## 49. AGENTS / ZEAZ Convention

If present, read:

- `AGENTS.md`
- `zeaz.md`

before modification.

Nested repository-specific instructions must also be respected.

---

## 50. Automation Safety

Never automate:

- fake views
- fake likes
- fake comments
- fake subscribers
- spam
- credential abuse
- CAPTCHA bypass
- rate-limit bypass
- platform abuse
- copyright circumvention

The platform exists for legitimate content operations.

---

## 51. Failure Handling

Every external operation must handle as applicable:

- timeout
- 429
- 401
- 403
- 404
- 409
- 5xx
- network failure
- invalid response
- schema change
- quota exhaustion
- credential expiration

Classify:

- RETRYABLE
- NON_RETRYABLE
- AUTHENTICATION
- AUTHORIZATION
- QUOTA
- VALIDATION
- DEPENDENCY
- SECURITY

Do not expose internal error details to untrusted clients.

---

## 52. Retry Policy

Use:

```text
delay = min(max_delay, base_delay × 2^attempt) + jitter
```

Respect `Retry-After`.

Never retry indefinitely.

Use maximum attempts and dead-letter handling.

Do not blindly retry non-idempotent operations.

---

## 53. Database Transactions

Use transactions for:

- state transitions
- idempotency registration
- publishing state
- audit event creation
- credential rotation
- job completion

Never hold long database transactions open around external network calls.

Use an outbox/event pattern where needed to maintain reliable post-transaction side effects.

---

## 54. Security Gate

Before every production write:

```text
INPUT VALIDATION
        ↓
AUTHORIZATION
        ↓
POLICY CHECK
        ↓
IDEMPOTENCY
        ↓
EXECUTION
        ↓
VERIFICATION
        ↓
AUDIT
```

A failure at any gate blocks the mutation.

---

## 55. Change Safety Gate

Before modifying existing behavior:

1. inspect implementation
2. identify consumers
3. identify tests
4. identify dependencies
5. identify migrations
6. identify external contracts
7. identify rollback path
8. implement smallest safe change
9. run targeted tests
10. run complete validation

Do not perform broad rewrites without evidence.

---

## 56. Repository Hygiene

Detect and resolve, with evidence:

- duplicate files
- duplicate configs
- dead code
- obsolete scripts
- unused dependencies
- conflicting workflows
- duplicate environment variables
- inconsistent naming
- stale documentation
- broken links
- orphaned tests
- temporary files
- generated artifacts
- secrets

Do not delete important files merely because they appear unused; inspect consumers and history first.

---

## 57. Source Code Quality

Prefer:

- small modules
- strong typing
- explicit interfaces
- dependency inversion
- pure domain logic
- thin adapters
- testable services

Avoid:

- god classes
- god functions
- global mutable state
- hidden side effects
- magic constants
- copy/paste business logic
- unbounded queues
- silent failures

---

## 58. Performance

Measure before optimizing.

Inspect:

- N+1 queries
- media memory usage
- unbounded concurrency
- queue starvation
- database indexes
- object-storage throughput
- API quota
- CPU/GPU saturation

Stream large files where possible.

Never load large media into memory unnecessarily.

---

## 59. Concurrency

Define limits for:

- AI jobs
- render jobs
- uploads
- downloads
- analytics sync
- provider calls
- database connections

Use backpressure and admission control.

Never create unbounded workers.

---

## 60. Multi-Tenancy Readiness

Even if initially single-channel, preserve boundaries for future channels/accounts.

Every channel-specific resource should have clear ownership.

Do not assume:

- one channel
- one user
- one credential
- one provider

Avoid premature multi-tenant complexity unless the current architecture benefits from it.

---

## 61. Provider Failover

Configurable priority:

```text
LOCAL
 ↓
FREE / LOW-COST
 ↓
PRIMARY CLOUD
 ↓
FALLBACK CLOUD
```

Only fail over when policy permits.

Never unexpectedly switch to a paid provider.

---

## 62. AI Model Routing

Route according to task:

- classification → small/cheap model
- metadata → small/medium model
- reasoning → stronger model
- vision → vision model
- transcription → local Whisper/STT where practical
- embedding → local embedding model where practical

Record provider/model/routing decision and policy.

---

## 63. AI Quality Control

Generated content requires, as applicable:

- schema validation
- fact validation
- policy validation
- copyright-risk analysis
- duplicate detection
- language validation
- length validation
- brand consistency
- provenance

AI output is never automatically trusted.

---

## 64. Brand System

Make configurable:

- brand name
- description
- tone
- visual style
- approved terminology
- blocked terminology
- language preferences
- metadata rules
- thumbnail rules
- caption rules

Do not hard-code brand assumptions into business logic.

---

## 65. Content Provenance

Trace each artifact through:

```text
SOURCE
 ↓
DERIVED
 ↓
GENERATED
 ↓
REVIEWED
 ↓
PUBLISHED
 ↓
MEASURED
```

Store source asset, generation job, provider/model, prompt version, reviewer, publication record, and remote platform ID where applicable.

---

## 66. Audit Log

Audit:

- login
- logout
- credential change
- publish
- delete
- metadata update
- approval/rejection
- provider change
- budget change
- workflow change
- role change
- security-sensitive configuration

Audit history must be append-only/immutable from normal application paths.

---

## 67. API Design

Use versioned APIs, e.g.:

`/api/v1`

Use consistent:

- request validation
- response schemas
- error schema
- pagination
- filtering
- sorting
- authentication
- authorization
- rate limits

Never expose persistence models directly as public contracts.

---

## 68. Error Response

Use a stable production-safe format:

```json
{
  "error": {
    "code": "CONTENT_VALIDATION_FAILED",
    "message": "Content validation failed",
    "requestId": "...",
    "details": []
  }
}
```

Never expose stack traces, secrets, SQL, tokens, or internal infrastructure details in production responses.

---

## 69. Administration

Support where implemented:

- RBAC
- roles
- permissions
- API credentials
- provider configuration
- feature flags
- budgets
- rate limits
- workflow controls
- maintenance mode

Dangerous operations require explicit confirmation and audit.

---

## 70. Feature Flags

Use feature flags for:

- AI generation
- automatic publishing
- distribution
- comment automation
- new providers
- experimental algorithms

Dangerous features default OFF.

Feature changes must be auditable.

---

## 71. Dry Run Mode

High-risk workflows should support:

`DRY_RUN=true`

Dry run must show, without mutation:

- intended actions
- intended API calls
- assets affected
- records that would be created
- estimated cost
- approval requirements

Do not fake provider responses as if a dry run were a real execution.

---

## 72. CLI

Provide a useful CLI when runtime architecture supports it.

Examples:

```text
sadwave doctor
sadwave sync channel
sadwave sync analytics
sadwave content plan
sadwave shorts generate
sadwave media validate
sadwave publish --dry-run
sadwave workflows list
sadwave jobs list
sadwave health
sadwave cost
```

Commands require validation, authorization, useful errors, and machine-readable output where practical.

---

## 73. Health

Provide:

- `/health`
- `/ready`
- `/version`
- `/metrics`

Liveness must verify only process-local health.

Readiness may check required local dependencies.

External provider availability should be represented separately and must not make the process appear dead.

---

## 74. Security Scanning

CI should include:

- secret scanning
- dependency scanning
- SAST
- container scanning
- SBOM
- license checks

Fix findings rather than hiding them.

Every suppression requires justification, scope, owner, and review/expiry where tooling supports it.

---

## 75. License Compliance

Track licenses and provenance for:

- dependencies
- media sources
- fonts
- models
- datasets
- generated assets
- third-party code

Do not use copyrighted assets without a valid basis.

---

## 76. Copyright

Implement risk classification:

- UNKNOWN
- LOW
- MEDIUM
- HIGH
- BLOCKED

Copyright-risk analysis is not legal advice.

High-risk material requires human review.

Never implement copyright circumvention.

---

## 77. Content Safety

Implement configurable policy checks.

Do not intentionally generate:

- spam
- deceptive metadata
- fake engagement
- impersonation
- harmful manipulation
- copyright circumvention
- platform abuse

Safety policy must be enforced before high-risk publication.

---

## 78. Research Mode

Agents may research current APIs, models, tools, and platform capabilities.

Research records should include:

- source
- retrieval date
- confidence
- applicability
- relevant version

Prefer authoritative documentation.

Do not silently convert research findings into implementation facts without validation.

---

## 79. Self-Improvement Loop

Use measured evidence:

```text
PUBLISH
 ↓
MEASURE
 ↓
ANALYZE
 ↓
FORM HYPOTHESIS
 ↓
TEST
 ↓
MEASURE
 ↓
UPDATE
```

Do not allow uncontrolled autonomous changes.

Model-driven recommendations must remain distinguishable from observed outcomes.

---

## 80. Autonomy Levels

Support:

- LEVEL 0 — Manual
- LEVEL 1 — AI suggestions
- LEVEL 2 — AI prepares actions
- LEVEL 3 — AI executes low-risk actions
- LEVEL 4 — AI executes approved workflows
- LEVEL 5 — Restricted autonomous operation

Default conservatively.

Every level requires explicit policy and auditability.

---

## 81. Production Readiness Definition

Not production-ready until all applicable gates pass:

- build
- typecheck
- lint
- unit tests
- integration tests
- E2E tests
- migrations
- Docker build
- health/readiness
- secrets scan
- dependency scan
- SAST
- container scan
- SBOM
- security tests
- API contract validation
- external integration validation
- retry testing
- idempotency testing
- failure recovery testing
- backup testing
- restore testing
- documentation consistency
- no critical TODO/fake implementation
- no known critical vulnerability
- no committed secret
- no uncontrolled paid fallback
- explicit approval policy for high-risk actions

“Files exist” is not evidence of production readiness.

---

## 82. Execution Protocol

### Phase 1 — Discovery

Read everything and produce:

- repository map
- architecture map
- dependency map
- workflow map
- security map
- technical debt map
- missing feature map
- duplicate map

Do not modify files during discovery.

### Phase 2 — Baseline

Run:

- build
- tests
- lint
- typecheck
- security scans
- repository validation

Record failures and preserve baseline evidence.

### Phase 3 — Architecture

Define:

- domain boundaries
- services
- database
- queues
- storage
- provider contracts
- workflow contracts
- security boundaries
- observability

Keep architecture proportional to requirements.

### Phase 4 — Implementation

Implement small validated increments.

After major changes:

- format
- lint
- typecheck
- targeted tests
- complete relevant build

### Phase 5 — Integration

Validate:

- YouTube
- OAuth
- AI
- media
- database
- queue
- storage
- notifications

Use sandbox/test credentials where available.

### Phase 6 — Security

Run complete security validation and fix real findings.

Do not suppress broad classes of findings merely to obtain green CI.

### Phase 7 — Production Hardening

Validate:

- restart
- crash recovery
- duplicate requests
- network interruption
- timeout
- quota exhaustion
- credential expiration
- database restart
- worker restart
- storage failure
- provider partial failure
- rollback

### Phase 8 — Documentation

Update documentation to match actual implementation.

### Phase 9 — Final Audit

Produce the final agent report defined below.

---

## 83. Git Workflow

Never rewrite unrelated history.

Prefer focused commits:

- feat:
- fix:
- refactor:
- test:
- docs:
- build:
- ci:
- security:
- perf:

One logical change per commit where practical.

Never commit:

- `.env`
- credentials
- tokens
- private keys
- large generated media
- temporary files
- local databases
- secrets

Use branches/PRs for meaningful changes.

---

## 84. Changelog

Every meaningful release must document:

- Added
- Changed
- Fixed
- Security
- Breaking Changes
- Migration

---

## 85. Final Agent Report

At completion report:

```text
## Repository

Repository:
Branch:
Commit:
Pull Request:

## Implementation

Completed:
Partial:
Not implemented:
Blocked:

## Tests

Build:
Lint:
Typecheck:
Unit:
Integration:
E2E:
Security:
Contract:

## Infrastructure

Database:
Queue:
Storage:
AI:
Media:
YouTube:
Notifications:

## Security

Critical:
High:
Medium:
Low:

## Production

Ready:
Blocked:
Required manual actions:

## Cost

Local:
Cloud:
Potential paid dependencies:
Budget controls:

## Risks

1.
2.
3.

## Next Actions

1.
2.
3.
```

Every claim must be supported by execution evidence.

---

## 86. Important Behavior

Do not stop after discovering problems.

Investigate.

Fix safely fixable issues.

Test every fix.

Continue through the lifecycle.

Do not claim success because files were generated.

Success means the implementation works under the relevant validation gates.

Do not optimize for code volume.

Optimize for:

- correctness
- clarity
- reliability
- security
- operability
- cost efficiency
- maintainability

Build SadwaveStudio as a long-lived production platform.

---

## 87. Final Command

Execute the complete lifecycle:

```text
DISCOVER
→ UNDERSTAND
→ PLAN
→ IMPLEMENT
→ TEST
→ SECURE
→ INTEGRATE
→ OBSERVE
→ DOCUMENT
→ AUDIT
→ HARDEN
```

Do not skip validation.

Do not fabricate external capabilities.

Do not silently introduce paid services.

Do not silently publish content.

Do not silently modify production infrastructure.

Do not delete existing functionality without evidence.

Do not declare production readiness without evidence.

**Build SadwaveStudio as a real, secure, observable, cost-controlled, maintainable production system.**
