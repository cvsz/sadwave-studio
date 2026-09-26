from __future__ import annotations

import logging
import random
import signal
import threading

import psycopg

from .config import Settings, get_settings
from .logging_config import configure_logging
from .repository import LeaseLostError, PostgresJobRepository

logger = logging.getLogger("sadwave.worker")


def run_worker(
    *,
    stop_event: threading.Event | None = None,
    settings: Settings | None = None,
) -> None:
    if settings is None:
        settings = get_settings(require_api_token=False)
    if settings.app_env not in {"production", "staging"}:
        raise RuntimeError("Worker requires APP_ENV=staging or APP_ENV=production")

    if stop_event is None:
        stop_event = threading.Event()
    repository = PostgresJobRepository(settings.database_url, settings.worker_max_attempts)
    worker_id = settings.worker_id

    while not stop_event.is_set():
        recovered = repository.recover_expired_leases(settings.worker_lease_seconds)
        if recovered:
            logger.warning(
                "recovered_expired_leases",
                extra={"event": "recovered_expired_leases", "count": recovered},
            )
        if stop_event.is_set():
            break

        item = repository.claim_next(worker_id, settings.worker_lease_seconds)
        if item is None:
            stop_event.wait(settings.worker_poll_seconds)
            continue

        queue_id = int(item["queue_id"])
        job_id = str(item["job_id"])
        attempts = int(item["attempts"])
        lease_token = item["lease_token"]

        try:
            repository.block_unhandled_job(queue_id, lease_token)
        except LeaseLostError:
            logger.info(
                "worker_lease_lost",
                extra={"event": "worker_lease_lost", "queue_id": queue_id, "job_id": job_id},
            )
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
                logger.info(
                    "worker_lease_lost",
                    extra={
                        "event": "worker_lease_lost",
                        "queue_id": queue_id,
                        "job_id": job_id,
                    },
                )
                continue
            logger.error(
                "worker_job_failed",
                extra={
                    "event": "worker_job_failed",
                    "queue_id": queue_id,
                    "job_id": job_id,
                    "error_type": type(exc).__name__,
                },
            )
        else:
            logger.warning(
                "worker_job_blocked",
                extra={
                    "event": "worker_job_blocked",
                    "queue_id": queue_id,
                    "job_id": job_id,
                    "reason": "no_processor_registered",
                },
            )
    logger.info("worker_shutdown_complete", extra={"event": "worker_shutdown_complete"})


def main() -> None:
    settings = get_settings(require_api_token=False)
    configure_logging(settings.log_level)
    stop_event = threading.Event()

    def request_shutdown(_signum: int, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    run_worker(stop_event=stop_event, settings=settings)


if __name__ == "__main__":
    main()
