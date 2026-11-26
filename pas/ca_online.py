"""在线静态安全分析（CA）核心业务层：算法与扫描参数、预想故障库、LF→CA 风险评估与审计日志。"""

from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from .se_log import utc_now

DEFAULT_CA_PARAMS: dict[str, Any] = {
    "use_lf_base": 1,
    "scan_n1": 1,
    "scan_nk": 1,
    "max_scan_count": 40,
    "v_min_pu": 0.93,
    "v_max_pu": 1.07,
    "overload_warn_pct": 80.0,
    "overload_limit_pct": 100.0,
    "load_loss_threshold_kw": 0.5,
    "do_cycle": 300,
}

# 允许作为 N-1 / N-k 预想故障开断对象的设备表及其默认扫描优先级（数字越小优先级越高）
CONTINGENCY_DEVICE_TABLES: dict[str, tuple[str, int]] = {
    "DCACConverter": ("换流器", 10),
    "DCDCConverter": ("直流变流器", 15),
    "ACBranch": ("交流线路", 20),
    "DCBranch": ("直流线路", 25),
    "ACGenerator": ("交流电源", 30),
    "DCGenerator": ("直流电源", 35),
}

SEVERITY_RANK: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "normal": 0,
}

VALID_CA_LOG_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")
VALID_CA_LOG_STAGES = (
    "trigger",
    "lf_import",
    "n0_check",
    "n1_scan",
    "nk_scan",
    "persist",
    "param_change",
    "contingency_change",
    "cleanup",
    "error",
    "system",
)


