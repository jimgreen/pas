"""状态估计（SE）预过滤规则配置、输入拦截评估、结果持久化与分布分析模块。"""

from __future__ import annotations

import math
import sqlite3
from typing import Any

from .input_store import SE_SOLVER_METRICS, _default_metric_unit
from .se_log import record_se_log, utc_now


def _parse_opt_float(val: Any, name: str) -> float | None:
    if val is None or val == "":
        return None
    if isinstance(val, bool):
        raise ValueError(f"{name} 必须为数值")
    try:
        num = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须为数值") from exc
    if not math.isfinite(num):
        raise ValueError(f"{name} 必须为有限数值")
    return num


def list_prefilter_rules(
    conn: sqlite3.Connection,
    *,
    enabled_only: bool = False,
    device_type: str = "",
    rule_type: str = "",
    q: str = "",
) -> list[dict[str, Any]]:
    """查询预过滤规则配置列表（se_prefilter_rule）。"""
    clauses: list[str] = []
    params: list[Any] = []
    if enabled_only:
        clauses.append("enabled = 1")
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if rule_type in {"range", "force_filter"}:
        clauses.append("rule_type = ?")
        params.append(rule_type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(device_name LIKE ? OR metric LIKE ? OR note LIKE ?)")
        params.extend([like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT * FROM se_prefilter_rule {where}
            ORDER BY enabled DESC, CASE WHEN scope = 'device' THEN 0 ELSE 1 END, id DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def save_prefilter_rule(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    rule_id: int | None = None,
    units: dict[str, Any] | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """新增或更新预过滤规则，并记录至 se_run_log（stage='prefilter_change'）。"""
    scope = str(payload.get("scope") or "device_type").strip()
    if scope not in {"device_type", "device"}:
        raise ValueError("scope 仅支持 device_type 或 device")
    dev_type = str(payload.get("device_type") or "").strip()
    if dev_type not in SE_SOLVER_METRICS:
        raise ValueError(f"不支持的设备类型: {dev_type}")
    metric = str(payload.get("metric") or "").strip()
    if metric not in SE_SOLVER_METRICS[dev_type]:
        raise ValueError(f"设备类型 {dev_type} 不支持指标: {metric}")
    se_type = SE_SOLVER_METRICS[dev_type][metric]

    if scope == "device_type":
        dev_name = "*"
        dev_idx = None
    else:
        dev_name = str(payload.get("device_name") or "").strip()
        if not dev_name or dev_name == "*":
            raise ValueError("按单设备生效时必须选择目标设备")
        idx_raw = payload.get("device_idx")
        dev_idx = int(idx_raw) if idx_raw not in (None, "") else None

    rule_type = str(payload.get("rule_type") or "range").strip()
    if rule_type not in {"range", "force_filter"}:
        raise ValueError("rule_type 仅支持 range 或 force_filter")

    min_val = _parse_opt_float(payload.get("min_value"), "min_value")
    max_val = _parse_opt_float(payload.get("max_value"), "max_value")
    if rule_type == "range":
        if min_val is None and max_val is None:
            raise ValueError("越限过滤规则至少需要设置下限或上限之一")
        if min_val is not None and max_val is not None and min_val > max_val:
            raise ValueError("下限 min_value 不能大于上限 max_value")
    else:
        min_val = None
        max_val = None

    enabled_raw = payload.get("enabled", 1)
    enabled = int(bool(int(enabled_raw))) if not isinstance(enabled_raw, bool) else int(enabled_raw)
    note = str(payload.get("note") or "").strip()[:240]
    unit = str(payload.get("unit") or "").strip() or _default_metric_unit(
        se_type, units or {"u_unit": "V", "p_unit": "kW", "i_unit": "A"}
    )
    now_str = utc_now()

    if rule_id is None and payload.get("id") not in (None, ""):
        rule_id = int(payload["id"])
    if rule_id is None:
        existing = conn.execute(
            "SELECT id FROM se_prefilter_rule WHERE scope=? AND device_type=? AND device_name=? AND metric=? LIMIT 1",
            (scope, dev_type, dev_name, metric),
        ).fetchone()
        if existing is not None:
            rule_id = int(existing["id"])

    if rule_id is not None:
        exists = conn.execute("SELECT id FROM se_prefilter_rule WHERE id=?", (rule_id,)).fetchone()
        if exists is None:
            raise ValueError(f"未找到预过滤规则 #{rule_id}")
        conn.execute(
            """UPDATE se_prefilter_rule
               SET scope=?, device_type=?, device_idx=?, device_name=?, metric=?, meas_type=?,
                   unit=?, rule_type=?, min_value=?, max_value=?, enabled=?, note=?, updated_at=?
               WHERE id=?""",
            (scope, dev_type, dev_idx, dev_name, metric, se_type, unit, rule_type, min_val, max_val, enabled, note, now_str, rule_id),
        )
        op = "update"
    else:
        cur = conn.execute(
            """INSERT INTO se_prefilter_rule(
                   scope, device_type, device_idx, device_name, metric, meas_type,
                   unit, rule_type, min_value, max_value, enabled, note, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scope, dev_type, dev_idx, dev_name, metric, se_type, unit, rule_type, min_val, max_val, enabled, note, now_str),
        )
        rule_id = int(cur.lastrowid)
        op = "create"

    target_desc = f"{dev_type}.{metric}" if scope == "device_type" else f"{dev_name}.{metric}"
    record_se_log(
        conn,
        level="INFO",
        stage="prefilter_change",
        source=source,
        message=f"{'新增' if op == 'create' else '更新'}预过滤规则 #{rule_id}: {target_desc} ({rule_type}, enabled={enabled})",
        detail={
            "op": op,
            "rule_id": rule_id,
            "scope": scope,
            "device_type": dev_type,
            "device_name": dev_name,
            "metric": metric,
            "rule_type": rule_type,
            "min_value": min_val,
            "max_value": max_val,
            "enabled": enabled,
        },
    )
    row = conn.execute("SELECT * FROM se_prefilter_rule WHERE id=?", (rule_id,)).fetchone()
    return dict(row)


def delete_prefilter_rule(conn: sqlite3.Connection, rule_id: int, *, source: str = "operator") -> bool:
    """删除预过滤规则并记录审计日志。"""
    row = conn.execute("SELECT * FROM se_prefilter_rule WHERE id=?", (int(rule_id),)).fetchone()
    if row is None:
        return False
    info = dict(row)
    conn.execute("DELETE FROM se_prefilter_rule WHERE id=?", (int(rule_id),))
    record_se_log(
        conn,
        level="WARN",
        stage="prefilter_change",
        source=source,
        message=f"删除预过滤规则 #{rule_id}: {info.get('device_type', '')}.{info.get('device_name', '*')}.{info.get('metric', '')}",
        detail={"op": "delete", "rule_id": int(rule_id), "device_type": info.get("device_type"), "device_name": info.get("device_name"), "metric": info.get("metric")},
    )
    return True


def evaluate_prefilter_rule(
    rules: list[dict[str, Any]],
    *,
    device_type: str,
    device_name: str,
    metric: str,
    value: float,
) -> dict[str, Any] | None:
    """按单设备优先、设备类次之的顺序校验量测是否命中预过滤规则。"""
    if not rules:
        return None
    matched_device: list[dict[str, Any]] = []
    matched_type: list[dict[str, Any]] = []
    for rule in rules:
        if not int(rule.get("enabled", 1)):
            continue
        if str(rule.get("device_type") or "") != device_type or str(rule.get("metric") or "") != metric:
            continue
        if rule.get("scope") == "device" and str(rule.get("device_name") or "") == device_name:
            matched_device.append(rule)
        elif rule.get("scope") == "device_type":
            matched_type.append(rule)

    for rule in (*matched_device, *matched_type):
        rtype = str(rule.get("rule_type") or "range")
        if rtype == "force_filter":
            return {
                "rule_id": rule.get("id"),
                "min_value": None,
                "max_value": None,
                "reason": str(rule.get("note") or "rule_force_filter"),
            }
        min_v = rule.get("min_value")
        max_v = rule.get("max_value")
        if min_v is not None and value < float(min_v):
            return {
                "rule_id": rule.get("id"),
                "min_value": float(min_v),
                "max_value": float(max_v) if max_v is not None else None,
                "reason": f"below_min({value:.3f} < {float(min_v):.3f})",
            }
        if max_v is not None and value > float(max_v):
            return {
                "rule_id": rule.get("id"),
                "min_value": float(min_v) if min_v is not None else None,
                "max_value": float(max_v),
                "reason": f"above_max({value:.3f} > {float(max_v):.3f})",
            }
    return None


def store_se_prefilter_results(
    conn: sqlite3.Connection,
    run_id: int,
    calc_time: str,
    measurements: list[dict[str, Any]],
) -> int:
    """原子刷新最新断面预过滤量测结果表 se_prefilter_result。"""
    prefiltered = [
        row
        for row in measurements
        if str(row.get("source") or "").lower() == "prefiltered"
    ]
    conn.execute("DELETE FROM se_prefilter_result")
    conn.executemany(
        """INSERT INTO se_prefilter_result(
               id, run_id, calc_time, meas_id, meas_name, device_type, device_idx, device_name,
               metric, meas_type, unit, meas_value, min_value, max_value, origin, rule_id, reason
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                row.get("min_value"),
                row.get("max_value"),
                str(row.get("prefilter_origin") or ("policy" if str(row.get("reason") or "").startswith("policy_suppressed") else "kernel")),
                row.get("prefilter_rule_id"),
                str(row.get("reason") or "prefiltered"),
            )
            for seq, row in enumerate(prefiltered, 1)
        ),
    )
    return len(prefiltered)


def _use_fallback_measurement(conn: sqlite3.Connection) -> bool:
    """当尚未产生 se_prefilter_result 时，平滑回退读取 se_measurement(source='prefiltered')。"""
    cnt = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_result").fetchone()[0] or 0)
    if cnt > 0:
        return False
    fallback = int(conn.execute("SELECT COUNT(*) FROM se_measurement WHERE source = 'prefiltered'").fetchone()[0] or 0)
    return fallback > 0


def prefilter_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    """汇总预过滤量测管理页单行指标条统计数据。"""
    rule_total = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_rule").fetchone()[0] or 0)
    rule_enabled = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_rule WHERE enabled = 1").fetchone()[0] or 0)

    if _use_fallback_measurement(conn):
        total = int(conn.execute("SELECT COUNT(*) FROM se_measurement WHERE source = 'prefiltered'").fetchone()[0] or 0)
        by_rule = 0
        by_policy = int(
            conn.execute(
                "SELECT COUNT(*) FROM se_measurement WHERE source = 'prefiltered' AND reason LIKE 'policy_suppressed%'"
            ).fetchone()[0]
            or 0
        )
        by_kernel = max(0, total - by_policy)
    else:
        total = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_result").fetchone()[0] or 0)
        by_rule = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_result WHERE origin = 'rule'").fetchone()[0] or 0)
        by_policy = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_result WHERE origin = 'policy'").fetchone()[0] or 0)
        by_kernel = int(conn.execute("SELECT COUNT(*) FROM se_prefilter_result WHERE origin = 'kernel'").fetchone()[0] or 0)

    latest_run = conn.execute(
        "SELECT run_id, calc_time, prefiltered_count, meas_count FROM se_statistics ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    return {
        "total": total,
        "by_rule": by_rule,
        "by_kernel": by_kernel,
        "by_policy": by_policy,
        "rule_total": rule_total,
        "rule_enabled": rule_enabled,
        "latest_run": dict(latest_run) if latest_run is not None else None,
    }


def list_prefilter_results(
    conn: sqlite3.Connection,
    *,
    origin: str = "all",
    device_type: str = "",
    q: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """分页筛选最新断面预过滤量测明细。"""
    use_fb = _use_fallback_measurement(conn)
    clauses: list[str] = []
    params: list[Any] = []
    if use_fb:
        clauses.append("source = 'prefiltered'")
        if origin == "rule":
            return {"rows": [], "total": 0, "limit": int(limit), "offset": int(offset)}
        if origin == "policy":
            clauses.append("reason LIKE 'policy_suppressed%'")
        elif origin == "kernel":
            clauses.append("reason NOT LIKE 'policy_suppressed%'")
    else:
        if origin in {"rule", "kernel", "policy"}:
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

    if use_fb:
        total = int(conn.execute(f"SELECT COUNT(*) FROM se_measurement {where}", params).fetchone()[0] or 0)
        raw_rows = conn.execute(
            f"""SELECT meas_id AS id, run_id, calc_time, meas_id, meas_name, device_type, device_idx,
                       device_name, metric, meas_type, unit, meas_value,
                       NULL AS min_value, NULL AS max_value,
                       CASE WHEN reason LIKE 'policy_suppressed%' THEN 'policy' ELSE 'kernel' END AS origin,
                       NULL AS rule_id, reason
                FROM se_measurement {where}
                ORDER BY meas_id ASC
                LIMIT ? OFFSET ?""",
            [*params, int(limit), int(offset)],
        ).fetchall()
    else:
        total = int(conn.execute(f"SELECT COUNT(*) FROM se_prefilter_result {where}", params).fetchone()[0] or 0)
        raw_rows = conn.execute(
            f"""SELECT * FROM se_prefilter_result {where}
                ORDER BY CASE origin WHEN 'rule' THEN 0 WHEN 'policy' THEN 1 ELSE 2 END, id ASC
                LIMIT ? OFFSET ?""",
            [*params, int(limit), int(offset)],
        ).fetchall()
    return {"rows": [dict(r) for r in raw_rows], "total": total, "limit": int(limit), "offset": int(offset)}


def prefilter_analysis(conn: sqlite3.Connection, *, limit: int = 60) -> dict[str, Any]:
    """返回预过滤数量历史趋势、按原因分布与按设备类型分布。"""
    trend = [
        dict(r)
        for r in reversed(
            conn.execute(
                """SELECT run_id, calc_time, prefiltered_count, meas_count
                   FROM se_statistics ORDER BY run_id DESC LIMIT ?""",
                (max(1, min(int(limit), 300)),),
            ).fetchall()
        )
    ]
    if _use_fallback_measurement(conn):
        by_reason = [
            {"reason": str(r[0] or "prefiltered"), "count": int(r[1])}
            for r in conn.execute(
                """SELECT COALESCE(NULLIF(reason, ''), 'prefiltered') AS r, COUNT(*) AS c
                   FROM se_measurement WHERE source = 'prefiltered'
                   GROUP BY r ORDER BY c DESC LIMIT 15"""
            )
        ]
        by_device_type = [
            {"device_type": str(r[0] or ""), "count": int(r[1])}
            for r in conn.execute(
                """SELECT device_type, COUNT(*) AS c
                   FROM se_measurement WHERE source = 'prefiltered'
                   GROUP BY device_type ORDER BY c DESC"""
            )
        ]
    else:
        by_reason = [
            {"reason": str(r[0] or "prefiltered"), "count": int(r[1])}
            for r in conn.execute(
                """SELECT COALESCE(NULLIF(reason, ''), 'prefiltered') AS r, COUNT(*) AS c
                   FROM se_prefilter_result GROUP BY r ORDER BY c DESC LIMIT 15"""
            )
        ]
        by_device_type = [
            {"device_type": str(r[0] or ""), "count": int(r[1])}
            for r in conn.execute(
                """SELECT device_type, COUNT(*) AS c
                   FROM se_prefilter_result GROUP BY device_type ORDER BY c DESC"""
            )
        ]
    return {
        "trend": trend,
        "by_reason": by_reason,
        "by_device_type": by_device_type,
    }
