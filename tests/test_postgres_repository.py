import json
import os
import secrets
import select
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from sadwave.domain import ContentJob, JobState
from sadwave.repository import LeaseLostError, PostgresJobRepository

TEST_DATABASE_URL = os.environ.get("SADWAVE_TEST_DATABASE_URL")
APP_TEST_USER = f"sadwave_test_{uuid4().hex[:12]}"
APP_TEST_PASSWORD = secrets.token_urlsafe(32)
APP_TEST_DATABASE_URL = (
    make_conninfo(TEST_DATABASE_URL, user=APP_TEST_USER, password=APP_TEST_PASSWORD)
    if TEST_DATABASE_URL
    else None
)
PROJECT_DIR = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="set SADWAVE_TEST_DATABASE_URL to run PostgreSQL integration tests",
)


@pytest.fixture(scope="module", autouse=True)
def migrated_test_database():
    if not TEST_DATABASE_URL:
        yield
        return
    env = _migration_environment()
    for _ in range(2):
        subprocess.run(
            [sys.executable, "scripts/migrate.py"],
            cwd=PROJECT_DIR,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    yield
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        role = sql.Identifier(APP_TEST_USER)
        connection.execute(sql.SQL("DROP OWNED BY {}").format(role))
        connection.execute(sql.SQL("DROP ROLE {}").format(role))


def _migration_environment() -> dict[str, str]:
    return os.environ | {
        "DATABASE_URL": TEST_DATABASE_URL,
        "APP_DATABASE_USER": APP_TEST_USER,
        "APP_DATABASE_PASSWORD": APP_TEST_PASSWORD,
    }


@pytest.fixture
def repository() -> PostgresJobRepository:
    assert TEST_DATABASE_URL
    return PostgresJobRepository(TEST_DATABASE_URL)


def test_versioned_migration_adds_lease_column_to_existing_queue_table():
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute("ALTER TABLE job_queue DROP COLUMN lease_token")
        connection.execute(
            "DELETE FROM schema_migrations WHERE version = '002_production_core.sql'"
        )
    subprocess.run(
        [sys.executable, "scripts/migrate.py"],
        cwd=PROJECT_DIR,
        env=_migration_environment(),
        check=True,
        capture_output=True,
        text=True,
    )
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        column_exists = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'job_queue'
                  AND column_name = 'lease_token'
            )
            """
        ).fetchone()[0]
        migration_recorded = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = %s)",
            ("002_production_core.sql",),
        ).fetchone()[0]
    assert column_exists and migration_recorded


@pytest.fixture(autouse=True)
def clean_integration_data():
    if not TEST_DATABASE_URL:
        yield
        return
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute(
            """
            DELETE FROM audit_events
            WHERE actor_id = 'integration-test'
               OR resource_id IN (
                    SELECT job_id::text FROM content_jobs
                    WHERE idempotency_key LIKE 'integration-%'
                       OR idempotency_key LIKE 'lease-integration-%'
                       OR idempotency_key LIKE 'app-role-%'
               )
            """
        )
        connection.execute(
            """
            DELETE FROM content_jobs
            WHERE idempotency_key LIKE 'integration-%'
               OR idempotency_key LIKE 'lease-integration-%'
               OR idempotency_key LIKE 'app-role-%'
            """
        )
        connection.execute("DELETE FROM rate_limit_buckets WHERE bucket_key LIKE 'integration:%'")
    yield


def test_concurrent_idempotent_create_persists_one_job_and_audit(repository):
    idempotency_key = f"integration-{uuid4()}"

    def create(_index: int):
        job = ContentJob.create(str(uuid4()), "channel-integration", "SHORT", idempotency_key)
        return repository.create_if_absent(
            job,
            actor_id="integration-test",
            request_id="integration-request",
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(create, range(36)))

    assert sum(created for _job, created in results) == 1
    assert len({job.job_id for job, _created in results}) == 1
    job_id = results[0][0].job_id
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        jobs = connection.execute(
            "SELECT COUNT(*) FROM content_jobs WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()[0]
        queue_items = connection.execute(
            "SELECT COUNT(*) FROM job_queue WHERE job_id = %s",
            (job_id,),
        ).fetchone()[0]
        events = connection.execute(
            "SELECT COUNT(*) FROM audit_events WHERE resource_id = %s",
            (str(job_id),),
        ).fetchone()[0]
    assert (jobs, queue_items, events) == (1, 1, 1)


def test_rate_limit_upsert_is_atomic_under_concurrency(repository):
    bucket = f"integration:{uuid4()}"
    limit = 7
    with ThreadPoolExecutor(max_workers=16) as pool:
        allowed = list(pool.map(lambda _index: repository.allow_rate(bucket, limit), range(48)))
    assert sum(allowed) == limit


def test_application_role_is_restricted_and_can_run_runtime_queries():
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        role = connection.execute(
            """
            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication,
                   has_table_privilege(rolname, 'schema_migrations', 'SELECT')
            FROM pg_roles WHERE rolname = %s
            """,
            (APP_TEST_USER,),
        ).fetchone()
    assert role == (True, False, False, False, False, False)

    app_repository = PostgresJobRepository(APP_TEST_DATABASE_URL)
    app_repository.healthcheck()
    job = ContentJob.create(str(uuid4()), "channel-app-role", "SHORT", f"app-role-{uuid4()}")
    stored, created = app_repository.create_if_absent(
        job,
        actor_id="integration-test",
        request_id="app-role-request",
    )
    assert created and stored.job_id == job.job_id
    item = app_repository.claim_next(f"worker-app-role-{uuid4()}")
    assert item is not None and str(item["job_id"]) == job.job_id
    blocked = app_repository.block_unhandled_job(item["queue_id"], item["lease_token"])
    assert blocked.state is JobState.BLOCKED
    assert app_repository.allow_rate(f"integration:{uuid4()}", 1)


def test_migration_refuses_existing_application_role_that_owns_objects():
    role_name = f"sadwave_owner_{uuid4().hex[:12]}"
    table_name = f"sadwave_owner_test_{uuid4().hex[:12]}"
    password = secrets.token_urlsafe(32)
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role_name), sql.Literal(password)
            )
        )
        connection.execute(
            sql.SQL("GRANT CREATE ON SCHEMA public TO {}").format(sql.Identifier(role_name))
        )
        connection.execute(
            sql.SQL("CREATE TABLE public.{} (id INTEGER)").format(sql.Identifier(table_name))
        )
        connection.execute(
            sql.SQL("ALTER TABLE public.{} OWNER TO {}").format(
                sql.Identifier(table_name), sql.Identifier(role_name)
            )
        )

    try:
        result = subprocess.run(
            [sys.executable, "scripts/migrate.py"],
            cwd=PROJECT_DIR,
            env=_migration_environment()
            | {"APP_DATABASE_USER": role_name, "APP_DATABASE_PASSWORD": password},
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "must not own the database or PostgreSQL objects" in result.stderr
    finally:
        with psycopg.connect(TEST_DATABASE_URL) as connection:
            connection.execute(
                sql.SQL("DROP TABLE IF EXISTS public.{}").format(sql.Identifier(table_name))
            )
            connection.execute(sql.SQL("DROP OWNED BY {}").format(sql.Identifier(role_name)))
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role_name)))


def test_expired_lease_fences_stale_worker_and_blocks_atomically(repository):
    idempotency_key = f"lease-integration-{uuid4()}"
    job = ContentJob.create(str(uuid4()), "channel-integration", "SHORT", idempotency_key)
    stored, created = repository.create_if_absent(job)
    assert created

    first = repository.claim_next(f"worker-old-{uuid4()}")
    assert first is not None and str(first["job_id"]) == stored.job_id
    old_token = first["lease_token"]
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute(
            "UPDATE job_queue SET locked_at = NOW() - INTERVAL '1 hour' WHERE queue_id = %s",
            (first["queue_id"],),
        )
    assert repository.recover_expired_leases(30) == 1

    second = repository.claim_next(f"worker-new-{uuid4()}")
    assert second is not None and second["queue_id"] == first["queue_id"]
    assert second["lease_token"] != old_token
    with pytest.raises(LeaseLostError):
        repository.fail(int(first["queue_id"]), old_token, "late failure")
    with pytest.raises(LeaseLostError):
        repository.block_unhandled_job(int(first["queue_id"]), old_token)

    blocked = repository.block_unhandled_job(int(second["queue_id"]), second["lease_token"])
    assert blocked.state is JobState.BLOCKED
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        state = connection.execute(
            "SELECT state FROM content_jobs WHERE job_id = %s",
            (stored.job_id,),
        ).fetchone()[0]
        queue_status = connection.execute(
            "SELECT status, lease_token FROM job_queue WHERE queue_id = %s",
            (second["queue_id"],),
        ).fetchone()
        events = connection.execute(
            "SELECT action FROM audit_events WHERE resource_id = %s ORDER BY created_at, action",
            (str(stored.job_id),),
        ).fetchall()
    assert state == JobState.BLOCKED.value
    assert queue_status == ("DEAD", None)
    assert [event[0] for event in events] == ["JOB_LEASE_RECOVERED", "JOB_BLOCKED"]


def test_retry_exhaustion_fails_job_and_audits_each_attempt(repository):
    bounded_repository = PostgresJobRepository(TEST_DATABASE_URL, max_attempts=2)
    job = ContentJob.create(
        str(uuid4()), "channel-integration", "SHORT", f"lease-integration-retry-{uuid4()}"
    )
    stored, created = bounded_repository.create_if_absent(job)
    assert created

    first = bounded_repository.claim_next(f"worker-retry-{uuid4()}")
    assert first is not None
    bounded_repository.fail(int(first["queue_id"]), first["lease_token"], "safe failure", 1)
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute(
            "UPDATE job_queue SET available_at = NOW() WHERE queue_id = %s",
            (first["queue_id"],),
        )
        state = connection.execute(
            "SELECT state FROM content_jobs WHERE job_id = %s", (stored.job_id,)
        ).fetchone()[0]
    assert state == JobState.DRAFT.value

    second = bounded_repository.claim_next(f"worker-retry-{uuid4()}")
    assert second is not None and second["attempts"] == 2
    bounded_repository.fail(int(second["queue_id"]), second["lease_token"], "safe failure", 1)
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        state = connection.execute(
            "SELECT state FROM content_jobs WHERE job_id = %s", (stored.job_id,)
        ).fetchone()[0]
        queue = connection.execute(
            "SELECT status, lease_token FROM job_queue WHERE queue_id = %s",
            (second["queue_id"],),
        ).fetchone()
        actions = connection.execute(
            "SELECT action FROM audit_events WHERE resource_id = %s ORDER BY created_at, action",
            (stored.job_id,),
        ).fetchall()
    assert state == JobState.FAILED.value
    assert queue == ("DEAD", None)
    assert [action[0] for action in actions] == ["JOB_RETRY_SCHEDULED", "JOB_FAILED"]


def test_expired_last_lease_fails_job_and_audits_dead_letter(repository):
    bounded_repository = PostgresJobRepository(TEST_DATABASE_URL, max_attempts=1)
    job = ContentJob.create(
        str(uuid4()), "channel-integration", "SHORT", f"lease-integration-expired-{uuid4()}"
    )
    stored, created = bounded_repository.create_if_absent(job)
    assert created
    claimed = bounded_repository.claim_next(f"worker-expired-{uuid4()}")
    assert claimed is not None
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        connection.execute(
            "UPDATE job_queue SET locked_at = NOW() - INTERVAL '1 hour' WHERE queue_id = %s",
            (claimed["queue_id"],),
        )

    assert bounded_repository.recover_expired_leases(30) == 1
    with psycopg.connect(TEST_DATABASE_URL) as connection:
        state = connection.execute(
            "SELECT state FROM content_jobs WHERE job_id = %s", (stored.job_id,)
        ).fetchone()[0]
        queue = connection.execute(
            "SELECT status, lease_token FROM job_queue WHERE queue_id = %s",
            (claimed["queue_id"],),
        ).fetchone()
        action = connection.execute(
            "SELECT action FROM audit_events WHERE resource_id = %s",
            (stored.job_id,),
        ).fetchone()[0]
    assert state == JobState.FAILED.value
    assert queue == ("DEAD", None)
    assert action == "JOB_FAILED"


@pytest.mark.skipif(os.name != "posix", reason="worker crash signaling requires POSIX")
def test_worker_process_restart_recovers_a_crashed_lease(repository):
    job = ContentJob.create(
        str(uuid4()),
        "channel-integration",
        "SHORT",
        f"lease-integration-crash-{uuid4()}",
    )
    stored, created = repository.create_if_absent(job)
    assert created

    crash_worker_id = f"worker-crash-{uuid4()}"
    crash_environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(PROJECT_DIR),
        "DATABASE_URL": APP_TEST_DATABASE_URL,
        "TEST_WORKER_ID": crash_worker_id,
    }
    claim_script = """