def _validate_ca_params(payload: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    float_ranges = {
        "v_min_pu": (0.5, 1.05),
        "v_max_pu": (0.95, 1.5),
        "overload_warn_pct": (10.0, 200.0),
        "overload_limit_pct": (20.0, 300.0),
        "load_loss_threshold_kw": (0.0, 1e6),
    }
    int_ranges = {
        "use_lf_base": (0, 1),
        "scan_n1": (0, 1),
        "scan_nk": (0, 1),
        "max_scan_count": (1, 500),
        "do_cycle": (5, 604800),
    }
    for k, (lo, hi) in float_ranges.items():
        if k in payload and payload[k] not in (None, ""):
            val = float(payload[k])
            if not math.isfinite(val) or not (lo <= val <= hi):
                raise ValueError(f"参数 {k} 超出允许范围 [{lo}, {hi}]")
            out[k] = val
    for k, (lo, hi) in int_ranges.items():
        if k in payload and payload[k] not in (None, ""):
            val = int(float(payload[k]))
            if not (lo <= val <= hi):
                raise ValueError(f"参数 {k} 超出允许范围 [{lo}, {hi}]")
            out[k] = val
    if out["v_min_pu"] >= out["v_max_pu"]:
        raise ValueError("电压下限 v_min_pu 必须小于上限 v_max_pu")
    if out["overload_warn_pct"] > out["overload_limit_pct"]:
        raise ValueError("重载预警阈值不能大于过载越限阈值")
    return out


def ensure_ca_params(conn: sqlite3.Connection, *, do_cycle: int | float = 300) -> dict[str, Any]:
    """读取或初始化 ca_para 单行配置。"""
    row = conn.execute("SELECT * FROM ca_para WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    defaults = dict(DEFAULT_CA_PARAMS)
    defaults["do_cycle"] = int(do_cycle or 300)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO ca_para(
               id, use_lf_base, scan_n1, scan_nk, max_scan_count,
               v_min_pu, v_max_pu, overload_warn_pct, overload_limit_pct,
               load_loss_threshold_kw, do_cycle, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            defaults["use_lf_base"],
            defaults["scan_n1"],
            defaults["scan_nk"],
            defaults["max_scan_count"],
            defaults["v_min_pu"],
            defaults["v_max_pu"],
            defaults["overload_warn_pct"],
            defaults["overload_limit_pct"],
            defaults["load_loss_threshold_kw"],
            defaults["do_cycle"],
            now,
        ),
    )
    return dict(conn.execute("SELECT * FROM ca_para WHERE id = 1").fetchone())


def save_ca_params(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    """校验并保存 CA 参数并记录审计日志。"""
    current = ensure_ca_params(conn)
    updated = _validate_ca_params(payload, current)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO ca_para(
               id, use_lf_base, scan_n1, scan_nk, max_scan_count,
               v_min_pu, v_max_pu, overload_warn_pct, overload_limit_pct,
               load_loss_threshold_kw, do_cycle, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            updated["use_lf_base"],
            updated["scan_n1"],
            updated["scan_nk"],
            updated["max_scan_count"],
            updated["v_min_pu"],
            updated["v_max_pu"],
            updated["overload_warn_pct"],
            updated["overload_limit_pct"],
            updated["load_loss_threshold_kw"],
            updated["do_cycle"],
            now,
        ),
    )
    record_ca_log(
        conn,
        level="INFO",
        stage="param_change",
        source="operator",
        message=(
            f"更新 CA 参数：use_lf_base={updated['use_lf_base']}, scan_n1={updated['scan_n1']}, "
            f"max_scan={updated['max_scan_count']}, V=[{updated['v_min_pu']},{updated['v_max_pu']}]pu"
        ),
        detail=updated,
    )
    return dict(conn.execute("SELECT * FROM ca_para WHERE id = 1").fetchone())


def reset_ca_params(conn: sqlite3.Connection) -> dict[str, Any]:
    """重置 CA 参数为工程默认值并记录审计日志。"""
    defaults = dict(DEFAULT_CA_PARAMS)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO ca_para(
               id, use_lf_base, scan_n1, scan_nk, max_scan_count,
               v_min_pu, v_max_pu, overload_warn_pct, overload_limit_pct,
               load_loss_threshold_kw, do_cycle, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            defaults["use_lf_base"],
            defaults["scan_n1"],
            defaults["scan_nk"],
            defaults["max_scan_count"],
            defaults["v_min_pu"],
            defaults["v_max_pu"],
            defaults["overload_warn_pct"],
            defaults["overload_limit_pct"],
            defaults["load_loss_threshold_kw"],
            defaults["do_cycle"],
            now,
        ),
    )
    record_ca_log(
        conn,
        level="WARN",
        stage="param_change",
        source="operator",
        message="已重置 CA 扫描与越限参数为默认值",
        detail=defaults,
    )
    return dict(conn.execute("SELECT * FROM ca_para WHERE id = 1").fetchone())


# ============================================================================
# 预想故障定义库 CRUD（ca_contingency_def）
# ============================================================================

def _format_target_desc(items: list[dict[str, Any]]) -> str:
    parts = []
    for it in items:
        dt = str(it.get("device_type") or "")
        dn = str(it.get("device_name") or f"#{it.get('device_idx', '')}")
        parts.append(f"{dt}:{dn}")
    return " + ".join(parts)


def _normalize_contingency_items(items: Any) -> list[dict[str, Any]]:
    if isinstance(items, str):
        items = json.loads(items or "[]")
    if not isinstance(items, list) or not items:
        raise ValueError("预想故障至少需要包含 1 个故障元件")
    cleaned: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("故障元件项必须为对象")
        dt = str(raw.get("device_type") or "").strip()
        if dt not in CONTINGENCY_DEVICE_TABLES:
            raise ValueError(f"不支持的预想故障元件类型：{dt}")
        dname = str(raw.get("device_name") or "").strip()
        didx = raw.get("device_idx")
        didx_int = int(didx) if didx not in (None, "") else None
        if not dname and didx_int is None:
            raise ValueError("故障元件必须指定 device_name 或 device_idx")
        cleaned.append(
            {
                "device_type": dt,
                "device_idx": didx_int,
                "device_name": dname or f"{dt}-{didx_int}",
            }
        )
    return cleaned


def _decode_contingency_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    d = dict(row)
    try:
        d["items"] = json.loads(d.get("items_json") or "[]")
    except (TypeError, ValueError):
        d["items"] = []
    return d


