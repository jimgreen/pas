import sqlite3
from pathlib import Path

from pas.db import Repository, RepositoryHub


def test_schema_is_idempotent_and_stores_run_result(tmp_path: Path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    repo.initialize()
    schedule_id = repo.upsert_schedule("lf", True, 10, {"model_file": "m.e"})
    run_id = repo.start_run(schedule_id, "lf", "2026-11-17T00:00:00+00:00", "kernel", "fingerprint")
    repo.finish_run(run_id, "succeeded", "2026-11-17T00:00:01+00:00", 1.0, 0)
    with repo.result_transaction():
        repo.store_lf_result(run_id, {"converged": True, "iterations": 2, "norm_f": 1e-9, "summary": {"nodes": 3}})

    with sqlite3.connect(tmp_path / "runs.db") as conn:
        assert conn.execute("select count(*) from schema_version").fetchone()[0] == 1
        assert conn.execute("select status from calculation_run where run_id = ?", (run_id,)).fetchone()[0] == "succeeded"
        assert conn.execute("select converged from lf_result where run_id = ?", (run_id,)).fetchone()[0] == 1


def test_failed_result_transaction_does_not_leave_partial_rows(tmp_path: Path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    schedule_id = repo.upsert_schedule("ca", True, 10, {})
    run_id = repo.start_run(schedule_id, "ca", "t", "kernel", "fp")

    try:
        with repo.result_transaction():
            repo.store_ca_result(run_id, {"risk_level": "高", "n0_risk_count": 1, "n1_scan_count": 0, "n1_risk_count": 0, "risks": []})
            raise RuntimeError("rollback")
    except RuntimeError:
        pass

    with sqlite3.connect(tmp_path / "runs.db") as conn:
        assert conn.execute("select count(*) from ca_result").fetchone()[0] == 0
        assert conn.execute("select count(*) from calculation_run").fetchone()[0] == 1


def test_repository_hub_aggregates_runs_from_separate_databases(tmp_path: Path):
    repositories = {name: Repository(tmp_path / f"{name}.db") for name in ("se", "lf", "ca")}
    hub = RepositoryHub(repositories, Repository(tmp_path / "control.db"))
    hub.initialize()
    for task, repo in repositories.items():
        schedule_id = repo.upsert_schedule(task, True, 10, {})
        run_id = repo.start_run(schedule_id, task, f"2026-11-17T00:00:0{len(task)}+00:00", "kernel", "fp")
        repo.finish_run(run_id, "succeeded", f"2026-11-17T00:00:1{len(task)}+00:00", 1.0, 0)

    overview = hub.overview()

    assert overview["counts"]["total_runs"] == 3
    assert {row["task_type"] for row in hub.list_runs(10)} == {"se", "lf", "ca"}
    hub.close()


def test_manual_execution_source_is_persisted_and_filterable(tmp_path: Path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    schedule_id = repo.upsert_schedule("se", False, 60, {})
    run_id = repo.start_run(schedule_id, "se", "2026-11-17T00:00:00+00:00", "kernel", "fp", "manual")
    assert repo.list_runs(execution_source="manual")[0]["run_id"] == run_id
    assert repo.count_runs(execution_source="schedule") == 0
    assert repo.get_run(run_id)["execution_source"] == "manual"


def test_hub_history_pages_beyond_first_500_per_task(tmp_path):
    repos={name:Repository(tmp_path/f"{name}.db") for name in ("se","lf","ca")}
    hub=RepositoryHub(repos)
    hub.initialize()
    for name,repo in repos.items():
        sid=repo.upsert_schedule(name,True,60,{})
        with repo.result_transaction():
            repo._connection().executemany("INSERT INTO calculation_run(schedule_id,task_type,status,started_at) VALUES (?,?,'running',?)",[(sid,name,f"2026-11-18T{i//60:02d}:{i%60:02d}:00+00:00") for i in range(520)])
    page=hub.list_runs(10,offset=1520)
    assert len(page)==10
    assert page[0]["run_id"]==14
    assert hub.count_runs()==1560
    hub.close()


def test_trend_groups_runs_by_hour(tmp_path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    sid = repo.upsert_schedule("se", True, 60, {})
    for index, status in enumerate(("succeeded", "failed", "succeeded")):
        rid = repo.start_run(sid, "se", f"2026-11-18T03:0{index}:00+00:00", "kernel", "fp")
        repo.finish_run(rid, status, f"2026-11-18T03:0{index}:01+00:00", index + 1, 0 if status == "succeeded" else 1)
    trend = repo.trend(1, "2026-11-18T03:59:00+00:00")
    assert trend[-1]["bucket"] == "2026-11-18T03"
    assert trend[-1]["tasks"]["se"]["runs"] == 3
    assert trend[-1]["tasks"]["se"]["failed"] == 1
    assert trend[-1]["tasks"]["se"]["avg_elapsed_seconds"] == 2.0
    repo.close()
