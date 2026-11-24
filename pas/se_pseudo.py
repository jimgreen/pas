"""状态估计（SE）伪量测与伪状态配置、注入及结果持久化模块。"""

from __future__ import annotations

import math
import sqlite3
import time
from typing import Any

from .input_store import SE_DEVICE_RESULT_METRICS, SE_SOLVER_METRICS, _default_metric_unit
from .se_log import record_se_log, utc_now

# 伪量测定义表 pas_se_psemeas_define 的结构化扩展列（幂等追加，兼容旧 dbdef 列）
PSEMEAS_DEFINE_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("device_type", "TEXT NOT NULL DEFAULT ''"),
    ("device_idx", "INTEGER"),
    ("metric", "TEXT NOT NULL DEFAULT ''"),
    ("se_type", "TEXT NOT NULL DEFAULT ''"),
    ("unit", "TEXT NOT NULL DEFAULT ''"),
    ("source_mode", "TEXT NOT NULL DEFAULT 'manual'"),
    ("note", "TEXT NOT NULL DEFAULT ''"),
    ("updated_at", "TEXT NOT NULL DEFAULT ''"),
)

# 伪状态定义表 pas_se_psestat_define 的结构化扩展列
PSESTAT_DEFINE_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("device_type", "TEXT NOT NULL DEFAULT ''"),
    ("device_idx", "INTEGER"),
    ("metric", "TEXT NOT NULL DEFAULT 'status'"),
    ("note", "TEXT NOT NULL DEFAULT ''"),
    ("updated_at", "TEXT NOT NULL DEFAULT ''"),
)

# 伪状态支持的设备类型与对应拓扑覆盖字段
PSEUDO_STAT_DEVICE_FIELDS: dict[str, tuple[str, str]] = {
    "ACBreak": ("status", "分/合位状态 (0=分, 1=合)"),
    "DCBreak": ("status", "分/合位状态 (0=分, 1=合)"),
    "ACGenerator": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "DCGenerator": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "ACLoad": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "DCLoad": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "ACBranch": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "DCBranch": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "ACZeroBranch": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "DCDCConverter": ("run_stat", "运行状态 (0=停运, 1=运行)"),
    "DCACConverter": ("run_stat", "运行状态 (0=停运, 1=运行)"),
}


def _meas_type_code(se_type: str) -> int:
    """将 SE 量测类型字符串转为稳定的整型编码（兼容 pas_se_psemeas_define.meas_type）。"""
    import zlib

    return zlib.crc32(str(se_type).encode("utf-8")) & 0x7FFFFFFF


def ensure_se_pseudo_columns(conn: sqlite3.Connection) -> int:
    """幂等补齐伪量测/伪状态定义表结构化列，并清理历史 dbdef 误灌入的运行时脏行。"""
    for table_name, extra_cols in (
        ("pas_se_psemeas_define", PSEMEAS_DEFINE_EXTRA_COLUMNS),
        ("pas_se_psestat_define", PSESTAT_DEFINE_EXTRA_COLUMNS),
    ):
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info([{table_name}])")}
        if not existing:
            continue
        for col_name, col_def in extra_cols:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE [{table_name}] ADD COLUMN [{col_name}] {col_def}")

    # 清理历史上 build_dbdef_rows 每次运行误写入 pas_se_psemeas_define 的结果行（id >= 1_000_000 且未标为人工配置）
    cols = {row[1] for row in conn.execute("PRAGMA table_info([pas_se_psemeas_define])")}
    cleaned = 0
    if "device_type" in cols:
        dirty = conn.execute(
            """SELECT 1 FROM pas_se_psemeas_define
               WHERE id >= 1000000 AND COALESCE(device_type, '') = '' AND COALESCE(metric, '') = ''
               LIMIT 1"""
        ).fetchone()
        if dirty is not None:
            cur = conn.execute(
                """DELETE FROM pas_se_psemeas_define
                   WHERE id >= 1000000 AND COALESCE(device_type, '') = '' AND COALESCE(metric, '') = ''"""
            )
            cleaned = max(0, cur.rowcount)
    return cleaned


