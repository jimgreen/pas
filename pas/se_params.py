"""SE 算法参数的提取、pas_se_para 持久化同步与内核参数文件生成。"""

from __future__ import annotations

import math
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# pas_se_para 在原 9 列 dbdef 定义基础上扩展的内核算法参数列
SE_PARA_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("tol", "REAL NOT NULL DEFAULT 1e-8"),
    ("diff_step", "REAL NOT NULL DEFAULT 1e-6"),
    ("flat_start", "INTEGER NOT NULL DEFAULT 0"),
    ("pseudo_measurement_weight", "REAL NOT NULL DEFAULT 0.0001"),
    ("targeted_pseudo_measurement_max", "INTEGER NOT NULL DEFAULT 2000"),
    ("targeted_pseudo_measurement_redundancy_ratio", "REAL NOT NULL DEFAULT 0.0"),
    ("targeted_pseudo_measurement_step", "INTEGER NOT NULL DEFAULT 10"),
    ("voltage_floor", "REAL NOT NULL DEFAULT 0.05"),
    ("min_current_voltage", "REAL NOT NULL DEFAULT 0.01"),
    ("power_flow_tol", "REAL NOT NULL DEFAULT 1e-8"),
    ("power_flow_max_iter", "INTEGER NOT NULL DEFAULT 200"),
    ("power_flow_min_voltage", "REAL NOT NULL DEFAULT 0.01"),
    ("updated_at", "TEXT NOT NULL DEFAULT ''"),
)

# 与 se.para <StateEstimationParameter> 块对应的全部参数默认值
DEFAULT_SE_PARAMS: dict[str, Any] = {
    "id": 1,
    "max_iterator": 20,
    "badnum_max": 10,
    "badnum_step": 1,
    "baderr_eps": 3.0,
    "do_cycle": 60,
    "calc_trigger": 1,
    "measqual_eps": 1e-8,
    "obj_scaling_factor": 1.0,
    "tol": 1e-8,
    "diff_step": 1e-6,
    "flat_start": 0,
    "pseudo_measurement_weight": 1e-4,
    "targeted_pseudo_measurement_max": 2000,
    "targeted_pseudo_measurement_redundancy_ratio": 0.0,
    "targeted_pseudo_measurement_step": 10,
    "voltage_floor": 0.05,
    "min_current_voltage": 0.01,
    "power_flow_tol": 1e-8,
    "power_flow_max_iter": 200,
    "power_flow_min_voltage": 0.01,
}

