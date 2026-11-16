import sqlite3
from pathlib import Path

from pas.db import Repository


def test_schema_is_idempotent_and_stores_run_result(tmp_path: Path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    repo.initialize()
    schedule_id = repo.upsert_schedule("lf", True, 10, {"model_file": "m.e"})
    run_id = repo.start_run(schedule_id, "lf", "2026-11-17T00:00:00+00:00", "kernel", "fingerprint")
    repo.finish_run(run_id, "succeeded", "2026-11-17T00:00:01+00:00", 1.0, 0)
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