def list_ca_contingencies(
    conn: sqlite3.Connection,
    *,
    category: str = "",
    enabled_only: bool = False,
    device_type: str = "",
    q: str = "",
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if category and category != "all":
        clauses.append("category = ?")
        params.append(category)
    if enabled_only:
        clauses.append("enabled = 1")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM ca_contingency_def {where} ORDER BY priority ASC, id ASC",
        tuple(params),
    ).fetchall()
    out: list[dict[str, Any]] = []
    search = str(q or "").strip().casefold()
    for r in rows:
        item = _decode_contingency_row(r)
        if device_type and device_type != "all":
            if not any(it.get("device_type") == device_type for it in item["items"]):
                continue
        if search:
            hay = f"{item['name']} {item['target_desc']} {item.get('note', '')}".casefold()
            if search not in hay:
                continue
        out.append(item)
    return out


def save_ca_contingency(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    contingency_id: int | None = None,
) -> dict[str, Any]:
    items = _normalize_contingency_items(payload.get("items"))
    category = "N-1" if len(items) == 1 else "N-k"
    if payload.get("category") in ("N-1", "N-k"):
        category = str(payload["category"])
        if len(items) > 1:
            category = "N-k"
    target_desc = _format_target_desc(items)
    name = str(payload.get("name") or "").strip()
    if not name:
        name = f"{category}:{items[0]['device_name']}" if len(items) == 1 else f"N-{len(items)}:{'+'.join(x['device_name'] for x in items[:2])}"
    priority = max(1, min(999, int(payload.get("priority", 50))))
    enabled = 1 if int(payload.get("enabled", 1)) else 0
    auto_gen = 1 if int(payload.get("auto_generated", 0)) else 0
    note = str(payload.get("note") or "").strip()[:240]
    now = utc_now()
    items_json = json.dumps(items, ensure_ascii=False)

    if contingency_id is not None:
        conn.execute(
            """UPDATE ca_contingency_def
               SET name=?, category=?, items_json=?, target_desc=?, priority=?, enabled=?, note=?, updated_at=?
               WHERE id=?""",
            (name, category, items_json, target_desc, priority, enabled, note, now, int(contingency_id)),
        )
        rid = int(contingency_id)
    else:
        cur = conn.execute(
            """INSERT INTO ca_contingency_def(
                   name, category, items_json, target_desc, priority, enabled, auto_generated, note, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   category=excluded.category,
                   items_json=excluded.items_json,
                   target_desc=excluded.target_desc,
                   priority=excluded.priority,
                   enabled=excluded.enabled,
                   note=excluded.note,
                   updated_at=excluded.updated_at""",
            (name, category, items_json, target_desc, priority, enabled, auto_gen, note, now),
        )
        row = conn.execute("SELECT id FROM ca_contingency_def WHERE name=?", (name,)).fetchone()
        rid = int(row["id"]) if row else int(cur.lastrowid)

    record_ca_log(
        conn,
        level="INFO",
        stage="contingency_change",
        source="operator",
        message=f"保存预想故障：{name}（{category}，启用={enabled}）",
        detail={"id": rid, "name": name, "category": category, "items": items},
    )
    saved = conn.execute("SELECT * FROM ca_contingency_def WHERE id=?", (rid,)).fetchone()
    if saved is None:
        raise ValueError(f"预想故障 #{rid} 不存在")
    return _decode_contingency_row(saved)


def delete_ca_contingency(conn: sqlite3.Connection, contingency_id: int) -> bool:
    row = conn.execute("SELECT name FROM ca_contingency_def WHERE id=?", (int(contingency_id),)).fetchone()
    cur = conn.execute("DELETE FROM ca_contingency_def WHERE id=?", (int(contingency_id),))
    if cur.rowcount > 0:
        record_ca_log(
            conn,
            level="WARN",
            stage="contingency_change",
            source="operator",
            message=f"删除预想故障：{(row['name'] if row else f'#{contingency_id}')}",
            detail={"id": int(contingency_id)},
        )
        return True
    return False


