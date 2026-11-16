import threading
from types import SimpleNamespace

from pas.scheduler import Scheduler


class FakeRepository:
    def __init__(self):
        self.statuses = []
        self.results = []

    def upsert_schedule(self, *args):
        return {"se": 1, "lf": 2, "ca": 3}[args[0]]

    def start_run(self, *args):
        return len(self.statuses) + len(self.results) + 1

    def finish_run(self, run_id, status, *args, **kwargs):
        self.statuses.append(status)

    def result_transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def store_result(self, task, run_id, result):
        self.results.append((task, result))


def _config():
    return SimpleNamespace(
        kernel_root="kernel",
        retry_seconds=1,
        tick_seconds=0.01,
        tasks={name: SimpleNamespace(name=name, enabled=True, period_seconds=1) for name in ("se", "lf", "ca")},
    )


def test_run_once_executes_enabled_tasks_in_order_and_isolates_failure():
    calls = []
    repository = FakeRepository()

    def run(task):
        calls.append(task)
        if task == "lf":
            raise ValueError("bad lf")
        return {"ok": True}

    scheduler = Scheduler(_config(), repository=repository, runners={name: (lambda name=name: run(name)) for name in ("se", "lf", "ca")})
    scheduler.run_once()

    assert calls == ["se", "lf", "ca"]
    assert repository.statuses == ["succeeded", "failed", "succeeded"]


def test_stop_event_ends_daemon_loop():
    event = threading.Event()
    event.set()
    scheduler = Scheduler(_config(), repository=FakeRepository(), runners={})
    scheduler.run_daemon(stop_event=event)
