"""在线潮流分析（LF）核心业务层：算法参数管理、SE→LF 基态注入器、方式调整与审计日志。"""

from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .se_log import utc_now

DEFAULT_LF_PARAMS: dict[str, Any] = {
    "tol": 1e-8,
    "max_iter": 50,
    "min_voltage": 0.01,
    "divergence_threshold": 1e6,
    "use_se_base": 1,
    "cascade_ca": 0,
    "v_min_pu": 0.93,
    "v_max_pu": 1.07,
    "overload_warn_pct": 80.0,
    "overload_limit_pct": 100.0,
    "do_cycle": 60,
}

LF_OVERRIDE_FIELDS: dict[str, tuple[str, ...]] = {
    "ACBreak": ("status", "run_stat"),
    "DCBreak": ("status", "run_stat"),
    "ACGenerator": ("p_set", "q_set", "v_set", "run_stat"),
    "DCGenerator": ("p_set", "v_set", "run_stat"),
    "ACLoad": ("pbase", "qbase", "p_set", "run_stat"),
    "DCLoad": ("pbase", "run_stat"),
    "ACBranch": ("run_stat",),
    "DCBranch": ("run_stat",),
    "ACZeroBranch": ("run_stat",),
    "DCDCConverter": ("p_set", "v_set", "i_set", "run_stat"),
    "DCACConverter": ("p_ac_set", "q_ac_set", "v_ac_set", "p_dc_set", "v_dc_set", "run_stat"),
}

VALID_LF_LOG_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")
VALID_LF_LOG_STAGES = (
    "trigger",
    "se_import",
    "override_apply",
    "solve",
    "persist",
    "param_change",
    "override_change",
    "cleanup",
    "error",
    "system",
)


def parse_lf_para_file(para_file: str | Path | None) -> dict[str, Any]:
    """解析内核 lf.para 文件，返回标准化 LF 参数字典。"""
    params = dict(DEFAULT_LF_PARAMS)
    if not para_file:
        return params
    path = Path(para_file)
    if not path.is_file():
        return params
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line.startswith("#"):
            continue
        parts = line[1:].split()
        if len(parts) < 2:
            continue
        key, val_s = parts[0].strip(), parts[1].strip()
        if key not in params:
            continue
        try:
            if key in {"max_iter", "do_cycle", "use_se_base", "cascade_ca"}:
                params[key] = int(float(val_s))
            else:
                params[key] = float(val_s)
        except ValueError:
            continue
    return params


