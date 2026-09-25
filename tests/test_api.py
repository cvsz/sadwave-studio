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


def test_create_job_is_idempotent():
    payload = {"channel_id": "c1", "kind": "SHORT"}
    headers = {"X-Idempotency-Key": "test-idem-1"}
    first = client.post("/api/v1/content/jobs", json=payload, headers=headers)
    second = client.post("/api/v1/content/jobs", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["job_id"] == second.json()["job_id"]
