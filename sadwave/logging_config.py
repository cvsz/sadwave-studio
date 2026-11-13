from __future__ import annotations

import json
import logging
import logging.config
from datetime import UTC, datetime

_STRUCTURED_FIELDS = (
    "count",
    "duration_ms",
    "error_type",
    "event",
    "job_id",
    "log_request_id",
    "method",
    "queue_id",
    "reason",
    "route",
    "status_code",
)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, str | int | float | bool] = {
            "timestamp": datetime.now(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if isinstance(value, (str, int, float, bool)):
                event[field] = value
        return json.dumps(event, ensure_ascii=True, separators=(",", ":"))


def configure_logging(log_level: str) -> None:
    configured_level = logging.getLevelNamesMapping().get(log_level.upper())
    if configured_level is None:
        raise ValueError("LOG_LEVEL must be a recognized logging level")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"json": {"()": JsonLogFormatter}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": configured_level,
                    "formatter": "json",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"level": configured_level, "handlers": ["console"]},
            "loggers": {
                "sadwave": {
                    "handlers": ["console"],
                    "level": configured_level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["console"],
                    "level": configured_level,
                    "propagate": False,
                },
            },
        }
    )
