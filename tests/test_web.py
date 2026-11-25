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


def test_static_web_is_split_into_real_pages():
    web_root = Path(__file__).resolve().parents[1] / "web"
    pages = {
        "index.html": "/overview",
        "overview.html": "/overview",
        "analysis/lf.html": "/analysis/lf",
        "analysis/ca.html": "/analysis/ca",
        "runs.html": "/runs",
        "settings.html": "/settings",
    }
    for relative, route in pages.items():
        html = (web_root / relative).read_text(encoding="utf-8")
        assert f'<body data-page="{route}">' in html
        assert "href=\"#/" not in html
    assert (web_root / "se-main.html").is_file()
    assert not (web_root / "analysis" / "se.html").exists()
    assert (web_root / "analysis" / "lf.html").is_file()
    assert (web_root / "analysis" / "ca.html").is_file()


def test_http_filtered_export_stream_and_validation(tmp_path):
    import csv
    import io
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.error import HTTPError
    from urllib.request import urlopen

    import pytest

    app, _ = make_app(tmp_path)
    with app.repository.result_transaction():
        app.repository.store_se_result(1, {"measurements": [
            {"name": f"m{i}", "value": -i, "residual": -i, "valid": i % 2 == 0}
            for i in range(1200)
        ]})
    server = ThreadingHTTPServer(("127.0.0.1", 0), app.handler_class())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/api/export/se/1?view=invalid&sort=abs_residual&direction=desc", timeout=5) as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert "attachment" in response.headers["Content-Disposition"]
            rows = list(csv.DictReader(io.StringIO(response.read().decode("utf-8-sig"))))
        assert len(rows) == 600  # More than one streaming chunk or UI page.
        assert rows[0]["measurement_name"] == "m1199"
        assert rows[-1]["measurement_name"] == "m1"
        assert rows[0]["value"] == "-1199.0"
        for path in ("/api/export/se/1?sort=bogus", "/api/export/se/999", "/api/export/se/invalid"):
            with pytest.raises(HTTPError) as caught:
                urlopen(base + path, timeout=5)
            assert caught.value.code == 400
            assert json.loads(caught.value.read())["ok"] is False
        with urlopen(base + "/api/results/se/1?compact=1", timeout=5) as response:
            compact = json.loads(response.read())["data"]
        assert compact["detail_count"] == 1200
        assert "details" not in compact and "state_json" not in compact["summary"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        app.repository.close()


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


def test_runs_api_supports_status_filters_and_run_details(tmp_path):
    app, _ = make_app(tmp_path)

    response = app.api_get("/api/runs?task=se&status=succeeded&limit=1")

    assert response["ok"] is True
    assert response["meta"] == {"limit": 1, "offset": 0, "total": 1, "task": "se", "status": "succeeded"}
    detail = app.api_get("/api/runs/se/1")
    assert detail["ok"] is True
    assert detail["data"]["run"]["task_type"] == "se"


def test_runs_api_supports_execution_source_filter(tmp_path):
    app, _ = make_app(tmp_path)
    source = app.api_get("/api/runs?source=manual&limit=1")
    assert source["ok"] is True
    assert source["meta"]["source"] == "manual"
    assert source["meta"]["total"] == 0


def test_status_api_reports_web_and_daemon_state(tmp_path):
    app, _ = make_app(tmp_path)

    response = app.api_get("/api/status")

    assert response["ok"] is True
    assert response["data"]["web_running"] is True
    assert response["data"]["daemon_running"] is False


def test_health_api_reports_database_and_task_readiness(tmp_path):
    app, _ = make_app(tmp_path)

    response = app.api_get("/api/health")

    assert response["ok"] is True
    assert response["data"]["status"] == "degraded"  # The fake task inputs are absent.
    assert response["data"]["databases"]["pas"]["sqlite"] == "ok"
    assert response["data"]["tasks"]["se"]["inputs_ready"] is False
    app.repository.close()


def test_web_daemon_control_is_idempotent(tmp_path):
    class DaemonScheduler(FakeScheduler):
        def __init__(self):
            super().__init__()
            self.stop = None

        def run_daemon(self, stop_event):
            self.stop = stop_event
            self.running = True
            stop_event.wait(2)
            self.running = False

        def shutdown(self):
            if self.stop:
                self.stop.set()

    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    scheduler = DaemonScheduler()
    config = SimpleNamespace(
        database=tmp_path / "runs.db",
        kernel_root=tmp_path / "kernel",
        tasks={name: SimpleNamespace(name=name, enabled=False, period_seconds=60) for name in ("se", "lf", "ca")},
    )
    app = PasWebApp(config, repo, scheduler, tmp_path)
    try:
        assert app.api_post("/api/actions/daemon/start")["data"]["running"] is True
        assert app.api_post("/api/actions/daemon/start")["data"]["running"] is True
        assert app.api_get("/api/status")["data"]["daemon_running"] is True
        stopped = app.api_post("/api/actions/daemon/stop")
        assert stopped["data"] == {"running": False, "stopping": False}
    finally:
        app.close()
        repo.close()


def test_invalid_result_id_returns_json_error(tmp_path):
    app, _ = make_app(tmp_path)

    response = app.api_get("/api/results/se/not-a-number")

    assert response == {"ok": False, "error": "invalid_run_id"}


def test_run_all_with_no_enabled_tasks_is_not_reported_as_success(tmp_path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    class EmptyScheduler(FakeScheduler):
        def run_once(self):
            return {}

    scheduler = EmptyScheduler()
    config = SimpleNamespace(
        database=tmp_path / "runs.db",
        kernel_root=tmp_path / "kernel",
        tasks={name: SimpleNamespace(name=name, enabled=False, period_seconds=60) for name in ("se", "lf", "ca")},
    )
    app = PasWebApp(config, repo, scheduler, tmp_path)

    response = app.api_post("/api/actions/run-once", {})

    assert response["ok"] is False


def test_trend_api_and_retry_failed_api(tmp_path):
    app, scheduler = make_app(tmp_path)
    trend = app.api_get("/api/metrics/trend?limit=2")
    assert trend["ok"] is True
    assert isinstance(trend["data"], list)

    class RetryScheduler(FakeScheduler):
        def retry_failed_async(self, task=None):
            return {"accepted": True, "tasks": {"se": {"accepted": True, "job_id": "job1", "task": "se"}}}

    app.scheduler = RetryScheduler()
    retry = app.api_post("/api/actions/retry-failed", {})
    assert retry["ok"] is True
    assert retry["data"]["tasks"]["se"]["accepted"] is True


def test_dbdef_browse_api_returns_catalog_and_rows(tmp_path):
    app, _ = make_app(tmp_path)
    result = {
        "converged": True,
        "observable": True,
        "statistics": {"measurement_count": 1, "normal_measurement_count": 1},
        "measurements": [{"idx": 1, "name": "m1", "device_name": "bus1", "meas_type": 1, "value": 1.0, "estimated_value": 1.01, "valid": True}],
    }
    with app.repository.result_transaction():
        app.repository.store_se_result(1, result)
        app.repository.store_dbdef_result("se", 1, result, "2026-11-17T00:00:00+00:00")

    catalog = app.api_get("/api/dbdef/se/1")
    assert catalog["ok"] is True
    assert any(row["table_name"] == "pas_se_meas" for row in catalog["data"]["tables"])
    rows = app.api_get("/api/dbdef/se/1/pas_se_meas?limit=1&q=bus1")
    assert rows["ok"] is True
    assert rows["data"]["meta"]["total"] == 1
    assert rows["data"]["rows"][0]["dev_name"] == "bus1"


def test_dbdef_browse_api_rejects_table_from_another_task(tmp_path):
    app, _ = make_app(tmp_path)
    response = app.api_get("/api/dbdef/se/1/pas_ra_info")
    assert response["ok"] is False
    assert "unsupported dbdef table" in response["error"]
