SHELL := /bin/sh

.PHONY: help validate docs security ci

help:
	@printf '%s\n' 'Targets: validate docs security ci'

validate:
	@set -eu; test -f README.md; test -f AGENTS.md; test -f SECURITY.md; test -f docs/AI_MASTER_PRODUCTION_PROMPT.md; test -f docs/ARCHITECTURE.md; test -f docs/PRODUCTION_READINESS.md; git diff --check

docs:
	@set -eu; test -f docs/AI_MASTER_PRODUCTION_PROMPT.md; test -f docs/ARCHITECTURE.md; test -f docs/IMPLEMENTATION_PLAN.md; test -f docs/SECURITY_MODEL.md; test -f docs/PRODUCTION_READINESS.md

security:
	@set -eu; if git ls-files | grep -E '(^|/)(\.env|id_rsa|id_ed25519|.*\.pem|.*\.key)$$' | grep -v '^\.env\.example$$'; then echo 'Potential secret-bearing file is tracked.'; exit 1; fi

ci: validate docs security
