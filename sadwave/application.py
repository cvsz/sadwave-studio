from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from .domain import ContentJob


class JobRepository(Protocol):
    def create_if_absent(
        self,
        job: ContentJob,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[ContentJob, bool]: ...


@dataclass(slots=True)
class InMemoryJobRepository:
    _jobs: dict[str, ContentJob]
    _idempotency_keys: dict[str, str]
    _lock: Lock

    def __init__(self) -> None:
        self._jobs = {}
        self._idempotency_keys = {}
        self._lock = Lock()

    def create_if_absent(
        self,
        job: ContentJob,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[ContentJob, bool]:
        with self._lock:
            existing_id = self._idempotency_keys.get(job.idempotency_key)
            if existing_id is not None:
                return self._jobs[existing_id], False
            if job.job_id in self._jobs:
                raise ValueError("Job ID already exists")
            self._jobs[job.job_id] = job
            self._idempotency_keys[job.idempotency_key] = job.job_id
            return job, True


class CreateContentJob:
    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        job_id: str,
        channel_id: str,
        kind: str,
        idempotency_key: str,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[ContentJob, bool]:
        if not idempotency_key.strip():
            raise ValueError("Idempotency key is required")
        if len(idempotency_key) > 256:
            raise ValueError("Idempotency key is too long")
        candidate = ContentJob.create(job_id, channel_id, kind, idempotency_key)
        existing, created = self._repository.create_if_absent(
            candidate,
            actor_id=actor_id,
            request_id=request_id,
        )
        if existing.channel_id != channel_id or existing.kind != kind:
            raise ValueError("Idempotency key was already used for a different request")
        return existing, created
