from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class JobState(StrEnum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    VALIDATING = "VALIDATING"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.DRAFT: frozenset(
        {JobState.PLANNED, JobState.FAILED, JobState.BLOCKED, JobState.CANCELLED}
    ),
    JobState.PLANNED: frozenset({JobState.GENERATING, JobState.CANCELLED}),
    JobState.GENERATING: frozenset({JobState.GENERATED, JobState.FAILED, JobState.CANCELLED}),
    JobState.GENERATED: frozenset({JobState.VALIDATING, JobState.CANCELLED}),
    JobState.VALIDATING: frozenset(
        {JobState.READY_FOR_REVIEW, JobState.BLOCKED, JobState.FAILED, JobState.CANCELLED}
    ),
    JobState.READY_FOR_REVIEW: frozenset({JobState.APPROVED, JobState.BLOCKED, JobState.CANCELLED}),
    JobState.APPROVED: frozenset({JobState.SCHEDULED, JobState.PUBLISHING, JobState.CANCELLED}),
    JobState.SCHEDULED: frozenset({JobState.PUBLISHING, JobState.CANCELLED}),
    JobState.PUBLISHING: frozenset({JobState.PUBLISHED, JobState.FAILED, JobState.BLOCKED}),
    JobState.PUBLISHED: frozenset(),
    JobState.FAILED: frozenset({JobState.PLANNED, JobState.CANCELLED}),
    JobState.BLOCKED: frozenset({JobState.PLANNED, JobState.CANCELLED}),
    JobState.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ContentJob:
    job_id: str
    channel_id: str
    kind: str
    state: JobState
    idempotency_key: str
    created_at: datetime

    @staticmethod
    def create(job_id: str, channel_id: str, kind: str, idempotency_key: str) -> "ContentJob":
        return ContentJob(
            job_id=job_id,
            channel_id=channel_id,
            kind=kind,
            state=JobState.DRAFT,
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC),
        )

    def transition(self, target: JobState) -> "ContentJob":
        if target not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"Invalid job transition: {self.state} -> {target}")
        return ContentJob(
            job_id=self.job_id,
            channel_id=self.channel_id,
            kind=self.kind,
            state=target,
            idempotency_key=self.idempotency_key,
            created_at=self.created_at,
        )
