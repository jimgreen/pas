"""未来 24 小时 96 点安全预警与绿电维生分析（EW）单元测试。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from pas.db import Repository
from pas.ew_online import (
    DEFAULT_EW_PARAMS,
    persist_ew_run,
    run_ew_analysis,
    simulate_green_survival,
)
from pas.web import PasWebApp


def _seed_forecast_dbs(forecast_dir: Path) -> None:
    """在临时目录构造 renewgen.db / load.db / weather.db 标准 96 点测试库。"""
    forecast_dir.mkdir(parents=True, exist_ok=True)

    # 1. renewgen.db
    with sqlite3.connect(forecast_dir / "renewgen.db") as con:
        con.execute(
            """CREATE TABLE energy_forecasts (
                   run_id TEXT, target_time_utc TEXT, horizon TEXT,
                   pv_power_kw REAL, wind_power_kw REAL
               )"""
        )
        rows = [
            ("r1", f"2099-01-01T{i // 4:02d}:{(i % 4) * 15:02d}:00Z", "day_ahead", 20.0 if 24 <= i <= 60 else 0.0, 50.0)
            for i in range(96)
        ]
        con.executemany("INSERT INTO energy_forecasts VALUES (?,?,?,?,?)", rows)

    # 2. load.db
    with sqlite3.connect(forecast_dir / "load.db") as con:
        con.execute(
            """CREATE TABLE energy_forecasts (
                   run_id TEXT, target_time_utc TEXT, horizon TEXT, load_kw REAL
               )"""
        )
        rows = [
            ("r1", f"2099-01-01T{i // 4:02d}:{(i % 4) * 15:02d}:00Z", "day_ahead", 160.0)
            for i in range(96)
        ]
        con.executemany("INSERT INTO energy_forecasts VALUES (?,?,?,?)", rows)

    # 3. weather.db
    with sqlite3.connect(forecast_dir / "weather.db") as con:
        con.execute(
            """CREATE TABLE weather_forecasts (
                   run_id TEXT, target_time_utc TEXT, horizon TEXT,
                   wind_speed_mps REAL, temperature_c REAL, solar_radiation_wm2 REAL
               )"""
        )
        rows = [
            ("r1", f"2099-01-01T{i // 4:02d}:{(i % 4) * 15:02d}:00Z", "day_ahead", 8.5, -20.0, 300.0 if 24 <= i <= 60 else 0.0)
            for i in range(96)
        ]
        con.executemany("INSERT INTO weather_forecasts VALUES (?,?,?,?,?,?)", rows)


def test_green_survival_exact_depletion_physics():
    """纯绿电维生时长物理精度：零风光、恒定 100kW 负荷、可用电量 400kWh（效率1.0）应精确维生 4.0h。"""
    pts = [
        {
            "slot_idx": i,
            "time_label": f"{i // 4:02d}:{(i % 4) * 15:02d}",
            "load_kw": 100.0,
            "renewable_kw": 0.0,
            "net_load_kw": 100.0,
            "storage_cold_factor": 1.0,
        }
        for i in range(96)
    ]
    storage = {
        "total_kwh": 500.0,
        "weighted_soc": 0.95,  # 可用 (0.95 - 0.15) * 500 = 400 kWh
        "max_charge_kw": 300.0,
        "max_discharge_kw": 300.0,
        "h2_usable_kwh": 200.0,
    }
    params = {**DEFAULT_EW_PARAMS, "storage_min_soc": 0.15, "storage_eff": 1.0}
    stats = simulate_green_survival(pts, storage, params)
    assert stats["green_survival_capped"] == 0
    assert stats["green_survival_hours"] == pytest.approx(4.0, abs=0.05)
    assert stats["green_exhaust_slot"] == 16
    assert stats["green_survival_with_h2_hours"] == pytest.approx(6.0, abs=0.05)
    assert stats["deficit_total_kwh"] > 0


def test_ew_reads_three_forecast_dbs_and_persists(tmp_path: Path):
    """验证 EW 优先直连 renewgen.db / load.db / weather.db 三大预测库并持久化 96 点与预警。"""
    ws = tmp_path / "qinling"
    _seed_forecast_dbs(ws / "sqldb" / "forecast")

    repo = Repository(tmp_path / "pas.db")
    repo.initialize()
    params = repo.ew_params_get()
    # 传入真实模型储能表，验证按列名精确读取容量（绝不编造默认假储能）
    model_tables = {
        "ACGenerator": {"rows": [{"idx": 23, "name": "交流电化学储能-23"}, {"idx": 26, "name": "交流电化学储能-26"}]},
        "ACStorageGen": {
            "rows": [
                {"idx": 1, "idx_acgenerator": 23, "energy_capacity": 200.0, "max_charge_power": 100.0, "max_discharge_power": 100.0, "state_of_charge": 72.0},
                {"idx": 2, "idx_acgenerator": 26, "energy_capacity": 100.0, "max_charge_power": 100.0, "max_discharge_power": 100.0, "state_of_charge": 68.0},
            ]
        },
        "DCGenerator": {"rows": [{"idx": 4, "name": "电化学储能-1"}]},
        "DCStorageGen": {
            "rows": [
                {"idx": 1, "idx_dcgenerator": 4, "energy_capacity": 60.0, "max_charge_power": 60.0, "max_discharge_power": 60.0, "state_of_charge": 88.0},
            ]
        },
    }
    res = run_ew_analysis(
        params=params,
        weather_state={"irradiance_wm2": 300.0, "wind_speed_ms": 8.5, "ambient_temp_c": -20.0},
        lf_snap={
            "latest": {"run_id": 1, "total_load_p": 160.0, "max_loading_pct": 68.0, "min_v_pu": 0.975},
            "branches": [{"name": "换流器-1", "branch_type": "DCACConverter", "loading_pct": 68.0}],
        },
        ca_snap={"latest": {"run_id": 2, "max_loading_pct": 72.0}},
        contingencies=[{"name": "N-1:换流器-1", "category": "N-1", "target_desc": "换流器-1", "priority": 10, "enabled": 1}],
        model_tables=model_tables,
        scada_db_path=None,
        workspace_dir=ws,
        overrides=[],
    )
    assert res["forecast_source"] == "forecast_db"
    assert len(res["points"]) == 96
    assert res["storage_total_kwh"] == pytest.approx(360.0)
    ds = res["weather_snapshot"]["data_sources"]
    assert ds["renewgen"]["connected"] is True and ds["renewgen"]["rows"] == 96
    assert ds["load"]["connected"] is True and ds["load"]["rows"] == 96
    assert ds["weather"]["connected"] is True and ds["weather"]["rows"] == 96
    assert res["green_survival_hours"] is not None and res["green_survival_hours"] > 0

    ew_run_id = repo.ew_persist_run(res, source="test")
    assert ew_run_id >= 1
    home = repo.ew_home_summary()
    assert home["latest"]["ew_run_id"] == ew_run_id
    assert len(home["points"]) == 96
    csv_bytes = repo.ew_risks_export_csv()
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    repo.close()


def test_ew_missing_db_never_fabricates_data(tmp_path: Path):
    """验证缺少三大预测库与模型储能库时，严格返回空数据，严禁伪造假曲线或假储能。"""
    res = run_ew_analysis(
        params=DEFAULT_EW_PARAMS,
        weather_state={},
        lf_snap=None,
        ca_snap=None,
        contingencies=[],
        model_tables=None,
        scada_db_path=None,
        workspace_dir=tmp_path,
        overrides=[],
    )
    assert res["forecast_source"] == "missing"
    assert res["points"] == []
    assert res["risks"] == []
    assert res["storage_units"] == []
    assert res["green_survival_hours"] is None
    assert res["security_score"] is None
    assert res["risk_level"] == "无数据"


def test_ew_web_api_and_static_pages(tmp_path: Path):
    """验证 EW REST API 读写闭环与 5 个前端主页面完备。"""
    _seed_forecast_dbs(tmp_path / "sqldb" / "forecast")
    repo = Repository(tmp_path / "pas.db")
    repo.initialize()

    class _DummyCfg:
        tasks = {}
        workspace_directory = tmp_path

    web_root = Path(__file__).resolve().parents[1] / "web"
    app = PasWebApp(_DummyCfg(), repo, scheduler=None, static_root=web_root)

    # 首次 GET /api/ew/home 自动读取真实预测库并持久化
    r_home = app.api_get("/api/ew/home")
    assert r_home["ok"] is True
    assert r_home["data"]["latest"] is not None
    assert len(r_home["data"]["points"]) == 96

    # 切换暴风雪过境演练并重算
    r_run = app.api_post("/api/ew/run", {"scenario": "blizzard_transit", "source": "test"})
    assert r_run["ok"] is True
    assert r_run["data"]["latest"]["forecast_scenario"] == "blizzard_transit"
    assert r_run["data"]["latest"]["risk_slots_count"] > 0

    # 验证扫描真实预测库文件列表接口
    r_files = app.api_get("/api/ew/forecast-files")
    assert r_files["ok"] is True
    paths = [x["path"] for x in r_files["data"]]
    assert "sqldb/forecast/renewgen.db" in paths
    assert "sqldb/forecast/load.db" in paths
    assert "sqldb/forecast/weather.db" in paths

    # 覆写区间批量录入（#10..#12 共 3 点）并验证查询
    r_ovr = app.api_post("/api/ew/overrides", {"slot_from": 10, "slot_to": 12, "load_kw": 320.0, "wind_kw": 0.0, "pv_kw": 0.0})
    assert r_ovr["ok"] is True
    assert r_ovr["data"]["count"] == 3
    assert len(app.api_get("/api/ew/overrides")["data"]) == 3

    # 确认 EW 5 个主页面存在且脚本引用完备
    for fn in ("ew-main.html", "ew-scenario.html", "ew-risks.html", "ew-green.html", "ew-logs.html"):
        html = (web_root / fn).read_text(encoding="utf-8")
        assert "/assets/ew-app.js" in html
        assert "/assets/pas-kit.js" in html
    repo.close()
