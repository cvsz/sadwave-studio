from uuid import uuid4

from fastapi.testclient import TestClient

from sadwave import api


class RecordingRateLimiter:
    def __init__(self, *, allowed: bool) -> None:
        self.allowed = allowed
        self.calls = []

    def allow_rate(self, key: str, limit: int, window_seconds: int) -> bool:
        self.calls.append((key, limit, window_seconds))
        return self.allowed


def _configure_staging(monkeypatch, *, token: str) -> None:
    monkeypatch.setattr(api.settings, "app_env", "staging")
    monkeypatch.setattr(api.settings, "api_token", token)


def _create_job(client: TestClient, *, authorization: str | None = None):
    headers = {"X-Idempotency-Key": f"security-test-{uuid4()}"}
    if authorization is not None:
        headers["Authorization"] = authorization
    return client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "security-test-channel", "kind": "SHORT"},
        headers=headers,
    )


def test_invalid_bearer_token_is_rejected_before_rate_limit(monkeypatch):
    _configure_staging(monkeypatch, token="s" * 32)
    limiter = RecordingRateLimiter(allowed=True)
    monkeypatch.setattr(api, "repository", limiter)

    response = _create_job(TestClient(api.app), authorization="Bearer wrong-token")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert limiter.calls == []


def test_rate_limited_request_never_reaches_job_creation(monkeypatch):
    _configure_staging(monkeypatch, token="s" * 32)
    limiter = RecordingRateLimiter(allowed=False)
    monkeypatch.setattr(api, "repository", limiter)
    create_calls = []
    monkeypatch.setattr(
        api.create_content_job, "execute", lambda **kwargs: create_calls.append(kwargs)
    )

    response = _create_job(TestClient(api.app), authorization=f"Bearer {'s' * 32}")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["Retry-After"] == str(api.settings.api_rate_window_seconds)
    assert len(limiter.calls) == 1
    assert limiter.calls[0][1:] == (
        api.settings.api_rate_limit,
        api.settings.api_rate_window_seconds,
    )
    assert create_calls == []


def test_valid_bearer_token_reaches_job_creation_after_rate_limit(monkeypatch):
    token = "s" * 32
    _configure_staging(monkeypatch, token=token)
    limiter = RecordingRateLimiter(allowed=True)
    monkeypatch.setattr(api, "repository", limiter)

    response = _create_job(TestClient(api.app), authorization=f"Bearer {token}")

    assert response.status_code == 201
    assert len(limiter.calls) == 1
    assert response.json()["state"] == "DRAFT"
