from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from sadwave.application import CreateContentJob, InMemoryJobRepository


def test_in_memory_idempotency_is_atomic_under_concurrency():
    use_case = CreateContentJob(InMemoryJobRepository())

    def create(_index: int):
        return use_case.execute(
            job_id=str(uuid4()),
            channel_id="channel-1",
            kind="SHORT",
            idempotency_key="same-key",
        )

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(create, range(64)))

    jobs = {job.job_id for job, _created in results}
    assert len(jobs) == 1
    assert sum(created for _job, created in results) == 1


def test_idempotency_key_cannot_be_reused_for_different_request():
    use_case = CreateContentJob(InMemoryJobRepository())
    use_case.execute(
        job_id=str(uuid4()),
        channel_id="channel-1",
        kind="SHORT",
        idempotency_key="same-key",
    )

    with pytest.raises(ValueError, match="different request"):
        use_case.execute(
            job_id=str(uuid4()),
            channel_id="channel-2",
            kind="VIDEO",
            idempotency_key="same-key",
        )
