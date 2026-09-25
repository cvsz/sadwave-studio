# SadwaveStudio container contract
# Application runtime images must be added only with an implemented service.
# This image intentionally fails closed instead of pretending the platform is runnable.

FROM alpine:3.24

WORKDIR /app

COPY docs/PRODUCTION_READINESS.md /app/PRODUCTION_READINESS.md

CMD ["sh", "-c", "echo 'SadwaveStudio application runtime is not implemented yet; see PRODUCTION_READINESS.md' >&2; exit 78"]
