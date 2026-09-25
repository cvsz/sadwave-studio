# SadwaveStudio

Production-grade, secure, observable, cost-controlled automation for YouTube content operations.

> **Current status: API, PostgreSQL job queue, and worker foundation implemented; the full production platform remains gated.**

## Implemented now

- Python 3.12 + FastAPI runtime
- Environment validation with production fail-closed rules
- Request correlation IDs
- /health, /ready, /version
- Bearer authentication for staging/production API mutations
- Content-job lifecycle state machine
- Idempotent job creation with request-conflict protection
- PostgreSQL persistence, versioned migrations, durable queue, lease fencing, and audit writes
- Restricted PostgreSQL application role; schema migrations use the separate administrator role
- Production Docker image and Compose API/worker/migration topology
- Ruff formatting/linting
- Unit/API tests
- Dependency vulnerability audit
- SBOM generation
- Cost-lock, dry-run, and autonomy controls

## Quick start

~~~bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
python -m sadwave
~~~

For a production-shaped local stack:

~~~bash
export POSTGRES_PASSWORD='<random value of at least 32 characters>'
export APP_DATABASE_PASSWORD='<a different random value of at least 32 characters>'
export API_TOKEN='<random value of at least 32 characters>'
docker compose up --build
~~~

Compose waits for PostgreSQL, applies pending versioned migrations, and then starts the API and worker.
The migration service uses the PostgreSQL administrator account to provision schema and a restricted
`sadwave_app` role. The API and worker receive only that role's password, separately from `DATABASE_URL`.

The production API requires:

~~~text
Authorization: Bearer <API_TOKEN>
X-Idempotency-Key: <unique-key>
~~~

## Safety

Public mutations must follow:

~~~text
validate → authorize → policy → idempotency → execute → verify → audit
~~~

Publishing, deletion, replacement, public communication, credentials, billing, copyright-sensitive actions, and other high-risk operations remain approval-gated.

The system must never automate fake engagement, spam, credential abuse, CAPTCHA/rate-limit bypass, or copyright circumvention.

## Architecture and governance

- Architecture: docs/ARCHITECTURE.md
- Implementation Plan: docs/IMPLEMENTATION_PLAN.md
- AI Master Production Prompt: docs/AI_MASTER_PRODUCTION_PROMPT.md
- Security Model: docs/SECURITY_MODEL.md
- Production Readiness: docs/PRODUCTION_READINESS.md
- Agent Contract: AGENTS.md

cvsz/ztemplate is reference-only and must not be modified by SadwaveStudio work.

## Production status

Do not treat the existence of a Docker image or green unit tests as proof that the complete YouTube automation platform is production-ready. The readiness checklist is evidence-based and remains incomplete until all applicable integration, security, recovery, and operational gates pass.

PostgreSQL integration tests run in CI. To run them locally, set `SADWAVE_TEST_DATABASE_URL` to a disposable PostgreSQL database before running `pytest`; migrations are applied by the test fixture.

## License

MIT. See LICENSE.
