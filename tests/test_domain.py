import pytest

from sadwave.domain import ContentJob, JobState


def test_valid_job_transition():
    job = ContentJob.create("job-1", "channel-1", "SHORT", "idem-1")
    assert job.transition(JobState.PLANNED).state is JobState.PLANNED


def test_invalid_job_transition_is_rejected():
    job = ContentJob.create("job-1", "channel-1", "SHORT", "idem-1")
    with pytest.raises(ValueError, match="Invalid job transition"):
        job.transition(JobState.PUBLISHED)


@pytest.mark.parametrize("state", [JobState.FAILED, JobState.BLOCKED])
def test_draft_job_can_record_terminal_worker_outcome(state):
    job = ContentJob.create("job-1", "channel-1", "SHORT", "idem-1")

    assert job.transition(state).state is state
