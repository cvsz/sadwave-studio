SHELL := /bin/sh

.PHONY: help install format lint test typecheck validate migrate worker docker-build security audit ci

help:
	@printf '%s\n' 'Targets: install format lint test typecheck validate migrate worker docker-build security audit ci'

install:
	python -m pip install -e '.[dev]'

format:
	ruff format .

lint:
	ruff check .

test:
	pytest

typecheck:
	python -m compileall -q sadwave tests

validate:
	@set -eu; test -f README.md; test -f AGENTS.md; test -f SECURITY.md; test -f docs/AI_MASTER_PRODUCTION_PROMPT.md; test -f docs/ARCHITECTURE.md; test -f docs/PRODUCTION_READINESS.md; test -f migrations/002_production_core.sql; git diff --check

migrate:
	python scripts/migrate.py

worker:
	python -m sadwave.worker

docker-build:
	docker build --pull --tag sadwave-studio:local .

security:
	@set -eu; if git ls-files | grep -E '(^|/)(\.env|id_rsa|id_ed25519|.*\.pem|.*\.key)$$' | grep -v '^\.env\.example$$'; then echo 'Potential secret-bearing file is tracked.'; exit 1; fi

audit:
	pip-audit

ci: format lint test typecheck validate security audit
