from __future__ import annotations

import logging
import random
import time

from .config import get_settings
from .domain import JobState
from .repository import PostgresJobRepository

logger = logging.getLogger("sadwave.worker")


def run_worker() -> None:
    settings = get_settings()
    if settings.app_env not in {"production", "staging"}:
        raise RuntimeError("Worker requires APP_ENV=staging or APP_ENV=production")

    repository = PostgresJobRepository(settings.database_url)
    worker_id = settings.worker_id

    while True:
        recovered = repository.recover_expired_leases(settings.worker_lease_seconds)
        if recovered:
            logger.warning("recovered_expired_leases count=%s", recovered)

        item = repository.claim_next(worker_id, settings.worker_lease_seconds)
        if item is None:
            time.sleep(settings.worker_poll_seconds)
            continue

        queue_id = int(item["queue_id"])
        job_id = str(item["job_id"])
        attempts = int(item["attempts"])

        try:
            job = repository.get_by_id(job_id)
            if job is None:
                raise RuntimeError(f"queued job {job_id} no longer exists")
            if job.state != JobState.DRAFT:
                raise RuntimeError(
                    f"unsupported queued state {job.state}; refusing implicit execution"
                )
            repository.transition(job_id, JobState.PLANNED)
            repository.audit(
                actor_id=f"worker:{worker_id}",
                action="JOB_PLANNED",
                resource_type="content_job",
                resource_id=job_id,
                details={"attempt": attempts, "queue_id": queue_id},
            )
            repository.complete(queue_id)
        except Exception as exc:
            delay = min(3600, max(5, 2 ** min(attempts, 10))) + random.uniform(0, 3)
            repository.fail(queue_id, str(exc), int(delay))
            logger.exception("worker_job_failed queue_id=%s job_id=%s", queue_id, job_id)


if __name__ == "__main__":
    logging.basicConfig(level=get_settings().log_level)
    run_worker()