import os
import time
from sadwave import worker
from sadwave.config import Settings

def hold_after_claim(_repository, queue_id, _lease_token):
    print(f"lease-claimed:{queue_id}", flush=True)
    while True:
        time.sleep(60)

worker.PostgresJobRepository.block_unhandled_job = hold_after_claim
worker.run_worker(
    settings=Settings(
        app_env="production",
        database_url=os.environ["DATABASE_URL"],
        worker_id=os.environ["TEST_WORKER_ID"],
        worker_lease_seconds=30,
        worker_poll_seconds=0.1,
    )
)
"""
    crashed_worker = subprocess.Popen(
        [sys.executable, "-c", claim_script],
        cwd=PROJECT_DIR,
        env=crash_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        assert crashed_worker.stdout is not None
        readable, _, _ = select.select([crashed_worker.stdout], [], [], 10)
        assert readable, "worker did not claim the job before the startup timeout"
        claim = crashed_worker.stdout.readline().strip()
        assert claim.startswith("lease-claimed:")
        queue_id = int(claim.removeprefix("lease-claimed:"))
        crashed_worker.kill()
        assert crashed_worker.wait(timeout=10) == -signal.SIGKILL
    finally:
        if crashed_worker.poll() is None:
            crashed_worker.kill()
            crashed_worker.wait(timeout=10)

    with psycopg.connect(TEST_DATABASE_URL) as connection:
        crashed_lease = connection.execute(
            """
            SELECT job_id::text, status, locked_by, lease_token IS NOT NULL
            FROM job_queue WHERE queue_id = %s
            """,
            (queue_id,),
        ).fetchone()
        assert crashed_lease == (stored.job_id, "RUNNING", crash_worker_id, True)
        expired = connection.execute(
            """
            UPDATE job_queue
            SET locked_at = NOW() - INTERVAL '1 hour'
            WHERE queue_id = %s AND status = 'RUNNING' AND locked_by = %s
            """,
            (queue_id, crash_worker_id),
        ).rowcount
        assert expired == 1

    restart_worker_id = f"worker-restart-{uuid4()}"
    restart_environment = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str(PROJECT_DIR),
        "APP_ENV": "production",
        "DATABASE_URL": APP_TEST_DATABASE_URL,
        "WORKER_ID": restart_worker_id,
        "WORKER_LEASE_SECONDS": "30",
        "WORKER_POLL_SECONDS": "0.1",
        "LOG_LEVEL": "INFO",
    }
    restarted_worker = subprocess.Popen(
        [sys.executable, "-m", "sadwave.worker"],
        cwd=PROJECT_DIR,
        env=restart_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 10
        recovered = False
        while time.monotonic() < deadline:
            if restarted_worker.poll() is not None:
                output, _ = restarted_worker.communicate()
                pytest.fail(f"restarted worker exited before recovery: {output}")
            with psycopg.connect(TEST_DATABASE_URL) as connection:
                result = connection.execute(
                    """
                    SELECT job.state, queue.status,
                        (SELECT COUNT(*) FROM audit_events
                         WHERE resource_id = job.job_id::text
                           AND action = 'JOB_LEASE_RECOVERED'),
                        (SELECT COUNT(*) FROM audit_events
                         WHERE resource_id = job.job_id::text
                           AND action = 'JOB_BLOCKED')
                    FROM content_jobs AS job
                    JOIN job_queue AS queue USING (job_id)
                    WHERE job.job_id = %s
                    """,
                    (stored.job_id,),
                ).fetchone()
            if result == (JobState.BLOCKED.value, "DEAD", 1, 1):
                recovered = True
                break
            time.sleep(0.1)

        assert recovered, "restarted worker did not recover and audit the abandoned job"
        restarted_worker.send_signal(signal.SIGTERM)
        output, _ = restarted_worker.communicate(timeout=10)
        assert restarted_worker.returncode == 0
        log_events = [json.loads(line) for line in output.splitlines()]
        recovered_event = next(
            event for event in log_events if event.get("event") == "recovered_expired_leases"
        )
        assert recovered_event["count"] == 1
        assert any(event.get("event") == "worker_job_blocked" for event in log_events)
        assert any(event.get("event") == "worker_shutdown_complete" for event in log_events)
    finally:
        if restarted_worker.poll() is None:
            restarted_worker.kill()
            restarted_worker.communicate(timeout=10)


@pytest.mark.parametrize("lease_seconds", [0, 29, 3601])
def test_recovery_rejects_invalid_lease_timeout(repository, lease_seconds):
    with pytest.raises(ValueError, match="lease_seconds must be between 30 and 3600"):
        repository.recover_expired_leases(lease_seconds)
