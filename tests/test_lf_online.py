"""在线潮流分析（LF）全栈单元测试：算法参数、SE→LF 基态注入、方式调整、结果入库与历史回放、REST API 及前端页面。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from pas.db import Repository, RepositoryHub
from pas.lf_online import (
    DEFAULT_LF_PARAMS,
    build_se_base_overrides,
    lf_parameter_file,
    merge_study_overrides,
    parse_lf_para_file,
)
from pas.web import PasWebApp


def _write_rtdb_model(path: Path, tables: dict[str, tuple[list[str], list[tuple]]]) -> Path:
    """构造最小 RTDB 格式 devices.sqlite3（仅用于单测，绝不修改外部实库）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE rtdb_schema_tables(table_name TEXT PRIMARY KEY, ordinal INTEGER NOT NULL);
            CREATE TABLE rtdb_schema_columns(table_name TEXT NOT NULL, ordinal INTEGER NOT NULL, eng_name TEXT NOT NULL);
            """
        )
        for ordinal, (table_name, (fields, rows)) in enumerate(tables.items()):
            conn.execute("INSERT INTO rtdb_schema_tables VALUES (?, ?)", (table_name, ordinal))
            for col_idx, field in enumerate(fields):
                conn.execute("INSERT INTO rtdb_schema_columns VALUES (?, ?, ?)", (table_name, col_idx, field))
            col_defs = ", ".join(f'"c{i}"' for i in range(len(fields)))
            conn.execute(f'CREATE TABLE "rtdb_data_{table_name}" (_pos INTEGER PRIMARY KEY, {col_defs})')
            placeholders = ", ".join("?" for _ in range(len(fields) + 1))
            for pos, row in enumerate(rows, 1):
                conn.execute(f'INSERT INTO "rtdb_data_{table_name}" VALUES ({placeholders})', (pos, *row))
        conn.commit()
    finally:
        conn.close()
    return path


def _sample_lf_result(
    *,
    source_se_run_id: int = 10,
    total_gen_kw: float = 120.0,
    total_load_kw: float = 115.0,
    loss_kw: float = 5.0,
    max_loading_pct: float = 88.5,
    bus_v_pu: float = 0.91,
    applied_overrides: int = 1,
) -> dict:
    """构造结构完整的合成 LF 结果字典（对齐 kernels._enrich_lf_result 输出）。"""
    is_overload = 1 if max_loading_pct > 100.0 else 0
    is_v_low = 1 if bus_v_pu < 0.93 else 0
    return {
        "converged": True,
        "iterations": 5,
        "norm_f": 1.2e-9,
        "summary": {
            "converged": True,
            "iterations": 5,
            "source_se_run_id": source_se_run_id,
        },
        "lf_statistics": {
            "source_se_run_id": source_se_run_id,
            "mode": "online",
            "converged": True,
            "iterations": 5,
            "norm_f": 1.2e-9,
            "ac_converged": 1,
            "ac_iterations": 5,
            "ac_norm_f": 1.2e-9,
            "dc_converged": 1,
            "dc_iterations": 3,
            "dc_norm_f": 2.0e-10,
            "ac_gen_p": total_gen_kw,
            "ac_gen_q": 18.0,
            "ac_load_p": 80.0,
            "ac_load_q": 14.0,
            "ac_loss_p": 3.0,
            "dc_gen_p": 0.0,
            "dc_load_p": 35.0,
            "dc_loss_p": 2.0,
            "total_gen_p": total_gen_kw,
            "total_load_p": total_load_kw,
            "total_loss_p": loss_kw,
            "loss_rate": round(loss_kw / total_gen_kw * 100.0, 3),
            "min_v_pu": bus_v_pu,
            "max_v_pu": 1.01,
            "min_v_bus": "交流母线2",
            "max_v_bus": "交流母线1",
            "max_loading_pct": max_loading_pct,
            "max_loading_dev": "交流线路1",
            "v_violation_count": is_v_low,
            "overload_count": is_overload,
            "device_count": 7,
            "override_count": applied_overrides,
            "u_unit": "V",
            "p_unit": "kW",
            "i_unit": "A",
        },
        "lf_buses": [
            {
                "domain": "AC",
                "device_type": "ACNode",
                "device_idx": 1,
                "device_name": "交流母线1",
                "vbase": 380.0,
                "v_pu": 1.01,
                "v_eng": 383.8,
                "angle_deg": 0.0,
                "v_se": 383.0,
                "v_diff": 0.8,
                "v_status": "normal",
            },
            {
                "domain": "AC",
                "device_type": "ACNode",
                "device_idx": 2,
                "device_name": "交流母线2",
                "vbase": 380.0,
                "v_pu": bus_v_pu,
                "v_eng": round(380.0 * bus_v_pu, 3),
                "angle_deg": -2.4,
                "v_se": 350.0,
                "v_diff": round(380.0 * bus_v_pu - 350.0, 3),
                "v_status": "low" if is_v_low else "normal",
            },
            {
                "domain": "DC",
                "device_type": "DCNode",
                "device_idx": 1,
                "device_name": "直流母线1",
                "vbase": 750.0,
                "v_pu": 1.0,
                "v_eng": 750.0,
                "angle_deg": 0.0,
                "v_se": 749.5,
                "v_diff": 0.5,
                "v_status": "normal",
            },
        ],
        "lf_branches": [
            {
                "domain": "AC",
                "device_type": "ACBranch",
                "device_idx": 1,
                "device_name": "交流线路1",
                "node_from": 1,
                "node_to": 2,
                "p_from": 83.0,
                "q_from": 15.0,
                "i_from": 128.0,
                "v_from": 383.8,
                "p_to": -80.0,
                "q_to": -14.0,
                "i_to": 126.5,
                "v_to": round(380.0 * bus_v_pu, 3),
                "p_loss": 3.0,
                "rated_capacity": 144.6,
                "loading_pct": max_loading_pct,
                "overload": is_overload,
                "p_se": 82.0,
                "p_diff": 1.0,
            },
            {
                "domain": "HYBRID",
                "device_type": "DCACConverter",
                "device_idx": 1,
                "device_name": "换流器1",
                "node_from": 1,
                "node_to": 1,
                "p_from": -35.0,
                "q_from": 0.0,
                "i_from": 46.7,
                "v_from": 750.0,
                "p_to": 37.0,
                "q_to": 3.0,
                "i_to": 56.2,
                "v_to": 383.8,
                "p_loss": 2.0,
                "rated_capacity": 200.0,
                "loading_pct": 28.1,
                "overload": 0,
                "p_se": -34.5,
                "p_diff": -0.5,
            },
        ],
        "lf_units": [
            {
                "domain": "AC",
                "device_type": "ACGenerator",
                "device_idx": 1,
                "device_name": "平衡机组1",
                "node_idx": 1,
                "control_type": "Slack",
                "p_lf": total_gen_kw,
                "q_lf": 18.0,
                "v_lf": 383.8,
                "i_lf": 182.0,
                "p_se": 119.2,
                "p_diff": round(total_gen_kw - 119.2, 3),
                "rated_capacity": 200.0,
                "loading_pct": round(total_gen_kw / 200.0 * 100.0, 2),
                "overload": 0,
            },
            {
                "domain": "DC",
                "device_type": "DCLoad",
                "device_idx": 1,
                "device_name": "直流负荷1",
                "node_idx": 1,
                "control_type": "LOAD",
                "p_lf": 35.0,
                "q_lf": 0.0,
                "v_lf": 750.0,
                "i_lf": 46.7,
                "p_se": 35.0,
                "p_diff": 0.0,
                "rated_capacity": 100.0,
                "loading_pct": 35.0,
                "overload": 0,
            },
        ],
        "devices": [
            {"device_type": "ACBranch", "idx": 1, "name": "交流线路1", "p": 83.0},
        ],
    }


def _make_lf_app(tmp_path: Path) -> tuple[PasWebApp, RepositoryHub, Path]:
    """构建带 se/lf 独立库的 PasWebApp 测试实例与配套 SVG/模型文件。"""
    model_db = _write_rtdb_model(
        tmp_path / "model" / "devices.sqlite3",
        {
            "Model": (["path", "name", "p_base", "u_unit", "p_unit", "i_unit"], [("t", "demo", 100.0, "V", "kW", "A")]),
            "ACNode": (["idx", "name", "vbase", "run_stat"], [(1, "交流母线1", 380.0, 1), (2, "交流母线2", 380.0, 1)]),
            "DCNode": (["idx", "name", "vbase", "run_stat"], [(1, "直流母线1", 750.0, 1)]),
            "ACBranch": (["idx", "name", "i_node", "j_node", "run_stat", "i_max"], [(1, "交流线路1", 1, 2, 1, 144.6)]),
            "ACGenerator": (
                ["idx", "name", "node", "control_type", "p_set", "q_set", "v_set", "run_stat"],
                [(1, "平衡机组1", 1, "Slack", 100.0, 10.0, 380.0, 1)],
            ),
            "ACLoad": (["idx", "name", "node", "pbase", "qbase", "p_set", "run_stat"], [(1, "交流负荷1", 2, 80.0, 14.0, 80.0, 1)]),
            "DCLoad": (["idx", "name", "node", "pbase", "run_stat"], [(1, "直流负荷1", 1, 35.0, 1)]),
            "DCACConverter": (["idx", "name", "i_node", "j_node", "run_stat"], [(1, "换流器1", 1, 1, 1)]),
        },
    )
    svg_file = tmp_path / "model" / "demo.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<use id="ACBranch-1" dev-id="ACBranch-1" idx="1" name="交流线路1"/>'
        '<use id="ACNode-2" dev-id="ACNode-2" idx="2" name="交流母线2"/>'
        "</svg>",
        encoding="utf-8",
    )
    para_file = tmp_path / "lf.para"
    para_file.write_text(
        "<PowerFlowParameter>\n@ name value\n# tol 1e-7\n# max_iter 80\n# min_voltage 0.02\n# divergence_threshold 1e5\n</PowerFlowParameter>\n",
        encoding="utf-8",
    )

    control_repo = Repository(tmp_path / "pas.sqlite3")
    se_repo = Repository(tmp_path / "se.sqlite3")
    lf_repo = Repository(tmp_path / "lf.sqlite3")
    hub = RepositoryHub({"se": se_repo, "lf": lf_repo}, control_repo)
    hub.initialize()

    cfg = SimpleNamespace(
        kernel_root=tmp_path,
        database=tmp_path / "pas.sqlite3",
        databases={"se": tmp_path / "se.sqlite3", "lf": tmp_path / "lf.sqlite3"},
        tasks={
            "se": SimpleNamespace(
                name="se",
                enabled=True,
                period_seconds=60,
                model_file=model_db,
                measurement_file=None,
                parameter_file=None,
                limit_file=None,
            ),
            "lf": SimpleNamespace(
                name="lf",
                enabled=True,
                period_seconds=60,
                model_file=model_db,
                parameter_file=para_file,
            ),
            "ca": SimpleNamespace(name="ca", enabled=False, period_seconds=300, model_file=model_db, limit_file=None, scan_n1=False),
        },
        workspace_root=str(tmp_path),
        runtime="realtime",
        scenario="demo",
        workspace_directory=str(tmp_path),
    )
    sched = SimpleNamespace(status=lambda: {"active_tasks": [], "pending_tasks": [], "jobs": [], "schedules": []})
    web_root = Path(__file__).resolve().parents[1] / "web"
    return PasWebApp(cfg, hub, sched, web_root), hub, para_file


def test_lf_params_parse_save_validate_reset_and_render(tmp_path: Path) -> None:
    """验证 lf.para 解析、参数落库校验、越界拒绝、重置与临时 lf.para 文件渲染。"""
    para_file = tmp_path / "lf.para"
    para_file.write_text(
        "<PowerFlowParameter>\n@ name value\n# tol 1e-6\n# max_iter 65\n# min_voltage 0.02\n# divergence_threshold 50000\n</PowerFlowParameter>\n",
        encoding="utf-8",
    )
    parsed = parse_lf_para_file(para_file)
    assert parsed["tol"] == pytest.approx(1e-6)
    assert parsed["max_iter"] == 65
    assert parsed["min_voltage"] == pytest.approx(0.02)
    assert parsed["use_se_base"] == DEFAULT_LF_PARAMS["use_se_base"]

    repo = Repository(tmp_path / "lf.sqlite3")
    repo.initialize()
    try:
        initial = repo.lf_params_get(para_file, do_cycle=120)
        assert initial["max_iter"] == 65
        assert initial["do_cycle"] == 120

        saved = repo.lf_params_save(
            {
                "tol": 1e-9,
                "max_iter": 100,
                "use_se_base": 1,
                "cascade_ca": 1,
                "v_min_pu": 0.94,
                "v_max_pu": 1.06,
                "overload_warn_pct": 75.0,
                "overload_limit_pct": 95.0,
                "do_cycle": 30,
            },
            para_file,
        )
        assert saved["tol"] == pytest.approx(1e-9)
        assert saved["max_iter"] == 100
        assert saved["cascade_ca"] == 1
        assert saved["v_min_pu"] == pytest.approx(0.94)

        # 非法越界与逻辑冲突必须抛 ValueError
        with pytest.raises(ValueError):
            repo.lf_params_save({"v_min_pu": 1.08, "v_max_pu": 1.05}, para_file)
        with pytest.raises(ValueError):
            repo.lf_params_save({"overload_warn_pct": 110.0, "overload_limit_pct": 100.0}, para_file)
        with pytest.raises(ValueError):
            repo.lf_params_save({"max_iter": 0}, para_file)

        # 临时 lf.para 渲染
        with lf_parameter_file(para_file, saved) as (tmp_para, merged):
            assert tmp_para.is_file()
            text = tmp_para.read_text(encoding="utf-8")
            assert "# max_iter             100" in text
            assert merged["tol"] == pytest.approx(1e-9)

        # 重置回 lf.para 默认值并产生审计日志
        reset = repo.lf_params_reset(para_file)
        assert reset["max_iter"] == 65
        assert reset["tol"] == pytest.approx(1e-6)
        logs = repo.lf_logs_list(stage="param_change")
        assert logs["total"] >= 2
    finally:
        repo.close()


def test_se_to_lf_base_overrides_and_study_merge() -> None:
    """验证 SE→LF 基态注入器按控制类型生成覆盖、支持直流零值兜底且叠加方式调整优先级正确。"""
    model_tables = {
        "ACNode": {"rows": [{"idx": 1, "name": "AC1"}, {"idx": 2, "name": "AC2"}]},
        "DCNode": {"rows": [{"idx": 1, "name": "DC1"}]},
        "ACGenerator": {
            "rows": [
                {"idx": 1, "name": "G_PQ", "node": 2, "control_type": "PQ", "run_stat": 1},
                {"idx": 2, "name": "G_PV", "node": 2, "control_type": "PV", "run_stat": 1},
                {"idx": 3, "name": "G_SLACK", "node": 1, "control_type": "Slack", "run_stat": 1},
            ]
        },
        "ACLoad": {"rows": [{"idx": 1, "name": "L_AC", "node": 2, "p_set": 50.0, "run_stat": 1}]},
        "DCGenerator": {
            "rows": [
                {"idx": 1, "name": "DCG_P", "node": 1, "control_type": "P", "run_stat": 1},
                {"idx": 2, "name": "DCG_V", "node": 1, "control_type": "V", "run_stat": 1},
            ]
        },
        "DCLoad": {"rows": [{"idx": 1, "name": "L_DC", "node": 1, "run_stat": 1}]},
        "ACBreak": {"rows": [{"idx": 1, "name": "BRK1", "status": 1, "run_stat": 1}]},
    }
    se_snap = {
        "latest": {"run_id": 42, "converged": 1, "calc_time": "2026-11-26T01:00:00Z"},
        "devices_by_type": {
            "ACNode": [{"idx": 1, "uab_se": 382.0}, {"idx": 2, "uab_se": 376.5}],
            "DCNode": [{"idx": 1, "u_se": 748.0}],
            "ACGenerator": [
                {"idx": 1, "p_se": 45.2, "q_se": 8.1},
                {"idx": 2, "p_se": 60.0, "uab_se": 379.0},
                {"idx": 3, "p_se": 120.0, "uab_se": 382.0},
            ],
            "ACLoad": [{"idx": 1, "p_se": 92.4, "q_se": 12.3}],
            "DCGenerator": [
                {"idx": 1, "p_se": 0.0, "p_meas": 32.5},  # SE 直流退化 0 -> 回退实测 32.5
                {"idx": 2, "u_se": 751.0},
            ],
            "DCLoad": [{"idx": 1, "p_se": 0.0, "p_meas": 87.53}],  # 直流负荷零值回退实测
        },
    }
    overrides, meta = build_se_base_overrides(
        se_snap,
        model_tables,
        breaker_status={("ACBreak", 1): 0},
        pseudo_stats=[{"device_type": "ACBreak", "dev_name": "BRK1", "stat_value": 1, "stat_useflag": 1}],
    )
    assert meta["used_se_base"] is True
    assert meta["source_se_run_id"] == 42
    # 人工伪状态优先级高于 SCADA 分合位
    assert overrides["ACBreak"][1]["status"] == 1
    # PQ/PV/Slack 控制量区分准确（Slack 不应覆盖 p_set）
    assert overrides["ACGenerator"][1] == {"p_set": 45.2, "q_set": 8.1}
    assert overrides["ACGenerator"][2] == {"p_set": 60.0, "v_set": 379.0}
    assert overrides["ACGenerator"][3] == {"v_set": 382.0}
    assert overrides["ACLoad"][1]["pbase"] == 92.4
    assert overrides["DCGenerator"][1]["p_set"] == 32.5
    assert overrides["DCGenerator"][2]["v_set"] == 751.0
    assert overrides["DCLoad"][1]["pbase"] == 87.53

    # 方式调整叠加（启用生效、停用忽略、非法字段忽略）
    merged, count = merge_study_overrides(
        overrides,
        [
            {"device_type": "ACLoad", "device_name": "L_AC", "field": "pbase", "value": 110.0, "enabled": 1},
            {"device_type": "ACBreak", "device_idx": 1, "field": "status", "value": 0, "enabled": 1},
            {"device_type": "ACLoad", "device_idx": 1, "field": "qbase", "value": 99.0, "enabled": 0},
            {"device_type": "ACLoad", "device_idx": 1, "field": "invalid_field", "value": 1.0, "enabled": 1},
        ],
        model_tables,
    )
    assert count == 2
    assert merged["ACLoad"][1]["pbase"] == 110.0
    assert merged["ACLoad"][1]["qbase"] == 12.3
    assert merged["ACBreak"][1]["status"] == 0
    # 原 overrides 字典不被就地污染
    assert overrides["ACLoad"][1]["pbase"] == 92.4


def _record_lf_run(repo: Repository, result: dict, source: str = "manual") -> int:
    """在测试库中写入一次完整的 LF 运行记录及结果。"""
    with repo._lock:
        conn = repo._connection()
        conn.execute(
            """INSERT OR IGNORE INTO schedule(
                   schedule_id, task_type, enabled, period_seconds, next_due_at, config_json, created_at, updated_at
               ) VALUES (1, 'lf', 1, 60, '2026-11-26T00:01:00Z', '{}', '2026-11-26T00:00:00Z', '2026-11-26T00:00:00Z')"""
        )
        conn.commit()
    run_id = repo.start_run(1, "lf", "2026-11-26T00:00:00Z", "test-kernel", "fp-demo", execution_source=source)
    repo.store_result("lf", run_id, result, calc_time="2026-11-26T00:00:01Z", elapsed_seconds=0.12, kernel_seconds=0.05)
    repo.finish_run(run_id, "succeeded", "2026-11-26T00:00:01Z", 0.12, 0)
    return run_id


def test_lf_repository_storage_history_replay_overrides_and_logs(tmp_path: Path) -> None:
    """验证 LF 扩展表入库、多断面历史回放、筛选分页、CSV 导出、方式调整与审计日志清理。"""
    repo = Repository(tmp_path / "lf.sqlite3")
    repo.initialize()
    try:
        r1 = _record_lf_run(
            repo,
            _sample_lf_result(source_se_run_id=11, total_gen_kw=120.0, max_loading_pct=88.5, bus_v_pu=0.91),
            source="manual",
        )
        r2 = _record_lf_run(
            repo,
            _sample_lf_result(source_se_run_id=12, total_gen_kw=150.0, max_loading_pct=106.0, bus_v_pu=0.95),
            source="schedule",
        )

        runs = repo.lf_converged_runs(limit=10)
        assert [x["run_id"] for x in runs] == [r2, r1]
        assert runs[0]["source_se_run_id"] == 12

        home = repo.lf_home_summary()
        assert home["latest"]["run_id"] == r2
        assert home["latest"]["overload_count"] == 1
        assert home["latest"]["v_violation_count"] == 0
        assert len(home["trend_series"]) == 2
        assert len(home["top_loading"]) >= 1

        # 最新断面 vs 历史断面 r1 回放
        latest_buses = repo.lf_results_browse(kind="buses", only_abnormal=True)
        assert latest_buses["meta"]["total"] == 0
        hist_buses = repo.lf_results_browse(kind="buses", only_abnormal=True, run_id=r1)
        assert hist_buses["meta"]["total"] == 1
        assert hist_buses["rows"][0]["device_name"] == "交流母线2"
        assert hist_buses["rows"][0]["v_status"] == "low"

        # 支路筛选与 CSV 导出
        branches = repo.lf_results_browse(kind="branches", domain="AC", only_abnormal=True)
        assert branches["meta"]["total"] == 1
        assert branches["rows"][0]["overload"] == 1
        csv_text = repo.lf_results_export_csv(kind="branches", run_id=r2).decode("utf-8-sig")
        assert "交流线路1" in csv_text
        assert "106.0" in csv_text

        # 方式调整 CRUD & 清空
        ov = repo.lf_override_save(
            {"scheme_name": "summer", "device_type": "ACLoad", "device_idx": 1, "device_name": "交流负荷1", "field": "pbase", "value": 95.0, "note": "迎峰度夏"}
        )
        assert ov["id"] > 0
        ov_upd = repo.lf_override_save({**ov, "value": 99.0, "enabled": 0}, override_id=ov["id"])
        assert ov_upd["value"] == pytest.approx(99.0)
        assert ov_upd["enabled"] == 0
        assert len(repo.lf_overrides_list(scheme_name="summer")) == 1
        assert repo.lf_override_delete(ov["id"]) is True

        repo.lf_override_save({"device_type": "ACBreak", "device_idx": 1, "device_name": "BRK1", "field": "status", "value": 0})
        assert repo.lf_overrides_clear() == 1

        # 日志记录、策略更新、预览与清理
        repo.record_lf_run_log(level="INFO", stage="solve", source="manual", run_id=r2, message="潮流收敛", elapsed_ms=12.5)
        summary = repo.lf_logs_summary()
        assert summary["total"] >= 1
        pol = repo.lf_logs_policy_update({"auto_enabled": 1, "retention_days": 14, "keep_error_days": 30, "max_rows": 5000})
        assert pol["retention_days"] == 14
        preview = repo.lf_logs_purge(dry_run=True, max_rows=1)
        assert preview["deleted"] == 0
        assert preview["total_to_delete"] >= 1
        csv_logs = repo.lf_logs_export_csv()
        if isinstance(csv_logs, bytes):
            csv_logs = csv_logs.decode("utf-8-sig")
        assert "潮流收敛" in csv_logs
    finally:
        repo.close()


def test_lf_web_apis_and_pages(tmp_path: Path) -> None:
    """验证全部 /api/lf/* REST API（GET/POST/PUT/DELETE）、接线图数值与 5 套前端页面资产。"""
    app, hub, _para = _make_lf_app(tmp_path)
    try:
        lf_repo = hub.for_task("lf")
        r1 = _record_lf_run(
            lf_repo,
            _sample_lf_result(source_se_run_id=5, max_loading_pct=108.0, bus_v_pu=0.90),
            source="manual",
        )

        # GET 接口全覆盖
        home = app.api_get("/api/lf/home")
        assert home["ok"] is True
        assert home["data"]["latest"]["source_se_run_id"] == 5

        runs = app.api_get("/api/lf/runs/converged?limit=10")
        assert runs["ok"] is True and len(runs["data"]) == 1

        topo = app.api_get(f"/api/lf/topology-values?run_id={r1}")
        assert topo["ok"] is True
        assert topo["data"]["svg_available"] is True
        assert "ACBranch-1" in topo["data"]["alert_dev_ids"]
        assert "ACNode-2" in topo["data"]["alert_dev_ids"]
        assert "DCACConverter-1" in topo["data"]["devices"]

        res_br = app.api_get("/api/lf/results?kind=branches&only_abnormal=1")
        assert res_br["ok"] is True and res_br["data"]["meta"]["total"] == 1

        res_unit = app.api_get("/api/lf/results?kind=units&domain=DC")
        assert res_unit["ok"] is True and res_unit["data"]["meta"]["total"] == 1

        hist = app.api_get("/api/lf/history/stats?limit=10")
        assert hist["ok"] is True and len(hist["data"]) == 1

        cat = app.api_get("/api/lf/model-catalog")
        assert cat["ok"] is True and "ACLoad" in cat["data"]["override_fields"]

        # POST / PUT / DELETE 写接口全覆盖
        p_upd = app.api_post("/api/lf/params", {"max_iter": 77, "cascade_ca": 1})
        assert p_upd["ok"] is True and p_upd["data"]["max_iter"] == 77

        p_rst = app.api_post("/api/lf/params/reset", {})
        assert p_rst["ok"] is True and p_rst["data"]["max_iter"] == 80

        ov_add = app.api_post(
            "/api/lf/overrides",
            {"device_type": "ACLoad", "device_idx": 1, "device_name": "交流负荷1", "field": "pbase", "value": 85.0},
        )
        assert ov_add["ok"] is True
        oid = ov_add["data"]["id"]

        ov_put = app.api_put(f"/api/lf/overrides/{oid}", {**ov_add["data"], "value": 90.0})
        assert ov_put["ok"] is True and ov_put["data"]["value"] == pytest.approx(90.0)

        ov_del = app.api_delete(f"/api/lf/overrides/{oid}")
        assert ov_del["ok"] is True and ov_del["data"]["deleted"] is True

        pol = app.api_post("/api/lf/logs/policy", {"retention_days": 21})
        assert pol["ok"] is True and pol["data"]["retention_days"] == 21

        purge = app.api_post("/api/lf/logs/purge", {"dry_run": True})
        assert purge["ok"] is True

        # 静态页面资产与全站导航入口检查
        web_root = Path(__file__).resolve().parents[1] / "web"
        assert (web_root / "assets" / "lf-app.js").is_file()
        for page, dp in (
            ("lf-main.html", "/lf-main"),
            ("lf-flow.html", "/lf-flow"),
            ("lf-results.html", "/lf-results"),
            ("lf-params.html", "/lf-params"),
            ("lf-logs.html", "/lf-logs"),
        ):
            html = (web_root / page).read_text(encoding="utf-8")
            assert f'data-page="{dp}"' in html
            assert "/assets/lf-app.js" in html
            assert "/assets/se-dashboard.css" in html
        for nav_page in ("overview.html", "se-main.html", "runs.html", "settings.html"):
            assert 'href="/lf-main.html"' in (web_root / nav_page).read_text(encoding="utf-8")
    finally:
        hub.close()
