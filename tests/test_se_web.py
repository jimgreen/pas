"""状态估计主画面 (/se-main.html) 与 /api/se/* 后端接口单元测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pas.db import Repository, RepositoryHub
from pas.web import PasWebApp
from tests.test_se_online import SE_PARA, _build_minimal_hybrid_scenario


def _seed_se_web_app(tmp_path: Path):
    config_file, model_db, scada_db, se_db = _build_minimal_hybrid_scenario(tmp_path)
    # 准备同场景 SVG 文件
    svg_file = tmp_path / "workspace/realtime/demo/model/demo.svg"
    svg_file.parent.mkdir(parents=True, exist_ok=True)
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">'
        '<use id="ACBranch-1" dev-id="ACBranch-1" idx="1" name="线路1"/>'
        '<g class="mg" dev="ACBranch-1"><text><tspan>P</tspan><tspan id="mv-ACBranch-1-activePower-0" class="mv" mt="activePower">--</tspan><tspan>MW</tspan></text></g>'
        "</svg>",
        encoding="utf-8",
    )

    from pas.cli import run_se_snapshot
    from pas.config import load_config

    config = load_config(config_file)
    # 连续运行两次，形成多点历史曲线数据
    assert run_se_snapshot(config) == 0
    assert run_se_snapshot(config) == 0

    repos = {name: Repository(path) for name, path in config.databases.items()}
    control = Repository(config.database)
    hub = RepositoryHub(repos, control)
    hub.initialize()

    class DummyScheduler:
        def status(self):
            return {"active_tasks": [], "pending_tasks": [], "daemon_running": False, "jobs": []}

    web_root = Path(__file__).resolve().parents[1] / "web"
    app = PasWebApp(config, hub, DummyScheduler(), web_root)
    return app, hub, svg_file


def test_se_main_page_and_assets_exist():
    web_root = Path(__file__).resolve().parents[1] / "web"
    html = (web_root / "se-main.html").read_text(encoding="utf-8")
    assert '<body data-page="/se-main"' in html
    assert "/assets/se-dashboard.css" in html
    assert "/assets/se-dashboard.js" in html
    assert (web_root / "assets" / "se-dashboard.css").is_file()
    assert (web_root / "assets" / "se-dashboard.js").is_file()
    # 验证侧边栏入口存在于主页面
    for name in ("overview.html", "analysis/se.html", "runs.html", "settings.html"):
        assert 'href="/se-main.html"' in (web_root / name).read_text(encoding="utf-8")


def test_se_api_overview_devices_measurements_history_topology_and_params(tmp_path: Path):
    app, hub, svg_file = _seed_se_web_app(tmp_path)
    try:
        # 1. Overview
        ov = app.api_get("/api/se/overview")
        assert ov["ok"] is True
        assert ov["data"]["latest"]["converged"] == 1
        assert ov["data"]["latest"]["bad_data_count"] == 1
        assert len(ov["data"]["bad_data"]) == 1
        assert len(ov["data"]["recent_runs"]) == 2

        # 2. Devices & bad_only filter
        devs = app.api_get("/api/se/devices?type=ACBranch&bad_only=1")
        assert devs["ok"] is True
        assert devs["data"]["device_type"] == "ACBranch"
        assert len(devs["data"]["rows"]) == 1
        assert devs["data"]["rows"][0]["has_bad"] is True
        assert "j_p" in devs["data"]["rows"][0]["bad_metrics"]

        # 3. Measurements filter
        meas = app.api_get("/api/se/measurements?source=bad_data&sort=abs_norm_residual&direction=desc")
        assert meas["ok"] is True
        assert meas["data"]["meta"]["total"] == 1
        assert meas["data"]["rows"][0]["device_name"] == "线路1"

        # 4. History stats (2 points)
        h_stats = app.api_get("/api/se/history/stats?limit=20")
        assert h_stats["ok"] is True
        assert len(h_stats["data"]) == 2
        assert h_stats["data"][0]["run_id"] < h_stats["data"][1]["run_id"]

        # 5. History points catalog + single point series
        h_pts = app.api_get("/api/se/history/points")
        assert h_pts["ok"] is True
        assert len(h_pts["data"]["points"]) > 0
        pt_series = app.api_get("/api/se/history/point?device_type=ACBranch&device_name=线路1&meas_type=P_TO&limit=20")
        assert pt_series["ok"] is True
        assert len(pt_series["data"]["points"]) == 2
        assert all(p["is_bad"] == 1 for p in pt_series["data"]["points"])
        assert pt_series["data"]["bad_threshold"] == 3.0

        # 6. Bad data history hotspots
        h_bad = app.api_get("/api/se/history/bad-data?limit=20")
        assert h_bad["ok"] is True
        assert len(h_bad["data"]["hotspots"]) >= 1
        assert h_bad["data"]["hotspots"][0]["bad_hits"] == 2

        # 7. SVG discovery & topology values with bad-data flagging
        assert app._se_svg_path() == svg_file.resolve()
        topo = app.api_get("/api/se/topology-values")
        assert topo["ok"] is True
        assert topo["data"]["svg_available"] is True
        assert "ACBranch-1" in topo["data"]["bad_dev_ids"]
        br = topo["data"]["devices"]["ACBranch-1"]
        assert br["has_bad"] is True
        assert br["svg_slots"]["activePower"]["any_bad"] is True

        # 8. Parameters read, update, and reset
        p0 = app.api_get("/api/se/params")
        assert p0["ok"] is True
        assert p0["data"]["max_iterator"] == 20
        p1 = app.api_post("/api/se/params", {"max_iterator": 30, "badnum_max": 12, "baderr_eps": 2.8})
        assert p1["ok"] is True
        assert p1["data"]["max_iterator"] == 30
        assert p1["data"]["badnum_max"] == 12
        assert p1["data"]["baderr_eps"] == 2.8
        p2 = app.api_post("/api/se/params/reset", {"action": "reset"})
        assert p2["ok"] is True
        assert p2["data"]["max_iterator"] == 20
        assert p2["data"]["badnum_max"] == 10
        assert p2["data"]["baderr_eps"] == 3.0
    finally:
        hub.close()
