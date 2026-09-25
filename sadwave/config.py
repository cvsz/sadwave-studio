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
    max_daily_api_cost: float = Field(default=0.0, ge=0)
    max_monthly_api_cost: float = Field(default=0.0, ge=0)
    max_ai_tokens: int = Field(default=0, ge=0)
    max_render_time_seconds: int = Field(default=0, ge=0)
    ai_provider_mode: Literal["local", "explicit"] = "local"

    database_url: str = "postgresql://sadwave:sadwave@localhost:5432/sadwave"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    def validate_startup(self) -> None:
        if self.app_env in {"production", "staging"} and not self.api_token:
            raise ValueError("API_TOKEN is required in production/staging")
        if self.app_env == "production" and not self.database_url:
            raise ValueError("DATABASE_URL is required in production")
        if self.app_env == "production" and self.autonomy_level > 4:
            raise ValueError("AUTONOMY_LEVEL 5 is restricted and cannot be enabled by default")
        if self.cost_lock and (
            self.max_daily_api_cost > 0 or self.max_monthly_api_cost > 0
        ) and self.ai_provider_mode != "explicit":
            raise ValueError("Paid budgets require AI_PROVIDER_MODE=explicit")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    try:
        settings.validate_startup()
    except (ValidationError, ValueError) as exc:
        raise RuntimeError(f"Invalid application configuration: {exc}") from exc
    return settings
