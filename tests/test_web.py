import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from pas.db import Repository, RepositoryHub
from pas.web import PasWebApp


class FakeScheduler:
    def __init__(self):
        self.calls = []
        self.running = False

    def run_task(self, task):
        self.calls.append(task)
        return True

    def run_once(self):
        self.calls.append("all")
        return {"se": True, "lf": True, "ca": True}


def make_app(tmp_path: Path) -> tuple[PasWebApp, FakeScheduler]:
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    repo.upsert_schedule("se", True, 60, {"model_file": "model.e"})
    run_id = repo.start_run(1, "se", "2026-11-17T00:00:00+00:00", "kernel", "fp")
    repo.finish_run(run_id, "succeeded", "2026-11-17T00:00:01+00:00", 1.0, 0)
    scheduler = FakeScheduler()
    config = SimpleNamespace(
        database=tmp_path / "runs.db",
        kernel_root=tmp_path / "kernel",
        tasks={name: SimpleNamespace(name=name, enabled=(name == "se"), period_seconds=60) for name in ("se", "lf", "ca")},
    )
    return PasWebApp(config, repo, scheduler, tmp_path), scheduler


def test_overview_api_returns_counts_and_recent_runs(tmp_path):
    app, _ = make_app(tmp_path)

    response = app.api_get("/api/overview")

    assert response["ok"] is True
    assert response["data"]["counts"]["total_runs"] == 1
    assert response["data"]["recent_runs"][0]["task_type"] == "se"


def test_run_action_dispatches_selected_task(tmp_path):
    app, scheduler = make_app(tmp_path)

    response = app.api_post("/api/actions/run-once", {"task": "lf"})

    assert response["ok"] is True
    assert response["data"]["task"] == "lf"
    assert scheduler.calls == ["lf"]


def test_result_api_returns_task_result(tmp_path):
    app, _ = make_app(tmp_path)
    with app.repository.result_transaction():
        app.repository.store_se_result(1, {"converged": True, "observable": True, "statistics": {}, "state": [1.0], "summary": {}})

    response = app.api_get("/api/results/se/1")

    assert response["ok"] is True
    assert response["data"]["task_type"] == "se"


def test_static_route_rejects_path_traversal(tmp_path):
    app, _ = make_app(tmp_path)
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")

    assert app.static_path("/") == (tmp_path / "index.html").resolve()
    assert app.static_path("/../runs.db") is None


def test_config_and_logs_api_expose_pas_and_result_databases(tmp_path):
    result_repositories = {name: Repository(tmp_path / f"{name}.db") for name in ("se", "lf", "ca")}
    control = Repository(tmp_path / "control.db")
    hub = RepositoryHub(result_repositories, control)
    hub.initialize()
    control.record_log("INFO", "test", "service ready")
    config = SimpleNamespace(
        database=tmp_path / "control.db",
        databases={name: tmp_path / f"{name}.db" for name in ("se", "lf", "ca")},
        kernel_root=tmp_path / "kernel",
        tasks={name: SimpleNamespace(name=name, enabled=False, period_seconds=60) for name in ("se", "lf", "ca")},
    )
    app = PasWebApp(config, hub, FakeScheduler(), tmp_path)

    config_response = app.api_get("/api/config")
    logs_response = app.api_get("/api/logs?limit=1")

    assert config_response["data"]["control_database"] == str(tmp_path / "control.db")
    assert config_response["data"]["result_databases"]["se"] == str(tmp_path / "se.db")
    assert logs_response["data"][0]["message"] == "service ready"
    hub.close()
