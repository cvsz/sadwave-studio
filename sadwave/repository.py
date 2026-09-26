import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from .domain import ContentJob, JobState


class LeaseLostError(RuntimeError):
    """The worker no longer owns the queue item's current lease."""


@dataclass(slots=True)
class PostgresJobRepository:
    database_url: str
    max_attempts: int = 5

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def healthcheck(self) -> None:
        required_tables = (
            "schema_migrations",
            "content_jobs",
            "job_queue",
            "audit_events",
            "rate_limit_buckets",
        )
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT "
                + ", ".join(
                    f"to_regclass('public.{table}') AS {table}" for table in required_tables
                )
            ).fetchone()
        if rows is None:
            raise RuntimeError("database schema is unavailable")
        if any(rows[table] is None for table in required_tables):
            raise RuntimeError("database schema is not fully migrated")

    def create_if_absent(
        self,
        job: ContentJob,
        *,
        actor_id: str | None = None,
        request_id: str | None = None,
    ) -> tuple[ContentJob, bool]:
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO content_jobs
                    (job_id, channel_id, kind, state, idempotency_key, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING job_id, channel_id, kind, state, idempotency_key, created_at
                """,
                (
                    job.job_id,
                    job.channel_id,
                    job.kind,
                    job.state.value,
                    job.idempotency_key,
                    job.created_at,
                ),
            ).fetchone()
            created = row is not None
            if row is None:
                row = connection.execute(
                    """
                    SELECT job_id, channel_id, kind, state, idempotency_key, created_at
                    FROM content_jobs WHERE idempotency_key = %s
                    """,
                    (job.idempotency_key,),
                ).fetchone()
                if row is None:
                    raise RuntimeError("idempotency conflict row could not be read")
            stored = self._to_domain(row)
            if created:
                connection.execute(
                    """
                    INSERT INTO job_queue (job_id, status, max_attempts)
                    VALUES (%s, 'READY', %s) ON CONFLICT (job_id) DO NOTHING
                    """,
                    (job.job_id, self.max_attempts),
                )
                if actor_id is not None:
                    self._insert_audit(
                        connection,
                        actor_id=actor_id,
                        action="CONTENT_JOB_CREATED",
                        resource_type="content_job",
                        resource_id=job.job_id,
                        request_id=request_id,
                        details={"channel_id": job.channel_id, "kind": job.kind},
                    )
            return stored, created

    def claim_next(self, worker_id: str, lease_seconds: int = 300) -> dict[str, Any] | None:
        if not worker_id.strip():
            raise ValueError("worker_id is required")
        if lease_seconds < 30 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be between 30 and 3600")
        lease_token = uuid4()
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
                    locked_at = NOW(), locked_by = %s, lease_token = %s, updated_at = NOW()
                FROM candidate
                WHERE q.queue_id = candidate.queue_id
                RETURNING q.queue_id, q.job_id, q.attempts, q.max_attempts,
                          q.locked_at, q.locked_by, q.lease_token
                """,
                (worker_id, lease_token),
            ).fetchone()
            if row is None:
                return None
            return dict(row)

    def block_unhandled_job(self, queue_id: int, lease_token: UUID | str) -> ContentJob:
        reason = "no processor is registered for this job kind"
        with self._connect() as connection:
            queue = connection.execute(
                """
                SELECT job_id, attempts, locked_by FROM job_queue
                WHERE queue_id = %s AND status = 'RUNNING' AND lease_token = %s
                FOR UPDATE
                """,
                (queue_id, lease_token),
            ).fetchone()
            if queue is None:
                raise LeaseLostError("worker lease is no longer current")
            row = connection.execute(
                """
                SELECT job_id, channel_id, kind, state, idempotency_key, created_at
                FROM content_jobs WHERE job_id = %s FOR UPDATE
                """,
                (queue["job_id"],),
            ).fetchone()
            if row is None:
                raise KeyError("Queued job not found")
            job = self._to_domain(row)
            updated = job.transition(JobState.BLOCKED)
            changed = connection.execute(
                "UPDATE content_jobs SET state = %s WHERE job_id = %s AND state = %s",
                (updated.state.value, updated.job_id, job.state.value),
            ).rowcount
            if changed != 1:
                raise RuntimeError("job state changed before block was recorded")
            changed = connection.execute(
                """
                UPDATE job_queue
                SET status = 'DEAD', last_error = %s,
                    locked_at = NULL, locked_by = NULL, lease_token = NULL, updated_at = NOW()
                WHERE queue_id = %s AND status = 'RUNNING' AND lease_token = %s
                """,
                (reason, queue_id, lease_token),
            ).rowcount
            if changed != 1:
                raise LeaseLostError("worker lease changed before block was recorded")
            self._insert_audit(
                connection,
                actor_id=f"worker:{queue['locked_by']}",
                action="JOB_BLOCKED",
                resource_type="content_job",
                resource_id=updated.job_id,
                details={
                    "attempt": queue["attempts"],
                    "queue_id": queue_id,
                    "kind": row["kind"],
                    "reason": reason,
                },
            )
            return updated

    def fail(
        self,
        queue_id: int,
        lease_token: UUID | str,
        error: str,
        retry_delay_seconds: int = 30,
    ) -> None:
        if not error.strip():
            raise ValueError("error is required")
        if retry_delay_seconds < 1 or retry_delay_seconds > 86400:
            raise ValueError("retry_delay_seconds must be between 1 and 86400")
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id, attempts, max_attempts, locked_by FROM job_queue
                WHERE queue_id = %s AND status = 'RUNNING' AND lease_token = %s FOR UPDATE
                """,
                (queue_id, lease_token),
            ).fetchone()
            if row is None:
                raise LeaseLostError("worker lease is no longer current")
            terminal = row["attempts"] >= row["max_attempts"]
            status = "DEAD" if terminal else "READY"
            if terminal:
                job_row = connection.execute(
                    """
                    SELECT job_id, channel_id, kind, state, idempotency_key, created_at
                    FROM content_jobs WHERE job_id = %s FOR UPDATE
                    """,
                    (row["job_id"],),
                ).fetchone()
                if job_row is None:
                    raise KeyError("Queued job not found")
                job = self._to_domain(job_row)
                failed = job.transition(JobState.FAILED)
                changed = connection.execute(
                    "UPDATE content_jobs SET state = %s WHERE job_id = %s AND state = %s",
                    (failed.state.value, failed.job_id, job.state.value),
                ).rowcount
                if changed != 1:
                    raise RuntimeError("job state changed before failure was recorded")
            updated = connection.execute(
                """
                UPDATE job_queue
                SET status = %s, available_at = NOW() + (%s * INTERVAL '1 second'),
                    locked_at = NULL, locked_by = NULL, lease_token = NULL,
                    last_error = %s, updated_at = NOW()
                WHERE queue_id = %s AND status = 'RUNNING' AND lease_token = %s
                """,
                (status, retry_delay_seconds, error[:4000], queue_id, lease_token),
            ).rowcount
            if updated != 1:
                raise LeaseLostError("worker lease changed before failure was recorded")
            self._insert_audit(
                connection,
                actor_id=f"worker:{row['locked_by']}",
                action="JOB_FAILED" if terminal else "JOB_RETRY_SCHEDULED",
                resource_type="content_job",
                resource_id=str(row["job_id"]),
                details={
                    "attempt": row["attempts"],
                    "max_attempts": row["max_attempts"],
                    "queue_id": queue_id,
                    "retry_delay_seconds": None if terminal else retry_delay_seconds,
                },
            )

    def recover_expired_leases(self, lease_seconds: int = 300) -> int:
        if lease_seconds < 30 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be between 30 and 3600")
        with self._connect() as connection:
            expired = connection.execute(
                """
                SELECT queue_id, job_id, attempts, max_attempts, locked_by
                FROM job_queue
                WHERE status = 'RUNNING' AND locked_at < NOW() - (%s * INTERVAL '1 second')
                ORDER BY queue_id
                FOR UPDATE SKIP LOCKED
                """,
                (lease_seconds,),
            ).fetchall()
            for queue in expired:
                terminal = queue["attempts"] >= queue["max_attempts"]
                status = "DEAD" if terminal else "READY"
                changed = connection.execute(
                    """
                    UPDATE job_queue
                    SET status = %s, available_at = NOW(), locked_at = NULL, locked_by = NULL,
                        lease_token = NULL, last_error = 'worker lease expired', updated_at = NOW()
                    WHERE queue_id = %s AND status = 'RUNNING'
                    """,
                    (status, queue["queue_id"]),
                ).rowcount
                if changed != 1:
                    raise LeaseLostError("worker lease changed during recovery")
                action = "JOB_LEASE_RECOVERED"
                if terminal:
                    job_row = connection.execute(
                        """
                        SELECT job_id, channel_id, kind, state, idempotency_key, created_at
                        FROM content_jobs WHERE job_id = %s FOR UPDATE
                        """,
                        (queue["job_id"],),
                    ).fetchone()
                    if job_row is None:
                        raise KeyError("Queued job not found")
                    job = self._to_domain(job_row)
                    failed = job.transition(JobState.FAILED)
                    changed = connection.execute(
                        "UPDATE content_jobs SET state = %s WHERE job_id = %s AND state = %s",
                        (failed.state.value, failed.job_id, job.state.value),
                    ).rowcount
                    if changed != 1:
                        raise RuntimeError("job state changed before recovery failure was recorded")
                    action = "JOB_FAILED"
                self._insert_audit(
                    connection,
                    actor_id=f"worker:{queue['locked_by'] or 'lease-recovery'}",
                    action=action,
                    resource_type="content_job",
                    resource_id=str(queue["job_id"]),
                    details={
                        "attempt": queue["attempts"],
                        "max_attempts": queue["max_attempts"],
                        "queue_id": queue["queue_id"],
                        "reason": "worker lease expired",
                        "status": status,
                    },
                )
            return len(expired)

    def allow_rate(self, bucket_key: str, limit: int, window_seconds: int = 60) -> bool:
        if not bucket_key.strip() or limit < 1 or window_seconds < 1:
            raise ValueError("invalid rate-limit parameters")
        with self._connect() as connection:
            row = connection.execute(
                """
                INSERT INTO rate_limit_buckets (bucket_key, window_started_at, request_count)
                VALUES (%s, NOW(), 1)
                ON CONFLICT (bucket_key) DO UPDATE SET
                    window_started_at = CASE
                        WHEN rate_limit_buckets.window_started_at <= NOW() - (%s * INTERVAL '1 second')
                        THEN NOW() ELSE rate_limit_buckets.window_started_at END,
                    request_count = CASE
                        WHEN rate_limit_buckets.window_started_at <= NOW() - (%s * INTERVAL '1 second')
                        THEN 1 ELSE rate_limit_buckets.request_count + 1 END
                WHERE rate_limit_buckets.window_started_at <= NOW() - (%s * INTERVAL '1 second')
                   OR rate_limit_buckets.request_count < %s
                RETURNING bucket_key
                """,
                (bucket_key, window_seconds, window_seconds, window_seconds, limit),
            ).fetchone()
            return row is not None

    @staticmethod
    def _insert_audit(
        connection,
        *,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO audit_events
                (event_id, actor_id, action, resource_type, resource_id, request_id, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                uuid4(),
                actor_id[:256],
                action[:128],
                resource_type[:128],
                resource_id[:256],
                request_id[:256] if request_id else None,
                json.dumps(details or {}, separators=(",", ":")),
            ),
        )

    @staticmethod
    def _to_domain(row: dict[str, Any]) -> ContentJob:
        return ContentJob(
            job_id=str(row["job_id"]),
            channel_id=row["channel_id"],
            kind=row["kind"],
            state=JobState(row["state"]),
            idempotency_key=row["idempotency_key"],
            created_at=row["created_at"],
        )
