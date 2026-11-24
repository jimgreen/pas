"""状态估计（SE）坏量测处置策略、确认消警、异常/缺测与可疑遥信分析模块。"""

from __future__ import annotations

import math
import sqlite3
from typing import Any

from .input_store import SE_DEVICE_RESULT_METRICS, SE_SOLVER_METRICS, _default_metric_unit
from .se_log import record_se_log, utc_now
from .se_pseudo import save_pseudo_meas_define

SE_BAD_DATA_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("ack_status", "TEXT NOT NULL DEFAULT 'unacked'"),
    ("ack_time", "TEXT NOT NULL DEFAULT ''"),
    ("ack_note", "TEXT NOT NULL DEFAULT ''"),
    ("policy_id", "INTEGER"),
)


def ensure_se_bad_columns(conn: sqlite3.Connection) -> None:
    """幂等补齐 se_bad_data 处置状态列（兼容既有旧库）。"""
    existing = {row[1] for row in conn.execute("PRAGMA table_info([se_bad_data])")}
    if not existing:
        return
    for col_name, col_def in SE_BAD_DATA_EXTRA_COLUMNS:
        if col_name not in existing:
            conn.execute(f"ALTER TABLE [se_bad_data] ADD COLUMN [{col_name}] {col_def}")


def list_bad_meas_policies(
    conn: sqlite3.Connection,
    *,
    enabled_only: bool = False,
    device_type: str = "",
    action: str = "",
    q: str = "",
) -> list[dict[str, Any]]:
    """查询坏量测屏蔽/转伪量测处置策略列表。"""
    clauses: list[str] = []
    params: list[Any] = []
    if enabled_only:
        clauses.append("enabled = 1")
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if action in {"suppress", "replace_pseudo"}:
        clauses.append("action = ?")
        params.append(action)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(device_name LIKE ? OR metric LIKE ? OR reason LIKE ?)")
        params.extend([like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT * FROM se_bad_meas_policy {where}
            ORDER BY enabled DESC, id DESC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def save_bad_meas_policy(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    policy_id: int | None = None,
    units: dict[str, Any] | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    """新增或更新坏量测处置策略，并写入运行日志（stage='bad_change'）。"""
    dev_type = str(payload.get("device_type") or "").strip()
    if dev_type not in SE_SOLVER_METRICS:
        raise ValueError(f"不支持的坏量测设备类型: {dev_type}")
    metric = str(payload.get("metric") or "").strip()
    if metric not in SE_SOLVER_METRICS[dev_type]:
        raise ValueError(f"设备类型 {dev_type} 不支持指标: {metric}")
    se_type = SE_SOLVER_METRICS[dev_type][metric]
    dev_name = str(payload.get("device_name") or "").strip()
    if not dev_name:
        raise ValueError("必须选择目标设备")
    dev_idx_raw = payload.get("device_idx")
    dev_idx = int(dev_idx_raw) if dev_idx_raw not in (None, "") else None

    action = str(payload.get("action") or "suppress").strip()
    if action not in {"suppress", "replace_pseudo"}:
        raise ValueError("action 仅支持 suppress 或 replace_pseudo")
    enabled_raw = payload.get("enabled", 1)
    enabled = int(bool(int(enabled_raw))) if not isinstance(enabled_raw, bool) else int(enabled_raw)
    reason = str(payload.get("reason") or "").strip()[:240]
    unit = str(payload.get("unit") or "").strip() or _default_metric_unit(
        se_type, units or {"u_unit": "V", "p_unit": "kW", "i_unit": "A"}
    )
    pseudo_define_id = payload.get("pseudo_define_id")
    pseudo_define_id = int(pseudo_define_id) if pseudo_define_id not in (None, "") else None
    now_str = utc_now()

    if policy_id is None and payload.get("id") not in (None, ""):
        policy_id = int(payload["id"])
    if policy_id is None:
        existing = conn.execute(
            "SELECT id FROM se_bad_meas_policy WHERE device_type=? AND device_name=? AND metric=? LIMIT 1",
            (dev_type, dev_name, metric),
        ).fetchone()
        if existing is not None:
            policy_id = int(existing["id"])

    if policy_id is not None:
        exists = conn.execute("SELECT id FROM se_bad_meas_policy WHERE id=?", (policy_id,)).fetchone()
        if exists is None:
            raise ValueError(f"未找到坏量测策略 #{policy_id}")
        conn.execute(
            """UPDATE se_bad_meas_policy
               SET device_type=?, device_idx=?, device_name=?, metric=?, meas_type=?, unit=?,
                   action=?, enabled=?, pseudo_define_id=?, reason=?, updated_at=?
               WHERE id=?""",
            (dev_type, dev_idx, dev_name, metric, se_type, unit, action, enabled, pseudo_define_id, reason, now_str, policy_id),
        )
        op = "update"
    else:
        cur = conn.execute(
            """INSERT INTO se_bad_meas_policy(
                   device_type, device_idx, device_name, metric, meas_type, unit,
                   action, enabled, pseudo_define_id, reason, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (dev_type, dev_idx, dev_name, metric, se_type, unit, action, enabled, pseudo_define_id, reason, now_str),
        )
        policy_id = int(cur.lastrowid)
        op = "create"

    # 同步刷新当前断面 se_bad_data 中对应行的处置状态
    ensure_se_bad_columns(conn)
    if enabled:
        new_ack = "replaced_pseudo" if action == "replace_pseudo" else "suppressed"
        conn.execute(
            """UPDATE se_bad_data
               SET ack_status=?, ack_time=?, ack_note=?, policy_id=?
               WHERE device_type=? AND device_name=? AND metric=?""",
            (new_ack, now_str, reason or new_ack, policy_id, dev_type, dev_name, metric),
        )

    record_se_log(
        conn,
        level="INFO",
        stage="bad_change",
        source=source,
        message=f"{'新增' if op == 'create' else '更新'}坏量测策略 #{policy_id}: {dev_name}.{metric} -> {action} (enabled={enabled})",
        detail={
            "op": op,
            "policy_id": policy_id,
            "device_type": dev_type,
            "device_name": dev_name,
            "metric": metric,
            "action": action,
            "enabled": enabled,
            "reason": reason,
        },
    )
    row = conn.execute("SELECT * FROM se_bad_meas_policy WHERE id=?", (policy_id,)).fetchone()
    return dict(row)


def delete_bad_meas_policy(conn: sqlite3.Connection, policy_id: int, *, source: str = "operator") -> bool:
    """删除坏量测处置策略并写入运行日志。"""
    row = conn.execute("SELECT * FROM se_bad_meas_policy WHERE id=?", (int(policy_id),)).fetchone()
    if row is None:
        return False
    info = dict(row)
    conn.execute("DELETE FROM se_bad_meas_policy WHERE id=?", (int(policy_id),))
    ensure_se_bad_columns(conn)
    conn.execute(
        "UPDATE se_bad_data SET policy_id=NULL WHERE policy_id=?",
        (int(policy_id),),
    )
    record_se_log(
        conn,
        level="WARN",
        stage="bad_change",
        source=source,
        message=f"删除坏量测策略 #{policy_id}: {info.get('device_name', '')}.{info.get('metric', '')}",
        detail={"op": "delete", "policy_id": int(policy_id), "device_name": info.get("device_name"), "metric": info.get("metric")},
    )
    return True


def ack_bad_data(
    conn: sqlite3.Connection,
    *,
    bad_id: int,
    ack_status: str = "acked",
    ack_note: str = "",
    source: str = "operator",
) -> dict[str, Any]:
    """对当前坏量测执行人工确认消警（acked）或恢复未确认（unacked）。"""
    ensure_se_bad_columns(conn)
    if ack_status not in {"acked", "unacked"}:
        raise ValueError("ack_status 仅支持 acked 或 unacked")
    row = conn.execute("SELECT * FROM se_bad_data WHERE id=?", (int(bad_id),)).fetchone()
    if row is None:
        raise ValueError(f"未找到坏量测记录 #{bad_id}")
    now_str = utc_now() if ack_status == "acked" else ""
    note = str(ack_note or "").strip()[:240]
    conn.execute(
        "UPDATE se_bad_data SET ack_status=?, ack_time=?, ack_note=? WHERE id=?",
        (ack_status, now_str, note, int(bad_id)),
    )
    info = dict(row)
    record_se_log(
        conn,
        level="INFO",
        stage="bad_change",
        source=source,
        message=f"{'确认消警' if ack_status == 'acked' else '撤销确认'}坏量测 #{bad_id}: {info.get('device_name', '')}.{info.get('metric', '')}",
        detail={"op": ack_status, "bad_id": int(bad_id), "device_name": info.get("device_name"), "metric": info.get("metric"), "note": note},
    )
    updated = conn.execute("SELECT * FROM se_bad_data WHERE id=?", (int(bad_id),)).fetchone()
    return dict(updated)


def convert_bad_to_pseudo(
    conn: sqlite3.Connection,
    *,
    bad_id: int | None = None,
    device_type: str = "",
    device_idx: int | None = None,
    device_name: str = "",
    metric: str = "",
    pseudo_value: float | None = None,
    weight: float = 1e-3,
    note: str = "",
    source: str = "operator",
) -> dict[str, Any]:
    """一键将坏量测转为伪量测：屏蔽原坏量测并写入 pas_se_psemeas_define。"""
    ensure_se_bad_columns(conn)
    target_row: dict[str, Any] | None = None
    if bad_id is not None:
        raw = conn.execute("SELECT * FROM se_bad_data WHERE id=?", (int(bad_id),)).fetchone()
        if raw is None:
            raise ValueError(f"未找到坏量测记录 #{bad_id}")
        target_row = dict(raw)
        device_type = str(target_row["device_type"])
        device_idx = target_row.get("device_idx")
        device_name = str(target_row["device_name"])
        metric = str(target_row["metric"])
        if pseudo_value is None:
            est = target_row.get("se_value")
            pseudo_value = float(est) if isinstance(est, (int, float)) and math.isfinite(est) else 0.0
    if pseudo_value is None:
        raise ValueError("必须提供伪量测替代值或指定有效的坏量测记录")

    pseudo_define = save_pseudo_meas_define(
        conn,
        {
            "device_type": device_type,
            "device_idx": device_idx,
            "device_name": device_name,
            "metric": metric,
            "meas_value": pseudo_value,
            "meas_weight": weight,
            "meas_useflag": 1,
            "source_mode": "bad_replace",
            "note": note or f"由坏量测转换替代 ({device_name}.{metric})",
        },
        source=source,
    )
    policy = save_bad_meas_policy(
        conn,
        {
            "device_type": device_type,
            "device_idx": device_idx,
            "device_name": device_name,
            "metric": metric,
            "action": "replace_pseudo",
            "enabled": 1,
            "pseudo_define_id": pseudo_define["id"],
            "reason": note or f"一键转伪量测 #{pseudo_define['id']}",
        },
        source=source,
    )
    return {"policy": policy, "pseudo_define": pseudo_define}


def detect_suspect_statuses(
    snapshot: dict[str, list[dict[str, Any]]],
    device_tables: dict[str, list[dict[str, Any]]],
    device_meas: dict[tuple[str, int, str], dict[str, Any]],
    topology_overrides: dict[str, dict[int, dict[str, int]]] | None = None,
) -> list[dict[str, Any]]:
    """结合 SCADA 遥信状态、静态模型状态与 SE 潮流估计结果，识别可疑遥信/开关状态。"""
    overrides = topology_overrides or {}
    suspects: list[dict[str, Any]] = []

    # 1. 检查断路器：SCADA 报分位(0)但实测或估计电流显著非零；或 SCADA 与静态模型不一致且电流异常
    for brk_table, cur_metric in (("ACBreak", "ia"), ("DCBreak", "i")):
        se_by_idx = {int(r["idx"]): r for r in (device_tables.get(brk_table) or ())}
        for row in snapshot.get(brk_table) or ():
            dev_idx = int(row.get("idx", 0))
            dev_name = str(row.get("name", dev_idx))
            model_status = int(row.get("status", 1))
            scada_status = overrides.get(brk_table, {}).get(dev_idx, {}).get("status")
            if scada_status is None:
                continue
            se_rec = se_by_idx.get(dev_idx) or {}
            meas_entry = device_meas.get((brk_table, dev_idx, cur_metric)) or {}
            meas_i = meas_entry.get("meas_value")
            se_i = se_rec.get(f"{cur_metric}_se")
            if scada_status == 0:
                if isinstance(meas_i, (int, float)) and abs(meas_i) > 5.0:
                    suspects.append(
                        {
                            "device_type": brk_table,
                            "device_idx": dev_idx,
                            "device_name": dev_name,
                            "metric": "status",
                            "scada_status": 0,
                            "model_status": model_status,
                            "se_inferred_status": 1,
                            "evidence": f"{cur_metric}_meas={meas_i:.2f} A",
                            "reason": "breaker_open_with_live_current",
                        }
                    )
                elif isinstance(se_i, (int, float)) and abs(se_i) > 5.0:
                    suspects.append(
                        {
                            "device_type": brk_table,
                            "device_idx": dev_idx,
                            "device_name": dev_name,
                            "metric": "status",
                            "scada_status": 0,
                            "model_status": model_status,
                            "se_inferred_status": 1,
                            "evidence": f"{cur_metric}_se={se_i:.2f} A",
                            "reason": "breaker_open_with_se_current",
                        }
                    )

    # 2. 检查机组/负荷/支路/换流器：遥信报停运(0)但实测有功显著非零
    power_check_tables: dict[str, tuple[str, ...]] = {
        "ACGenerator": ("p",),
        "DCGenerator": ("p",),
        "ACLoad": ("p",),
        "DCLoad": ("p",),
        "ACBranch": ("i_p", "j_p"),
        "DCBranch": ("i_p", "j_p"),
        "DCDCConverter": ("i_p", "j_p"),
        "DCACConverter": ("ac_p", "dc_p"),
    }
    for tbl, p_metrics in power_check_tables.items():
        for row in snapshot.get(tbl) or ():
            dev_idx = int(row.get("idx", 0))
            dev_name = str(row.get("name", dev_idx))
            model_run = int(row.get("run_stat", 1))
            scada_run = overrides.get(tbl, {}).get(dev_idx, {}).get("run_stat")
            if scada_run != 0:
                continue
            for m in p_metrics:
                m_val = (device_meas.get((tbl, dev_idx, m)) or {}).get("meas_value")
                if isinstance(m_val, (int, float)) and abs(m_val) > 5.0:
                    suspects.append(
                        {
                            "device_type": tbl,
                            "device_idx": dev_idx,
                            "device_name": dev_name,
                            "metric": "run_stat",
                            "scada_status": 0,
                            "model_status": model_run,
                            "se_inferred_status": 1,
                            "evidence": f"{m}_meas={m_val:.2f}",
                            "reason": "device_stopped_with_live_power",
                        }
                    )
                    break

    return suspects


def store_se_suspect_statuses(
    conn: sqlite3.Connection,
    run_id: int,
    calc_time: str,
    suspects: list[dict[str, Any]],
) -> int:
    """原子刷新最新断面可疑遥信表 se_suspect_status，并同步写入 pas_se_susstat。"""
    conn.execute("DELETE FROM se_suspect_status")
    conn.executemany(
        """INSERT INTO se_suspect_status(
               id, run_id, calc_time, device_type, device_idx, device_name, metric,
               scada_status, model_status, se_inferred_status, evidence, reason
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            (
                seq,
                run_id,
                calc_time,
                str(item.get("device_type", "")),
                item.get("device_idx"),
                str(item.get("device_name", "")),
                str(item.get("metric", "status")),
                item.get("scada_status"),
                item.get("model_status"),
                item.get("se_inferred_status"),
                str(item.get("evidence", "")),
                str(item.get("reason", "")),
            )
            for seq, item in enumerate(suspects, 1)
        ),
    )
    # 同步刷新兼容表 pas_se_susstat 最新断面
    conn.execute("DELETE FROM pas_se_susstat")
    conn.executemany(
        """INSERT INTO pas_se_susstat(
               id, stat_id, stat_name, dev_name, stat_type, stat_value, stat_status,
               se_value, sus_reason, stat_st, stat_mpsys
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)""",
        (
            (
                seq,
                seq,
                f"{item.get('device_type', '')}.{item.get('device_name', '')}.{item.get('metric', 'status')}",
                str(item.get("device_name", "")),
                1 if item.get("metric") == "status" else 2,
                item.get("scada_status"),
                1,
                item.get("se_inferred_status"),
                f"{item.get('reason', '')}: {item.get('evidence', '')}".strip(": "),
            )
            for seq, item in enumerate(suspects, 1)
        ),
    )
    return len(suspects)


def bad_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    """汇总坏量测独立页顶部 KPI 与各异常类别计数。"""
    ensure_se_bad_columns(conn)
    bad_total = int(conn.execute("SELECT COUNT(*) FROM se_bad_data").fetchone()[0] or 0)
    unacked = int(
        conn.execute("SELECT COUNT(*) FROM se_bad_data WHERE COALESCE(ack_status, 'unacked') = 'unacked'").fetchone()[0] or 0
    )
    policy_total = int(conn.execute("SELECT COUNT(*) FROM se_bad_meas_policy").fetchone()[0] or 0)
    policy_enabled = int(conn.execute("SELECT COUNT(*) FROM se_bad_meas_policy WHERE enabled = 1").fetchone()[0] or 0)
    suspect_count = int(conn.execute("SELECT COUNT(*) FROM se_suspect_status").fetchone()[0] or 0)

    # 统计当前最新一次运行的预过滤 / 未参与 / 缺测计数
    latest_run_row = conn.execute(
        "SELECT run_id, calc_time, bad_data_count, prefiltered_count, pass_rate FROM se_statistics ORDER BY run_id DESC LIMIT 1"
    ).fetchone()
    latest_run = dict(latest_run_row) if latest_run_row is not None else None
    prefiltered_count = int(
        conn.execute("SELECT COUNT(*) FROM se_measurement WHERE source = 'prefiltered'").fetchone()[0] or 0
    )
    notuse_count = int(
        conn.execute("SELECT COUNT(*) FROM se_measurement WHERE valid = 0").fetchone()[0] or 0
    )
    nomeas_count = int(conn.execute("SELECT COUNT(*) FROM pas_se_nomeas").fetchone()[0] or 0)
    return {
        "bad_total": bad_total,
        "unacked_count": unacked,
        "policy_total": policy_total,
        "policy_enabled": policy_enabled,
        "suspect_count": suspect_count,
        "prefiltered_count": prefiltered_count,
        "notuse_count": notuse_count,
        "nomeas_count": nomeas_count,
        "latest_run": latest_run,
        "supported_metrics": {k: dict(v) for k, v in SE_SOLVER_METRICS.items()},
    }


def list_current_bad_data(
    conn: sqlite3.Connection,
    *,
    device_type: str = "",
    ack_status: str = "all",
    q: str = "",
) -> list[dict[str, Any]]:
    """查询当前最新断面坏量测明细（附带是否已关联策略）。"""
    ensure_se_bad_columns(conn)
    clauses: list[str] = []
    params: list[Any] = []
    if device_type and device_type != "all":
        clauses.append("b.device_type = ?")
        params.append(device_type)
    if ack_status in {"unacked", "acked", "suppressed", "replaced_pseudo"}:
        clauses.append("COALESCE(b.ack_status, 'unacked') = ?")
        params.append(ack_status)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(b.device_name LIKE ? OR b.meas_name LIKE ? OR b.metric LIKE ? OR b.reason LIKE ?)")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"""SELECT b.*, p.action AS policy_action, p.enabled AS policy_enabled
            FROM se_bad_data b
            LEFT JOIN se_bad_meas_policy p
              ON p.device_type = b.device_type AND p.device_name = b.device_name AND p.metric = b.metric
            {where}
            ORDER BY ABS(COALESCE(b.normalized_residual, 0)) DESC, ABS(COALESCE(b.residual, 0)) DESC, b.id ASC""",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def list_abnormal_measurements(
    conn: sqlite3.Connection,
    *,
    category: str = "susstat",
    device_type: str = "",
    q: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """按分类读取异常量测与可疑遥信：susstat / filter / notuse / nomeas。"""
    cat = str(category or "susstat").lower()
    search = q.strip()
    like = f"%{search}%"

    if cat == "susstat":
        clauses, params = [], []
        if device_type and device_type != "all":
            clauses.append("device_type = ?")
            params.append(device_type)
        if search:
            clauses.append("(device_name LIKE ? OR reason LIKE ? OR evidence LIKE ?)")
            params.extend([like, like, like])
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        total = int(conn.execute(f"SELECT COUNT(*) FROM se_suspect_status {where}", params).fetchone()[0] or 0)
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM se_suspect_status {where} ORDER BY id ASC LIMIT ? OFFSET ?",
                [*params, int(limit), int(offset)],
            )
        ]
        return {"category": cat, "rows": rows, "total": total, "limit": int(limit), "offset": int(offset)}

    if cat == "nomeas":
        clauses, params = [], []
        if search:
            clauses.append("(dev_name LIKE ? OR meas_name LIKE ? OR COALESCE(filter_reason,'') LIKE ?)")
            params.extend([like, like, like])
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        total = int(conn.execute(f"SELECT COUNT(*) FROM pas_se_nomeas {where}", params).fetchone()[0] or 0)
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM pas_se_nomeas {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                [*params, int(limit), int(offset)],
            )
        ]
        return {"category": cat, "rows": rows, "total": total, "limit": int(limit), "offset": int(offset)}

    # filter / notuse 直接读取最新断面 se_measurement，避免历史累积表重复
    clauses = ["source = 'prefiltered'"] if cat == "filter" else ["valid = 0"]
    params = []
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if search:
        clauses.append("(device_name LIKE ? OR meas_name LIKE ? OR metric LIKE ? OR reason LIKE ?)")
        params.extend([like, like, like, like])
    where = "WHERE " + " AND ".join(clauses)
    total = int(conn.execute(f"SELECT COUNT(*) FROM se_measurement {where}", params).fetchone()[0] or 0)
    rows = [
        dict(r)
        for r in conn.execute(
            f"SELECT * FROM se_measurement {where} ORDER BY meas_id ASC LIMIT ? OFFSET ?",
            [*params, int(limit), int(offset)],
        )
    ]
    return {"category": cat, "rows": rows, "total": total, "limit": int(limit), "offset": int(offset)}
