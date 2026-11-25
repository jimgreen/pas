"""状态估计（SE）量测权重规则管理与输入权重覆盖匹配模块。"""

from __future__ import annotations

import math
import sqlite3
from typing import Any

from .input_store import SE_SOLVER_METRICS
from .se_log import record_se_log, utc_now


def list_weight_rules(
    conn: sqlite3.Connection,
    *,
    enabled_only: bool = False,
    device_type: str = "",
    q: str = "",
) -> list[dict[str, Any]]:
    """查询量测权重覆盖规则（se_weight_rule）。"""
    clauses: list[str] = []
    params: list[Any] = []
    if enabled_only:
        clauses.append("enabled = 1")
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(device_type LIKE ? OR device_name LIKE ? OR metric LIKE ? OR note LIKE ?)")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT * FROM se_weight_rule {where}
            ORDER BY enabled DESC, CASE WHEN scope = 'device' THEN 0 ELSE 1 END, id DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def save_weight_rule(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    rule_id: int | None = None,
) -> dict[str, Any]:
    """新增或更新一条量测权重规则，并写入 param_change 审计日志。"""
    scope = str(payload.get("scope") or "device_type").strip()
    if scope not in {"device_type", "device"}:
        raise ValueError("scope 仅支持 device_type 或 device")
    dev_type = str(payload.get("device_type") or "").strip()
    if dev_type not in SE_SOLVER_METRICS:
        raise ValueError(f"不支持的设备类型: {dev_type}")
    metric = str(payload.get("metric") or "").strip()
    if metric not in SE_SOLVER_METRICS[dev_type]:
        raise ValueError(f"设备类型 {dev_type} 不支持指标: {metric}")
    dev_name = "*" if scope == "device_type" else str(payload.get("device_name") or "").strip()
    if scope == "device" and not dev_name:
        raise ValueError("单设备权重规则必须指定设备名称")
    dev_idx_raw = payload.get("device_idx")
    dev_idx = int(dev_idx_raw) if (scope == "device" and dev_idx_raw not in (None, "")) else None

    try:
        weight = float(payload.get("weight"))
    except (TypeError, ValueError) as exc:
        raise ValueError("权重必须为有效正数") from exc
    if not math.isfinite(weight) or not (1e-9 <= weight <= 1e9):
        raise ValueError("权重必须在 [1e-9, 1e9] 范围内")

    enabled_raw = payload.get("enabled", 1)
    enabled = int(bool(int(enabled_raw))) if not isinstance(enabled_raw, bool) else int(enabled_raw)
    note = str(payload.get("note") or "").strip()[:240]
    now = utc_now()

    if rule_id is None and payload.get("id") not in (None, ""):
        rule_id = int(payload["id"])

    if rule_id is None:
        existing = conn.execute(
            "SELECT id FROM se_weight_rule WHERE scope=? AND device_type=? AND device_name=? AND metric=? LIMIT 1",
            (scope, dev_type, dev_name, metric),
        ).fetchone()
        if existing is not None:
            rule_id = int(existing["id"])

    if rule_id is not None:
        exists = conn.execute("SELECT id FROM se_weight_rule WHERE id = ?", (rule_id,)).fetchone()
        if exists is None:
            raise ValueError(f"未找到量测权重规则 #{rule_id}")
        conn.execute(
            """UPDATE se_weight_rule
               SET scope=?, device_type=?, device_idx=?, device_name=?, metric=?, weight=?, enabled=?, note=?, updated_at=?
               WHERE id=?""",
            (scope, dev_type, dev_idx, dev_name, metric, weight, enabled, note, now, rule_id),
        )
        action = "update"
    else:
        cur = conn.execute(
            """INSERT INTO se_weight_rule(scope, device_type, device_idx, device_name, metric, weight, enabled, note, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scope, dev_type, dev_idx, dev_name, metric, weight, enabled, note, now),
        )
        rule_id = int(cur.lastrowid)
        action = "create"

    row = dict(conn.execute("SELECT * FROM se_weight_rule WHERE id = ?", (rule_id,)).fetchone())
    record_se_log(
        conn,
        level="INFO",
        stage="param_change",
        source="operator",
        message=f"{'新增' if action == 'create' else '更新'}量测权重 #{rule_id}: {dev_type}.{dev_name}.{metric} -> {weight:g}",
        detail={"action": action, "rule_id": rule_id, "scope": scope, "weight": weight},
    )
    return row


def delete_weight_rule(conn: sqlite3.Connection, rule_id: int) -> bool:
    """删除量测权重规则并记录审计日志。"""
    row = conn.execute("SELECT * FROM se_weight_rule WHERE id = ?", (int(rule_id),)).fetchone()
    if row is None:
        return False
    conn.execute("DELETE FROM se_weight_rule WHERE id = ?", (int(rule_id),))
    record_se_log(
        conn,
        level="WARN",
        stage="param_change",
        source="operator",
        message=f"删除量测权重 #{rule_id}: {row['device_type']}.{row['device_name']}.{row['metric']}",
        detail={"action": "delete", "rule_id": int(rule_id)},
    )
    return True


def resolve_measurement_weight(
    rules: list[dict[str, Any]] | None,
    *,
    device_type: str,
    device_name: str,
    metric: str,
    default_weight: float,
) -> float:
    """按单设备优先、设备类次之的优先级匹配生效的量测权重覆盖值。"""
    if not rules:
        return default_weight
    type_fallback: float | None = None
    for rule in rules:
        if not int(rule.get("enabled", 1)):
            continue
        if str(rule.get("device_type") or "") != device_type or str(rule.get("metric") or "") != metric:
            continue
        scope = str(rule.get("scope") or "device_type")
        if scope == "device" and str(rule.get("device_name") or "") == device_name:
            return float(rule["weight"])
        if scope == "device_type" and type_fallback is None:
            type_fallback = float(rule["weight"])
    return type_fallback if type_fallback is not None else default_weight
