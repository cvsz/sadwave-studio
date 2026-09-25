from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from .domain import ContentJob


class JobRepository(Protocol):
    def get_by_idempotency_key(self, key: str) -> ContentJob | None: ...
    def save(self, job: ContentJob) -> None: ...


@dataclass(slots=True)
class InMemoryJobRepository:
    _jobs: dict[str, ContentJob]
    _lock: Lock

    def __init__(self) -> None:
        self._jobs = {}
        self._lock = Lock()

    def get_by_idempotency_key(self, key: str) -> ContentJob | None:
        with self._lock:
            return next((job for job in self._jobs.values() if job.idempotency_key == key), None)

    def save(self, job: ContentJob) -> None:
        with self._lock:
            existing = self._jobs.get(job.job_id)
            if existing is not None and existing.idempotency_key != job.idempotency_key:
                raise ValueError("Job ID already exists with a different idempotency key")
            self._jobs[job.job_id] = job


class CreateContentJob:
    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def execute(self, *, job_id: str, channel_id: str, kind: str, idempotency_key: str) -> ContentJob:
        if not idempotency_key.strip():
            raise ValueError("Idempotency key is required")
        existing = self._repository.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        job = ContentJob.create(job_id, channel_id, kind, idempotency_key)
        self._repository.save(job)
        return job