def _validate_pseudo_meas_payload(payload: dict[str, Any], units: dict[str, Any] | None = None) -> dict[str, Any]:
    dev_type = str(payload.get("device_type") or "").strip()
    if dev_type not in SE_SOLVER_METRICS:
        raise ValueError(f"不支持的伪量测设备类型: {dev_type}")
    metric = str(payload.get("metric") or "").strip()
    solver_map = SE_SOLVER_METRICS[dev_type]
    if metric not in solver_map:
        raise ValueError(f"设备类型 {dev_type} 不支持伪量测指标: {metric}")
    se_type = solver_map[metric]

    dev_name = str(payload.get("device_name") or payload.get("dev_name") or "").strip()
    if not dev_name:
        raise ValueError("必须选择目标设备")
    dev_idx_raw = payload.get("device_idx")
    dev_idx = int(dev_idx_raw) if dev_idx_raw not in (None, "") else None

    raw_val = payload.get("meas_value", payload.get("value"))
    if isinstance(raw_val, bool) or raw_val is None or raw_val == "":
        raise ValueError("伪量测设定值必须为有效数值")
    try:
        value = float(raw_val)
    except (TypeError, ValueError) as exc:
        raise ValueError("伪量测设定值必须为有效数值") from exc
    if not math.isfinite(value):
        raise ValueError("伪量测设定值必须为有限数值")

    raw_weight = payload.get("meas_weight", payload.get("weight", 1e-4))
    if isinstance(raw_weight, bool) or raw_weight is None or raw_weight == "":
        weight = 1e-4
    else:
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError) as exc:
            raise ValueError("伪量测权重必须为正数") from exc
    if not math.isfinite(weight) or not 1e-12 <= weight <= 1e6:
        raise ValueError("伪量测权重超出允许范围 [1e-12, 1e6]")

    useflag_raw = payload.get("meas_useflag", payload.get("enabled", 1))
    useflag = int(bool(int(useflag_raw))) if not isinstance(useflag_raw, bool) else int(useflag_raw)

    source_mode = str(payload.get("source_mode") or "manual").strip()
    if source_mode not in {"manual", "bad_replace", "zero_injection"}:
        source_mode = "manual"

    unit = str(payload.get("unit") or "").strip() or _default_metric_unit(se_type, units or {"u_unit": "V", "p_unit": "kW", "i_unit": "A"})
    meas_name = str(payload.get("meas_name") or "").strip() or (
        f"{dev_type}.{dev_idx}.{metric}" if dev_idx is not None else f"{dev_type}.{dev_name}.{metric}"
    )
    note = str(payload.get("note") or "").strip()[:240]
    return {
        "device_type": dev_type,
        "device_idx": dev_idx,
        "dev_name": dev_name,
        "metric": metric,
        "se_type": se_type,
        "meas_type": _meas_type_code(se_type),
        "meas_name": meas_name,
        "meas_value": value,
        "meas_weight": weight,
        "meas_useflag": useflag,
        "unit": unit,
        "source_mode": source_mode,
        "note": note,
    }


