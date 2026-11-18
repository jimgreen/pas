from __future__ import annotations

import sqlite3
from pathlib import Path

from pas.db import Repository
from pas.dbdef import load_catalog


def _run(repo: Repository, task: str) -> int:
    schedule_id = repo.upsert_schedule(task, True, 10, {})
    return repo.start_run(schedule_id, task, "2026-11-18T00:00:00+00:00", "kernel", "fp")


def test_catalog_and_schema_include_all_reference_tables(tmp_path: Path):
    repo = Repository(tmp_path / "pas.db")
    repo.initialize()
    catalog = load_catalog()
    with sqlite3.connect(tmp_path / "pas.db") as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert len(catalog) == 42
    assert set(catalog).issubset(tables)
    assert "pas_dbdef_run" in tables
    repo.close()


def test_se_dbdef_rows_are_written_and_exposed(tmp_path: Path):
    repo = Repository(tmp_path / "se.db")
    repo.initialize()
    run_id = _run(repo, "se")
    result = {
        "converged": True,
        "observable": True,
        "statistics": {"measurement_count": 2, "normal_measurement_count": 1, "bad_data_count": 1, "iterations": 3, "objective": 2.0, "residual_inf": 0.1},
        "measurements": [
            {"idx": 1, "name": "m1", "device_name": "d1", "meas_type": 1, "value": 2.0, "estimated_value": 2.1, "valid": True},
            {"idx": 2, "name": "m2", "device_name": "d2", "meas_type": 2, "value": None, "valid": False, "reason": "bad"},
        ],
    }
    with repo.result_transaction():
        repo.store_result("se", run_id, result)
        counts = repo.store_dbdef_result("se", run_id, result, "2026-11-18T00:00:00+00:00", "2026-11-18T00:00:01+00:00")
    assert counts["pas_se_info"] == 1
    assert counts["pas_se_meas"] == 2
    exposed = repo.get_result("se", run_id)["dbdef"]["tables"]
    assert exposed["pas_se_meas"]["count"] == 2
    assert exposed["pas_se_badmeas"]["count"] == 1
    repo.close()


def test_composite_key_upsert_replaces_row(tmp_path: Path):
    repo = Repository(tmp_path / "lf.db")
    repo.initialize()
    with repo.result_transaction():
        repo.upsert_dbdef_row("pas_lf_result", {"time": 100, "dev_type": "branch", "dev_name": "b1", "type": "ac", "calc_value": 2.0})
        repo.upsert_dbdef_row("pas_lf_result", {"time": 100, "dev_type": "branch", "dev_name": "b1", "type": "ac", "calc_value": 3.0})
    with sqlite3.connect(tmp_path / "lf.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM pas_lf_result").fetchone()[0] == 1
        assert conn.execute("SELECT calc_value FROM pas_lf_result").fetchone()[0] == 3.0
    repo.close()


def test_transaction_rolls_back_dbdef_projection(tmp_path: Path):
    repo = Repository(tmp_path / "ca.db")
    repo.initialize()
    run_id = _run(repo, "ca")
    try:
        with repo.result_transaction():
            repo.store_result("ca", run_id, {"risk_level": "高", "risks": []})
            repo.store_dbdef_result("ca", run_id, {"risk_level": "高", "risks": []}, "2026-11-18T00:00:00+00:00")
            raise RuntimeError("rollback")
    except RuntimeError:
        pass
    with sqlite3.connect(tmp_path / "ca.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM ca_result").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM pas_ra_info").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM pas_dbdef_run").fetchone()[0] == 0
    repo.close()


def test_ca_exposes_security_and_risk_tables(tmp_path):
    repo=Repository(tmp_path/"ca.db");repo.initialize()
    rid=_run(repo,"ca")
    result={"risk_level":"中","risks":[{"risk_type":"voltage","risk_value":1.2}]}
    with repo.result_transaction():
        repo.store_ca_result(rid,result)
        repo.store_dbdef_result("ca",rid,result,"2026-11-18T00:00:00+00:00")
    tables=repo.get_result("ca",rid)["dbdef"]["tables"]
    assert tables["pas_lf_secure_result"]["rows"][0]["value"]==1.2
    assert tables["pas_ra_risk_list"]["count"]==1
    assert "pas_lf_secure_result" in {row["table_name"] for row in repo.list_dbdef_tables("ca",rid)}
    repo.close()
