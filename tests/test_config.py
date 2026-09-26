import pytest
from pydantic import ValidationError

from sadwave.config import Settings


def test_api_startup_requires_credentials_in_production():
    settings = Settings(app_env="production", database_url="postgresql://localhost/sadwave")

    with pytest.raises(ValueError, match="API_TOKEN is required"):
        settings.validate_startup()


def test_worker_can_start_without_receiving_api_token():
    settings = Settings(app_env="production", database_url="postgresql://localhost/sadwave")

    settings.validate_startup(require_api_token=False)


@pytest.mark.parametrize("token", ["short", "x" * 31, "x" * 32 + " ", "x" * 16 + " " + "x" * 16])
def test_production_api_rejects_weak_or_whitespace_token(token):
    settings = Settings(
        app_env="production",
        api_token=token,
        database_url="postgresql://localhost/sadwave",
    )

    with pytest.raises(ValueError, match="API_TOKEN must be at least 32"):
        settings.validate_startup()


def test_production_api_accepts_minimum_length_token():
    settings = Settings(
        app_env="production",
        api_token="x" * 32,
        database_url="postgresql://localhost/sadwave",
    )

    settings.validate_startup()


@pytest.mark.parametrize("field", ["max_daily_api_cost", "max_monthly_api_cost"])
@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_cost_budgets_reject_non_finite_values(field, amount):
    with pytest.raises(ValidationError):
        Settings(**{field: amount})


@pytest.mark.parametrize("amount", [float("nan"), float("inf"), float("-inf")])
def test_worker_poll_interval_rejects_non_finite_values(amount):
    with pytest.raises(ValidationError):
        Settings(worker_poll_seconds=amount)
