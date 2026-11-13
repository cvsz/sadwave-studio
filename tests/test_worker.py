import threading

from sadwave import worker
from sadwave.config import Settings


class StopAfterWaitEvent(threading.Event):
    def __init__(self, expected_timeout: float) -> None:
        super().__init__()
        self.expected_timeout = expected_timeout
        self.wait_calls = 0

    def wait(self, timeout: float | None = None) -> bool:
        assert timeout == self.expected_timeout
        self.wait_calls += 1
        self.set()
        return True


class IdleRepository:
    def __init__(self) -> None:
        self.recovery_calls = 0
        self.claim_calls = 0

    def recover_expired_leases(self, _lease_seconds: int) -> int:
        self.recovery_calls += 1
        return 0

    def claim_next(self, _worker_id: str, _lease_seconds: int):
        self.claim_calls += 1


def test_worker_interrupts_idle_poll_when_shutdown_is_requested(monkeypatch, caplog):
    settings = Settings(
        app_env="production",
        database_url="postgresql://localhost/sadwave",
        worker_poll_seconds=17,
    )
    stop_event = StopAfterWaitEvent(expected_timeout=17)
    repository = IdleRepository()
    caplog.set_level("INFO", logger="sadwave.worker")
    monkeypatch.setattr(worker, "PostgresJobRepository", lambda *_args: repository)

    worker.run_worker(stop_event=stop_event, settings=settings)

    assert stop_event.wait_calls == 1
    assert repository.recovery_calls == 1
    assert repository.claim_calls == 1
    assert "worker_shutdown_complete" in caplog.text


def test_main_installs_sigint_and_sigterm_shutdown_handlers(monkeypatch):
    settings = Settings(app_env="production", database_url="postgresql://localhost/sadwave")
    handlers = {}
    started = []
    configured_levels = []
    monkeypatch.setattr(worker, "get_settings", lambda **_kwargs: settings)
    monkeypatch.setattr(worker, "configure_logging", configured_levels.append)
    monkeypatch.setattr(
        worker.signal,
        "signal",
        lambda signum, handler: handlers.__setitem__(signum, handler),
    )
    monkeypatch.setattr(
        worker,
        "run_worker",
        lambda *, stop_event, settings: started.append((stop_event, settings)),
    )

    worker.main()

    assert configured_levels == [settings.log_level]
    stop_event, received_settings = started[0]
    assert received_settings is settings
    assert not stop_event.is_set()
    assert worker.signal.SIGINT in handlers
    assert worker.signal.SIGTERM in handlers
    for signum in (worker.signal.SIGINT, worker.signal.SIGTERM):
        stop_event.clear()
        handlers[signum](signum, None)
        assert stop_event.is_set()
