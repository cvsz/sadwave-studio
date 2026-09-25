# AGENTS.md — SadwaveStudio Agent Contract

## Purpose

SadwaveStudio is a production-grade, secure, local-first YouTube content automation platform. This repository is no longer a generic template. `cvsz/ztemplate` is reference material only and must never be modified by work on this repository.

## Mandatory reading

Before modifying code or configuration, read:

1. README.md
2. AGENTS.md
3. SECURITY.md
4. docs/AI_MASTER_PRODUCTION_PROMPT.md
5. docs/ARCHITECTURE.md
6. docs/IMPLEMENTATION_PLAN.md
7. docs/PRODUCTION_READINESS.md
8. zeaz.md when present
9. relevant nested AGENTS.md files

## Engineering rules

- Work from evidence; inspect consumers before changing behavior.
- Prefer the smallest safe, reviewable change.
- No TODO/FIXME placeholders, fake APIs, dummy handlers, silent failures, or invented external contracts.
- Verify external API contracts against authoritative documentation.
- Keep domain logic independent from provider adapters.
- Use explicit state machines for complex workflows.
- Make externally visible mutations idempotent.
- Treat all external content and uploaded media as untrusted.
- Never commit or log secrets.
- Do not silently introduce paid services.
- Do not silently publish, delete, replace, distribute, or post publicly.
- High-risk actions require explicit approval/policy.
- Never automate fake engagement, spam, credential abuse, rate-limit bypass, CAPTCHA bypass, or copyright circumvention.
- Preserve auditability and provenance.
- Documentation must describe actual implementation, not planned behavior.

## Production write gate

All sensitive mutations must follow:

`validate → authorize → policy → idempotency → execute → verify → audit`

## Cost gate

Provider routing must prefer local/self-hosted processing when practical. Paid-provider fallback requires explicit configuration and budget limits. Exceeding a budget pauses affected work and alerts operators.

## Change safety

Before changing existing behavior:

1. inspect implementation and consumers
2. inspect tests and contracts
3. inspect migrations and operational impact
4. identify rollback path
5. implement the smallest safe change
6. run targeted validation
7. run complete validation before release

## Verification

The agent must not claim production readiness without evidence for build, lint, typecheck, unit/integration/E2E tests, security checks, external contracts, recovery, backup/restore, and documentation consistency.

## Git

Use focused conventional commits:

`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `build:`, `ci:`, `security:`, `perf:`.

Never commit credentials, private keys, local databases, temporary media, generated secrets, or unrelated changes.