def clear_ca_contingencies(conn: sqlite3.Connection, *, only_auto: bool = False) -> int:
    if only_auto:
        cur = conn.execute("DELETE FROM ca_contingency_def WHERE auto_generated = 1")
    else:
        cur = conn.execute("DELETE FROM ca_contingency_def")
    cnt = int(cur.rowcount or 0)
    record_ca_log(
        conn,
        level="WARN",
        stage="contingency_change",
        source="operator",
        message=f"清空预想故障定义 {cnt} 条（仅自动生成={only_auto}）",
        detail={"deleted": cnt, "only_auto": only_auto},
    )
    return cnt


def sync_ca_contingencies_from_model(
    conn: sqlite3.Connection,
    model_tables: dict[str, dict[str, Any]],
    *,
    device_types: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """根据只读模型自动生成标准 N-1 预想故障集（跳过停运设备，不修改源模型）。"""
    selected = [dt for dt in (device_types or list(CONTINGENCY_DEVICE_TABLES.keys())) if dt in CONTINGENCY_DEVICE_TABLES]
    if overwrite:
        conn.execute("DELETE FROM ca_contingency_def WHERE auto_generated = 1")
    now = utc_now()
    inserted = 0
    skipped = 0
    for dt in selected:
        _label, base_prio = CONTINGENCY_DEVICE_TABLES[dt]
        rows = (model_tables.get(dt) or {}).get("rows") or ()
        for mrow in rows:
            if mrow.get("idx") is None:
                continue
            if int(mrow.get("run_stat", 1)) == 0:
                continue
            didx = int(mrow["idx"])
            dname = str(mrow.get("name") or f"{dt}-{didx}").strip()
            cname = f"N-1:{dname}"
            exists = conn.execute("SELECT id FROM ca_contingency_def WHERE name=?", (cname,)).fetchone()
            if exists is not None:
                skipped += 1
                continue
            items = [{"device_type": dt, "device_idx": didx, "device_name": dname}]
            conn.execute(
                """INSERT INTO ca_contingency_def(
                       name, category, items_json, target_desc, priority, enabled, auto_generated, note, updated_at
                   ) VALUES (?, 'N-1', ?, ?, ?, 1, 1, ?, ?)""",
                (cname, json.dumps(items, ensure_ascii=False), _format_target_desc(items), base_prio, f"自动同步自模型 {dt}", now),
            )
            inserted += 1
    total = int(conn.execute("SELECT COUNT(*) FROM ca_contingency_def").fetchone()[0] or 0)
    record_ca_log(
        conn,
        level="INFO",
        stage="contingency_change",
        source="system",
        message=f"自动同步 N-1 预想故障集：新增 {inserted} 条，已存在 {skipped} 条，总计 {total} 条",
        detail={"inserted": inserted, "skipped": skipped, "total": total, "types": selected},
    )
    return {"inserted": inserted, "skipped": skipped, "total": total}


def bulk_toggle_ca_contingencies(conn: sqlite3.Connection, *, enabled: bool, category: str = "", device_type: str = "") -> int:
    rows = list_ca_contingencies(conn, category=category, device_type=device_type)
    ids = [int(r["id"]) for r in rows]
    if not ids:
        return 0
    now = utc_now()
    val = 1 if enabled else 0
    conn.executemany(
        "UPDATE ca_contingency_def SET enabled=?, updated_at=? WHERE id=?",
        [(val, now, i) for i in ids],
    )
    record_ca_log(
        conn,
        level="INFO",
        stage="contingency_change",
        source="operator",
        message=f"批量{'启用' if enabled else '停用'}预想故障 {len(ids)} 条",
        detail={"count": len(ids), "enabled": val, "category": category, "device_type": device_type},
    )
    return len(ids)


# ============================================================================
# 安全风险评估与定级引擎（基于工程单位 LF 断面 + ca_para + ca_limit）
# ============================================================================

def _classify_voltage_severity(v_pu: float, v_min: float, v_max: float) -> tuple[str | None, str, float]:
    """返回 (risk_category, severity, violation_pct)。"""
    if v_pu < v_min:
        vp = (v_min - v_pu) / max(v_min, 1e-6) * 100.0
        sev = "critical" if (v_pu < 0.85 or vp >= 8.0) else ("high" if vp >= 4.0 else "medium")
        return "voltage_low", sev, round(vp, 2)
    if v_pu > v_max:
        vp = (v_pu - v_max) / max(v_max, 1e-6) * 100.0
        sev = "critical" if (v_pu > 1.15 or vp >= 8.0) else ("high" if vp >= 4.0 else "medium")
        return "voltage_high", sev, round(vp, 2)
    return None, "normal", 0.0


def _classify_loading_severity(loading_pct: float, warn_pct: float, limit_pct: float) -> tuple[str | None, str, float]:
    if loading_pct > limit_pct:
        vp = loading_pct - limit_pct
        sev = "critical" if loading_pct >= limit_pct + 20.0 else "high"
        return "overload", sev, round(vp, 2)
    if loading_pct >= warn_pct:
        vp = loading_pct - warn_pct
        return "heavy_load", "low", round(vp, 2)
    return None, "normal", 0.0


def evaluate_lf_state_risks(
    *,
    contingency_name: str,
    category: str,
    buses: list[dict[str, Any]],
    branches: list[dict[str, Any]],
    params: dict[str, Any],
    device_limits: dict[tuple[str, str, str], dict[str, Any]] | None = None,
    u_unit: str = "V",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """对单次潮流断面（N-0 基态或 N-1/N-k 故障态）进行精准工程单位越限校核。

    返回 (risk_rows, metrics_summary)。
    """
    v_min_default = float(params.get("v_min_pu", 0.93))
    v_max_default = float(params.get("v_max_pu", 1.07))
    warn_pct = float(params.get("overload_warn_pct", 80.0))
    limit_pct = float(params.get("overload_limit_pct", 100.0))
    limits = device_limits or {}

    risks: list[dict[str, Any]] = []
    min_v_pu: float | None = None
    min_v_bus = ""
    max_v_pu: float | None = None
    max_v_bus = ""
    max_loading_pct = 0.0
    max_loading_dev = ""

    # 1. 母线电压越限校核（仅校核带电有效母线，避免停运孤岛 0V 假告警）
    for b in buses:
        v_pu = b.get("v_pu")
        v_eng = b.get("v_eng")
        vbase = b.get("vbase")
        if v_pu is None or not isinstance(v_pu, (int, float)) or not math.isfinite(v_pu):
            continue
        v_pu_f = float(v_pu)
        if v_pu_f <= 1e-4:
            continue
        dname = str(b.get("device_name") or "")
        dtype = str(b.get("device_type") or "ACNode")
        didx = b.get("device_idx")
        if min_v_pu is None or v_pu_f < min_v_pu:
            min_v_pu = v_pu_f
            min_v_bus = dname
        if max_v_pu is None or v_pu_f > max_v_pu:
            max_v_pu = v_pu_f
            max_v_bus = dname

        # 优先采用设备级个性化限值（若配置了合理工程电压上下限）
        lo_pu, hi_pu = v_min_default, v_max_default
        lim_rec = limits.get((dtype, dname, "v"))
        if lim_rec and vbase and float(vbase) > 0:
            if lim_rec.get("min_value") is not None and float(lim_rec["min_value"]) > 0:
                lo_pu = float(lim_rec["min_value"]) / float(vbase)
            if lim_rec.get("max_value") is not None and float(lim_rec["max_value"]) > 0:
                hi_pu = float(lim_rec["max_value"]) / float(vbase)

        rcat, sev, vpct = _classify_voltage_severity(v_pu_f, lo_pu, hi_pu)
        if rcat is not None:
            lim_pu = lo_pu if rcat == "voltage_low" else hi_pu
            lim_eng = round(lim_pu * float(vbase), 2) if (vbase and float(vbase) > 0) else round(lim_pu, 4)
            act_eng = round(float(v_eng), 2) if isinstance(v_eng, (int, float)) else round(v_pu_f, 4)
            risks.append(
                {
                    "contingency_name": contingency_name,
                    "category": category,
                    "device_type": dtype,
                    "device_idx": didx,
                    "device_name": dname,
                    "risk_category": rcat,
                    "severity": sev,
                    "metric": "v",
                    "actual_value": act_eng,
                    "limit_value": lim_eng,
                    "violation_pct": vpct,
                    "unit": u_unit if (vbase and float(vbase) > 0) else "pu",
                    "detail": (
                        f"电压 {act_eng} {u_unit} ({v_pu_f:.4f} pu) "
                        f"{'低于下限' if rcat == 'voltage_low' else '超过上限'} {lim_eng} {u_unit} ({lim_pu:.3f} pu)"
                    ),
                }
            )

    # 2. 支路与换流器热稳定负载率校核
    for br in branches:
        lp = br.get("loading_pct")
        if lp is None or not isinstance(lp, (int, float)) or not math.isfinite(lp):
            continue
        lp_f = float(lp)
        dname = str(br.get("device_name") or "")
        dtype = str(br.get("device_type") or "ACBranch")
        didx = br.get("device_idx")
        if lp_f > max_loading_pct:
            max_loading_pct = lp_f
            max_loading_dev = dname
        rcat, sev, vpct = _classify_loading_severity(lp_f, warn_pct, limit_pct)
        if rcat is not None:
            lim_val = limit_pct if rcat == "overload" else warn_pct
            risks.append(
                {
                    "contingency_name": contingency_name,
                    "category": category,
                    "device_type": dtype,
                    "device_idx": didx,
                    "device_name": dname,
                    "risk_category": rcat,
                    "severity": sev,
                    "metric": "loading_pct",
                    "actual_value": round(lp_f, 2),
                    "limit_value": round(lim_val, 2),
                    "violation_pct": vpct,
                    "unit": "%",
                    "detail": (
                        f"负载率 {lp_f:.2f}% {'超过过载限额' if rcat == 'overload' else '达到重载预警'} {lim_val:.1f}%"
                    ),
                }
            )

    return risks, {
        "min_v_pu": round(min_v_pu, 5) if min_v_pu is not None else None,
        "min_v_bus": min_v_bus,
        "max_v_pu": round(max_v_pu, 5) if max_v_pu is not None else None,
        "max_v_bus": max_v_bus,
        "max_loading_pct": round(max_loading_pct, 2),
        "max_loading_dev": max_loading_dev,
    }


def compute_security_score_and_level(
    *,
    base_converged: bool,
    critical_count: int,
    high_count: int,
    medium_count: int,
    low_count: int,
) -> tuple[float, str]:
    """根据各等级风险数计算 0–100 安全健康评分与总体风险等级。"""
    if not base_converged:
        return 0.0, "严重"
    penalty = critical_count * 18.0 + high_count * 8.0 + medium_count * 3.0 + low_count * 1.0
    score = round(max(0.0, min(100.0, 100.0 - penalty)), 1)
    if critical_count > 0:
        level = "严重"
    elif high_count > 0:
        level = "高"
    elif medium_count > 0:
        level = "中"
    elif low_count > 0:
        level = "低"
    else:
        level = "安全"
    return score, level


# ============================================================================
# CA 运行与配置审计日志（ca_run_log / ca_log_policy）
# ============================================================================

def ensure_ca_log_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM ca_log_policy WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO ca_log_policy(
               id, enabled, retention_days, keep_error_days, max_rows,
               cleanup_interval_hours, min_level, last_cleanup_at, last_deleted_count, updated_at
           ) VALUES (1, 1, 30, 90, 50000, 6, 'INFO', '', 0, ?)""",
        (now,),
    )
    return dict(conn.execute("SELECT * FROM ca_log_policy WHERE id = 1").fetchone())


def update_ca_log_policy(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    cur = ensure_ca_log_policy(conn)
    enabled = 1 if int(payload.get("enabled", payload.get("auto_enabled", cur["enabled"]))) else 0
    retention_days = max(1, min(3650, int(payload.get("retention_days", cur["retention_days"]))))
    keep_error_days = max(retention_days, min(3650, int(payload.get("keep_error_days", cur["keep_error_days"]))))
    max_rows = max(100, min(500000, int(payload.get("max_rows", cur["max_rows"]))))
    cleanup_hours = max(1, min(720, int(payload.get("cleanup_interval_hours", cur["cleanup_interval_hours"]))))
    min_level = str(payload.get("min_level", cur["min_level"])).upper()
    if min_level not in VALID_CA_LOG_LEVELS:
        min_level = "INFO"
    now = utc_now()
    conn.execute(
        """UPDATE ca_log_policy
           SET enabled=?, retention_days=?, keep_error_days=?, max_rows=?,
               cleanup_interval_hours=?, min_level=?, updated_at=?
           WHERE id = 1""",
        (enabled, retention_days, keep_error_days, max_rows, cleanup_hours, min_level, now),
    )
    return dict(conn.execute("SELECT * FROM ca_log_policy WHERE id = 1").fetchone())


def record_ca_log(
    conn: sqlite3.Connection,
    *,
    level: str = "INFO",
    stage: str = "system",
    message: str = "",
    run_id: int | None = None,
    source: str = "system",
    elapsed_ms: float | None = None,
    detail: dict[str, Any] | None = None,
) -> int | None:
    lvl = str(level or "INFO").upper()
    if lvl not in VALID_CA_LOG_LEVELS:
        lvl = "INFO"
    stg = str(stage or "system").lower()
    if stg not in VALID_CA_LOG_STAGES:
        stg = "system"
    cur = conn.execute(
        """INSERT INTO ca_run_log(run_id, calc_time, level, stage, source, elapsed_ms, message, detail_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run_id,
            utc_now(),
            lvl,
            stg,
            str(source or "system"),
            float(elapsed_ms) if elapsed_ms is not None else None,
            str(message or "")[:2000],
            json.dumps(detail or {}, ensure_ascii=False, default=str),
        ),
    )
    return int(cur.lastrowid) if cur.lastrowid else None


def list_ca_logs(
    conn: sqlite3.Connection,
    *,
    level: str = "",
    stage: str = "",
    source: str = "",
    run_id: int | None = None,
    window: str = "all",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    clauses: list[str] = []
    params: list[Any] = []
    if level and level != "all":
        clauses.append("level = ?")
        params.append(level.upper())
    if stage and stage != "all":
        clauses.append("stage = ?")
        params.append(stage.lower())
    if source and source != "all":
        clauses.append("source = ?")
        params.append(source)
    if run_id is not None:
        clauses.append("run_id = ?")
        params.append(int(run_id))
    win_hours = {"24h": 24, "7d": 168, "30d": 720}.get(window)
    if win_hours:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=win_hours)).isoformat(timespec="milliseconds")
        clauses.append("calc_time >= ?")
        params.append(cutoff)
    if q:
        clauses.append("(message LIKE ? OR detail_json LIKE ?)")
        like = f"%{q.strip()}%"
        params.extend([like, like])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    total = int(conn.execute(f"SELECT COUNT(*) FROM ca_run_log {where}", tuple(params)).fetchone()[0] or 0)
    rows = conn.execute(
        f"SELECT * FROM ca_run_log {where} ORDER BY log_id DESC LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    ).fetchall()
    out_rows = []
    for r in rows:
        d = dict(r)
        try:
            d["detail"] = json.loads(d.get("detail_json") or "{}")
        except (ValueError, TypeError):
            d["detail"] = {}
        out_rows.append(d)
    return {"total": total, "limit": limit, "offset": offset, "rows": out_rows}


def ca_log_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    pol = ensure_ca_log_policy(conn)
    total = int(conn.execute("SELECT COUNT(*) FROM ca_run_log").fetchone()[0] or 0)
    cut24 = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="milliseconds")
    c24 = conn.execute(
        "SELECT COALESCE(SUM(level='ERROR'),0) AS err_24h, COALESCE(SUM(level='WARN'),0) AS warn_24h FROM ca_run_log WHERE calc_time >= ?",
        (cut24,),
    ).fetchone()
    by_stage = {
        str(r["stage"]): int(r["cnt"])
        for r in conn.execute("SELECT stage, COUNT(*) AS cnt FROM ca_run_log GROUP BY stage").fetchall()
    }
    pending = purge_ca_logs(conn, dry_run=True)["total_to_delete"]
    return {
        "total": total,
        "error_24h": int(c24["err_24h"] or 0),
        "warn_24h": int(c24["warn_24h"] or 0),
        "policy": pol,
        "by_stage": by_stage,
        "pending_purge": pending,
    }