def _validate_lf_params(payload: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    float_ranges = {
        "tol": (1e-14, 1e-1),
        "min_voltage": (1e-5, 0.9),
        "divergence_threshold": (10.0, 1e12),
        "v_min_pu": (0.5, 1.05),
        "v_max_pu": (0.95, 1.5),
        "overload_warn_pct": (10.0, 200.0),
        "overload_limit_pct": (20.0, 300.0),
    }
    int_ranges = {
        "max_iter": (1, 2000),
        "use_se_base": (0, 1),
        "cascade_ca": (0, 1),
        "do_cycle": (1, 604800),
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
        raise ValueError("重载预警阈值不能大于越限阈值")
    return out


def ensure_lf_params(
    conn: sqlite3.Connection,
    para_file: str | Path | None = None,
    *,
    do_cycle: int | float = 60,
) -> dict[str, Any]:
    """读取或初始化 lf_para 单行配置。"""
    row = conn.execute("SELECT * FROM lf_para WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    defaults = parse_lf_para_file(para_file)
    defaults["do_cycle"] = int(do_cycle or 60)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO lf_para(
               id, tol, max_iter, min_voltage, divergence_threshold,
               use_se_base, cascade_ca, v_min_pu, v_max_pu,
               overload_warn_pct, overload_limit_pct, do_cycle, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            defaults["tol"],
            defaults["max_iter"],
            defaults["min_voltage"],
            defaults["divergence_threshold"],
            defaults["use_se_base"],
            defaults["cascade_ca"],
            defaults["v_min_pu"],
            defaults["v_max_pu"],
            defaults["overload_warn_pct"],
            defaults["overload_limit_pct"],
            defaults["do_cycle"],
            now,
        ),
    )
    return dict(conn.execute("SELECT * FROM lf_para WHERE id = 1").fetchone())


def save_lf_params(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    para_file: str | Path | None = None,
) -> dict[str, Any]:
    """校验并保存 LF 参数，同时写入审计日志。"""
    current = ensure_lf_params(conn, para_file)
    updated = _validate_lf_params(payload, current)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO lf_para(
               id, tol, max_iter, min_voltage, divergence_threshold,
               use_se_base, cascade_ca, v_min_pu, v_max_pu,
               overload_warn_pct, overload_limit_pct, do_cycle, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            updated["tol"],
            updated["max_iter"],
            updated["min_voltage"],
            updated["divergence_threshold"],
            updated["use_se_base"],
            updated["cascade_ca"],
            updated["v_min_pu"],
            updated["v_max_pu"],
            updated["overload_warn_pct"],
            updated["overload_limit_pct"],
            updated["do_cycle"],
            now,
        ),
    )
    record_lf_log(
        conn,
        level="INFO",
        stage="param_change",
        source="operator",
        message=f"更新 LF 参数：tol={updated['tol']:g}, max_iter={updated['max_iter']}, use_se_base={updated['use_se_base']}, cascade_ca={updated['cascade_ca']}",
        detail=updated,
    )
    return dict(conn.execute("SELECT * FROM lf_para WHERE id = 1").fetchone())


def reset_lf_params(conn: sqlite3.Connection, para_file: str | Path | None = None) -> dict[str, Any]:
    """从 lf.para 恢复默认 LF 参数并写入审计日志。"""
    defaults = parse_lf_para_file(para_file)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO lf_para(
               id, tol, max_iter, min_voltage, divergence_threshold,
               use_se_base, cascade_ca, v_min_pu, v_max_pu,
               overload_warn_pct, overload_limit_pct, do_cycle, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            defaults["tol"],
            defaults["max_iter"],
            defaults["min_voltage"],
            defaults["divergence_threshold"],
            defaults["use_se_base"],
            defaults["cascade_ca"],
            defaults["v_min_pu"],
            defaults["v_max_pu"],
            defaults["overload_warn_pct"],
            defaults["overload_limit_pct"],
            defaults["do_cycle"],
            now,
        ),
    )
    record_lf_log(
        conn,
        level="WARN",
        stage="param_change",
        source="operator",
        message="已重置 LF 参数为 lf.para 默认值",
        detail=defaults,
    )
    return dict(conn.execute("SELECT * FROM lf_para WHERE id = 1").fetchone())


@contextmanager
def lf_parameter_file(
    base_para_file: str | Path | None,
    params: dict[str, Any] | None = None,
) -> Iterator[tuple[Path, dict[str, Any]]]:
    """将数据库中的 LF 参数渲染为临时内核 lf.para 文件。"""
    merged = parse_lf_para_file(base_para_file)
    if params:
        for k in ("tol", "max_iter", "min_voltage", "divergence_threshold"):
            if k in params and params[k] is not None:
                merged[k] = params[k]
    content = "\n".join(
        [
            "<PowerFlowParameter>",
            "@ name                 value",
            f"# tol                  {merged['tol']}",
            f"# max_iter             {int(merged['max_iter'])}",
            f"# min_voltage          {merged['min_voltage']}",
            f"# divergence_threshold {merged['divergence_threshold']}",
            "</PowerFlowParameter>",
            "",
        ]
    )
    with tempfile.TemporaryDirectory(prefix="pas_lf_para_") as tmpdir:
        out = Path(tmpdir) / "lf.para"
        out.write_text(content, encoding="utf-8")
        yield out, merged


