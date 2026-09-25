import pytest

from sadwave.config import Settings


def test_api_startup_requires_credentials_in_production():
    settings = Settings(app_env="production", database_url="postgresql://localhost/sadwave")

    with pytest.raises(ValueError, match="API_TOKEN is required"):
        settings.validate_startup()


def test_worker_can_start_without_receiving_api_token():
    settings = Settings(app_env="production", database_url="postgresql://localhost/sadwave")

    settings.validate_startup(require_api_token=False)
