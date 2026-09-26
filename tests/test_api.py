from fastapi.testclient import TestClient

from sadwave.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_job_requires_idempotency():
    response = client.post("/api/v1/content/jobs", json={"channel_id": "c1", "kind": "SHORT"})
    assert response.status_code == 400


def test_create_job_rejects_oversized_idempotency_key():
    response = client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "c1", "kind": "SHORT"},
        headers={"X-Idempotency-Key": "x" * 257},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "X-Idempotency-Key is too long"


def test_create_job_rejects_oversized_request_body():
    response = client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "c1", "kind": "SHORT", "unused": "x" * 1_048_576},
        headers={"X-Idempotency-Key": "large-body-key", "X-Request-ID": "large-body-request"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert response.json()["error"]["requestId"] == "large-body-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_create_job_is_idempotent():
    payload = {"channel_id": "c1", "kind": "SHORT"}
    headers = {"X-Idempotency-Key": "test-idem-1"}
    first = client.post("/api/v1/content/jobs", json=payload, headers=headers)
    second = client.post("/api/v1/content/jobs", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["job_id"] == second.json()["job_id"]


def test_idempotency_key_cannot_change_request():
    headers = {"X-Idempotency-Key": "test-idem-2"}
    first = client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "c1", "kind": "SHORT"},
        headers=headers,
    )
    second = client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "c2", "kind": "VIDEO"},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "REQUEST_ERROR"


def test_validation_errors_have_sanitized_request_id_and_security_headers():
    invalid_id = "x" * 129
    response = client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "", "kind": "SHORT"},
        headers={"X-Idempotency-Key": "validation-key", "X-Request-ID": invalid_id},
    )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["requestId"] != invalid_id
    assert response.headers["X-Request-ID"] == body["requestId"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "input" not in str(body["details"])


def test_unauthorized_early_response_has_security_headers(monkeypatch):
    from sadwave import api

    monkeypatch.setattr(api.settings, "app_env", "staging")
    response = client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "c1", "kind": "SHORT"},
        headers={"X-Idempotency-Key": "unauthorized-key", "X-Request-ID": "safe-request-2"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["requestId"] == "safe-request-2"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"


def test_unexpected_errors_use_common_error_envelope(monkeypatch):
    from sadwave import api

    def fail(**_kwargs):
        raise RuntimeError("sensitive implementation detail")

    monkeypatch.setattr(api.create_content_job, "execute", fail)
    test_client = TestClient(app, raise_server_exceptions=False)
    response = test_client.post(
        "/api/v1/content/jobs",
        json={"channel_id": "c1", "kind": "SHORT"},
        headers={"X-Idempotency-Key": "unexpected-key", "X-Request-ID": "safe-request-1"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "internal server error",
            "requestId": "safe-request-1",
            "details": [],
        }
    }
    assert "sensitive implementation detail" not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"
