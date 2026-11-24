"""覆盖 SE 伪量测、坏量测、运行日志（存储/读取/定期删除）及 Web API 的单元测试。"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from pas.db import Repository
from pas.dbdef import build_dbdef_rows
from pas.input_store import measurement_input
from pas.se_bad import detect_suspect_statuses
from pas.se_log import maybe_auto_purge_se_logs, preview_purge_se_logs, purge_se_logs, record_se_log
from pas.se_pseudo import ensure_se_pseudo_columns
from pas.web import PasWebApp


def _build_temp_wide_scada(path: Path) -> Path:
    """构造最小只读宽表 scdfe_d 测试库。"""
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """CREATE TABLE ACNode (
                   idx INTEGER PRIMARY KEY, name TEXT,
                   uab REAL, uab_qual INTEGER, uab_pre REAL, uab_time INTEGER, uab_notuse INTEGER, uab_weight REAL, uab_rtu INTEGER, uab_pnt INTEGER
               )"""
        )
        conn.execute("INSERT INTO ACNode VALUES (1, 'Bus1', 380.0, 0, 380.0, 1700000000000, 0, 1.0, 1, 1)")
        conn.execute("INSERT INTO ACNode VALUES (2, 'Bus2', NULL, 1, NULL, 1700000000000, 0, 1.0, 1, 2)")
        conn.execute(
            """CREATE TABLE ACBreak (
                   idx INTEGER PRIMARY KEY, name TEXT,
                   position INTEGER, position_qual INTEGER, position_notuse INTEGER,
                   ia REAL, ia_qual INTEGER, ia_pre REAL, ia_time INTEGER, ia_notuse INTEGER, ia_weight REAL, ia_rtu INTEGER, ia_pnt INTEGER
               )"""
        )
        conn.execute("INSERT INTO ACBreak VALUES (1, 'Brk1', 1, 0, 0, 12.5, 0, 12.5, 1700000000000, 0, 1.0, 1, 3)")
        conn.commit()
    finally:
        conn.close()
    return path


def _make_dummy_app(tmp_path: Path) -> tuple[PasWebApp, Repository]:
    db_path = tmp_path / "se.sqlite3"
    repo = Repository(db_path)
    repo.initialize()
    cfg = SimpleNamespace(
        kernel_root=tmp_path,
        database=db_path,
        databases={"se": db_path},
        tasks={
            "se": SimpleNamespace(
                name="se",
                enabled=True,
                period_seconds=60,
                model_file=None,
                measurement_file=None,
                parameter_file=None,
                limit_file=None,
            ),
            "lf": SimpleNamespace(name="lf", enabled=False, period_seconds=60, model_file=None, parameter_file=None),
            "ca": SimpleNamespace(name="ca", enabled=False, period_seconds=300, model_file=None, limit_file=None, scan_n1=False),
        },
        workspace_root=str(tmp_path),
        runtime="realtime",
        scenario="test",
        workspace_directory=str(tmp_path),
    )
    sched = SimpleNamespace(status=lambda: {"active_tasks": [], "pending_tasks": [], "jobs": [], "schedules": []})
    web_root = Path(__file__).resolve().parent.parent / "web"
    return PasWebApp(cfg, repo, sched, web_root), repo


def test_pseudo_meas_and_stat_crud_and_legacy_cleanup(tmp_path: Path) -> None:
    """验证伪量测/伪状态 CRUD、历史污染清理以及 dbdef 不再污染配置表。"""
    repo = Repository(tmp_path / "se.sqlite3")
    repo.initialize()
    try:
        # 模拟历史上 dbdef 误写入 pas_se_psemeas_define 的脏数据（id >= 1_000_000 且无 device_type）
        with repo._lock:
            conn = repo._connection()
            conn.execute(
                "INSERT INTO pas_se_psemeas_define(id, meas_id, meas_name, dev_name, meas_type, meas_value, meas_weight, meas_useflag) VALUES (894000001, 1, 'dirty', 'Brk1', 1, 0.0, 1e-8, 1)"
            )
            conn.commit()
            cleaned = ensure_se_pseudo_columns(conn)
            conn.commit()
            assert cleaned == 1

        # 新增伪量测定义并检验去重更新与审计日志
        saved = repo.se_pseudo_meas_save(
            {
                "device_type": "ACNode",
                "device_idx": 1,
                "device_name": "Bus1",
                "metric": "uab",
                "meas_value": 380.5,
                "meas_weight": 0.01,
                "meas_useflag": 1,
                "source_mode": "manual",
                "note": "测试母线伪量测",
            }
        )
        assert saved["id"] == 1
        assert saved["se_type"] == "V"
        assert saved["unit"] == "V"

        # 同设备同指标再次保存应执行更新而非重复插入
        updated = repo.se_pseudo_meas_save(
            {
                "device_type": "ACNode",
                "device_idx": 1,
                "device_name": "Bus1",
                "metric": "uab",
                "meas_value": 382.0,
                "meas_weight": 0.02,
                "meas_useflag": 1,
            }
        )
        assert updated["id"] == saved["id"]
        assert len(repo.se_pseudo_meas_list()) == 1

        # 伪状态 CRUD
        pstat = repo.se_pseudo_stat_save(
            {
                "device_type": "ACBreak",
                "device_idx": 1,
                "device_name": "Brk1",
                "stat_value": 0,
                "stat_useflag": 1,
                "note": "强制分位",
            }
        )
        assert pstat["metric"] == "status"
        assert len(repo.se_pseudo_stat_list(enabled_only=True)) == 1

        # 验证 build_dbdef_rows 不再写入 pas_se_psemeas_define
        dbdef_rows = build_dbdef_rows(
            "se",
            {
                "converged": True,
                "measurements": [{"idx": 1, "name": "p1", "device_name": "Brk1", "meas_type": "P_FROM", "value": 0.0, "estimated_value": 0.0, "valid": True, "source": "pseudo", "reason": "observability"}],
                "missing_measurements": [{"device_idx": 2, "meas_name": "ACNode.2.uab", "device_name": "Bus2", "se_type": "V_MAG", "raw_value": None, "reason": "missing_sample"}],
            },
            run_id=10,
        )
        assert "pas_se_psemeas_define" not in dbdef_rows
        assert "pas_se_psemeas" in dbdef_rows
        assert len(dbdef_rows["pas_se_nomeas"]) == 1

        assert repo.se_pseudo_meas_delete(saved["id"]) is True
        assert repo.se_pseudo_stat_delete(pstat["id"]) is True
        # 验证变更审计均统一记录到 se_run_log
        logs = repo.se_logs_list(stage="pseudo_change")
        assert logs["total"] >= 4
    finally:
        repo.close()


def test_measurement_input_applies_bad_policy_and_pseudo_injection(tmp_path: Path) -> None:
    """验证坏量测屏蔽策略与人工伪量测/伪状态能够正确生成带 status 列的 .meas 与内存拓扑覆盖。"""
    scada_db = _build_temp_wide_scada(tmp_path / "scdfe_d.sqlite3")
    model = {
        "Model": [{"u_unit": "V", "p_unit": "kW", "i_unit": "A"}],
        "ACNode": [{"idx": 1, "name": "Bus1"}, {"idx": 2, "name": "Bus2"}],
        "ACBreak": [{"idx": 1, "name": "Brk1", "status": 1}],
    }
    task = SimpleNamespace(measurement_file=scada_db, model_file=None, point_catalog_file=None)
    bad_policies = [{"id": 7, "device_type": "ACNode", "device_name": "Bus1", "metric": "uab", "action": "suppress", "enabled": 1, "reason": "漂移"}]
    pseudo_meas = [{"id": 3, "device_type": "ACNode", "device_idx": 2, "dev_name": "Bus2", "metric": "uab", "se_type": "V_MAG", "unit": "V", "meas_value": 379.5, "meas_weight": 0.001, "meas_useflag": 1, "note": "人工补测"}]
    pseudo_stat = [{"id": 2, "device_type": "ACBreak", "device_idx": 1, "dev_name": "Brk1", "metric": "status", "stat_value": 0, "stat_useflag": 1}]

    with measurement_input(
        task,
        model,
        scada_snapshot=True,
        bad_policies=bad_policies,
        pseudo_meas_defines=pseudo_meas,
        pseudo_stat_defines=pseudo_stat,
    ) as (meas_path, meta):
        text = meas_path.read_text(encoding="utf-8")
        assert "@ idx name dev_type dev_name meas_type weight valid value status" in text
        assert meta["policy_suppressed_count"] == 1
        assert meta["user_pseudo_injected"] == 1
        assert meta["pseudo_stat_applied"] == 1
        assert meta["topology_overrides"]["ACBreak"][1]["status"] == 0
        assert len(meta["missing_measurements"]) == 1
        # Bus1.uab 被置 valid=0 status=1；Bus2.uab 作为伪量测置 valid=1 status=2
        lines = [ln for ln in text.splitlines() if ln.startswith("# ")]
        assert any("Bus1" in ln and ln.endswith(" 0 380.0 1") for ln in lines)
        assert any("Bus2" in ln and ln.endswith(" 1 379.5 2") for ln in lines)


def test_bad_data_workflow_ack_suppress_convert_and_suspect_status(tmp_path: Path) -> None:
    """验证坏量测确认、屏蔽策略、一键转伪量测、跨运行保留确认状态以及可疑遥信识别。"""
    repo = Repository(tmp_path / "se.sqlite3")
    repo.initialize()
    try:
        sid = repo.upsert_schedule("se", True, 60, {})
        run1 = repo.start_run(sid, "se", "2026-11-25T00:00:00+00:00", str(tmp_path), "fp1", "manual")
        sample_result = {
            "converged": True,
            "observable": True,
            "iterations": 4,
            "objective": 12.5,
            "max_correction": 1e-6,
            "residual_inf": 15.0,
            "measurements": [
                {
                    "idx": 1,
                    "name": "ACNode.1.uab",
                    "device_type": "ACNode",
                    "device_idx": 1,
                    "device_name": "Bus1",
                    "metric": "uab",
                    "meas_type": "V_MAG",
                    "unit": "V",
                    "value": 420.0,
                    "estimated_value": 380.0,
                    "residual": 40.0,
                    "normalized_residual": 9.5,
                    "weight": 1.0,
                    "valid": False,
                    "is_bad": 1,
                    "is_good": 0,
                    "source": "bad_data",
                    "reason": "norm_residual_exceeded",
                },
                {
                    "idx": 2,
                    "name": "ACBreak.1.p",
                    "device_type": "ACBreak",
                    "device_idx": 1,
                    "device_name": "Brk1",
                    "metric": "i_p",
                    "meas_type": "P_FROM",
                    "unit": "kW",
                    "value": 0.0,
                    "estimated_value": 0.0,
                    "residual": 0.0,
                    "weight": 1e-8,
                    "valid": True,
                    "is_bad": 0,
                    "is_good": 0,
                    "is_pseudo": 1,
                    "pseudo_origin": "kernel_auto",
                    "source": "pseudo",
                    "reason": "observability",
                },
            ],
            "suspect_statuses": [
                {
                    "device_type": "ACBreak",
                    "device_idx": 1,
                    "device_name": "Brk1",
                    "metric": "status",
                    "scada_status": 0,
                    "model_status": 1,
                    "se_inferred_status": 1,
                    "evidence": "ia_meas=25.00 A",
                    "reason": "breaker_open_with_live_current",
                }
            ],
            "se_statistics": {"meas_count": 1, "valid_meas_count": 1, "good_meas_count": 0, "pass_rate": 0.0, "bad_data_count": 1},
        }
        with repo.result_transaction():
            repo.store_se_result(run1, sample_result)

        bad_list = repo.se_bad_current()
        assert len(bad_list) == 1
        assert bad_list[0]["ack_status"] == "unacked"

        # 确认消警并在下一次运行同点再现时保留 acked 状态
        acked = repo.se_bad_ack(bad_list[0]["id"], ack_status="acked", ack_note="现场校验中")
        assert acked["ack_status"] == "acked"

        run2 = repo.start_run(sid, "se", "2026-11-25T00:01:00+00:00", str(tmp_path), "fp2", "manual")
        with repo.result_transaction():
            repo.store_se_result(run2, sample_result)
        bad_list2 = repo.se_bad_current()
        assert bad_list2[0]["ack_status"] == "acked"

        # 一键转伪量测
        conv = repo.se_bad_convert_pseudo(bad_id=bad_list2[0]["id"])
        assert conv["policy"]["action"] == "replace_pseudo"
        assert conv["pseudo_define"]["meas_value"] == pytest.approx(380.0)
        assert conv["pseudo_define"]["source_mode"] == "bad_replace"

        # 验证可疑遥信识别函数
        suspects = detect_suspect_statuses(
            {"ACBreak": [{"idx": 1, "name": "Brk1", "status": 1}]},
            {"ACBreak": [{"idx": 1, "name": "Brk1", "ia_se": 30.0}]},
            {("ACBreak", 1, "ia"): {"meas_value": 28.0}},
            {"ACBreak": {1: {"status": 0}}},
        )
        assert len(suspects) == 1
        assert suspects[0]["reason"] == "breaker_open_with_live_current"
        abn = repo.se_bad_abnormal(category="susstat")
        assert abn["total"] == 1
    finally:
        repo.close()


def test_se_run_log_storage_query_retention_and_auto_purge(tmp_path: Path) -> None:
    """验证 SE 运行日志的级别过滤、多维检索、CSV 导出以及按天数与条数上限的定期自动删除。"""
    repo = Repository(tmp_path / "se.sqlite3")
    repo.initialize()
    try:
        now_dt = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)
        with repo._lock:
            conn = repo._connection()
            # min_level 默认 INFO，DEBUG 应被过滤
            skipped = record_se_log(conn, level="DEBUG", stage="solve", message="debug skipped", calc_time=now_dt.isoformat(timespec="milliseconds"))
            assert skipped is None
            # 插入 40 天前的 INFO（超 30 天应删除）、40 天前的 ERROR（未超 90 天应保留）、100 天前的 ERROR（应删除）和今日 INFO
            record_se_log(conn, level="INFO", stage="solve", run_id=1, message="old info", calc_time=(now_dt - timedelta(days=40)).isoformat(timespec="milliseconds"))
            record_se_log(conn, level="ERROR", stage="error", run_id=2, message="mid error keep", calc_time=(now_dt - timedelta(days=40)).isoformat(timespec="milliseconds"))
            record_se_log(conn, level="ERROR", stage="error", run_id=3, message="ancient error drop", calc_time=(now_dt - timedelta(days=100)).isoformat(timespec="milliseconds"))
            record_se_log(conn, level="INFO", stage="persist", run_id=4, message="fresh info", calc_time=now_dt.isoformat(timespec="milliseconds"))
            conn.commit()

            preview = preview_purge_se_logs(conn, now_dt=now_dt)
            assert preview["expired_count"] == 2
            assert preview["total_to_delete"] == 2

            # 首次到期自动清理应生效
            auto_res = maybe_auto_purge_se_logs(conn, now_dt=now_dt)
            conn.commit()
            assert auto_res is not None
            assert auto_res["deleted"] == 2

            # 间隔未到（1 小时后）再次调用不触发清理
            assert maybe_auto_purge_se_logs(conn, now_dt=now_dt + timedelta(hours=1)) is None

            # 超过 max_rows 裁剪测试
            for i in range(12):
                record_se_log(conn, level="INFO", stage="solve", run_id=100 + i, message=f"batch {i}", calc_time=(now_dt + timedelta(seconds=i)).isoformat(timespec="milliseconds"))
            conn.commit()
            trim_res = purge_se_logs(conn, retention_days=365, keep_error_days=365, max_rows=5, source="operator", now_dt=now_dt + timedelta(hours=10))
            conn.commit()
            assert trim_res["overflow_count"] > 0

        # 检验查询与 CSV 导出
        page = repo.se_logs_list(stage="cleanup")
        assert page["total"] >= 1
        csv_text = repo.se_logs_export_csv(stage="cleanup")
        assert "log_id,run_id,calc_time,level,stage" in csv_text
        assert "cleanup" in csv_text
    finally:
        repo.close()


def test_se_extensions_web_api_and_static_pages(tmp_path: Path) -> None:
    """验证三模块 REST API（GET/POST/PUT/DELETE）及独立 HTML 页面的 1 级/2 级导航一致性。"""
    app, repo = _make_dummy_app(tmp_path)
    try:
        # 1. 伪量测 API 闭环
        assert app.api_get("/api/se/pseudo/overview")["ok"] is True
        created = app.api_post(
            "/api/se/pseudo/meas",
            {"device_type": "ACNode", "device_name": "Bus1", "metric": "uab", "meas_value": 380.0, "meas_weight": 0.01},
        )
        assert created["ok"] is True
        pid = created["data"]["id"]
        assert app.api_put(f"/api/se/pseudo/meas/{pid}", {"device_type": "ACNode", "device_name": "Bus1", "metric": "uab", "meas_value": 385.0, "meas_weight": 0.01})["ok"] is True
        assert app.api_delete(f"/api/se/pseudo/meas/{pid}")["data"]["deleted"] is True

        # 2. 坏量测策略 API 闭环
        assert app.api_get("/api/se/bad/overview")["ok"] is True
        pol = app.api_post(
            "/api/se/bad/policies",
            {"device_type": "ACNode", "device_name": "Bus1", "metric": "uab", "action": "suppress", "enabled": 1},
        )
        assert pol["ok"] is True
        pol_id = pol["data"]["id"]
        assert app.api_delete(f"/api/se/bad/policies/{pol_id}")["data"]["deleted"] is True

        # 3. 运行日志 API 闭环
        assert app.api_get("/api/se/logs/summary")["ok"] is True
        pol_upd = app.api_post("/api/se/logs/policy", {"retention_days": 15, "keep_error_days": 60, "max_rows": 20000, "cleanup_interval_hours": 12, "min_level": "INFO", "enabled": 1})
        assert pol_upd["ok"] is True
        assert pol_upd["data"]["retention_days"] == 15
        dry = app.api_post("/api/se/logs/purge", {"dry_run": True})
        assert dry["ok"] is True

        # 4. 验证三套新页面静态路径与 1 级/2 级导航结构
        for html_name in ("se-main.html", "se-pseudo.html", "se-bad.html", "se-logs.html"):
            p = app.static_path(f"/{html_name}")
            assert p is not None and p.is_file()
            text = p.read_text(encoding="utf-8")
            assert 'class="nav-sub"' in text
            assert "/se-pseudo.html" in text and "/se-bad.html" in text and "/se-logs.html" in text
        # 非 SE 页面应保持 1 级导航清爽（无 nav-sub）
        lf_html = app.static_path("/analysis/lf.html").read_text(encoding="utf-8")
        assert 'class="nav-sub"' not in lf_html
        assert 'data-route="se-root"' in lf_html
    finally:
        repo.close()
