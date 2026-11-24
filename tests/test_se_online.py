"""在线 SE 模块（scdfe_d 宽表量测、pas_se_para 算法参数与四类结果表回写）测试。"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pas.cli import run_se_snapshot
from pas.config import load_config
from pas.db import Repository
from pas.input_store import SE_DEVICE_RESULT_METRICS, is_scdfe_d_wide_db, read_scdfe_d_wide_snapshot
from pas.model_input import read_model_tables
from pas.se_params import render_se_para_text


KERNEL_ROOT = Path("D:/codex/hybrid_power_kernel_acceptance_d1603be")
SE_PARA = KERNEL_ROOT / "data/se/se.para"


def _write_rtdb_model(path: Path, tables: dict[str, tuple[list[str], list[tuple]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
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
    conn.close()


def _create_wide_table(
    conn: sqlite3.Connection,
    table_name: str,
    metrics: list[str],
    rows: list[dict],
) -> None:
    cols = ["idx INTEGER PRIMARY KEY", "name TEXT NOT NULL"]
    for m in metrics:
        cols.extend(
            [
                f'"{m}" REAL',
                f'"{m}_qual" INTEGER DEFAULT 128',
                f'"{m}_pre" REAL',
                f'"{m}_time" INTEGER',
                f'"{m}_notuse" INTEGER DEFAULT 0',
                f'"{m}_weight" REAL DEFAULT 1.0',
                f'"{m}_rtu" INTEGER',
                f'"{m}_pnt" INTEGER',
            ]
        )
    conn.execute(f'CREATE TABLE "{table_name}" ({", ".join(cols)})')
    for rec in rows:
        keys = list(rec.keys())
        quoted = ", ".join(f'"{k}"' for k in keys)
        placeholders = ", ".join("?" for _ in keys)
        conn.execute(f'INSERT INTO "{table_name}" ({quoted}) VALUES ({placeholders})', tuple(rec[k] for k in keys))


def _build_minimal_hybrid_scenario(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """构造最小可收敛 2 节点交流 + 1 台发电机 + 1 台负荷 + 1 条支路 + 1 台断路器的完整测试场景。"""
    work = tmp_path / "workspace/realtime/demo"
    model_db = work / "sqldb/model/devices.sqlite3"
    scada_db = work / "sqldb/scada/scdfe_d.sqlite3"
    config_file = tmp_path / "config.json"

    # 380V 基准, p_base=100 kW, 支路阻抗 r=0.01, x=0.02 (p.u.)
    # 节点1(松弛/发电机): V=380V (1.0 pu), 节点2(负荷): P=50kW, Q=10kvar
    _write_rtdb_model(
        model_db,
        {
            "Model": (
                ["path", "name", "p_base", "u_unit", "p_unit", "i_unit"],
                [("test", "demo", 100.0, "V", "kW", "A")],
            ),
            "ACNode": (
                ["idx", "name", "vbase", "run_stat"],
                [(1, "交流母线1", 380.0, 1), (2, "交流母线2", 380.0, 1), (3, "备用母线3", 380.0, 1)],
            ),
            "ACGenerator": (
                ["idx", "name", "dev_type", "node", "control_type", "p_set", "p_max", "p_min", "q_set", "q_max", "q_min", "v_set", "alpha", "run_stat", "rated_capacity", "rated_voltage", "v_max", "v_min"],
                [
                    (1, "风机1", "ac-gen", 1, "PH", 50.0, 200.0, 0.0, 10.0, 100.0, -100.0, 1.0, 1.0, 1, 200.0, 380.0, 1.1, 0.9),
                    (2, "备用柴发", "ac-gen", 3, "PQ", 0.0, 100.0, 0.0, 0.0, 50.0, -50.0, 1.0, 0.0, 1, 100.0, 380.0, 1.1, 0.9),
                ],
            ),
            "ACLoad": (
                ["idx", "name", "dev_type", "node", "p_set", "p_max", "p_min", "q_max", "q_min", "run_stat", "rated_capacity", "pbase", "pv0", "pv1", "pv2", "qbase", "qv0", "qv1", "qv2", "v_max", "v_min"],
                [(1, "负荷1", "ac-load", 2, 50.0, 100.0, 0.0, 50.0, 0.0, 1, 100.0, 50.0, 1.0, 0.0, 0.0, 10.0, 1.0, 0.0, 0.0, 1.1, 0.9)],
            ),
            "ACBranch": (
                ["idx", "name", "dev_type", "i_node", "j_node", "run_stat", "rated_capacity", "i_max", "r", "x", "b"],
                [(1, "线路1", "ac-line", 1, 2, 1, 200.0, 500.0, 0.01444, 0.02888, 0.0)],
            ),
            "ACBreak": (
                ["idx", "name", "dev_type", "i_node", "j_node", "status", "run_stat", "rated_capacity", "i_max"],
                [(1, "开关1", "ac-brk", 1, 3, 1, 1, 200.0, 500.0)],
            ),
        },
    )

    # 创建 scdfe_d.sqlite3 宽表：开关1断开(position=0)，备用柴发停运(run=0)，并在负荷1有功上注入显著坏数据(250kW vs 真实约50kW)
    scada_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(scada_db)
    now_ms = 1795538377717
    _create_wide_table(
        conn,
        "ACNode",
        ["uab", "run"],
        [
            {"idx": 1, "name": "交流母线1", "uab": 380.0, "uab_qual": 0, "uab_time": now_ms, "uab_notuse": 0, "uab_weight": 10.0, "run": 1, "run_qual": 0},
            {"idx": 2, "name": "交流母线2", "uab": 377.77, "uab_qual": 0, "uab_time": now_ms, "uab_notuse": 0, "uab_weight": 10.0, "run": 1, "run_qual": 0},
            {"idx": 3, "name": "备用母线3", "uab": 0.0, "uab_qual": 0, "uab_time": now_ms, "uab_notuse": 0, "uab_weight": 1.0, "run": 0, "run_qual": 0},
        ],
    )
    _create_wide_table(
        conn,
        "ACGenerator",
        ["p", "q", "uab", "ia", "run"],
        [
            {
                "idx": 1, "name": "风机1",
                "p": 50.26, "p_qual": 0, "p_time": now_ms, "p_notuse": 0, "p_weight": 10.0,
                "q": 10.52, "q_qual": 0, "q_time": now_ms, "q_notuse": 0, "q_weight": 10.0,
                "uab": 380.0, "uab_qual": 0, "uab_time": now_ms, "uab_notuse": 0, "uab_weight": 10.0,
                "ia": 78.0, "ia_qual": 0, "ia_time": now_ms, "ia_notuse": 0, "ia_weight": 1.0,
                "run": 1, "run_qual": 0,
            },
            {
                "idx": 2, "name": "备用柴发",
                "p": 0.0, "p_qual": 0, "p_time": now_ms, "p_notuse": 0, "p_weight": 1.0,
                "q": 0.0, "q_qual": 0, "q_time": now_ms, "q_notuse": 0, "q_weight": 1.0,
                "uab": 0.0, "uab_qual": 0, "uab_time": now_ms, "uab_notuse": 0, "uab_weight": 1.0,
                "ia": 0.0, "ia_qual": 128, "ia_time": now_ms, "ia_notuse": 1, "ia_weight": 1.0,
                "run": 0, "run_qual": 0,
            },
        ],
    )
    _create_wide_table(
        conn,
        "ACLoad",
        ["p", "q", "uab", "ia", "run"],
        [
            {
                "idx": 1, "name": "负荷1",
                "p": 50.0, "p_qual": 0, "p_time": now_ms, "p_notuse": 0, "p_weight": 10.0,
                "q": 10.0, "q_qual": 0, "q_time": now_ms, "q_notuse": 0, "q_weight": 10.0,
                "uab": 377.77, "uab_qual": 0, "uab_time": now_ms, "uab_notuse": 0, "uab_weight": 10.0,
                "ia": 77.5, "ia_qual": 0, "ia_time": now_ms, "ia_notuse": 0, "ia_weight": 1.0,
                "run": 1, "run_qual": 0,
            }
        ],
    )
    _create_wide_table(
        conn,
        "ACBranch",
        ["i_p", "i_q", "i_uab", "i_ia", "j_p", "j_q", "j_uab", "j_ia", "run"],
        [
            {
                "idx": 1, "name": "线路1",
                "i_p": 50.26, "i_p_qual": 0, "i_p_time": now_ms, "i_p_notuse": 0, "i_p_weight": 10.0,
                "i_q": 10.52, "i_q_qual": 0, "i_q_time": now_ms, "i_q_notuse": 0, "i_q_weight": 10.0,
                "i_uab": None, "i_uab_qual": 128, "i_uab_notuse": 0,
                "i_ia": 78.0, "i_ia_qual": 0, "i_ia_time": now_ms, "i_ia_notuse": 0, "i_ia_weight": 1.0,
                "j_p": -550.0, "j_p_qual": 0, "j_p_time": now_ms, "j_p_notuse": 0, "j_p_weight": 1.0,  # 故意注入显著坏数据
                "j_q": -10.0, "j_q_qual": 0, "j_q_time": now_ms, "j_q_notuse": 0, "j_q_weight": 10.0,
                "j_uab": None, "j_uab_qual": 128, "j_uab_notuse": 0,
                "j_ia": None, "j_ia_qual": 128, "j_ia_notuse": 0,
                "run": 1, "run_qual": 0,
            }
        ],
    )
    _create_wide_table(
        conn,
        "ACBreak",
        ["ia", "position"],
        [
            {"idx": 1, "name": "开关1", "ia": 0.0, "ia_qual": 0, "ia_time": now_ms, "ia_notuse": 0, "ia_weight": 1.0, "position": 0, "position_qual": 0}
        ],
    )
    conn.commit()
    conn.close()

    config_file.write_text(
        json.dumps(
            {
                "kernel_root": str(KERNEL_ROOT),
                "workspace_root": str(tmp_path / "workspace"),
                "runtime": "realtime",
                "scenario": "demo",
                "tasks": {
                    "se": {
                        "enabled": True,
                        "period_seconds": 60,
                        "measurement_file": "sqldb/scada/scdfe_d.sqlite3",
                        "parameter_file": str(SE_PARA),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return config_file, model_db, scada_db, work / "sqldb/pas/se.sqlite3"


def test_se_para_extraction_persistence_and_override(tmp_path: Path):
    se_db = tmp_path / "se.sqlite3"
    repo = Repository(se_db)
    repo.initialize()
    params = repo.sync_se_parameters(SE_PARA, do_cycle=45)
    assert params["max_iterator"] == 20
    assert params["badnum_max"] == 10
    assert params["badnum_step"] == 1
    assert params["baderr_eps"] == 3.0
    assert params["tol"] == 1e-8
    assert params["do_cycle"] == 45
    assert params["power_flow_max_iter"] == 200

    # 校验 RTDB 定义已包含扩展后的 pas_se_para 列
    with sqlite3.connect(se_db) as conn:
        rtdb_cols = {
            row[0]
            for row in conn.execute(
                "SELECT eng_name FROM rtdb_schema_columns WHERE table_name = 'pas_se_para'"
            )
        }
        assert {"id", "max_iterator", "badnum_max", "badnum_step", "baderr_eps", "tol", "diff_step", "voltage_floor"} <= rtdb_cols
        assert conn.execute("SELECT COUNT(*) FROM pas_se_weight").fetchone()[0] > 0

        # 模拟用户在线修改 pas_se_para 中的坏数据上限与门槛
        conn.execute("UPDATE pas_se_para SET max_iterator = 35, badnum_max = 15, baderr_eps = 2.5 WHERE id = 1")
        conn.commit()

    updated = repo.get_se_parameters(SE_PARA, do_cycle=45)
    assert updated["max_iterator"] == 35
    assert updated["badnum_max"] == 15
    assert updated["baderr_eps"] == 2.5
    rendered = render_se_para_text(updated)
    assert "# max_iter 35" in rendered
    assert "# max_remove 15" in rendered
    assert "# bad_threshold 2.5" in rendered
    repo.close()


def test_online_se_wide_scdfe_d_end_to_end_and_four_table_outputs(tmp_path: Path):
    config_file, model_db, scada_db, se_db = _build_minimal_hybrid_scenario(tmp_path)
    assert is_scdfe_d_wide_db(scada_db)

    model_before = model_db.read_bytes()
    scada_before = scada_db.read_bytes()

    # 验证宽表快照读取与遥信覆盖提取
    model = {name: blk["rows"] for name, blk in read_model_tables(model_db).items()}
    selected, meta = read_scdfe_d_wide_snapshot(scada_db, model)
    assert meta["format"] == "scdfe_d_wide"
    assert meta["topology_overrides"]["ACBreak"][1]["status"] == 0
    assert meta["topology_overrides"]["ACGenerator"][2]["run_stat"] == 0
    assert len(selected) > 0

    # 执行一次完整在线 SE 计算并回写 se.sqlite3
    config = load_config(config_file)
    exit_code = run_se_snapshot(config)
    assert exit_code == 0

    # 源模型库和源量测库必须严格只读零修改
    assert model_db.read_bytes() == model_before
    assert scada_db.read_bytes() == scada_before

    with sqlite3.connect(se_db) as conn:
        conn.row_factory = sqlite3.Row

        # 1. 验证 pas_se_para 已提取并落库
        para = conn.execute("SELECT * FROM pas_se_para WHERE id = 1").fetchone()
        assert para is not None
        assert para["max_iterator"] == 20
        assert para["badnum_max"] == 10
        assert para["baderr_eps"] == 3.0

        # 2. 验证统计表 se_statistics
        stat = conn.execute("SELECT * FROM se_statistics ORDER BY run_id DESC LIMIT 1").fetchone()
        assert stat is not None
        assert stat["converged"] == 1
        assert stat["observable"] == 1
        assert stat["calc_time"]
        assert stat["elapsed_seconds"] >= 0.0
        assert stat["meas_count"] > 0
        assert stat["bad_data_count"] >= 1
        assert 0.0 < stat["pass_rate"] < 1.0
        assert stat["total_residual"] >= 0.0

        # 3. 验证坏数据表 se_bad_data 与 pas_se_badmeas（精准定位到注入的线路1末端有功坏数据）
        bad_rows = conn.execute("SELECT * FROM se_bad_data").fetchall()
        assert len(bad_rows) == 1
        br_bad = bad_rows[0]
        assert br_bad["device_name"] == "线路1" and br_bad["metric"] == "j_p"
        assert abs(br_bad["meas_value"] - (-550.0)) < 1e-6
        assert -100.0 < br_bad["se_value"] < -40.0
        assert conn.execute("SELECT COUNT(*) FROM pas_se_badmeas").fetchone()[0] == 1

        # 验证线路设备表中 j_p_meas=-550 且 j_p_se 与坏数据表估计值一致
        br_dev = conn.execute("SELECT * FROM se_dev_ACBranch WHERE idx = 1").fetchone()
        assert abs(br_dev["j_p_meas"] - (-550.0)) < 1e-6
        assert abs(br_dev["j_p_se"] - br_bad["se_value"]) < 1e-9

        # 4. 验证量测表 se_measurement（工程单位、真实设备名，无 pos: 占位符）
        meas_rows = conn.execute("SELECT * FROM se_measurement").fetchall()
        assert len(meas_rows) > 0
        assert all(not str(r["device_name"]).startswith("pos:") for r in meas_rows)
        bus1 = next(r for r in meas_rows if r["device_name"] == "交流母线1" and r["meas_type"] == "V")
        assert 370.0 < bus1["meas_value"] < 390.0
        assert 370.0 < bus1["se_value"] < 390.0

        # 5. 验证各类设备表（含未配置实测但经 SE 补算出的 i_uab_se / j_ia_se）
        node_rows = {r["idx"]: dict(r) for r in conn.execute("SELECT * FROM se_dev_ACNode")}
        assert set(node_rows) == {1, 2, 3}
        assert 370.0 < node_rows[1]["uab_meas"] < 390.0
        assert 370.0 < node_rows[1]["uab_se"] < 390.0

        br = conn.execute("SELECT * FROM se_dev_ACBranch WHERE idx = 1").fetchone()
        assert br["i_uab_meas"] is None
        assert 370.0 < br["i_uab_se"] < 390.0
        assert 370.0 < br["j_uab_se"] < 390.0
        assert 40.0 < br["i_p_se"] < 100.0
        assert br["j_ia_se"] is not None and br["j_ia_se"] > 50.0

        gen = conn.execute("SELECT * FROM se_dev_ACGenerator WHERE idx = 1").fetchone()
        assert gen["ia_se"] is not None and gen["ia_se"] > 50.0

        # 6. 验证 RTDB 内置定义完整注册
        rtdb_tables = {row[0] for row in conn.execute("SELECT table_name FROM rtdb_schema_tables")}
        assert {"se_statistics", "se_measurement", "se_bad_data", "pas_se_para"} <= rtdb_tables
        for dev_type in SE_DEVICE_RESULT_METRICS:
            assert f"se_dev_{dev_type}" in rtdb_tables