# ============================================================================
# SE → LF 基态注入器（绝不修改源模型，返回供 apply_topology_overrides 使用的覆盖字典）
# ============================================================================

def _finite_float(val: Any) -> float | None:
    if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
        return float(val)
    return None


def _pick_se_eng_value(
    rec: dict[str, Any] | None,
    metric: str,
    *,
    fallback_meas_if_zero: bool = False,
) -> float | None:
    """从 se_dev_* 记录中提取用于 LF 基态的工程值：优先采用 SE 估计值，缺失或直流退化零值时安全回退实测值。"""
    if not rec:
        return None
    se_v = _finite_float(rec.get(f"{metric}_se"))
    meas_v = _finite_float(rec.get(f"{metric}_meas"))
    if se_v is not None:
        if fallback_meas_if_zero and abs(se_v) < 1e-6 and meas_v is not None and abs(meas_v) > 1e-3:
            return meas_v
        return se_v
    return meas_v


def build_se_base_overrides(
    se_snap: dict[str, Any] | None,
    model_tables: dict[str, dict[str, Any]],
    *,
    breaker_status: dict[tuple[str, int], int] | None = None,
    pseudo_stats: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, Any]]:
    """基于最新收敛的 SE 断面（se_topology_snapshot）构造 LF 内存模型覆盖字典。

    严格遵循控制类型物理约束：
    - ACBreak / DCBreak：注入实时 SCADA 与 SE 人工伪状态分合位；
    - ACGenerator：PQ 机注入 p_set/q_set；PV 机注入 p_set 与 v_set；Slack/VTheta 仅注入 v_set；
    - ACLoad：注入恒功率基值 pbase/p_set/qbase；
    - DCGenerator：P 控制型注入 p_set，V 控制型注入 v_set；
    - DCLoad：注入 pbase；
    - 绝不覆盖源模型磁盘文件，仅用于内存模型临时导出。
    """
    overrides: dict[str, dict[int, dict[str, Any]]] = {}
    meta: dict[str, Any] = {
        "used_se_base": False,
        "source_se_run_id": None,
        "se_calc_time": "",
        "applied_devices": 0,
        "applied_breakers": 0,
    }
    if not se_snap or not model_tables:
        return overrides, meta

    latest = se_snap.get("latest")
    if not latest or not int(latest.get("converged") or 0):
        return overrides, meta

    meta["used_se_base"] = True
    meta["source_se_run_id"] = int(latest["run_id"])
    meta["se_calc_time"] = str(latest.get("calc_time") or "")
    devices_by_type = se_snap.get("devices_by_type") or {}
    dev_map: dict[tuple[str, int], dict[str, Any]] = {
        (dt, int(r["idx"])): r
        for dt, rlist in devices_by_type.items()
        for r in rlist
        if r.get("idx") is not None
    }
    node_v_se: dict[tuple[str, int], float] = {}
    for n_tbl, vk in (("ACNode", "uab"), ("DCNode", "u")):
        for r in devices_by_type.get(n_tbl) or ():
            if r.get("idx") is None:
                continue
            v = _pick_se_eng_value(r, vk)
            if v is not None and v > 0:
                node_v_se[(n_tbl, int(r["idx"]))] = v

    # 1. 开关实时分合位 + 人工伪状态覆盖
    if breaker_status:
        for (brk_tbl, b_idx), pos in breaker_status.items():
            if pos in (0, 1):
                overrides.setdefault(brk_tbl, {}).setdefault(int(b_idx), {})["status"] = int(pos)
                meta["applied_breakers"] += 1
    if pseudo_stats:
        name_to_idx: dict[tuple[str, str], int] = {}
        for dt, blk in model_tables.items():
            for mrow in blk.get("rows") or ():
                if mrow.get("idx") is not None and mrow.get("name"):
                    name_to_idx[(dt, str(mrow["name"]))] = int(mrow["idx"])
        for ps in pseudo_stats:
            if not int(ps.get("stat_useflag", 1)):
                continue
            dt = str(ps.get("device_type") or "")
            idx = ps.get("device_idx")
            if idx is None and ps.get("dev_name"):
                idx = name_to_idx.get((dt, str(ps["dev_name"])))
            if idx is None:
                continue
            field = "status" if dt in ("ACBreak", "DCBreak") else "run_stat"
            overrides.setdefault(dt, {}).setdefault(int(idx), {})[field] = int(ps.get("stat_value", 1))
            meta["applied_breakers"] += 1

    # 2. ACGenerator 控制量覆盖
    for mrow in (model_tables.get("ACGenerator") or {}).get("rows") or ():
        if mrow.get("idx") is None or not int(mrow.get("run_stat", 1)):
            continue
        idx = int(mrow["idx"])
        rec = dev_map.get(("ACGenerator", idx))
        if not rec:
            continue
        ctype = str(mrow.get("control_type") or "PQ").upper()
        patch: dict[str, Any] = {}
        p_val = _pick_se_eng_value(rec, "p")
        q_val = _pick_se_eng_value(rec, "q")
        v_val = _pick_se_eng_value(rec, "uab") or node_v_se.get(("ACNode", int(mrow["node"]))) if mrow.get("node") is not None else None
        if ctype in {"PQ"}:
            if p_val is not None:
                patch["p_set"] = round(p_val, 6)
            if q_val is not None:
                patch["q_set"] = round(q_val, 6)
        elif ctype in {"PV"}:
            if p_val is not None:
                patch["p_set"] = round(p_val, 6)
            if v_val is not None and v_val > 0:
                patch["v_set"] = round(v_val, 6)
        else:
            # Slack / VTheta 平衡机只锚定电压，保持自由平衡功率
            if v_val is not None and v_val > 0:
                patch["v_set"] = round(v_val, 6)
        if patch:
            overrides.setdefault("ACGenerator", {}).setdefault(idx, {}).update(patch)
            meta["applied_devices"] += 1

    # 3. ACLoad 恒功率负荷覆盖
    for mrow in (model_tables.get("ACLoad") or {}).get("rows") or ():
        if mrow.get("idx") is None or not int(mrow.get("run_stat", 1)):
            continue
        idx = int(mrow["idx"])
        rec = dev_map.get(("ACLoad", idx))
        if not rec:
            continue
        patch = {}
        p_val = _pick_se_eng_value(rec, "p")
        q_val = _pick_se_eng_value(rec, "q")
        if p_val is not None:
            patch["pbase"] = round(max(0.0, p_val), 6)
            if "p_set" in mrow:
                patch["p_set"] = round(max(0.0, p_val), 6)
        if q_val is not None:
            patch["qbase"] = round(q_val, 6)
        if patch:
            overrides.setdefault("ACLoad", {}).setdefault(idx, {}).update(patch)
            meta["applied_devices"] += 1

    # 4. DCGenerator 控制量覆盖
    for mrow in (model_tables.get("DCGenerator") or {}).get("rows") or ():
        if mrow.get("idx") is None or not int(mrow.get("run_stat", 1)):
            continue
        idx = int(mrow["idx"])
        rec = dev_map.get(("DCGenerator", idx))
        if not rec:
            continue
        ctype = str(mrow.get("control_type") or "P").upper()
        patch = {}
        p_val = _pick_se_eng_value(rec, "p", fallback_meas_if_zero=True)
        v_val = _pick_se_eng_value(rec, "u") or (node_v_se.get(("DCNode", int(mrow["node"]))) if mrow.get("node") is not None else None)
        if ctype in {"P", "PQ", "PI"}:
            if p_val is not None:
                patch["p_set"] = round(p_val, 6)
        elif ctype in {"V", "SLACK", "REF", "VDROOP"}:
            if v_val is not None and v_val > 0:
                patch["v_set"] = round(v_val, 6)
        if patch:
            overrides.setdefault("DCGenerator", {}).setdefault(idx, {}).update(patch)
            meta["applied_devices"] += 1

    # 5. DCLoad 负荷覆盖
    for mrow in (model_tables.get("DCLoad") or {}).get("rows") or ():
        if mrow.get("idx") is None or not int(mrow.get("run_stat", 1)):
            continue
        idx = int(mrow["idx"])
        rec = dev_map.get(("DCLoad", idx))
        if not rec:
            continue
        p_val = _pick_se_eng_value(rec, "p", fallback_meas_if_zero=True)
        if p_val is not None:
            overrides.setdefault("DCLoad", {}).setdefault(idx, {})["pbase"] = round(max(0.0, p_val), 6)
            meta["applied_devices"] += 1

    return overrides, meta


