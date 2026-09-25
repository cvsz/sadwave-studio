from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4

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
                "SELECT job_id, channel_id, kind, state, idempotency_key, created_at FROM content_jobs WHERE idempotency_key = %s",
                (key,),
            ).fetchone()
        return self._to_domain(row) if row else None

    def get_by_id(self, job_id: str) -> ContentJob | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id, channel_id, kind, state, idempotency_key, created_at FROM content_jobs WHERE job_id = %s",
                (job_id,),
            ).fetchone()
        return self._to_domain(row) if row else None

    def save(self, job: ContentJob) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO content_jobs (job_id, channel_id, kind, state, idempotency_key, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    channel_id = EXCLUDED.channel_id,
                    kind = EXCLUDED.kind,
                    state = EXCLUDED.state,
                    idempotency_key = EXCLUDED.idempotency_key
                WHERE content_jobs.idempotency_key = EXCLUDED.idempotency_key
                """,
                (job.job_id, job.channel_id, job.kind, job.state.value, job.idempotency_key, job.created_at),
            )
            if job.state == JobState.DRAFT:
                connection.execute(
                    "INSERT INTO job_queue (job_id, status) VALUES (%s, 'READY') ON CONFLICT (job_id) DO NOTHING",
                    (job.job_id,),
                )

    def transition(self, job_id: str, target: JobState) -> ContentJob:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id, channel_id, kind, state, idempotency_key, created_at FROM content_jobs WHERE job_id = %s FOR UPDATE",
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Job not found")
            current = self._to_domain(row)
            updated = current.transition(target)
            connection.execute("UPDATE content_jobs SET state = %s WHERE job_id = %s", (updated.state.value, job_id))
        return updated

    def claim_next(self, worker_id: str, lease_seconds: int = 300) -> dict[str, Any] | None:
        if not worker_id.strip():
            raise ValueError("worker_id is required")
        if lease_seconds < 30 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be between 30 and 3600")
        with self._connect() as connection:
            row = connection.execute(
                """
                WITH candidate AS (
                    SELECT queue_id FROM job_queue
                    WHERE status = 'READY' AND available_at <= NOW()
                    ORDER BY queue_id FOR UPDATE SKIP LOCKED LIMIT 1
                )
                UPDATE job_queue q
                SET status = 'RUNNING', attempts = q.attempts + 1,
                    locked_at = NOW(), locked_by = %s, updated_at = NOW()
                FROM candidate
                WHERE q.queue_id = candidate.queue_id
                RETURNING q.queue_id, q.job_id, q.attempts, q.max_attempts, q.locked_at, q.locked_by
                """,
                (worker_id,),
            ).fetchone()
            return dict(row) if row else None

    def complete(self, queue_id: int) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE job_queue SET status = 'DONE', locked_at = NULL, locked_by = NULL, updated_at = NOW() WHERE queue_id = %s AND status = 'RUNNING'",
                (queue_id,),
            ).rowcount
            if updated != 1:
                raise KeyError("Queue item is not running")

    def fail(self, queue_id: int, error: str, retry_delay_seconds: int = 30) -> None:
        if not error.strip():
            raise ValueError("error is required")
        if retry_delay_seconds < 1 or retry_delay_seconds > 86400:
            raise ValueError("retry_delay_seconds must be between 1 and 86400")
        with self._connect() as connection:
            row = connection.execute("SELECT attempts, max_attempts FROM job_queue WHERE queue_id = %s FOR UPDATE", (queue_id,)).fetchone()
            if row is None:
                raise KeyError("Queue item not found")
            status = "DEAD" if row["attempts"] >= row["max_attempts"] else "READY"
            connection.execute(
                "UPDATE job_queue SET status = %s, available_at = NOW() + (%s * INTERVAL '1 second'), locked_at = NULL, locked_by = NULL, last_error = %s, updated_at = NOW() WHERE queue_id = %s",
                (status, retry_delay_seconds, error[:4000], queue_id),
            )

    def recover_expired_leases(self, lease_seconds: int = 300) -> int:
        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE job_queue
                SET status = CASE WHEN attempts >= max_attempts THEN 'DEAD' ELSE 'READY' END,
                    available_at = NOW(), locked_at = NULL, locked_by = NULL,
                    last_error = COALESCE(last_error, 'worker lease expired'), updated_at = NOW()
                WHERE status = 'RUNNING' AND locked_at < NOW() - (%s * INTERVAL '1 second')
                """,
                (lease_seconds,),
            )
            return result.rowcount

    def audit(self, *, actor_id: str, action: str, resource_type: str, resource_id: str,
              request_id: str | None = None, correlation_id: str | None = None,
              details: dict[str, Any] | None = None) -> str:
        import json

        event_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events
                    (event_id, actor_id, action, resource_type, resource_id, request_id, correlation_id, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (event_id, actor_id[:256], action[:128], resource_type[:128], resource_id[:256],
                 request_id[:256] if request_id else None, correlation_id[:256] if correlation_id else None,
                 json.dumps(details or {}, separators=(",", ":"))),
            )
        return event_id

    def allow_rate(self, bucket_key: str, limit: int, window_seconds: int = 60) -> bool:
        if not bucket_key.strip() or limit < 1 or window_seconds < 1:
            raise ValueError("invalid rate-limit parameters")
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            row = connection.execute("SELECT window_started_at, request_count FROM rate_limit_buckets WHERE bucket_key = %s FOR UPDATE", (bucket_key,)).fetchone()
            if row is None or row["window_started_at"] <= now - timedelta(seconds=window_seconds):
                connection.execute(
                    """
                    INSERT INTO rate_limit_buckets (bucket_key, window_started_at, request_count)
                    VALUES (%s, %s, 1)
                    ON CONFLICT (bucket_key) DO UPDATE SET window_started_at = EXCLUDED.window_started_at, request_count = 1
                    """,
                    (bucket_key, now),
                )
                return True
            if row["request_count"] >= limit:
                return False
            connection.execute("UPDATE rate_limit_buckets SET request_count = request_count + 1 WHERE bucket_key = %s", (bucket_key,))
            return True

    @staticmethod
    def _to_domain(row: dict) -> ContentJob:
        return ContentJob(
            job_id=row["job_id"], channel_id=row["channel_id"], kind=row["kind"],
            state=JobState(row["state"]), idempotency_key=row["idempotency_key"], created_at=row["created_at"],
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
