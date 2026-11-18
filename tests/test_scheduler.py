import threading
from types import SimpleNamespace

from pas.scheduler import Scheduler


class FakeRepository:
    def __init__(self):
        self.statuses = []
        self.results = []
        self.sources = []
        self.due = []

    def upsert_schedule(self, *args):
        return {"se": 1, "lf": 2, "ca": 3}[args[0]]

    def start_run(self, *args):
        self.sources.append(args[-1] if len(args) > 5 else "schedule")
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

    def update_schedule_due(self, task, due):
        self.due.append((task, due))

    def list_schedules(self):
        return []


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


def test_manual_trigger_runs_disabled_task_and_marks_source():
    config = _config()
    config.tasks["lf"].enabled = False
    repository = FakeRepository()
    calls = []
    scheduler = Scheduler(config, repository=repository, runners={name: (lambda name=name: calls.append(name) or {"ok": True}) for name in ("se", "lf", "ca")})

    assert scheduler.trigger_task("lf") is True
    assert calls == ["lf"]
    assert repository.sources == ["manual"]


def test_daemon_persists_next_due_for_enabled_tasks():
    event = threading.Event()
    repository = FakeRepository()
    config = _config()
    config.tasks["se"].period_seconds = 60
    scheduler = Scheduler(config, repository=repository, runners={"se": lambda: {"ok": True}})
    event.set()
    scheduler.run_daemon(stop_event=event)

    assert {task for task, _ in repository.due} == {"se", "lf", "ca"}