# 常用量测类型默认权重（写入 pas_se_weight）
DEFAULT_SE_WEIGHTS: tuple[tuple[int, float], ...] = (
    (1, 1.0),   # V
    (4, 1.0),   # P_FROM
    (5, 1.0),   # Q_FROM
    (6, 1.0),   # V_FROM
    (7, 1.0),   # I_FROM
    (8, 1.0),   # P_TO
    (9, 1.0),   # Q_TO
    (10, 1.0),  # V_TO
    (11, 1.0),  # I_TO
    (12, 1.0),  # P_LOAD
    (13, 1.0),  # Q_LOAD
    (14, 1.0),  # V_LOAD
    (15, 1.0),  # I_LOAD
    (16, 1.0),  # P_GEN
    (17, 1.0),  # Q_GEN
    (18, 1.0),  # V_GEN
    (19, 1.0),  # I_GEN
    (25, 1.0),  # P_DC
    (26, 1.0),  # V_DC
    (27, 1.0),  # I_DC
    (28, 1.0),  # P_AC
    (29, 1.0),  # Q_AC
    (30, 1.0),  # V_AC
    (31, 1.0),  # I_AC
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_bool_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return 1
    if text in {"0", "false", "no", "n", "off"}:
        return 0
    return default


def _parse_float(value: Any, default: float) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return num if math.isfinite(num) else default


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def ensure_se_para_columns(connection: sqlite3.Connection) -> None:
    """在当前事务内幂等补齐 pas_se_para 的扩展算法参数列。"""
    existing = {row[1] for row in connection.execute("PRAGMA table_info(pas_se_para)")}
    if not existing:
        return
    for name, ddl in SE_PARA_EXTRA_COLUMNS:
        if name not in existing:
            connection.execute(f"ALTER TABLE [pas_se_para] ADD COLUMN [{name}] {ddl}")


def parse_se_para_file(path: str | Path | None) -> dict[str, str]:
    """解析 E 格式 se.para 文件中的 <StateEstimationParameter> 键值块。"""
    if path is None:
        return {}
    file_path = Path(path)
    if not file_path.is_file():
        return {}
    values: dict[str, str] = {}
    in_block = False
    for raw_line in file_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "<StateEstimationParameter>":
            in_block = True
            continue
        if line == "</StateEstimationParameter>":
            break
        if not in_block or line.startswith("@") or line.startswith("//"):
            continue
        if line.startswith("#"):
            parts = line[1:].strip().split()
            if len(parts) >= 2:
                values[parts[0]] = parts[1]
    return values


def extract_se_parameters(
    para_file: str | Path | None,
    *,
    do_cycle: int | float = 60,
    calc_trigger: int = 1,
) -> dict[str, Any]:
    """从 se.para 提取全部 SE 算法参数并映射到 pas_se_para 表结构。"""
    raw = parse_se_para_file(para_file)
    tol = _parse_float(raw.get("tol"), DEFAULT_SE_PARAMS["tol"])
    max_iter = _parse_int(raw.get("max_iter"), DEFAULT_SE_PARAMS["max_iterator"])
    max_remove = _parse_int(raw.get("max_remove"), DEFAULT_SE_PARAMS["badnum_max"])
    badnum_step = _parse_int(raw.get("badnum_step"), DEFAULT_SE_PARAMS["badnum_step"])
    bad_threshold = _parse_float(raw.get("bad_threshold"), DEFAULT_SE_PARAMS["baderr_eps"])
    obj_scaling = _parse_float(raw.get("obj_scaling_factor"), DEFAULT_SE_PARAMS["obj_scaling_factor"])
    return {
        "id": 1,
        "max_iterator": max_iter,
        "badnum_max": max_remove,
        "badnum_step": max(1, badnum_step),
        "baderr_eps": bad_threshold,
        "do_cycle": max(1, _parse_int(do_cycle, DEFAULT_SE_PARAMS["do_cycle"])),
        "calc_trigger": _parse_int(calc_trigger, DEFAULT_SE_PARAMS["calc_trigger"]),
        "measqual_eps": tol,
        "obj_scaling_factor": obj_scaling,
        "tol": tol,
        "diff_step": _parse_float(raw.get("diff_step"), DEFAULT_SE_PARAMS["diff_step"]),
        "flat_start": _parse_bool_int(raw.get("flat_start"), DEFAULT_SE_PARAMS["flat_start"]),
        "pseudo_measurement_weight": _parse_float(
            raw.get("pseudo_measurement_weight"),
            DEFAULT_SE_PARAMS["pseudo_measurement_weight"],
        ),
        "targeted_pseudo_measurement_max": _parse_int(
            raw.get("targeted_pseudo_measurement_max"),
            DEFAULT_SE_PARAMS["targeted_pseudo_measurement_max"],
        ),
        "targeted_pseudo_measurement_redundancy_ratio": _parse_float(
            raw.get("targeted_pseudo_measurement_redundancy_ratio"),
            DEFAULT_SE_PARAMS["targeted_pseudo_measurement_redundancy_ratio"],
        ),
        "targeted_pseudo_measurement_step": _parse_int(
            raw.get("targeted_pseudo_measurement_step"),
            DEFAULT_SE_PARAMS["targeted_pseudo_measurement_step"],
        ),
        "voltage_floor": _parse_float(raw.get("voltage_floor"), DEFAULT_SE_PARAMS["voltage_floor"]),
        "min_current_voltage": _parse_float(
            raw.get("min_current_voltage"),
            DEFAULT_SE_PARAMS["min_current_voltage"],
        ),
        "power_flow_tol": _parse_float(raw.get("power_flow_tol"), DEFAULT_SE_PARAMS["power_flow_tol"]),
        "power_flow_max_iter": _parse_int(
            raw.get("power_flow_max_iter"),
            DEFAULT_SE_PARAMS["power_flow_max_iter"],
        ),
        "power_flow_min_voltage": _parse_float(
            raw.get("power_flow_min_voltage"),
            DEFAULT_SE_PARAMS["power_flow_min_voltage"],
        ),
        "updated_at": _utc_now(),
    }


def _row_to_params(row: sqlite3.Row | dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    tol = _parse_float(data.get("tol"), _parse_float(data.get("measqual_eps"), fallback["tol"]))
    if tol <= 0:
        tol = fallback["tol"]
    measqual_eps = _parse_float(data.get("measqual_eps"), tol)
    if measqual_eps <= 0:
        measqual_eps = tol
    return {
        "id": _parse_int(data.get("id"), 1),
        "max_iterator": max(1, _parse_int(data.get("max_iterator"), fallback["max_iterator"])),
        "badnum_max": max(0, _parse_int(data.get("badnum_max"), fallback["badnum_max"])),
        "badnum_step": max(1, _parse_int(data.get("badnum_step"), fallback["badnum_step"])),
        "baderr_eps": max(1e-6, _parse_float(data.get("baderr_eps"), fallback["baderr_eps"])),
        "do_cycle": max(1, _parse_int(data.get("do_cycle"), fallback["do_cycle"])),
        "calc_trigger": _parse_int(data.get("calc_trigger"), fallback["calc_trigger"]),
        "measqual_eps": measqual_eps,
        "obj_scaling_factor": _parse_float(data.get("obj_scaling_factor"), fallback["obj_scaling_factor"]),
        "tol": tol,
        "diff_step": max(1e-12, _parse_float(data.get("diff_step"), fallback["diff_step"])),
        "flat_start": _parse_bool_int(data.get("flat_start"), fallback["flat_start"]),
        "pseudo_measurement_weight": max(
            1e-12,
            _parse_float(data.get("pseudo_measurement_weight"), fallback["pseudo_measurement_weight"]),
        ),
        "targeted_pseudo_measurement_max": max(
            0,
            _parse_int(
                data.get("targeted_pseudo_measurement_max"),
                fallback["targeted_pseudo_measurement_max"],
            ),
        ),
        "targeted_pseudo_measurement_redundancy_ratio": max(
            0.0,
            _parse_float(
                data.get("targeted_pseudo_measurement_redundancy_ratio"),
                fallback["targeted_pseudo_measurement_redundancy_ratio"],
            ),
        ),
        "targeted_pseudo_measurement_step": max(
            1,
            _parse_int(
                data.get("targeted_pseudo_measurement_step"),
                fallback["targeted_pseudo_measurement_step"],
            ),
        ),
        "voltage_floor": max(1e-4, _parse_float(data.get("voltage_floor"), fallback["voltage_floor"])),
        "min_current_voltage": max(
            1e-6,
            _parse_float(data.get("min_current_voltage"), fallback["min_current_voltage"]),
        ),
        "power_flow_tol": max(1e-14, _parse_float(data.get("power_flow_tol"), fallback["power_flow_tol"])),
        "power_flow_max_iter": max(
            1,
            _parse_int(data.get("power_flow_max_iter"), fallback["power_flow_max_iter"]),
        ),
        "power_flow_min_voltage": max(
            1e-6,
            _parse_float(data.get("power_flow_min_voltage"), fallback["power_flow_min_voltage"]),
        ),
        "updated_at": str(data.get("updated_at") or fallback["updated_at"]),
    }


def sync_se_parameters_table(
    connection: sqlite3.Connection,
    para_file: str | Path | None,
    *,
    do_cycle: int | float = 60,
    calc_trigger: int = 1,
    overwrite: bool = False,
) -> dict[str, Any]:
    """确保 pas_se_para 存在有效参数行，并初始化默认 pas_se_weight。

    - 若 pas_se_para 为空或 overwrite=True，从 para_file 提取全量参数写入 id=1；
    - 若 pas_se_para 已有记录且 overwrite=False，保留用户在线调整值，仅补全缺失/空列。
    """
    extracted = extract_se_parameters(para_file, do_cycle=do_cycle, calc_trigger=calc_trigger)
    existing = connection.execute("SELECT * FROM [pas_se_para] ORDER BY id LIMIT 1").fetchone()
    if existing is None or overwrite:
        params = extracted
        columns = list(params.keys())
        quoted = ",".join(f"[{col}]" for col in columns)
        placeholders = ",".join("?" for _ in columns)
        connection.execute(
            f"INSERT OR REPLACE INTO [pas_se_para] ({quoted}) VALUES ({placeholders})",
            tuple(params[col] for col in columns),
        )
    else:
        params = _row_to_params(existing, extracted)
        # 若原表记录存在空扩展列，按提取值回填
        raw_existing = dict(existing)
        if any(raw_existing.get(col) is None for col in params):
            columns = [col for col in params if col != "id"]
            assignments = ",".join(f"[{col}]=?" for col in columns)
            connection.execute(
                f"UPDATE [pas_se_para] SET {assignments} WHERE id=?",
                tuple(params[col] for col in columns) + (params["id"],),
            )
    weight_count = connection.execute("SELECT COUNT(*) FROM [pas_se_weight]").fetchone()[0]
    if weight_count == 0:
        connection.executemany(
            "INSERT OR IGNORE INTO [pas_se_weight](meas_type, default_weight) VALUES (?, ?)",
            DEFAULT_SE_WEIGHTS,
        )
    return params


def render_se_para_text(params: dict[str, Any]) -> str:
    """将 pas_se_para 参数字典渲染为内核可读取的 E 格式 se.para 文本。"""
    entries = (
        ("tol", params["tol"]),
        ("max_iter", params["max_iterator"]),
        ("diff_step", params["diff_step"]),
        ("flat_start", int(bool(params["flat_start"]))),
        ("bad_threshold", params["baderr_eps"]),
        ("max_remove", params["badnum_max"]),
        ("pseudo_measurement_weight", params["pseudo_measurement_weight"]),
        ("targeted_pseudo_measurement_max", params["targeted_pseudo_measurement_max"]),
        ("targeted_pseudo_measurement_redundancy_ratio", params["targeted_pseudo_measurement_redundancy_ratio"]),
        ("targeted_pseudo_measurement_step", params["targeted_pseudo_measurement_step"]),
        ("voltage_floor", params["voltage_floor"]),
        ("min_current_voltage", params["min_current_voltage"]),
        ("power_flow_tol", params["power_flow_tol"]),
        ("power_flow_max_iter", params["power_flow_max_iter"]),
        ("power_flow_min_voltage", params["power_flow_min_voltage"]),
    )
    lines = ["<StateEstimationParameter>", "@ name value"]
    for key, value in entries:
        lines.append(f"# {key} {value}")
    lines.append("</StateEstimationParameter>")
    return "\n".join(lines) + "\n"


@contextmanager
def se_parameter_file(
    para_file: str | Path | None,
    *,
    params: dict[str, Any] | None = None,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    """为内核提供参数文件：若传入来自 pas_se_para 的参数则写入临时 se.para。"""
    if params is None:
        if para_file is None:
            raise FileNotFoundError("SE parameter_file is required when pas_se_para params are not provided")
        resolved = Path(para_file)
        yield resolved, extract_se_parameters(resolved)
        return
    with tempfile.TemporaryDirectory(prefix="pas_se_para_") as directory:
        target = Path(directory) / "se.para"
        target.write_text(render_se_para_text(params), encoding="utf-8")
        yield target, dict(params)