def list_pseudo_meas_defines(
    conn: sqlite3.Connection,
    *,
    device_type: str = "",
    enabled_only: bool = False,
    q: str = "",
) -> list[dict[str, Any]]:
    """读取人工配置的伪量测定义列表（pas_se_psemeas_define）。"""
    ensure_se_pseudo_columns(conn)
    clauses: list[str] = []
    params: list[Any] = []
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if enabled_only:
        clauses.append("COALESCE(meas_useflag, 1) = 1")
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(dev_name LIKE ? OR meas_name LIKE ? OR metric LIKE ? OR note LIKE ?)")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT id, meas_id, meas_name, dev_name, device_type, device_idx, metric, se_type, unit,
                   meas_type, meas_value, meas_weight, meas_useflag, source_mode, note, updated_at, meas_time
            FROM pas_se_psemeas_define {where}
            ORDER BY COALESCE(meas_useflag, 1) DESC, id DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def save_pseudo_meas_define(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    define_id: int | None = None,
    units: dict[str, Any] | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """新增或修改一条伪量测定义，并写入统一 SE 运行日志（stage='pseudo_change'）。"""
    ensure_se_pseudo_columns(conn)
    data = _validate_pseudo_meas_payload(payload, units=units)
    now_str = utc_now()
    now_epoch = int(time.time())

    if define_id is None and payload.get("id") not in (None, ""):
        define_id = int(payload["id"])

    # 若未指定 id，按 (device_type, dev_name, metric) 做去重更新
    if define_id is None:
        existing = conn.execute(
            """SELECT id FROM pas_se_psemeas_define
               WHERE device_type = ? AND dev_name = ? AND metric = ? LIMIT 1""",
            (data["device_type"], data["dev_name"], data["metric"]),
        ).fetchone()
        if existing is not None:
            define_id = int(existing["id"])

    if define_id is not None:
        exists = conn.execute("SELECT id FROM pas_se_psemeas_define WHERE id = ?", (define_id,)).fetchone()
        if exists is None:
            raise ValueError(f"未找到伪量测定义 #{define_id}")
        conn.execute(
            """UPDATE pas_se_psemeas_define
               SET meas_name=?, dev_name=?, device_type=?, device_idx=?, metric=?, se_type=?, unit=?,
                   meas_type=?, meas_value=?, meas_weight=?, meas_useflag=?, source_mode=?, note=?,
                   meas_time=?, updated_at=?
               WHERE id=?""",
            (
                data["meas_name"],
                data["dev_name"],
                data["device_type"],
                data["device_idx"],
                data["metric"],
                data["se_type"],
                data["unit"],
                data["meas_type"],
                data["meas_value"],
                data["meas_weight"],
                data["meas_useflag"],
                data["source_mode"],
                data["note"],
                now_epoch,
                now_str,
                define_id,
            ),
        )
        action = "update"
    else:
        next_id = int(
            conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM pas_se_psemeas_define WHERE id < 1000000").fetchone()[0] or 1
        )
        conn.execute(
            """INSERT INTO pas_se_psemeas_define(
                   id, meas_id, meas_name, dev_name, meas_type, meas_value, meas_weight,
                   meas_useflag, meas_st, meas_mpsys, meas_time,
                   device_type, device_idx, metric, se_type, unit, source_mode, note, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                next_id,
                next_id,
                data["meas_name"],
                data["dev_name"],
                data["meas_type"],
                data["meas_value"],
                data["meas_weight"],
                data["meas_useflag"],
                now_epoch,
                data["device_type"],
                data["device_idx"],
                data["metric"],
                data["se_type"],
                data["unit"],
                data["source_mode"],
                data["note"],
                now_str,
            ),
        )
        define_id = next_id
        action = "create"

    record_se_log(
        conn,
        level="INFO",
        stage="pseudo_change",
        source=source,
        message=f"{'新增' if action == 'create' else '更新'}伪量测 #{define_id}: {data['dev_name']}.{data['metric']} = {data['meas_value']} {data['unit']}",
        detail={"action": action, "define_id": define_id, **data},
    )
    row = conn.execute("SELECT * FROM pas_se_psemeas_define WHERE id = ?", (define_id,)).fetchone()
    return dict(row)


def delete_pseudo_meas_define(conn: sqlite3.Connection, define_id: int, *, source: str = "operator") -> bool:
    """删除一条伪量测定义并记录审计日志。"""
    ensure_se_pseudo_columns(conn)
    row = conn.execute("SELECT * FROM pas_se_psemeas_define WHERE id = ?", (int(define_id),)).fetchone()
    if row is None:
        return False
    info = dict(row)
    conn.execute("DELETE FROM pas_se_psemeas_define WHERE id = ?", (int(define_id),))
    record_se_log(
        conn,
        level="WARN",
        stage="pseudo_change",
        source=source,
        message=f"删除伪量测定义 #{define_id}: {info.get('dev_name', '')}.{info.get('metric', '')}",
        detail={"action": "delete", "define_id": int(define_id), "dev_name": info.get("dev_name"), "metric": info.get("metric")},
    )
    return True


def list_pseudo_stat_defines(
    conn: sqlite3.Connection,
    *,
    device_type: str = "",
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    """读取伪状态定义列表（pas_se_psestat_define）。"""
    ensure_se_pseudo_columns(conn)
    clauses: list[str] = []
    params: list[Any] = []
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if enabled_only:
        clauses.append("COALESCE(stat_useflag, 1) = 1")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT id, stat_id, stat_name, dev_name, device_type, device_idx, metric,
                   stat_type, stat_value, stat_useflag, note, updated_at
            FROM pas_se_psestat_define {where}
            ORDER BY COALESCE(stat_useflag, 1) DESC, id DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def save_pseudo_stat_define(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    define_id: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """新增或修改一条伪状态定义（断路器分合位或设备运行状态覆盖）。"""
    ensure_se_pseudo_columns(conn)
    dev_type = str(payload.get("device_type") or "").strip()
    if dev_type not in PSEUDO_STAT_DEVICE_FIELDS:
        raise ValueError(f"不支持的伪状态设备类型: {dev_type}")
    metric = PSEUDO_STAT_DEVICE_FIELDS[dev_type][0]
    dev_name = str(payload.get("device_name") or payload.get("dev_name") or "").strip()
    if not dev_name:
        raise ValueError("必须选择目标设备")
    dev_idx_raw = payload.get("device_idx")
    dev_idx = int(dev_idx_raw) if dev_idx_raw not in (None, "") else None

    raw_val = payload.get("stat_value", payload.get("value"))
    if raw_val not in (0, 1, "0", "1", 0.0, 1.0):
        raise ValueError("伪状态设定值仅支持 0（分/停运）或 1（合/运行）")
    stat_val = int(float(raw_val))

    useflag_raw = payload.get("stat_useflag", payload.get("enabled", 1))
    useflag = int(bool(int(useflag_raw))) if not isinstance(useflag_raw, bool) else int(useflag_raw)
    note = str(payload.get("note") or "").strip()[:240]
    stat_name = str(payload.get("stat_name") or "").strip() or f"{dev_type}.{dev_name}.{metric}"
    stat_type = 1 if metric == "status" else 2
    now_str = utc_now()

    if define_id is None and payload.get("id") not in (None, ""):
        define_id = int(payload["id"])
    if define_id is None:
        existing = conn.execute(
            "SELECT id FROM pas_se_psestat_define WHERE device_type=? AND dev_name=? AND metric=? LIMIT 1",
            (dev_type, dev_name, metric),
        ).fetchone()
        if existing is not None:
            define_id = int(existing["id"])

    if define_id is not None:
        exists = conn.execute("SELECT id FROM pas_se_psestat_define WHERE id=?", (define_id,)).fetchone()
        if exists is None:
            raise ValueError(f"未找到伪状态定义 #{define_id}")
        conn.execute(
            """UPDATE pas_se_psestat_define
               SET stat_name=?, dev_name=?, device_type=?, device_idx=?, metric=?,
                   stat_type=?, stat_value=?, stat_useflag=?, note=?, updated_at=?
               WHERE id=?""",
            (stat_name, dev_name, dev_type, dev_idx, metric, stat_type, float(stat_val), useflag, note, now_str, define_id),
        )
        action = "update"
    else:
        next_id = int(conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM pas_se_psestat_define").fetchone()[0] or 1)
        conn.execute(
            """INSERT INTO pas_se_psestat_define(
                   id, stat_id, stat_name, dev_name, stat_type, stat_value, stat_useflag,
                   stat_st, stat_mpsys, device_type, device_idx, metric, note, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?)""",
            (next_id, next_id, stat_name, dev_name, stat_type, float(stat_val), useflag, dev_type, dev_idx, metric, note, now_str),
        )
        define_id = next_id
        action = "create"

    record_se_log(
        conn,
        level="INFO",
        stage="pseudo_change",
        source=source,
        message=f"{'新增' if action == 'create' else '更新'}伪状态 #{define_id}: {dev_name}.{metric} = {stat_val}",
        detail={"action": action, "kind": "pseudo_stat", "define_id": define_id, "device_type": dev_type, "dev_name": dev_name, "metric": metric, "stat_value": stat_val, "enabled": useflag},
    )
    row = conn.execute("SELECT * FROM pas_se_psestat_define WHERE id=?", (define_id,)).fetchone()
    return dict(row)


def delete_pseudo_stat_define(conn: sqlite3.Connection, define_id: int, *, source: str = "operator") -> bool:
    """删除一条伪状态定义并写入运行日志。"""
    ensure_se_pseudo_columns(conn)
    row = conn.execute("SELECT * FROM pas_se_psestat_define WHERE id=?", (int(define_id),)).fetchone()
    if row is None:
        return False
    info = dict(row)
    conn.execute("DELETE FROM pas_se_psestat_define WHERE id=?", (int(define_id),))
    record_se_log(
        conn,
        level="WARN",
        stage="pseudo_change",
        source=source,
        message=f"删除伪状态定义 #{define_id}: {info.get('dev_name', '')}.{info.get('metric', '')}",
        detail={"action": "delete", "kind": "pseudo_stat", "define_id": int(define_id), "dev_name": info.get("dev_name")},
    )
    return True


def store_se_pseudo_results(
    conn: sqlite3.Connection,
    run_id: int,
    calc_time: str,
    measurements: list[dict[str, Any]],
) -> int:
    """原子刷新最新断面伪量测结果表 se_pseudo_result，区分人工定义与内核自动补充。"""
    pseudo_rows = [
        row
        for row in measurements
        if str(row.get("source") or "").lower() == "pseudo"
        or bool(row.get("is_pseudo"))
        or "pseudo" in str(row.get("reason") or "").lower()
    ]
    conn.execute("DELETE FROM se_pseudo_result")
    conn.executemany(
        """INSERT INTO se_pseudo_result(
               id, run_id, calc_time, meas_id, meas_name, device_type, device_idx, device_name,
               metric, meas_type, unit, pseudo_value, se_value, residual, weight,
               origin, define_id, reason
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            (
                seq,
                run_id,
                calc_time,
                int(row.get("idx", seq)),
                str(row.get("name", "")),
                str(row.get("device_type", "")),
                row.get("device_idx"),
                str(row.get("device_name", "")),
                str(row.get("metric", "")),
                str(row.get("meas_type", "")),
                str(row.get("unit", "")),
                row.get("value"),
                row.get("estimated_value"),
                row.get("residual"),
                row.get("weight"),
                str(row.get("pseudo_origin") or ("user_defined" if row.get("pseudo_define_id") else "kernel_auto")),
                row.get("pseudo_define_id"),
                str(row.get("reason") or "observability_pseudo"),
            )
            for seq, row in enumerate(pseudo_rows, 1)
        ),
    )
    return len(pseudo_rows)


def list_se_pseudo_results(
    conn: sqlite3.Connection,
    *,
    origin: str = "all",
    device_type: str = "",
    q: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """查询最新断面伪量测结果（se_pseudo_result）。"""
    clauses: list[str] = []
    params: list[Any] = []
    if origin in {"user_defined", "kernel_auto"}:
        clauses.append("origin = ?")
        params.append(origin)
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(device_name LIKE ? OR meas_name LIKE ? OR metric LIKE ? OR reason LIKE ?)")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = int(conn.execute(f"SELECT COUNT(*) FROM se_pseudo_result {where}", params).fetchone()[0] or 0)
    rows = [
        dict(r)
        for r in conn.execute(
            f"""SELECT * FROM se_pseudo_result {where}
                ORDER BY CASE WHEN origin = 'user_defined' THEN 0 ELSE 1 END, id ASC
                LIMIT ? OFFSET ?""",
            [*params, int(limit), int(offset)],
        )
    ]
    return {"rows": rows, "total": total, "limit": int(limit), "offset": int(offset)}


def pseudo_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    """汇总伪量测页面顶部 KPI 与最近运行关联信息。"""
    ensure_se_pseudo_columns(conn)
    defined_total = int(conn.execute("SELECT COUNT(*) FROM pas_se_psemeas_define").fetchone()[0] or 0)
    defined_enabled = int(
        conn.execute("SELECT COUNT(*) FROM pas_se_psemeas_define WHERE COALESCE(meas_useflag, 1) = 1").fetchone()[0] or 0
    )
    stat_total = int(conn.execute("SELECT COUNT(*) FROM pas_se_psestat_define").fetchone()[0] or 0)
    stat_enabled = int(
        conn.execute("SELECT COUNT(*) FROM pas_se_psestat_define WHERE COALESCE(stat_useflag, 1) = 1").fetchone()[0] or 0
    )
    res_total = int(conn.execute("SELECT COUNT(*) FROM se_pseudo_result").fetchone()[0] or 0)
    res_user = int(
        conn.execute("SELECT COUNT(*) FROM se_pseudo_result WHERE origin = 'user_defined'").fetchone()[0] or 0
    )
    res_auto = int(
        conn.execute("SELECT COUNT(*) FROM se_pseudo_result WHERE origin = 'kernel_auto'").fetchone()[0] or 0
    )
    latest_run = conn.execute(
        "SELECT run_id, calc_time, converged, observable, pseudo_count FROM se_statistics ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    return {
        "defined_total": defined_total,
        "defined_enabled": defined_enabled,
        "stat_total": stat_total,
        "stat_enabled": stat_enabled,
        "result_total": res_total,
        "result_user": res_user,
        "result_auto": res_auto,
        "latest_run": dict(latest_run) if latest_run is not None else None,
        "supported_meas_metrics": {k: dict(v) for k, v in SE_SOLVER_METRICS.items()},
        "supported_stat_types": {k: {"metric": v[0], "label": v[1]} for k, v in PSEUDO_STAT_DEVICE_FIELDS.items()},
    }
