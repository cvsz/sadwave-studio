# SadwaveStudio

Production-grade, secure, observable, cost-controlled automation for YouTube content operations.

> **Current status: Runtime foundation implemented; full production platform is still under staged implementation.**

## Implemented now

- Python 3.12 + FastAPI runtime
- Environment validation with production fail-closed rules
- Request correlation IDs
- /health, /ready, /version
- Bearer authentication for staging/production API mutations
- Content-job lifecycle state machine
- Idempotent job creation with request-conflict protection
- PostgreSQL persistence adapter and migration
- Production Docker image and Compose topology
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
export POSTGRES_PASSWORD='use-a-local-secret'
export API_TOKEN='use-a-local-secret'
docker compose up --build
~~~

Then run the database migration:

~~~bash
docker compose exec api python scripts/migrate.py
~~~

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

## License

MIT. See LICENSE.