def purge_ca_logs(
    conn: sqlite3.Connection,
    *,
    dry_run: bool = False,
    retention_days: int | None = None,
    keep_error_days: int | None = None,
    max_rows: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    pol = ensure_ca_log_policy(conn)
    ret_d = int(retention_days if retention_days is not None else pol["retention_days"])
    err_d = int(keep_error_days if keep_error_days is not None else pol["keep_error_days"])
    cap = int(max_rows if max_rows is not None else pol["max_rows"])
    now_dt = datetime.now(timezone.utc)
    cut_norm = (now_dt - timedelta(days=ret_d)).isoformat(timespec="milliseconds")
    cut_err = (now_dt - timedelta(days=err_d)).isoformat(timespec="milliseconds")
    exp_ids = [
        int(r[0])
        for r in conn.execute(
            "SELECT log_id FROM ca_run_log WHERE (level != 'ERROR' AND calc_time < ?) OR (level = 'ERROR' AND calc_time < ?)",
            (cut_norm, cut_err),
        ).fetchall()
    ]
    total = int(conn.execute("SELECT COUNT(*) FROM ca_run_log").fetchone()[0] or 0)
    remain = max(0, total - len(exp_ids))
    overflow = max(0, remain - cap)
    total_del = len(exp_ids) + overflow
    if dry_run:
        return {"expired_count": len(exp_ids), "overflow_count": overflow, "total_to_delete": total_del, "deleted": 0}
    if exp_ids:
        conn.execute(
            "DELETE FROM ca_run_log WHERE (level != 'ERROR' AND calc_time < ?) OR (level = 'ERROR' AND calc_time < ?)",
            (cut_norm, cut_err),
        )
    if overflow > 0:
        conn.execute(
            "DELETE FROM ca_run_log WHERE log_id IN (SELECT log_id FROM ca_run_log ORDER BY log_id ASC LIMIT ?)",
            (overflow,),
        )
    now_str = utc_now()
    conn.execute(
        "UPDATE ca_log_policy SET last_cleanup_at=?, last_deleted_count=?, updated_at=? WHERE id = 1",
        (now_str, total_del, now_str),
    )
    if total_del > 0:
        record_ca_log(
            conn,
            level="INFO",
            stage="cleanup",
            source=source,
            message=f"清理 CA 运行日志 {total_del} 条（过期 {len(exp_ids)}，超限 {overflow}）",
            detail={"expired": len(exp_ids), "overflow": overflow},
        )
    return {"expired_count": len(exp_ids), "overflow_count": overflow, "total_to_delete": total_del, "deleted": total_del}


def export_ca_logs_csv(conn: sqlite3.Connection, **kwargs) -> str:
    page = list_ca_logs(conn, **{**kwargs, "limit": 500, "offset": 0})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["log_id", "run_id", "calc_time", "level", "stage", "source", "elapsed_ms", "message"])
    for r in page["rows"]:
        w.writerow([r["log_id"], r["run_id"], r["calc_time"], r["level"], r["stage"], r["source"], r["elapsed_ms"], r["message"]])
    return "\ufeff" + buf.getvalue()