def merge_study_overrides(
    base_overrides: dict[str, dict[int, dict[str, Any]]],
    study_rows: list[dict[str, Any]] | None,
    model_tables: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[int, dict[str, Any]]], int]:
    """将启用的方式调整（lf_study_override）高优先级叠加到基态覆盖字典之上。"""
    merged: dict[str, dict[int, dict[str, Any]]] = {
        dt: {idx: dict(fields) for idx, fields in items.items()}
        for dt, items in base_overrides.items()
    }
    if not study_rows:
        return merged, 0
    name_to_idx: dict[tuple[str, str], int] = {}
    for dt, blk in model_tables.items():
        for mrow in blk.get("rows") or ():
            if mrow.get("idx") is not None and mrow.get("name"):
                name_to_idx[(dt, str(mrow["name"]))] = int(mrow["idx"])
    count = 0
    for row in study_rows:
        if not int(row.get("enabled", 1)):
            continue
        dt = str(row.get("device_type") or "")
        field = str(row.get("field") or "")
        if dt not in LF_OVERRIDE_FIELDS or field not in LF_OVERRIDE_FIELDS[dt]:
            continue
        idx = row.get("device_idx")
        if idx is None:
            idx = name_to_idx.get((dt, str(row.get("device_name") or "")))
        if idx is None:
            continue
        val = float(row["value"])
        if field in {"status", "run_stat"}:
            val = int(bool(round(val)))
        merged.setdefault(dt, {}).setdefault(int(idx), {})[field] = val
        count += 1
    return merged, count


