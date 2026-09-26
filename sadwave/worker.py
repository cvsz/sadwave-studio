from __future__ import annotations

import logging
import random
import time

import psycopg

from .config import get_settings
from .repository import LeaseLostError, PostgresJobRepository

logger = logging.getLogger("sadwave.worker")


def run_worker() -> None:
    settings = get_settings(require_api_token=False)
    if settings.app_env not in {"production", "staging"}:
        raise RuntimeError("Worker requires APP_ENV=staging or APP_ENV=production")

    repository = PostgresJobRepository(settings.database_url, settings.worker_max_attempts)
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
        lease_token = item["lease_token"]

        try:
            repository.block_unhandled_job(queue_id, lease_token)
        except LeaseLostError:
            logger.info("worker_lease_lost queue_id=%s job_id=%s", queue_id, job_id)
        except (KeyError, RuntimeError, ValueError, psycopg.Error) as exc:
            delay = min(3600, max(5, 2 ** min(attempts, 10))) + random.uniform(0, 3)
            try:
                repository.fail(
                    queue_id,
                    lease_token,
                    f"processing failed ({type(exc).__name__})",
                    int(delay),
                )
            except LeaseLostError:
                logger.info("worker_lease_lost queue_id=%s job_id=%s", queue_id, job_id)
                continue
            logger.error(
                "worker_job_failed queue_id=%s job_id=%s error_type=%s",
                queue_id,
                job_id,
                type(exc).__name__,
            )
        else:
            logger.warning(
                "worker_job_blocked queue_id=%s job_id=%s reason=no_processor_registered",
                queue_id,
                job_id,
            )


if __name__ == "__main__":
    logging.basicConfig(level=get_settings(require_api_token=False).log_level)
    run_worker()
