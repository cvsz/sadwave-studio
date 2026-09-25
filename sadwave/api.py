import logging
import re
import secrets
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from .application import CreateContentJob, InMemoryJobRepository
from .config import get_settings
from .domain import JobState
from .repository import PostgresJobRepository

logger = logging.getLogger("sadwave.api")
settings = get_settings()
repository = (
    PostgresJobRepository(settings.database_url, settings.worker_max_attempts)
    if settings.app_env in {"production", "staging"}
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


def _safe_request_id(value: str | None) -> str:
    if value and len(value) <= 128 and re.fullmatch(r"[A-Za-z0-9._-]+", value):
        return value
    return str(uuid4())


def _secure_response(response: Response, request_id: str, path: str) -> Response:
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store" if path.startswith("/api/") else "no-cache"
    return response


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", _safe_request_id(None))
    return _secure_response(
        JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "requestId": request_id,
                    "details": details or [],
                }
            },
        ),
        request_id,
        request.url.path,
    )


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = _safe_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    if request.url.path.startswith("/api/") and not _authorized(request):
        return _error_response(
            request,
            status_code=401,
            code="UNAUTHORIZED",
            message="unauthorized",
        )

    if settings.app_env in {"production", "staging"} and request.url.path.startswith("/api/"):
        client_host = request.client.host if request.client else "unknown"
        allowed = repository.allow_rate(
            f"api:{client_host}", settings.api_rate_limit, settings.api_rate_window_seconds
        )
        if not allowed:
            response = _error_response(
                request,
                status_code=429,
                code="RATE_LIMITED",
                message="rate limit exceeded",
            )
            response.headers["Retry-After"] = str(settings.api_rate_window_seconds)
            return response

    response = await call_next(request)
    _secure_response(response, request_id, request.url.path)
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    code = {
        401: "UNAUTHORIZED",
        429: "RATE_LIMITED",
    }.get(exc.status_code, "REQUEST_ERROR")
    return _error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "reason": str(error["type"]),
        }
        for error in exc.errors()
    ]
    return _error_response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="request validation failed",
        details=details,
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    logger.error(
        "request_failed request_id=%s path=%s error_type=%s",
        getattr(request.state, "request_id", "unknown"),
        request.url.path,
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="internal server error",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sadwave-studio"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if settings.app_env in {"production", "staging"}:
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
    if not x_idempotency_key or not x_idempotency_key.strip():
        raise HTTPException(status_code=400, detail="X-Idempotency-Key is required")
    if len(x_idempotency_key) > 256:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key is too long")
    try:
        job, _created = create_content_job.execute(
            job_id=str(uuid4()),
            channel_id=payload.channel_id,
            kind=payload.kind,
            idempotency_key=x_idempotency_key,
            actor_id=(
                "api:authenticated" if settings.app_env in {"production", "staging"} else None
            ),
            request_id=getattr(request.state, "request_id", None),
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
