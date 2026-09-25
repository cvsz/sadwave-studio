from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .application import CreateContentJob, InMemoryJobRepository
from .config import get_settings
from .domain import JobState

settings = get_settings()
repository = InMemoryJobRepository()
create_content_job = CreateContentJob(repository)

app = FastAPI(title=settings.app_name, version="0.1.0")


class CreateJobRequest(BaseModel):
    channel_id: str = Field(min_length=1, max_length=256)
    kind: str = Field(min_length=1, max_length=128)


class JobResponse(BaseModel):
    job_id: str
    channel_id: str
    kind: str
    state: JobState
    idempotency_key: str


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sadwave-studio"}


@app.get("/ready")
def ready() -> dict[str, str]:
    # Dependency readiness will be extended when PostgreSQL/queue adapters are enabled.
    return {"status": "ready", "service": "sadwave-studio"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"name": settings.app_name, "version": app.version}


@app.post("/api/v1/content/jobs", response_model=JobResponse, status_code=201)
def create_job(
    payload: CreateJobRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JobResponse:
    if not x_idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key is required")
    try:
        job = create_content_job.execute(
            job_id=str(uuid4()),
            channel_id=payload.channel_id,
            kind=payload.kind,
            idempotency_key=x_idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return JobResponse(
        job_id=job.job_id,
        channel_id=job.channel_id,
        kind=job.kind,
        state=job.state,
        idempotency_key=job.idempotency_key,
    )