# ============================================================================
# 方式调整表 CRUD（lf_study_override）
# ============================================================================

def list_lf_overrides(
    conn: sqlite3.Connection,
    *,
    scheme_name: str = "",
    enabled_only: bool = False,
    device_type: str = "",
    q: str = "",
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if scheme_name:
        clauses.append("scheme_name = ?")
        params.append(scheme_name)
    if enabled_only:
        clauses.append("enabled = 1")
    if device_type and device_type != "all":
        clauses.append("device_type = ?")
        params.append(device_type)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(device_name LIKE ? OR device_type LIKE ? OR field LIKE ? OR note LIKE ?)")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM lf_study_override {where} ORDER BY enabled DESC, id DESC",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


def save_lf_override(
    conn: sqlite3.Connection,
    payload: dict[str, Any],
    *,
    override_id: int | None = None,
) -> dict[str, Any]:
    scheme = str(payload.get("scheme_name") or "default").strip()[:64] or "default"
    dev_type = str(payload.get("device_type") or "").strip()
    if dev_type not in LF_OVERRIDE_FIELDS:
        raise ValueError(f"不支持的方式调整设备类型: {dev_type}")
    field = str(payload.get("field") or "").strip()
    if field not in LF_OVERRIDE_FIELDS[dev_type]:
        raise ValueError(f"设备类型 {dev_type} 不支持调整字段: {field}")
    dev_name = str(payload.get("device_name") or "").strip()
    if not dev_name:
        raise ValueError("必须指定目标设备名称")
    dev_idx_raw = payload.get("device_idx")
    dev_idx = int(dev_idx_raw) if dev_idx_raw not in (None, "") else None
    try:
        val = float(payload.get("value"))
    except (TypeError, ValueError) as exc:
        raise ValueError("调整设定值必须为有效数字") from exc
    if not math.isfinite(val):
        raise ValueError("调整设定值不能为 NaN 或无穷大")
    if field in {"status", "run_stat"} and val not in (0.0, 1.0):
        raise ValueError(f"{field} 仅支持 0（分/停运）或 1（合/运行）")
    enabled_raw = payload.get("enabled", 1)
    enabled = int(bool(int(enabled_raw))) if not isinstance(enabled_raw, bool) else int(enabled_raw)
    note = str(payload.get("note") or "").strip()[:240]
    now = utc_now()

    if override_id is None and payload.get("id") not in (None, ""):
        override_id = int(payload["id"])
    if override_id is None:
        existing = conn.execute(
            "SELECT id FROM lf_study_override WHERE scheme_name=? AND device_type=? AND device_name=? AND field=? LIMIT 1",
            (scheme, dev_type, dev_name, field),
        ).fetchone()
        if existing is not None:
            override_id = int(existing["id"])

    if override_id is not None:
        exists = conn.execute("SELECT id FROM lf_study_override WHERE id = ?", (override_id,)).fetchone()
        if exists is None:
            raise ValueError(f"未找到方式调整记录 #{override_id}")
        conn.execute(
            """UPDATE lf_study_override
               SET scheme_name=?, device_type=?, device_idx=?, device_name=?, field=?, value=?, enabled=?, note=?, updated_at=?
               WHERE id=?""",
            (scheme, dev_type, dev_idx, dev_name, field, val, enabled, note, now, override_id),
        )
        action = "update"
    else:
        cur = conn.execute(
            """INSERT INTO lf_study_override(scheme_name, device_type, device_idx, device_name, field, value, enabled, note, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scheme, dev_type, dev_idx, dev_name, field, val, enabled, note, now),
        )
        override_id = int(cur.lastrowid)
        action = "create"

    row = dict(conn.execute("SELECT * FROM lf_study_override WHERE id = ?", (override_id,)).fetchone())
    record_lf_log(
        conn,
        level="INFO",
        stage="override_change",
        source="operator",
        message=f"{'新增' if action == 'create' else '更新'}方式调整 #{override_id}: {dev_type}.{dev_name}.{field} = {val:g}",
        detail=row,
    )
    return row


def delete_lf_override(conn: sqlite3.Connection, override_id: int) -> bool:
    row = conn.execute("SELECT * FROM lf_study_override WHERE id = ?", (int(override_id),)).fetchone()
    if row is None:
        return False
    conn.execute("DELETE FROM lf_study_override WHERE id = ?", (int(override_id),))
    record_lf_log(
        conn,
        level="WARN",
        stage="override_change",
        source="operator",
        message=f"删除方式调整 #{override_id}: {row['device_type']}.{row['device_name']}.{row['field']}",
        detail={"override_id": int(override_id)},
    )
    return True


def clear_lf_overrides(conn: sqlite3.Connection, *, scheme_name: str = "") -> int:
    if scheme_name:
        cur = conn.execute("DELETE FROM lf_study_override WHERE scheme_name = ?", (scheme_name,))
    else:
        cur = conn.execute("DELETE FROM lf_study_override")
    deleted = int(cur.rowcount or 0)
    record_lf_log(
        conn,
        level="WARN",
        stage="override_change",
        source="operator",
        message=f"清空方式调整方案，共删除 {deleted} 条",
        detail={"deleted": deleted, "scheme_name": scheme_name},
    )
    return deleted


# ============================================================================
# LF 运行与审计日志（lf_run_log & lf_log_policy）
# ============================================================================

def ensure_lf_log_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM lf_log_policy WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO lf_log_policy(
               id, enabled, retention_days, keep_error_days, max_rows, cleanup_interval_hours,
               min_level, last_cleanup_at, last_deleted_count, updated_at
           ) VALUES (1, 1, 30, 90, 50000, 6, 'INFO', '', 0, ?)""",
        (now,),
    )
    return dict(conn.execute("SELECT * FROM lf_log_policy WHERE id = 1").fetchone())


def update_lf_log_policy(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    cur = ensure_lf_log_policy(conn)
    enabled = int(bool(int(payload.get("enabled", cur["enabled"]))))
    ret_days = max(1, min(3650, int(payload.get("retention_days", cur["retention_days"]))))
    err_days = max(ret_days, min(3650, int(payload.get("keep_error_days", cur["keep_error_days"]))))
    max_rows = max(100, min(5_000_000, int(payload.get("max_rows", cur["max_rows"]))))
    interval_h = max(1, min(720, int(payload.get("cleanup_interval_hours", cur["cleanup_interval_hours"]))))
    min_level = str(payload.get("min_level", cur["min_level"])).upper()
    if min_level not in VALID_LF_LOG_LEVELS:
        min_level = "INFO"
    now = utc_now()
    conn.execute(
        """UPDATE lf_log_policy
           SET enabled=?, retention_days=?, keep_error_days=?, max_rows=?,
               cleanup_interval_hours=?, min_level=?, updated_at=?
           WHERE id = 1""",
        (enabled, ret_days, err_days, max_rows, interval_h, min_level, now),
    )
    return dict(conn.execute("SELECT * FROM lf_log_policy WHERE id = 1").fetchone())


def record_lf_log(
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
    if lvl not in VALID_LF_LOG_LEVELS:
        lvl = "INFO"
    stg = str(stage or "system").strip()
    if stg not in VALID_LF_LOG_STAGES:
        stg = "system"
    cur = conn.execute(
        """INSERT INTO lf_run_log(run_id, calc_time, level, stage, source, elapsed_ms, message, detail_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            int(run_id) if run_id is not None else None,
            utc_now(),
            lvl,
            stg,
            str(source or "system"),
            float(elapsed_ms) if elapsed_ms is not None else None,
            str(message or "")[:1000],
            json.dumps(detail or {}, ensure_ascii=False, default=str),
        ),
    )
    return int(cur.lastrowid) if cur.lastrowid else None


def list_lf_logs(
    conn: sqlite3.Connection,
    *,
    level: str = "",
    stage: str = "",
    source: str = "",
    run_id: int | None = None,
    window: str = "all",
    q: str = "",
    limit: int = 100,
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
        params.append(stage)
    if source and source != "all":
        clauses.append("source = ?")
        params.append(source)
    if run_id is not None:
        clauses.append("run_id = ?")
        params.append(int(run_id))
    win_hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}.get(str(window or "all"))
    if win_hours:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=win_hours)).isoformat(timespec="milliseconds")
        clauses.append("calc_time >= ?")
        params.append(cutoff)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(message LIKE ? OR stage LIKE ? OR detail_json LIKE ?)")
        params.extend([like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    total = int(conn.execute(f"SELECT COUNT(*) FROM lf_run_log {where}", params).fetchone()[0] or 0)
    rows = [
        dict(r)
        for r in conn.execute(
            f"SELECT * FROM lf_run_log {where} ORDER BY log_id DESC LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    ]
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


def lf_log_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    pol = ensure_lf_log_policy(conn)
    total = int(conn.execute("SELECT COUNT(*) FROM lf_run_log").fetchone()[0] or 0)
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="milliseconds")
    c24 = conn.execute(
        """SELECT COUNT(*) AS total_24h,
                  COALESCE(SUM(level = 'ERROR'), 0) AS err_24h,
                  COALESCE(SUM(level = 'WARN'), 0) AS warn_24h
           FROM lf_run_log WHERE calc_time >= ?""",
        (cutoff_24h,),
    ).fetchone()
    by_stage = [
        dict(r)
        for r in conn.execute(
            """SELECT stage, COUNT(*) AS count, AVG(elapsed_ms) AS avg_ms
               FROM lf_run_log GROUP BY stage ORDER BY count DESC"""
        ).fetchall()
    ]
    pending = purge_lf_logs(conn, dry_run=True)
    return {
        "total": total,
        "total_24h": int(c24["total_24h"] or 0),
        "error_24h": int(c24["err_24h"] or 0),
        "warn_24h": int(c24["warn_24h"] or 0),
        "policy": pol,
        "by_stage": by_stage,
        "pending_purge": pending,
    }


def purge_lf_logs(
    conn: sqlite3.Connection,
    *,
    dry_run: bool = False,
    retention_days: int | None = None,
    keep_error_days: int | None = None,
    max_rows: int | None = None,
    source: str = "operator",
) -> dict[str, Any]:
    pol = ensure_lf_log_policy(conn)
    ret_d = int(retention_days if retention_days is not None else pol["retention_days"])
    err_d = int(keep_error_days if keep_error_days is not None else pol["keep_error_days"])
    cap = int(max_rows if max_rows is not None else pol["max_rows"])
    now_dt = datetime.now(timezone.utc)
    cut_norm = (now_dt - timedelta(days=ret_d)).isoformat(timespec="milliseconds")
    cut_err = (now_dt - timedelta(days=err_d)).isoformat(timespec="milliseconds")
    exp_ids = [
        int(r[0])
        for r in conn.execute(
            "SELECT log_id FROM lf_run_log WHERE (level != 'ERROR' AND calc_time < ?) OR (level = 'ERROR' AND calc_time < ?)",
            (cut_norm, cut_err),
        ).fetchall()
    ]
    total = int(conn.execute("SELECT COUNT(*) FROM lf_run_log").fetchone()[0] or 0)
    remain = max(0, total - len(exp_ids))
    overflow = max(0, remain - cap)
    total_del = len(exp_ids) + overflow
    if dry_run:
        return {"expired_count": len(exp_ids), "overflow_count": overflow, "total_to_delete": total_del, "deleted": 0}
    if exp_ids:
        conn.execute(
            "DELETE FROM lf_run_log WHERE (level != 'ERROR' AND calc_time < ?) OR (level = 'ERROR' AND calc_time < ?)",
            (cut_norm, cut_err),
        )
    if overflow > 0:
        conn.execute(
            "DELETE FROM lf_run_log WHERE log_id IN (SELECT log_id FROM lf_run_log ORDER BY log_id ASC LIMIT ?)",
            (overflow,),
        )
    now_str = utc_now()
    conn.execute(
        "UPDATE lf_log_policy SET last_cleanup_at=?, last_deleted_count=?, updated_at=? WHERE id = 1",
        (now_str, total_del, now_str),
    )
    if total_del > 0:
        record_lf_log(
            conn,
            level="INFO",
            stage="cleanup",
            source=source,
            message=f"清理 LF 运行日志 {total_del} 条（过期 {len(exp_ids)}，超限 {overflow}）",
            detail={"expired": len(exp_ids), "overflow": overflow},
        )
    return {"expired_count": len(exp_ids), "overflow_count": overflow, "total_to_delete": total_del, "deleted": total_del}


def export_lf_logs_csv(conn: sqlite3.Connection, **kwargs) -> str:
    page = list_lf_logs(conn, **{**kwargs, "limit": 500, "offset": 0})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["log_id", "run_id", "calc_time", "level", "stage", "source", "elapsed_ms", "message"])
    for r in page["rows"]:
        w.writerow([r["log_id"], r["run_id"], r["calc_time"], r["level"], r["stage"], r["source"], r["elapsed_ms"], r["message"]])
    return "\ufeff" + buf.getvalue()
