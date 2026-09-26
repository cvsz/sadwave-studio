import uvicorn

from .config import get_settings
from .logging_config import configure_logging

if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "sadwave.api:app",
        host="0.0.0.0",
        port=settings.app_port,
        log_config=None,
        access_log=False,
    )
