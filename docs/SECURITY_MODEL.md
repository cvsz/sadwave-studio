# SadwaveStudio Security Model

## Security objectives

Protect channel credentials, media, analytics, user data, publishing authority, provider budgets, and the integrity of generated content.

## Threat model

The initial threat model covers:

- OAuth token theft
- SSRF
- command injection
- path traversal
- malicious media
- prompt injection
- webhook forgery and replay
- dependency/supply-chain compromise
- privilege escalation
- accidental data leakage
- unauthorized publishing
- uncontrolled provider spending

## Trust rules

External content can contain instructions, claims, or malicious payloads. It is data, never system policy.

AI output is untrusted until schema, policy, provenance, safety, and domain validation pass.

Uploaded media is untrusted and must be processed in an isolated worker with resource and file-type limits.

## Secrets

Secrets must be injected through runtime secret management. Never store OAuth access/refresh tokens, API keys, cookies, passwords, authorization headers, or private keys in source control or logs.

The PostgreSQL runtime role must not own the application database or objects. The migration runner fails closed when an existing runtime role still owns database objects; ownership must be corrected by the database administrator before migrations continue.

Docker builds use a context allowlist containing only the Dockerfile, package metadata, runtime package, migrations, and scripts. Local environment files, tests, backups, generated data, and Git metadata must not be sent to the builder.

## Publishing

Publishing is a privileged mutation. The application must authenticate the actor, authorize the operation, enforce policy, register an idempotency key, execute the provider call, verify the remote result, and write an immutable audit event.

## Cost security

Paid providers require explicit configuration. Budget limits are enforcement controls, not advisory metrics. Reaching a limit must pause affected work and notify operators.

At the current implementation baseline, no paid-provider calls or content processors exist. The cost and dry-run settings are configuration only; they are not yet enforced by an execution workflow and must not be presented as active budget protection.

## Audit

Audit sensitive actions including authentication events, credential changes, publishing, deletion, metadata changes, approval decisions, provider changes, budget changes, workflow changes, and role changes.

Normal application paths must not permit mutation of historical audit records.
