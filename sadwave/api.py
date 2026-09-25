import secrets
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .application import CreateContentJob, InMemoryJobRepository
from .config import get_settings
from .domain import JobState
from .repository import PostgresJobRepository

settings = get_settings()
repository = (
    PostgresJobRepository(settings.database_url)
    if settings.app_env == "production"
    else InMemoryJobRepository()
)
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


def _authorized(request: Request) -> bool:
    if settings.app_env not in {"production", "staging"}:
        return True
    provided = request.headers.get("Authorization", "")
    if not provided.startswith("Bearer "):
        return False
    return secrets.compare_digest(provided[7:], settings.api_token or "")


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    if request.url.path.startswith("/api/") and not _authorized(request):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "unauthorized",
                    "requestId": request_id,
                    "details": [],
                }
            },
            headers={"X-Request-ID": request_id},
        )

    if settings.app_env == "production" and request.url.path.startswith("/api/"):
        client_host = request.client.host if request.client else "unknown"
        allowed = repository.allow_rate(
            f"api:{client_host}", settings.api_rate_limit, settings.api_rate_window_seconds
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "rate limit exceeded",
                        "requestId": request_id,
                        "details": [],
                    }
                },
                headers={"X-Request-ID": request_id, "Retry-After": str(settings.api_rate_window_seconds)},
            )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("X-Request-ID") or "unknown"
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "UNAUTHORIZED" if exc.status_code == 401 else "REQUEST_ERROR",
                "message": str(exc.detail),
                "requestId": request_id,
                "details": [],
            }
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sadwave-studio"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if settings.app_env == "production":
        try:
            repository.healthcheck()  # type: ignore[attr-defined]
        except Exception as exc:
            raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready", "service": "sadwave-studio"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"name": settings.app_name, "version": app.version}


@app.post("/api/v1/content/jobs", response_model=JobResponse, status_code=201)
def create_job(
    request: Request,
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

    if settings.app_env == "production":
        repository.audit(
            actor_id="api:authenticated",
            action="CONTENT_JOB_CREATED",
            resource_type="content_job",
            resource_id=job.job_id,
            request_id=request.headers.get("X-Request-ID"),
            details={"channel_id": job.channel_id, "kind": job.kind},
        )

    return JobResponse(
        job_id=job.job_id,
        channel_id=job.channel_id,
        kind=job.kind,
        state=job.state,
        idempotency_key=job.idempotency_key,
    )
