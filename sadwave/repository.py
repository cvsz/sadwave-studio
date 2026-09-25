from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from .domain import ContentJob, JobState


class JobStore(Protocol):
    def get_by_idempotency_key(self, key: str) -> ContentJob | None: ...
    def save(self, job: ContentJob) -> None: ...
    def transition(self, job_id: str, target: JobState) -> ContentJob: ...
    def healthcheck(self) -> None: ...


@dataclass(slots=True)
class PostgresJobRepository:
    database_url: str

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def healthcheck(self) -> None:
        with self._connect() as connection:
            connection.execute("SELECT 1")

    def get_by_idempotency_key(self, key: str) -> ContentJob | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, channel_id, kind, state, idempotency_key, created_at
                FROM content_jobs WHERE idempotency_key = %s
                """,
                (key,),
            ).fetchone()
        return self._to_domain(row) if row else None

    def save(self, job: ContentJob) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_jobs
                    (job_id, channel_id, kind, state, idempotency_key, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    channel_id = EXCLUDED.channel_id,
                    kind = EXCLUDED.kind,
                    state = EXCLUDED.state,
                    idempotency_key = EXCLUDED.idempotency_key
                WHERE content_jobs.idempotency_key = EXCLUDED.idempotency_key
                """,
                (
                    job.job_id,
                    job.channel_id,
                    job.kind,
                    job.state.value,
                    job.idempotency_key,
                    job.created_at,
                ),
            )

    def transition(self, job_id: str, target: JobState) -> ContentJob:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, channel_id, kind, state, idempotency_key, created_at
                FROM content_jobs WHERE job_id = %s FOR UPDATE
                """,
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Job not found")
            current = self._to_domain(row)
            updated = current.transition(target)
            connection.execute(
                "UPDATE content_jobs SET state = %s WHERE job_id = %s",
                (updated.state.value, job_id),
            )
        return updated

    @staticmethod
    def _to_domain(row: dict) -> ContentJob:
        return ContentJob(
            job_id=row["job_id"],
            channel_id=row["channel_id"],
            kind=row["kind"],
            state=JobState(row["state"]),
            idempotency_key=row["idempotency_key"],
            created_at=row["created_at"],
        )


class InMemoryJobStore:
    def __init__(self) -> None:
        from .application import InMemoryJobRepository

        self._inner = InMemoryJobRepository()

    def get_by_idempotency_key(self, key: str) -> ContentJob | None:
        return self._inner.get_by_idempotency_key(key)

    def save(self, job: ContentJob) -> None:
        self._inner.save(job)

    def transition(self, job_id: str, target: JobState) -> ContentJob:
        raise NotImplementedError("In-memory transition is intentionally not used for production")

    def healthcheck(self) -> None:
        return None
