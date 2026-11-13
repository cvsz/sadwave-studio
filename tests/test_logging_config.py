import json
import logging
import runpy
import subprocess
import sys
from pathlib import Path

import uvicorn

from sadwave import logging_config
from sadwave.config import get_settings
from sadwave.logging_config import JsonLogFormatter

PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_json_formatter_emits_only_allowlisted_fields():
    record = logging.LogRecord(
        name="sadwave.api",
        level=logging.INFO,
        pathname="api.py",
        lineno=1,
        msg="http_request",
        args=(),
        exc_info=None,
    )
    record.event = "http_request"
    record.log_request_id = "server-generated-id"
    record.method = "GET"
    record.route = "/health"
    record.status_code = 200
    record.duration_ms = 2.5
    record.authorization = "Bearer secret-sentinel"
    record.query = "access_token=secret-sentinel"

    formatted = JsonLogFormatter().format(record)
    payload = json.loads(formatted)

    assert payload["level"] == "INFO"
    assert payload["message"] == "http_request"
    assert payload["event"] == "http_request"
    assert payload["route"] == "/health"
    assert payload["timestamp"].endswith("Z")
    assert "authorization" not in payload
    assert "query" not in payload
    assert "secret-sentinel" not in formatted


def test_configure_logging_writes_json_to_stdout_with_filtered_extras():
    script = """
import logging
from sadwave.logging_config import configure_logging

configure_logging("INFO")
logging.getLogger("sadwave.test").info(
    "safe_event",
    extra={"event": "safe_event", "unapproved_field": "secret-sentinel"},
)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_DIR,
        capture_output=True,
        check=True,
        text=True,
    )

    [line] = result.stdout.splitlines()
    payload = json.loads(line)
    assert payload["message"] == "safe_event"
    assert payload["event"] == "safe_event"
    assert "unapproved_field" not in payload
    assert "secret-sentinel" not in line
    assert result.stderr == ""


def test_api_entrypoint_disables_raw_uvicorn_access_logs(monkeypatch):
    configured_levels = []
    uvicorn_calls = []
    monkeypatch.setattr(logging_config, "configure_logging", configured_levels.append)
    monkeypatch.setattr(
        uvicorn, "run", lambda *args, **kwargs: uvicorn_calls.append((args, kwargs))
    )

    runpy.run_module("sadwave.__main__", run_name="__main__")

    assert configured_levels == [get_settings().log_level]
    assert len(uvicorn_calls) == 1
    kwargs = uvicorn_calls[0][1]
    assert kwargs["access_log"] is False
    assert kwargs["log_config"] is None
