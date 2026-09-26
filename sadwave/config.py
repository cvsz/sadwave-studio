from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SadwaveStudio"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_port: int = Field(default=3000, ge=1, le=65535)
    log_level: str = "INFO"
    api_token: str | None = None

    dry_run: bool = True
    autonomy_level: int = Field(default=0, ge=0, le=5)
    cost_lock: bool = True
    max_daily_api_cost: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    max_monthly_api_cost: float = Field(default=0.0, ge=0, allow_inf_nan=False)
    max_ai_tokens: int = Field(default=0, ge=0)
    max_render_time_seconds: int = Field(default=0, ge=0)
    ai_provider_mode: Literal["local", "explicit"] = "local"

    database_url: str = ""

    api_rate_limit: int = Field(default=60, ge=1, le=10000)
    api_rate_window_seconds: int = Field(default=60, ge=1, le=3600)
    worker_id: str = Field(default="sadwave-worker", min_length=1, max_length=128)
    worker_lease_seconds: int = Field(default=300, ge=30, le=3600)
    worker_poll_seconds: float = Field(default=2.0, gt=0, le=60, allow_inf_nan=False)
    worker_max_attempts: int = Field(default=5, ge=1, le=20)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_startup(self, *, require_api_token: bool = True) -> None:
        if require_api_token and self.app_env in {"production", "staging"}:
            if not self.api_token:
                raise ValueError("API_TOKEN is required in production/staging")
            if (
                len(self.api_token) < 32
                or self.api_token.strip() != self.api_token
                or any(character.isspace() for character in self.api_token)
            ):
                raise ValueError("API_TOKEN must be at least 32 non-whitespace characters")
        if self.app_env in {"production", "staging"} and not self.database_url.strip():
            raise ValueError("DATABASE_URL is required in production/staging")
        if self.app_env == "production" and self.autonomy_level > 4:
            raise ValueError("AUTONOMY_LEVEL 5 is restricted and cannot be enabled by default")
        if (
            self.cost_lock
            and (self.max_daily_api_cost > 0 or self.max_monthly_api_cost > 0)
            and self.ai_provider_mode != "explicit"
        ):
            raise ValueError("Paid budgets require AI_PROVIDER_MODE=explicit")


@lru_cache
def get_settings(*, require_api_token: bool = True) -> Settings:
    settings = Settings()
    try:
        settings.validate_startup(require_api_token=require_api_token)
    except (ValidationError, ValueError) as exc:
        raise RuntimeError(f"Invalid application configuration: {exc}") from exc
    return settings
