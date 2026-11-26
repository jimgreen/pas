"""在线静态安全分析（CA）与 SE→LF→CA 级联联动全栈单元测试。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from pas.ca_online import (
    DEFAULT_CA_PARAMS,
    compute_security_score_and_level,
    evaluate_lf_state_risks,
)
from pas.db import Repository, RepositoryHub
from pas.scheduler import Scheduler
from pas.web import PasWebApp


def _write_rtdb_model(path: Path, tables: dict[str, tuple[list[str], list[tuple]]]) -> Path:
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


def _record_run(repo: Repository, task: str, result: dict, source: str = "manual") -> int:
    with repo._lock:
        conn = repo._connection()
        sid = {"se": 1, "lf": 2, "ca": 3}[task]
        conn.execute(
            """INSERT OR IGNORE INTO schedule(
                   schedule_id, task_type, enabled, period_seconds, next_due_at, config_json, created_at, updated_at
               ) VALUES (?, ?, 1, 60, '2026-11-26T00:01:00Z', '{}', '2026-11-26T00:00:00Z', '2026-11-26T00:00:00Z')""",
            (sid, task),
        )
        conn.commit()
    run_id = repo.start_run(sid, task, "2026-11-26T00:00:00Z", "test-kernel", f"fp-{task}", execution_source=source)
    repo.store_result(task, run_id, result, calc_time="2026-11-26T00:00:01Z", elapsed_seconds=0.25, kernel_seconds=0.1)
    repo.finish_run(run_id, "succeeded", "2026-11-26T00:00:01Z", 0.25, 0)
    return run_id


def _sample_ca_result(*, source_lf_run_id: int = 21, source_se_run_id: int = 11, critical: int = 1, high: int = 1) -> dict:
    score, level = compute_security_score_and_level(
        base_converged=True,
        critical_count=critical,
        high_count=high,
        medium_count=0,
        low_count=0,
    )
    risks_detail = []
    if high:
        risks_detail.append(
            {
                "contingency_name": "N-0 基态",
                "category": "N-0",
                "device_type": "ACNode",
                "device_idx": 2,
                "device_name": "交流母线2",
                "risk_category": "voltage_low",
                "severity": "high",
                "metric": "v",
                "actual_value": 338.2,
                "limit_value": 353.4,
                "violation_pct": 4.3,
                "unit": "V",
                "detail": "电压 338.2 V (0.8900 pu) 低于下限 353.4 V",
            }
        )
    if critical:
        risks_detail.append(
            {
                "contingency_name": "N-1:换流器1",
                "category": "N-1",
                "device_type": "DCACConverter",
                "device_idx": 1,
                "device_name": "换流器1",
                "risk_category": "load_loss",
                "severity": "critical",
                "metric": "load_loss",
                "actual_value": 42.5,
                "limit_value": 0.5,
                "violation_pct": 36.9,
                "unit": "kW",
                "detail": "故障后损失负荷 42.50 kW（占基态 36.9%）",
            }
        )
    return {
        "risk_level": level,
        "n0_risk_count": high,
        "n1_scan_count": 2,
        "n1_risk_count": critical,
        "risks": [
            {
                "contingency": r["category"],
                "risk_source": r["contingency_name"],
                "risk_dist": f"{r['device_type']}.{r['device_name']}.{r['metric']}",
                "risk_type": r["risk_category"],
                "risk_value": r["actual_value"],
                "risk_info": r["detail"],
            }
            for r in risks_detail
        ],
        "ca_statistics": {
            "source_lf_run_id": source_lf_run_id,
            "source_se_run_id": source_se_run_id,
            "base_converged": 1,
            "risk_level": level,
            "security_score": score,
            "n0_risk_count": high,
            "n1_total_count": 2,
            "n1_converged_count": 2,
            "n1_diverged_count": 0,
            "n1_risk_count": critical,
            "nk_total_count": 0,
            "nk_risk_count": 0,
            "critical_count": critical,
            "high_count": high,
            "medium_count": 0,
            "low_count": 0,
            "max_loading_pct": 91.2,
            "max_loading_dev": "交流线路1",
            "min_v_pu": 0.89,
            "min_v_bus": "交流母线2",
            "max_v_pu": 1.01,
            "max_v_bus": "交流母线1",
            "max_load_loss_kw": 42.5 if critical else 0.0,
            "worst_contingency": "N-1:换流器1" if critical else "N-0 基态",
            "u_unit": "V",
            "p_unit": "kW",
            "i_unit": "A",
        },
        "ca_contingencies": [
            {
                "contingency_name": "N-1:换流器1",
                "category": "N-1",
                "target_desc": "DCACConverter:换流器1",
                "converged": 1,
                "iterations": 5,
                "elapsed_ms": 18.4,
                "load_loss_kw": 42.5 if critical else 0.0,
                "max_loading_pct": 91.2,
                "max_loading_dev": "交流线路1",
                "min_v_pu": 0.90,
                "min_v_bus": "交流母线2",
                "max_v_pu": 1.01,
                "max_v_bus": "交流母线1",
                "risk_count": critical,
                "severity": "critical" if critical else "normal",
                "failure_reason": "",
            },
            {
                "contingency_name": "N-1:交流线路1",
                "category": "N-1",
                "target_desc": "ACBranch:交流线路1",
                "converged": 1,
                "iterations": 4,
                "elapsed_ms": 14.2,
                "load_loss_kw": 0.0,
                "max_loading_pct": 48.0,
                "max_loading_dev": "换流器1",
                "min_v_pu": 0.98,
                "min_v_bus": "交流母线2",
                "max_v_pu": 1.00,
                "max_v_bus": "交流母线1",
                "risk_count": 0,
                "severity": "normal",
                "failure_reason": "",
            },
        ],
        "ca_risk_details": risks_detail,
        "summary": {"risk_level": level, "security_score": score},
    }


def _make_full_app(tmp_path: Path):
    model_db = _write_rtdb_model(
        tmp_path / "model" / "devices.sqlite3",
        {
            "Model": (["path", "name", "p_base", "u_unit", "p_unit", "i_unit"], [("t", "demo", 100.0, "V", "kW", "A")]),
            "ACNode": (["idx", "name", "vbase", "run_stat"], [(1, "交流母线1", 380.0, 1), (2, "交流母线2", 380.0, 1)]),
            "ACRealBs": (["idx", "name", "node"], [(1, "交流实母线2", 2)]),
            "ACBranch": (["idx", "name", "i_node", "j_node", "run_stat", "i_max"], [(1, "交流线路1", 1, 2, 1, 144.6)]),
            "DCACConverter": (["idx", "name", "dc_node", "ac_node", "run_stat"], [(1, "换流器1", 1, 1, 1)]),
        },
    )
    svg_file = tmp_path / "model" / "demo.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<use id="ACNode-2" dev-id="ACNode-2"/><use id="DCACConverter-1" dev-id="DCACConverter-1"/>'
        "</svg>",
        encoding="utf-8",
    )

    control_repo = Repository(tmp_path / "pas.sqlite3")
    se_repo = Repository(tmp_path / "se.sqlite3")
    lf_repo = Repository(tmp_path / "lf.sqlite3")
    ca_repo = Repository(tmp_path / "ca.sqlite3")
    hub = RepositoryHub({"se": se_repo, "lf": lf_repo, "ca": ca_repo}, control_repo)
    hub.initialize()

    cfg = SimpleNamespace(
        kernel_root=tmp_path,
        database=tmp_path / "pas.sqlite3",
        databases={"se": tmp_path / "se.sqlite3", "lf": tmp_path / "lf.sqlite3", "ca": tmp_path / "ca.sqlite3"},
        tick_seconds=1.0,
        retry_seconds=10.0,
        tasks={
            "se": SimpleNamespace(name="se", enabled=True, period_seconds=60, model_file=model_db, measurement_file=None, parameter_file=None, limit_file=None),
            "lf": SimpleNamespace(name="lf", enabled=True, period_seconds=60, model_file=model_db, parameter_file=None),
            "ca": SimpleNamespace(name="ca", enabled=True, period_seconds=300, model_file=model_db, limit_file=tmp_path / "ca.sqlite3", scan_n1=True),
        },
        workspace_root=str(tmp_path),
        runtime="realtime",
        scenario="demo",
        workspace_directory=str(tmp_path),
    )

    call_order: list[str] = []

    def _fake_se(**_kw):
        call_order.append("se")
        return {
            "converged": True,
            "observable": True,
            "iterations": 3,
            "objective": 0.01,
            "residual_inf": 0.002,
            "bad_data_count": 0,
            "se_statistics": {"converged": 1, "observable": 1, "meas_count": 10, "pass_rate": 1.0, "bad_data_count": 0, "total_residual": 0.01, "iterations": 3},
            "measurements": [],
            "summary": {"converged": True},
        }

    def _fake_lf(**_kw):
        call_order.append("lf")
        se_lat = se_repo.se_topology_snapshot().get("latest")
        return {
            "converged": True,
            "iterations": 4,
            "norm_f": 1e-10,
            "lf_statistics": {
                "source_se_run_id": se_lat["run_id"] if se_lat else None,
                "converged": True,
                "iterations": 4,
                "total_gen_p": 120.0,
                "total_load_p": 115.0,
                "total_loss_p": 5.0,
                "loss_rate": 4.17,
                "max_loading_pct": 55.0,
                "v_violation_count": 0,
                "overload_count": 0,
            },
            "lf_buses": [],
            "lf_branches": [],
            "lf_units": [],
            "devices": [],
            "summary": {"converged": True},
        }

    def _fake_ca(**_kw):
        call_order.append("ca")
        lf_lat = lf_repo.lf_snapshot().get("latest")
        se_id = lf_lat.get("source_se_run_id") if lf_lat else None
        return _sample_ca_result(source_lf_run_id=lf_lat["run_id"] if lf_lat else 0, source_se_run_id=se_id or 0)

    sched = Scheduler(cfg, hub, {"se": _fake_se, "lf": _fake_lf, "ca": _fake_ca}, {"se": se_repo, "lf": lf_repo, "ca": ca_repo})
    web_root = Path(__file__).resolve().parents[1] / "web"
    return PasWebApp(cfg, hub, sched, web_root), hub, sched, call_order


def test_ca_risk_evaluator_and_scoring() -> None:
    """验证工程单位风险评估器：过滤 0V 停运孤岛假告警、准确检出高低压/过载并计算安全评分。"""
    buses = [
        {"device_type": "ACNode", "device_idx": 1, "device_name": "正常母线", "vbase": 380.0, "v_pu": 1.0, "v_eng": 380.0},
        {"device_type": "ACNode", "device_idx": 2, "device_name": "低压母线", "vbase": 380.0, "v_pu": 0.84, "v_eng": 319.2},
        {"device_type": "ACNode", "device_idx": 3, "device_name": "停运孤岛", "vbase": 380.0, "v_pu": 0.0, "v_eng": 0.0},
    ]
    branches = [
        {"device_type": "ACBranch", "device_idx": 1, "device_name": "重过载线路", "loading_pct": 112.5},
        {"device_type": "DCACConverter", "device_idx": 1, "device_name": "预警换流器", "loading_pct": 85.0},
    ]
    risks, meta = evaluate_lf_state_risks(
        contingency_name="N-0 基态",
        category="N-0",
        buses=buses,
        branches=branches,
        params=DEFAULT_CA_PARAMS,
    )
    # 停运 0V 节点不得误报
    assert all(r["device_name"] != "停运孤岛" for r in risks)
    assert len(risks) == 3
    by_dev = {r["device_name"]: r for r in risks}
    assert by_dev["低压母线"]["risk_category"] == "voltage_low"
    assert by_dev["低压母线"]["severity"] == "critical"
    assert by_dev["重过载线路"]["risk_category"] == "overload"
    assert by_dev["重过载线路"]["severity"] == "high"
    assert by_dev["预警换流器"]["risk_category"] == "heavy_load"
    assert by_dev["预警换流器"]["severity"] == "low"
    assert meta["min_v_pu"] == pytest.approx(0.84)
    assert meta["max_loading_pct"] == pytest.approx(112.5)

    score, level = compute_security_score_and_level(
        base_converged=True, critical_count=1, high_count=1, medium_count=0, low_count=1
    )
    assert level == "严重"
    assert score == pytest.approx(73.0)


def test_ca_params_contingencies_storage_and_logs(tmp_path: Path) -> None:
    """验证 CA 参数校验/重置、预想故障同步与 CRUD、多断面历史回放与日志清理。"""
    repo = Repository(tmp_path / "ca.sqlite3")
    repo.initialize()
    try:
        p = repo.ca_params_get(do_cycle=180)
        assert p["do_cycle"] == 180
        saved = repo.ca_params_save({"max_scan_count": 25, "v_min_pu": 0.94, "v_max_pu": 1.06})
        assert saved["max_scan_count"] == 25
        with pytest.raises(ValueError):
            repo.ca_params_save({"v_min_pu": 1.1, "v_max_pu": 1.05})
        rst = repo.ca_params_reset()
        assert rst["max_scan_count"] == DEFAULT_CA_PARAMS["max_scan_count"]

        # 模型自动同步 N-1 预想故障集 + 自定义 N-k
        mt = {
            "ACBranch": {"rows": [{"idx": 1, "name": "线路A", "run_stat": 1}, {"idx": 2, "name": "停运线", "run_stat": 0}]},
            "DCACConverter": {"rows": [{"idx": 1, "name": "换流器A", "run_stat": 1}]},
        }
        sync_res = repo.ca_contingencies_sync(mt)
        assert sync_res["inserted"] == 2
        nk = repo.ca_contingency_save(
            {
                "name": "N-2:双回开断",
                "items": [
                    {"device_type": "ACBranch", "device_idx": 1, "device_name": "线路A"},
                    {"device_type": "DCACConverter", "device_idx": 1, "device_name": "换流器A"},
                ],
                "priority": 5,
            }
        )
        assert nk["category"] == "N-k"
        assert len(repo.ca_contingencies_list()) == 3
        assert repo.ca_contingencies_bulk_toggle(enabled=False, category="N-1") == 2
        assert len(repo.ca_contingencies_list(enabled_only=True)) == 1
        assert repo.ca_contingency_delete(nk["id"]) is True
        assert repo.ca_contingencies_clear() == 2

        # 两轮历史断面入库与回放
        r1 = _record_run(repo, "ca", _sample_ca_result(source_lf_run_id=10, critical=1, high=1))
        r2 = _record_run(repo, "ca", _sample_ca_result(source_lf_run_id=11, critical=0, high=0))
        hist = repo.ca_runs_history(limit=10)
        assert [x["run_id"] for x in hist] == [r2, r1]
        assert repo.ca_risks_browse(run_id=r2)["meta"]["total"] == 0
        assert repo.ca_risks_browse(run_id=r1, severity="critical")["meta"]["total"] == 1
        assert "换流器1" in repo.ca_risks_export_csv(run_id=r1).decode("utf-8-sig")

        # 日志审计与清理
        repo.record_ca_run_log(level="INFO", stage="n1_scan", run_id=r2, message="N-1 扫描全部通过", elapsed_ms=33.0)
        assert repo.ca_logs_summary()["total"] >= 1
        pol = repo.ca_logs_policy_update({"retention_days": 15, "max_rows": 1000})
        assert pol["retention_days"] == 15
        assert repo.ca_logs_purge(dry_run=True, max_rows=1)["deleted"] == 0
        assert "N-1 扫描全部通过" in repo.ca_logs_export_csv()
    finally:
        repo.close()


def test_ca_web_apis_pipeline_chain_and_pages(tmp_path: Path) -> None:
    """验证 /api/ca/*、/api/pipeline/*、/api/actions/run-chain 串联执行及前端页面资产。"""
    app, hub, sched, call_order = _make_full_app(tmp_path)
    try:
        # 1. 串联执行 SE → LF → CA，验证严格先后顺序与跨库溯源一致性
        chain = app.api_post("/api/actions/run-chain", {"tasks": ["se", "lf", "ca"], "async": False})
        assert chain["ok"] is True
        assert call_order == ["se", "lf", "ca"]
        assert len(chain["data"]["steps"]) == 3

        # 2. 全平台 Pipeline 状态接口验证全链路已同步（SE #id -> LF #id -> CA #id）
        pipe = app.api_get("/api/pipeline/status")
        assert pipe["ok"] is True
        lk = pipe["data"]["linkage"]
        assert lk["se_lf_synced"] is True
        assert lk["lf_ca_synced"] is True
        assert lk["all_synced"] is True
        assert len(pipe["data"]["alerts"]) >= 1
        assert len(pipe["data"]["recent_runs"]) >= 3

        # 3. 级联策略开关持久化
        cas = app.api_post("/api/pipeline/cascade", {"se_to_lf": True, "lf_to_ca": True})
        assert cas["ok"] is True
        assert cas["data"] == {"se_to_lf": True, "lf_to_ca": True}

        # 4. CA 全套只读与写 REST 接口
        assert app.api_get("/api/ca/home")["ok"] is True
        assert app.api_get("/api/ca/runs/history")["ok"] is True
        topo = app.api_get("/api/ca/topology-risks")
        assert topo["ok"] is True
        assert topo["data"]["svg_available"] is True
        assert "ACRealBs-1" in topo["data"]["risk_dev_ids"]
        assert app.api_get("/api/ca/risks")["data"]["meta"]["total"] >= 1
        assert app.api_get("/api/ca/contingencies/results")["data"]["meta"]["total"] == 2
        assert app.api_get("/api/ca/history/stats")["ok"] is True
        assert app.api_get("/api/ca/model-catalog")["ok"] is True

        sync = app.api_post("/api/ca/contingencies/sync", {})
        assert sync["ok"] is True and sync["data"]["inserted"] == 2
        add_c = app.api_post(
            "/api/ca/contingencies/defs",
            {"name": "N-1:测试", "items": [{"device_type": "ACBranch", "device_idx": 1, "device_name": "交流线路1"}]},
        )
        assert add_c["ok"] is True
        cid = add_c["data"]["id"]
        assert app.api_put(f"/api/ca/contingencies/defs/{cid}", {**add_c["data"], "priority": 7})["data"]["priority"] == 7
        assert app.api_delete(f"/api/ca/contingencies/defs/{cid}")["data"]["deleted"] is True

        # 5. 前端 5 套 CA 页面 + 升级后 overview.html 资产与全站侧栏入口断言
        web_root = Path(__file__).resolve().parents[1] / "web"
        assert (web_root / "assets" / "ca-app.js").is_file()
        assert (web_root / "assets" / "overview-app.js").is_file()
        for page, dp in (
            ("ca-main.html", "/ca-main"),
            ("ca-risks.html", "/ca-risks"),
            ("ca-contingencies.html", "/ca-contingencies"),
            ("ca-config.html", "/ca-config"),
            ("ca-logs.html", "/ca-logs"),
        ):
            html = (web_root / page).read_text(encoding="utf-8")
            assert f'data-page="{dp}"' in html
            assert "/assets/ca-app.js" in html
            assert "/assets/se-dashboard.css" in html
        ov_html = (web_root / "overview.html").read_text(encoding="utf-8")
        assert 'data-page="/overview"' in ov_html
        assert "/assets/overview-app.js" in ov_html
        for nav_page in ("overview.html", "se-main.html", "lf-main.html", "runs.html", "settings.html"):
            assert 'href="/ca-main.html"' in (web_root / nav_page).read_text(encoding="utf-8")
    finally:
        sched.shutdown()
        hub.close()
