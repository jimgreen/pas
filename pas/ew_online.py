"""未来 24 小时 96 点安全预警与绿电维生分析（EW: Early Warning）核心业务与算法引擎。

负责：
1. EW 参数管理（ew_para）与 96 点预测覆写（ew_forecast_override）；
2. 多源预测数据读取：优先直连 workspace 下三大预测库
   - 新能源预测：sqldb/forecast/renewgen.db
   - 负荷预测：  sqldb/forecast/load.db
   - 气象预测：  sqldb/forecast/weather.db
   当预测库尚未生成或无未来 96 点数据时，自动融合当前南极气象工况与极地演变剧本合成 96 点预测；
3. 全站实时储能（ACStorageGen / DCStorageGen / HydroStorage）容量与 SOC 采集，以及纯绿电自治
   （仅依赖新能源与储能、零柴发支撑）下的实时绿电维生时长精确逐点物理仿真；
4. 面向未来 96 个 15 分钟时间断面的 N-0 / N-1 预想故障与气象/负荷突变扰动风险扫描，输出
   分时段风险热力矩阵、结构化潜在风险预警清单与调度处置建议。
"""

from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .ca_online import DEFAULT_CA_PARAMS, SEVERITY_RANK
from .se_log import utc_now
from .weather_coupling import (
    DEFAULT_WEATHER_STATE,
    POLAR_REGIME_LABELS,
    SNOW_ICING_LABELS,
    compute_weather_coupling_summary,
)

DEFAULT_EW_PARAMS: dict[str, Any] = {
    "horizon_points": 96,
    "step_minutes": 15,
    "scan_n1": 1,
    "scan_weather": 1,
    "max_n1_devices": 12,
    "v_min_pu": 0.93,
    "v_max_pu": 1.07,
    "overload_warn_pct": 80.0,
    "overload_limit_pct": 100.0,
    "storage_min_soc": 0.15,
    "storage_max_soc": 0.95,
    "storage_eff": 0.92,
    "include_hydrogen": 0,
    "forecast_scenario": "auto",
    "renewgen_db_path": "sqldb/forecast/renewgen.db",
    "load_db_path": "sqldb/forecast/load.db",
    "weather_db_path": "sqldb/forecast/weather.db",
    "do_cycle": 300,
    "enabled": 1,
}

# 6 套南极未来 24 小时极端气象演变剧本（预测库缺失或手工演练时使用）
EW_FORECAST_SCENARIOS: dict[str, dict[str, Any]] = {
    "auto": {
        "key": "auto",
        "label": "自动耦合实时工况",
        "note": "优先直连三大预测库；缺库时自动以当前南极实时气象状态为起点推演未来 24h",
    },
    "normal": {
        "key": "normal",
        "label": "常规风光互补",
        "note": "秦岭站常规风电+日间光伏互补，午间新能源充裕、晚间储能平稳顶峰",
    },
    "blizzard_transit": {
        "key": "blizzard_transit",
        "label": "午后暴风雪过境",
        "note": "第 32–64 点（+8h~+16h）暴风雪袭境：辐照骤降、风速超切出停机、采暖负荷陡升",
    },
    "polar_night": {
        "key": "polar_night",
        "label": "极夜严寒无光",
        "note": "全天 0 辐照、气温 -34~-44℃，完全依赖风电与储能支撑极寒采暖高负荷",
    },
    "katabatic_cutout": {
        "key": "katabatic_cutout",
        "label": "强下降风切出冲击",
        "note": "恩克斯堡岛周期性下降风冲击（26–39 m/s），触发多台风机切出保护与剧烈爬坡",
    },
    "extreme_cold_calm": {
        "key": "extreme_cold_calm",
        "label": "极寒静风低发",
        "note": "极寒高压静风（1.2–3.5 m/s、-48℃），风光持续低发、电池低温折减且负荷尖峰",
    },
}


def _finite(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _ensure_ew_columns(conn: sqlite3.Connection) -> None:
    """平滑迁移已存在旧库，确保 ew_para / ew_run 新字段存在。"""
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ew_para)").fetchall()}
        if cols:
            for col, ddl in (
                ("renewgen_db_path", "TEXT NOT NULL DEFAULT 'sqldb/forecast/renewgen.db'"),
                ("load_db_path", "TEXT NOT NULL DEFAULT 'sqldb/forecast/load.db'"),
                ("weather_db_path", "TEXT NOT NULL DEFAULT 'sqldb/forecast/weather.db'"),
            ):
                if col not in cols:
                    conn.execute(f"ALTER TABLE ew_para ADD COLUMN {col} {ddl}")
    except sqlite3.Error:
        pass


def ensure_ew_params(conn: sqlite3.Connection, *, do_cycle: int | float = 300) -> dict[str, Any]:
    """读取或初始化 ew_para 单行配置。"""
    _ensure_ew_columns(conn)
    row = conn.execute("SELECT * FROM ew_para WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    d = dict(DEFAULT_EW_PARAMS)
    d["do_cycle"] = int(do_cycle or 300)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO ew_para(
               id, horizon_points, step_minutes, scan_n1, scan_weather, max_n1_devices,
               v_min_pu, v_max_pu, overload_warn_pct, overload_limit_pct,
               storage_min_soc, storage_max_soc, storage_eff, include_hydrogen,
               forecast_scenario, renewgen_db_path, load_db_path, weather_db_path,
               do_cycle, enabled, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            d["horizon_points"], d["step_minutes"], d["scan_n1"], d["scan_weather"], d["max_n1_devices"],
            d["v_min_pu"], d["v_max_pu"], d["overload_warn_pct"], d["overload_limit_pct"],
            d["storage_min_soc"], d["storage_max_soc"], d["storage_eff"], d["include_hydrogen"],
            d["forecast_scenario"], d["renewgen_db_path"], d["load_db_path"], d["weather_db_path"],
            d["do_cycle"], d["enabled"], now,
        ),
    )
    return dict(conn.execute("SELECT * FROM ew_para WHERE id = 1").fetchone())


def _validate_ew_params(payload: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    float_ranges = {
        "v_min_pu": (0.5, 1.05),
        "v_max_pu": (0.95, 1.5),
        "overload_warn_pct": (10.0, 200.0),
        "overload_limit_pct": (20.0, 300.0),
        "storage_min_soc": (0.02, 0.6),
        "storage_max_soc": (0.5, 1.0),
        "storage_eff": (0.5, 1.0),
    }
    int_ranges = {
        "horizon_points": (4, 96),
        "step_minutes": (5, 60),
        "scan_n1": (0, 1),
        "scan_weather": (0, 1),
        "max_n1_devices": (1, 60),
        "include_hydrogen": (0, 1),
        "do_cycle": (10, 86400),
        "enabled": (0, 1),
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
    if "forecast_scenario" in payload and str(payload["forecast_scenario"]).strip():
        sc = str(payload["forecast_scenario"]).strip()
        if sc not in EW_FORECAST_SCENARIOS:
            raise ValueError(f"不支持的预测剧本：{sc}")
        out["forecast_scenario"] = sc
    for pk in ("renewgen_db_path", "load_db_path", "weather_db_path"):
        if pk in payload and payload[pk] is not None:
            out[pk] = str(payload[pk]).strip() or DEFAULT_EW_PARAMS[pk]
    if out["v_min_pu"] >= out["v_max_pu"]:
        raise ValueError("电压下限 v_min_pu 必须小于上限 v_max_pu")
    if out["overload_warn_pct"] > out["overload_limit_pct"]:
        raise ValueError("重载预警阈值不能大于过载越限阈值")
    if out["storage_min_soc"] >= out["storage_max_soc"]:
        raise ValueError("储能保护下限 SOC 必须小于充电上限 SOC")
    return out


def save_ew_params(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    """校验并保存 EW 参数并写入审计日志。"""
    current = ensure_ew_params(conn)
    updated = _validate_ew_params(payload, current)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO ew_para(
               id, horizon_points, step_minutes, scan_n1, scan_weather, max_n1_devices,
               v_min_pu, v_max_pu, overload_warn_pct, overload_limit_pct,
               storage_min_soc, storage_max_soc, storage_eff, include_hydrogen,
               forecast_scenario, renewgen_db_path, load_db_path, weather_db_path,
               do_cycle, enabled, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            updated["horizon_points"], updated["step_minutes"], updated["scan_n1"], updated["scan_weather"],
            updated["max_n1_devices"], updated["v_min_pu"], updated["v_max_pu"],
            updated["overload_warn_pct"], updated["overload_limit_pct"],
            updated["storage_min_soc"], updated["storage_max_soc"], updated["storage_eff"],
            updated["include_hydrogen"], updated["forecast_scenario"],
            updated["renewgen_db_path"], updated["load_db_path"], updated["weather_db_path"],
            updated["do_cycle"], updated["enabled"], now,
        ),
    )
    record_ew_log(conn, level="INFO", stage="param_change", source="manual", message="更新 EW 预警与绿电维生参数", detail=updated)
    return dict(conn.execute("SELECT * FROM ew_para WHERE id = 1").fetchone())


def reset_ew_params(conn: sqlite3.Connection) -> dict[str, Any]:
    """恢复 EW 默认参数。"""
    return save_ew_params(conn, dict(DEFAULT_EW_PARAMS))


def record_ew_log(
    conn: sqlite3.Connection,
    *,
    level: str = "INFO",
    stage: str = "system",
    source: str = "system",
    message: str = "",
    ew_run_id: int | None = None,
    elapsed_ms: float | None = None,
    detail: dict[str, Any] | None = None,
) -> int:
    """记录 EW 运行与配置审计日志。"""
    cur = conn.execute(
        """INSERT INTO ew_run_log(ew_run_id, calc_time, level, stage, source, elapsed_ms, message, detail_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ew_run_id,
            utc_now(),
            str(level or "INFO").upper(),
            str(stage or "system"),
            str(source or "system"),
            elapsed_ms,
            str(message or "")[:500],
            json.dumps(detail or {}, ensure_ascii=False, default=str),
        ),
    )
    return int(cur.lastrowid or 0)


def list_ew_overrides(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM ew_forecast_override ORDER BY slot_idx").fetchall()
    return [dict(r) for r in rows]


def save_ew_override(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    """保存单时段预测覆写。"""
    slot = int(payload.get("slot_idx"))
    if not (0 <= slot < 96):
        raise ValueError("slot_idx 必须在 0..95 范围内")
    now = utc_now()

    def _opt_float(k: str) -> float | None:
        v = payload.get(k)
        return None if v in (None, "") else float(v)

    def _opt_int(k: str) -> int | None:
        v = payload.get(k)
        return None if v in (None, "") else int(float(v))

    conn.execute(
        """INSERT OR REPLACE INTO ew_forecast_override(
               slot_idx, irradiance_wm2, wind_speed_ms, ambient_temp_c,
               snow_icing_level, wind_kw, pv_kw, load_kw, note, updated_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            slot,
            _opt_float("irradiance_wm2"),
            _opt_float("wind_speed_ms"),
            _opt_float("ambient_temp_c"),
            _opt_int("snow_icing_level"),
            _opt_float("wind_kw"),
            _opt_float("pv_kw"),
            _opt_float("load_kw"),
            str(payload.get("note") or "")[:200],
            now,
        ),
    )
    return dict(conn.execute("SELECT * FROM ew_forecast_override WHERE slot_idx = ?", (slot,)).fetchone())


def delete_ew_override(conn: sqlite3.Connection, slot_idx: int) -> bool:
    cur = conn.execute("DELETE FROM ew_forecast_override WHERE slot_idx = ?", (int(slot_idx),))
    return cur.rowcount > 0


def clear_ew_overrides(conn: sqlite3.Connection) -> int:
    cur = conn.execute("DELETE FROM ew_forecast_override")
    return int(cur.rowcount or 0)


# ==================== 1. 全站真实储能容量与实时 SOC 采集 ====================

def collect_storage_inventory(
    model_tables: dict[str, dict[str, Any]] | None,
    scada_db_path: Path | None,
) -> dict[str, Any]:
    """从 model/devices.db 与 scdfe_d.db 采集全站电化学储能 + 氢储能额定容量、最大放电功率与实时 SOC。"""
    units: list[dict[str, Any]] = []
    h2_units: list[dict[str, Any]] = []

    # 从 SCADA 实时库读取最新 SOC
    scada_soc: dict[tuple[str, int], tuple[str, float]] = {}
    scada_soc_by_name: dict[str, float] = {}
    if scada_db_path and Path(scada_db_path).is_file():
        try:
            con = sqlite3.connect(f"file:{Path(scada_db_path).resolve()}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
            for tbl in ("ACStorageGen", "DCStorageGen", "HydroStorage"):
                try:
                    cols = {r[1] for r in con.execute(f'PRAGMA table_info("{tbl}")').fetchall()}
                    if {"idx", "soc"} <= cols:
                        name_col = '"name"' if "name" in cols else "''"
                        for r in con.execute(f'SELECT idx, {name_col} AS name, soc FROM "{tbl}"'):
                            if r["soc"] is not None:
                                soc_val = float(r["soc"])
                                if soc_val > 1.5:
                                    soc_val /= 100.0
                                soc_val = max(0.0, min(1.0, soc_val))
                                scada_soc[(tbl, int(r["idx"]))] = (str(r["name"] or ""), soc_val)
                                if r["name"]:
                                    scada_soc_by_name[str(r["name"])] = soc_val
                except sqlite3.Error:
                    continue
            con.close()
        except sqlite3.Error:
            pass

    # 从模型库读取 ACStorageGen / DCStorageGen / HydroStorage 额定参数
    # 模型表列顺序（来自秦岭站 devices.db 实测）：
    # ACStorageGen: (idx, gen_idx, chemistry, ?, cap_kwh, eff, p_chg_max, p_dis_max, soc_init, soc_max, soc_min)
    # DCStorageGen: (idx, gen_idx, chemistry, ?, cap_kwh, eff, p_chg_max, p_dis_max, soc_init, soc_max, soc_min)
    gen_name_map: dict[tuple[str, int], str] = {}
    if model_tables:
        for gtbl in ("ACGenerator", "DCGenerator"):
            blk = model_tables.get(gtbl)
            if not blk:
                continue
            cols = list(blk.get("columns") or [])
            for row in blk.get("rows") or []:
                vals = row if isinstance(row, (list, tuple)) else [row.get(c) for c in cols]
                if len(vals) >= 2:
                    try:
                        gen_name_map[(gtbl, int(vals[0]))] = str(vals[1] or "")
                    except (TypeError, ValueError):
                        pass

        for stbl, domain, gtbl in (("ACStorageGen", "AC", "ACGenerator"), ("DCStorageGen", "DC", "DCGenerator")):
            blk = model_tables.get(stbl)
            if not blk:
                continue
            cols = list(blk.get("columns") or [])
            for r_i, row in enumerate(blk.get("rows") or [], start=1):
                vals = row if isinstance(row, (list, tuple)) else [row.get(c) for c in cols]
                idx = int(_finite(vals[0], r_i)) if len(vals) > 0 else r_i
                gen_idx = int(_finite(vals[1], idx)) if len(vals) > 1 else idx
                cap_kwh = _finite(vals[4], 100.0 if domain == "AC" else 60.0) if len(vals) > 4 else 100.0
                if cap_kwh <= 0:
                    cap_kwh = 100.0 if domain == "AC" else 60.0
                p_chg = _finite(vals[6], cap_kwh * 0.5) if len(vals) > 6 else cap_kwh * 0.5
                p_dis = _finite(vals[7], cap_kwh * 0.5) if len(vals) > 7 else cap_kwh * 0.5
                soc_default = _finite(vals[8], 75.0) if len(vals) > 8 else 75.0
                if soc_default > 1.5:
                    soc_default /= 100.0
                sc_name, soc_live = scada_soc.get((stbl, idx), ("", None))
                dev_name = sc_name or gen_name_map.get((gtbl, gen_idx)) or f"{domain}储能-{idx}"
                if soc_live is None and dev_name in scada_soc_by_name:
                    soc_live = scada_soc_by_name[dev_name]
                soc = soc_live if soc_live is not None else max(0.05, min(0.98, soc_default))
                units.append({
                    "table": stbl,
                    "domain": domain,
                    "idx": idx,
                    "name": dev_name,
                    "capacity_kwh": round(cap_kwh, 2),
                    "max_charge_kw": round(max(1.0, p_chg), 2),
                    "max_discharge_kw": round(max(1.0, p_dis), 2),
                    "soc": round(soc, 4),
                    "soc_pct": round(soc * 100.0, 1),
                    "soc_source": "scada" if soc_live is not None else "model",
                })

        # 氢储能罐（用于计算含储氢扩展维生时长）
        hblk = model_tables.get("HydroStorage")
        if hblk:
            cols = list(hblk.get("columns") or [])
            for r_i, row in enumerate(hblk.get("rows") or [], start=1):
                vals = row if isinstance(row, (list, tuple)) else [row.get(c) for c in cols]
                idx = int(_finite(vals[0], r_i)) if len(vals) > 0 else r_i
                sc_name, soc_live = scada_soc.get(("HydroStorage", idx), ("", None))
                name = sc_name or (str(vals[1]) if len(vals) > 1 and vals[1] else f"储氢罐-{idx}")
                # 集装格式储氢罐按燃料电池综合电等效 320 kWh、额定发电 40 kW 估算
                soc = soc_live if soc_live is not None else 0.58
                h2_units.append({
                    "table": "HydroStorage",
                    "domain": "H2",
                    "idx": idx,
                    "name": name,
                    "capacity_kwh": 320.0,
                    "max_discharge_kw": 40.0,
                    "soc": round(soc, 4),
                    "soc_pct": round(soc * 100.0, 1),
                    "soc_source": "scada" if soc_live is not None else "model",
                })

    # 若无模型表，仍根据 SCADA 储能或秦岭站标准配置兜底
    if not units:
        if scada_soc:
            for (tbl, idx), (nm, soc_val) in sorted(scada_soc.items()):
                if tbl == "HydroStorage":
                    h2_units.append({
                        "table": tbl, "domain": "H2", "idx": idx, "name": nm or f"储氢罐-{idx}",
                        "capacity_kwh": 320.0, "max_discharge_kw": 40.0,
                        "soc": round(soc_val, 4), "soc_pct": round(soc_val * 100.0, 1), "soc_source": "scada",
                    })
                else:
                    is_ac = tbl == "ACStorageGen"
                    cap = 150.0 if is_ac else 60.0
                    units.append({
                        "table": tbl, "domain": "AC" if is_ac else "DC", "idx": idx,
                        "name": nm or f"{'AC' if is_ac else 'DC'}储能-{idx}",
                        "capacity_kwh": cap, "max_charge_kw": 80.0 if is_ac else 60.0,
                        "max_discharge_kw": 80.0 if is_ac else 60.0,
                        "soc": round(soc_val, 4), "soc_pct": round(soc_val * 100.0, 1), "soc_source": "scada",
                    })
        else:
            units = [
                {"table": "ACStorageGen", "domain": "AC", "idx": 1, "name": "交流电化学储能-23", "capacity_kwh": 200.0, "max_charge_kw": 100.0, "max_discharge_kw": 100.0, "soc": 0.72, "soc_pct": 72.0, "soc_source": "default"},
                {"table": "ACStorageGen", "domain": "AC", "idx": 2, "name": "交流电化学储能-26", "capacity_kwh": 100.0, "max_charge_kw": 100.0, "max_discharge_kw": 100.0, "soc": 0.68, "soc_pct": 68.0, "soc_source": "default"},
                {"table": "DCStorageGen", "domain": "DC", "idx": 1, "name": "直流电化学储能组", "capacity_kwh": 360.0, "max_charge_kw": 360.0, "max_discharge_kw": 360.0, "soc": 0.85, "soc_pct": 85.0, "soc_source": "default"},
            ]

    total_kwh = sum(u["capacity_kwh"] for u in units)
    weighted_soc = (
        sum(u["capacity_kwh"] * u["soc"] for u in units) / total_kwh
        if total_kwh > 1e-6 else 0.75
    )
    max_chg = sum(u["max_charge_kw"] for u in units)
    max_dis = sum(u["max_discharge_kw"] for u in units)
    h2_usable_kwh = sum(max(0.0, (u["soc"] - 0.10)) * u["capacity_kwh"] * 0.55 for u in h2_units)
    return {
        "units": units,
        "h2_units": h2_units,
        "total_kwh": round(total_kwh, 2),
        "weighted_soc": round(weighted_soc, 4),
        "weighted_soc_pct": round(weighted_soc * 100.0, 1),
        "max_charge_kw": round(max_chg, 2),
        "max_discharge_kw": round(max_dis, 2),
        "h2_usable_kwh": round(h2_usable_kwh, 2),
    }


# ==================== 2. 三大预测库（renewgen.db / load.db / weather.db）自适应读取 ====================

def _resolve_db_path(raw_path: str, workspace_dir: Path | None) -> Path:
    p = Path(str(raw_path or "").strip())
    if not p.is_absolute() and workspace_dir is not None:
        p = (workspace_dir / p).resolve()
    return p


def _read_forecast_series_from_db(
    db_path: Path,
    kind: str,
    horizon_points: int = 96,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """自适应只读读取 renewgen.db / load.db / weather.db 中的未来 96 点预测序列。

    兼容 forecast_pipeline 标准表（energy_forecasts / weather_forecasts）及通用 96 点时间序列表。
    """
    info: dict[str, Any] = {
        "kind": kind,
        "path": str(db_path),
        "exists": db_path.is_file(),
        "connected": False,
        "table": "",
        "rows": 0,
        "status": "missing",
    }
    if not db_path.is_file():
        return [], info

    preferred_tables = {
        "renewgen": ("energy_forecasts", "renewgen_forecasts", "renewable_forecasts", "renewgen_forecast", "power_forecasts"),
        "load": ("energy_forecasts", "load_forecasts", "load_forecast", "demand_forecasts"),
        "weather": ("weather_forecasts", "weather_forecast", "nwp_forecasts", "meteo_forecasts"),
    }[kind]
    time_candidates = ("target_time_utc", "target_time", "forecast_time", "timestamp_utc", "timestamp", "time", "datetime", "slot_idx")

    try:
        con = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        all_tables = [
            r[0]
            for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if not str(r[0]).startswith(("sqlite_", "rtdb_schema_", "schema_meta"))
        ]
        # 按优先级寻找包含目标字段的数据表
        chosen_table = ""
        chosen_cols: list[str] = []
        ordered_candidates = [t for t in preferred_tables if t in all_tables] + [
            t for t in all_tables if t not in preferred_tables and not t.endswith(("_runs", "_points", "_objects", "_sources", "_logs"))
        ]

        def _has_value_col(cols_l: set[str]) -> bool:
            if kind == "renewgen":
                return bool(cols_l & {"pv_power_kw", "wind_power_kw", "pv_available_power_kw", "wind_available_power_kw", "pv_kw", "wind_kw", "renewable_kw", "power_kw", "p_kw"})
            if kind == "load":
                return bool(cols_l & {"load_kw", "demand_kw", "load_power_kw", "p_load_kw", "total_load_kw", "load", "value"})
            return bool(cols_l & {"wind_speed_mps", "wind_speed_ms", "wind_speed", "solar_radiation_wm2", "irradiance_wm2", "ghi", "temperature_c", "ambient_temp_c", "temp_c"})

        for tbl in ordered_candidates:
            cols = [r[1] for r in con.execute(f'PRAGMA table_info("{tbl}")').fetchall()]
            if _has_value_col({c.lower() for c in cols}):
                cnt = con.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
                if cnt > 0:
                    chosen_table = tbl
                    chosen_cols = cols
                    break

        if not chosen_table:
            con.close()
            info["status"] = "empty"
            return [], info

        cols_lower = {c.lower(): c for c in chosen_cols}
        tcol = next((cols_lower[c] for c in time_candidates if c in cols_lower), None)

        # 若存在 run_id + horizon，优先取最新 day_ahead run
        where_parts: list[str] = []
        params: list[Any] = []
        if "run_id" in cols_lower:
            rc = cols_lower["run_id"]
            if "horizon" in cols_lower:
                hc = cols_lower["horizon"]
                order_col = cols_lower.get("issued_at_utc") or tcol or "rowid"
                row_run = con.execute(
                    f'SELECT "{rc}" FROM "{chosen_table}" WHERE "{hc}" = ? ORDER BY "{order_col}" DESC LIMIT 1',
                    ("day_ahead",),
                ).fetchone()
                if row_run is None:
                    row_run = con.execute(
                        f'SELECT "{rc}" FROM "{chosen_table}" ORDER BY "{order_col}" DESC LIMIT 1'
                    ).fetchone()
            else:
                order_col = cols_lower.get("issued_at_utc") or tcol or "rowid"
                row_run = con.execute(
                    f'SELECT "{rc}" FROM "{chosen_table}" ORDER BY "{order_col}" DESC LIMIT 1'
                ).fetchone()
            if row_run is not None and row_run[0] is not None:
                where_parts.append(f'"{rc}" = ?')
                params.append(row_run[0])

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        order_sql = f'ORDER BY "{tcol}" ASC' if tcol else "ORDER BY rowid ASC"
        raw_rows = con.execute(
            f'SELECT * FROM "{chosen_table}" {where_sql} {order_sql} LIMIT ?',
            (*params, max(horizon_points * 4, 384)),
        ).fetchall()
        con.close()

        # 若记录数大于 horizon_points，从当前时间附近起截取未来 horizon_points 点（若全为历史则取最后 horizon_points 点）
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        records = [dict(r) for r in raw_rows]
        if tcol and len(records) > horizon_points:
            future_idx = next(
                (i for i, rec in enumerate(records) if str(rec.get(tcol) or "") >= now_iso),
                None,
            )
            if future_idx is not None and len(records) - future_idx >= min(16, horizon_points):
                records = records[future_idx : future_idx + horizon_points]
            else:
                records = records[-horizon_points:]
        else:
            records = records[:horizon_points]

        # 规范化字段
        out: list[dict[str, Any]] = []
        for idx, rec in enumerate(records):
            low = {k.lower(): v for k, v in rec.items()}
            item: dict[str, Any] = {
                "slot_idx": idx,
                "timestamp": str(low.get(tcol.lower()) or "") if tcol else "",
            }
            if kind == "renewgen":
                w_val = next((low[k] for k in ("wind_power_kw", "wind_available_power_kw", "wind_kw", "wind_p_kw") if k in low and low[k] is not None), None)
                p_val = next((low[k] for k in ("pv_power_kw", "pv_available_power_kw", "pv_kw", "solar_power_kw", "pv_p_kw") if k in low and low[k] is not None), None)
                tot_val = next((low[k] for k in ("renewable_kw", "power_kw", "p_kw") if k in low and low[k] is not None), None)
                if w_val is not None:
                    item["wind_kw"] = max(0.0, _finite(w_val, 0.0))
                if p_val is not None:
                    item["pv_kw"] = max(0.0, _finite(p_val, 0.0))
                if w_val is None and p_val is None and tot_val is not None:
                    item["renewable_kw"] = max(0.0, _finite(tot_val, 0.0))
            elif kind == "load":
                l_val = next((low[k] for k in ("load_kw", "demand_kw", "load_power_kw", "total_load_kw", "p_load_kw", "load", "value") if k in low and low[k] is not None), None)
                if l_val is not None:
                    item["load_kw"] = max(0.0, _finite(l_val, 0.0))
            else:
                irr = next((low[k] for k in ("solar_radiation_wm2", "irradiance_wm2", "shortwave_radiation", "ghi", "solar_radiation") if k in low and low[k] is not None), None)
                ws = next((low[k] for k in ("wind_speed_mps", "wind_speed_ms", "wind_speed_10m", "wind_speed") if k in low and low[k] is not None), None)
                tc = next((low[k] for k in ("temperature_c", "ambient_temp_c", "temperature_2m", "temp_c", "temperature") if k in low and low[k] is not None), None)
                ic = next((low[k] for k in ("snow_icing_level", "icing_level") if k in low and low[k] is not None), None)
                if irr is not None:
                    item["irradiance_wm2"] = max(0.0, _finite(irr, 0.0))
                if ws is not None:
                    item["wind_speed_ms"] = max(0.0, _finite(ws, 0.0))
                if tc is not None:
                    item["ambient_temp_c"] = _finite(tc, -18.5)
                if ic is not None:
                    item["snow_icing_level"] = max(0, min(3, int(_finite(ic, 0))))
            out.append(item)

        info.update({"connected": bool(out), "table": chosen_table, "rows": len(out), "status": "ok" if out else "empty"})
        return out, info
    except (OSError, sqlite3.Error) as exc:
        info["status"] = f"error:{exc}"
        return [], info


# ==================== 3. 未来 24h 96 点气象/风光/负荷预测曲线生成与融合 ====================

def _build_96_forecast_series(
    *,
    horizon_points: int,
    step_minutes: int,
    weather_state: dict[str, Any],
    base_load_kw: float,
    model_tables: dict[str, dict[str, Any]] | None,
    scenario: str,
    overrides_map: dict[int, dict[str, Any]],
    renewgen_series: list[dict[str, Any]],
    load_series: list[dict[str, Any]],
    weather_series: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """融合三大预测库 + 南极极地物理模型 + 演变剧本 + 手工覆写，输出完整 96 点预测序列。"""
    now_local = datetime.now().replace(second=0, microsecond=0)
    # 向下对齐到最近 15 分钟刻度
    minute_aligned = (now_local.minute // step_minutes) * step_minutes
    start_dt = now_local.replace(minute=minute_aligned)

    w0 = {**DEFAULT_WEATHER_STATE, **(weather_state or {})}
    base_irr = max(0.0, _finite(w0.get("irradiance_wm2"), 420.0))
    base_wind = max(0.0, _finite(w0.get("wind_speed_ms"), 9.5))
    base_temp = _finite(w0.get("ambient_temp_c"), -18.5)
    base_icing = int(_finite(w0.get("snow_icing_level"), 0))
    base_load = max(40.0, _finite(base_load_kw, 240.0))

    eff_scenario = scenario
    if eff_scenario == "auto":
        regime = str(w0.get("polar_regime") or "normal")
        eff_scenario = {
            "blizzard": "blizzard_transit",
            "polar_night": "polar_night",
            "katabatic": "katabatic_cutout",
            "extreme_cold": "extreme_cold_calm",
        }.get(regime, "normal")

    scenario_label = EW_FORECAST_SCENARIOS.get(eff_scenario, EW_FORECAST_SCENARIOS["normal"])["label"]

    points: list[dict[str, Any]] = []
    for i in range(horizon_points):
        dt = start_dt + timedelta(minutes=i * step_minutes)
        hour = dt.hour + dt.minute / 60.0
        phase = 2.0 * math.pi * (i / max(1, horizon_points))

        # 1) 合成南极典型 24h 气象演变基线
        solar_bell = max(0.0, math.sin(math.pi * (hour - 5.5) / 15.0)) ** 1.35 if 5.5 <= hour <= 20.5 else 0.0
        irr = max(0.0, max(base_irr, 520.0) * (0.18 + 1.05 * solar_bell))
        ws = max(0.4, base_wind + 2.4 * math.sin(phase + 0.6) + 1.3 * math.cos(2.0 * phase - 0.3))
        temp = base_temp + 3.2 * math.sin(math.pi * (hour - 8.0) / 12.0)
        icing = base_icing

        if eff_scenario == "blizzard_transit":
            # 第 28–60 点（+7h~+15h）强暴风雪过境
            if 28 <= i <= 60:
                intensity = math.sin(math.pi * (i - 28) / 32.0)
                irr = irr * max(0.0, 1.0 - 1.25 * intensity)
                ws = base_wind + 28.0 * intensity + 2.5 * math.sin(i * 0.5)
                temp = base_temp - 20.0 * intensity
                icing = 3 if intensity >= 0.55 else (2 if intensity >= 0.25 else 1)
        elif eff_scenario == "polar_night":
            irr = 0.0
            ws = max(1.5, 9.2 + 3.8 * math.sin(phase * 1.4) + 1.5 * math.cos(phase * 2.7))
            temp = min(base_temp, -34.0) - 5.5 * (0.5 + 0.5 * math.cos(phase))
            icing = max(1, base_icing)
        elif eff_scenario == "katabatic_cutout":
            gust = max(0.0, math.sin(phase * 2.0 - 0.4))
            ws = 14.0 + 25.0 * (gust ** 1.6)
            irr = irr * (0.45 + 0.35 * (1.0 - gust))
            temp = min(base_temp, -26.0) - 6.0 * gust
            icing = 2 if gust > 0.45 else 1
        elif eff_scenario == "extreme_cold_calm":
            irr = max(0.0, 120.0 * solar_bell)
            ws = max(0.6, 1.8 + 1.2 * math.sin(phase + 0.9))
            temp = min(base_temp, -46.0) - 5.0 * (0.5 + 0.5 * math.cos(phase + 0.5))
            icing = max(1, base_icing)

        # 2) 若 weather.db 提供了预测值，直接以真实预测库为准
        if i < len(weather_series):
            wrec = weather_series[i]
            if "irradiance_wm2" in wrec:
                irr = float(wrec["irradiance_wm2"])
            if "wind_speed_ms" in wrec:
                ws = float(wrec["wind_speed_ms"])
            if "ambient_temp_c" in wrec:
                temp = float(wrec["ambient_temp_c"])
            if "snow_icing_level" in wrec:
                icing = int(wrec["snow_icing_level"])

        # 应用手工气象覆写
        ovr = overrides_map.get(i) or {}
        if ovr.get("irradiance_wm2") is not None:
            irr = float(ovr["irradiance_wm2"])
        if ovr.get("wind_speed_ms") is not None:
            ws = float(ovr["wind_speed_ms"])
        if ovr.get("ambient_temp_c") is not None:
            temp = float(ovr["ambient_temp_c"])
        if ovr.get("snow_icing_level") is not None:
            icing = int(ovr["snow_icing_level"])

        # 3) 通过南极气象耦合模型计算物理风电/光伏出力与低温负荷增量
        coupling_summary = compute_weather_coupling_summary(
            {
                "irradiance_wm2": irr,
                "wind_speed_ms": ws,
                "ambient_temp_c": temp,
                "snow_icing_level": icing,
                "load_factor": 1.0,
            },
            model_tables=model_tables,
        )
        coupling = coupling_summary.get("coupling") or {}
        if int(coupling.get("wind_units") or 0) > 0:
            wind_kw = float(coupling.get("wind_avail_kw") or 0.0)
        else:
            wind_kw = round(120.0 * float(coupling.get("wind_avail_pct") or 0.0) / 100.0, 2)
        if int(coupling.get("pv_units") or 0) > 0:
            pv_kw = float(coupling.get("pv_avail_kw") or 0.0)
        else:
            pv_kw = round(100.0 * float(coupling.get("pv_avail_pct") or 0.0) / 100.0, 2)
        cold_heat_factor = 1.0 + float(coupling.get("cold_heating_delta_pct") or 0.0) / 100.0

        # 站区负荷日曲线（早晚科研+采暖双峰）
        diurnal_load = 0.86 + 0.18 * math.exp(-((hour - 10.5) / 3.4) ** 2) + 0.24 * math.exp(-((hour - 19.5) / 3.6) ** 2)
        load_kw = base_load * diurnal_load * cold_heat_factor

        # 4) 若 renewgen.db / load.db 有真实预测数据，直接覆写为真实预测值
        if i < len(renewgen_series):
            rrec = renewgen_series[i]
            if "wind_kw" in rrec:
                wind_kw = float(rrec["wind_kw"])
            if "pv_kw" in rrec:
                pv_kw = float(rrec["pv_kw"])
            if "renewable_kw" in rrec and "wind_kw" not in rrec and "pv_kw" not in rrec:
                tot = float(rrec["renewable_kw"])
                wind_kw = round(tot * 0.65, 2)
                pv_kw = round(tot * 0.35, 2)
        if i < len(load_series):
            lrec = load_series[i]
            if "load_kw" in lrec:
                load_kw = float(lrec["load_kw"])

        # 应用手工功率覆写
        if ovr.get("wind_kw") is not None:
            wind_kw = max(0.0, float(ovr["wind_kw"]))
        if ovr.get("pv_kw") is not None:
            pv_kw = max(0.0, float(ovr["pv_kw"]))
        if ovr.get("load_kw") is not None:
            load_kw = max(0.0, float(ovr["load_kw"]))

        ren_kw = max(0.0, wind_kw + pv_kw)
        points.append({
            "slot_idx": i,
            "time_label": dt.strftime("%H:%M"),
            "timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "irradiance_wm2": round(irr, 1),
            "wind_speed_ms": round(ws, 2),
            "ambient_temp_c": round(temp, 1),
            "snow_icing_level": int(icing),
            "wind_kw": round(wind_kw, 2),
            "pv_kw": round(pv_kw, 2),
            "renewable_kw": round(ren_kw, 2),
            "load_kw": round(load_kw, 2),
            "net_load_kw": round(load_kw - ren_kw, 2),
            "storage_cold_factor": round(float(coupling["storage_avail_pct"]) / 100.0, 4),
        })

    return points, scenario_label


# ==================== 4. 绿电维生时长精确物理仿真引擎 ====================

def simulate_green_survival(
    points: list[dict[str, Any]],
    storage: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    """逐点仿真纯绿电自治（只依赖风/光新能源和储能，零柴发），精确计算绿电维生时长指标。"""
    step_h = float(params.get("step_minutes", 15)) / 60.0
    soc_min = float(params.get("storage_min_soc", 0.15))
    soc_max = float(params.get("storage_max_soc", 0.95))
    eff = max(0.5, min(1.0, float(params.get("storage_eff", 0.92))))
    eff_sqrt = math.sqrt(eff)

    total_kwh = max(10.0, float(storage.get("total_kwh", 660.0)))
    init_soc = max(0.0, min(1.0, float(storage.get("weighted_soc", 0.75))))
    max_chg_kw = max(10.0, float(storage.get("max_charge_kw", 400.0)))
    max_dis_kw = max(10.0, float(storage.get("max_discharge_kw", 400.0)))
    h2_extra_kwh = float(storage.get("h2_usable_kwh", 0.0))

    first_cold = float(points[0].get("storage_cold_factor", 1.0)) if points else 1.0
    init_usable_kwh = max(0.0, (init_soc - soc_min) * total_kwh * first_cold)

    # 极端无风光保底维生时长（此刻风光骤降为 0、纯靠当前电化学储能能撑多久）
    load_now = max(1.0, float(points[0]["load_kw"])) if points else 150.0
    no_ren_hours = (init_usable_kwh * eff_sqrt) / load_now

    # 逐点纯电化学仿真
    soc = init_soc
    exhausted = False
    survival_hours = 0.0
    exhaust_slot: int | None = None
    exhaust_time = ""
    min_soc_24h = init_soc
    deficit_total_kwh = 0.0
    max_deficit_kw = 0.0
    total_load_kwh = 0.0
    green_served_kwh = 0.0

    # 同步跑一条“含氢储能扩展”仿真用于双口径参考
    h2_rem_kwh = h2_extra_kwh
    h2_exhausted = False
    h2_survival_hours = 0.0

    for pt in points:
        cold_fac = max(0.50, min(1.0, float(pt.get("storage_cold_factor", 1.0))))
        eff_cap_kwh = total_kwh * cold_fac
        load_kw = float(pt["load_kw"])
        ren_kw = float(pt["renewable_kw"])
        net_kw = load_kw - ren_kw  # >0 需储能放电，<0 绿电富余可充电
        total_load_kwh += load_kw * step_h

        st_power_kw = 0.0
        deficit_kw = 0.0

        if net_kw > 0.0:
            avail_kwh = max(0.0, (soc - soc_min) * eff_cap_kwh)
            max_deliver_kw = min(max_dis_kw, (avail_kwh * eff_sqrt) / step_h if step_h > 0 else 0.0)
            if net_kw <= max_deliver_kw + 1e-6:
                st_power_kw = net_kw
                energy_drawn = (net_kw * step_h) / eff_sqrt
                soc = max(soc_min, soc - energy_drawn / max(1e-6, eff_cap_kwh))
                if not exhausted:
                    survival_hours += step_h
            else:
                # 在本步内耗尽或超最大放电功率
                if not exhausted:
                    if net_kw > max_dis_kw + 1e-6 and avail_kwh > 1e-6:
                        frac = 0.0
                    else:
                        frac = max(0.0, min(1.0, (avail_kwh * eff_sqrt) / max(1e-6, net_kw * step_h)))
                    survival_hours += step_h * frac
                    exhausted = True
                    exhaust_slot = int(pt["slot_idx"])
                    exhaust_time = str(pt["time_label"])
                st_power_kw = max_deliver_kw
                deficit_kw = max(0.0, net_kw - max_deliver_kw)
                soc = soc_min if avail_kwh > 0 else soc
        else:
            # 绿电富余给储能充电
            surplus_kw = -net_kw
            room_kwh = max(0.0, (soc_max - soc) * eff_cap_kwh)
            max_absorb_kw = min(max_chg_kw, (room_kwh / eff_sqrt) / step_h if step_h > 0 else 0.0)
            chg_kw = min(surplus_kw, max_absorb_kw)
            st_power_kw = -chg_kw
            soc = min(soc_max, soc + (chg_kw * step_h * eff_sqrt) / max(1e-6, eff_cap_kwh))
            if not exhausted:
                survival_hours += step_h

        # 含储氢扩展口径
        if not h2_exhausted:
            if deficit_kw <= 1e-6:
                h2_survival_hours += step_h
            else:
                need_h2_kwh = deficit_kw * step_h
                if h2_rem_kwh >= need_h2_kwh - 1e-6:
                    h2_rem_kwh -= need_h2_kwh
                    h2_survival_hours += step_h
                else:
                    frac_h2 = max(0.0, min(1.0, h2_rem_kwh / max(1e-6, need_h2_kwh)))
                    h2_survival_hours += step_h * frac_h2
                    h2_rem_kwh = 0.0
                    h2_exhausted = True

        min_soc_24h = min(min_soc_24h, soc)
        deficit_total_kwh += deficit_kw * step_h
        max_deficit_kw = max(max_deficit_kw, deficit_kw)
        green_served_kwh += max(0.0, (load_kw - deficit_kw) * step_h)

        usable_now = max(0.0, (soc - soc_min) * eff_cap_kwh)
        pt["storage_soc_pct"] = round(soc * 100.0, 2)
        pt["storage_power_kw"] = round(st_power_kw, 2)
        pt["storage_usable_kwh"] = round(usable_now, 2)
        pt["green_deficit_kw"] = round(deficit_kw, 2)
        pt["green_alive"] = 0 if (deficit_kw > 0.5) else 1

    horizon_hours = len(points) * step_h
    capped = not exhausted

    # 若 24h 全程未耗尽，按末尾剩余可用电量与 24h 平均净负荷估算外推极限续航时长
    if capped:
        avg_net_kw = max(
            1.0,
            sum(max(0.0, float(p["net_load_kw"])) for p in points) / max(1, len(points)),
        )
        end_usable = float(points[-1]["storage_usable_kwh"]) if points else init_usable_kwh
        extrap_hours = min(168.0, horizon_hours + (end_usable * eff_sqrt) / avg_net_kw)
        if not h2_exhausted:
            h2_survival_hours = min(168.0, extrap_hours + h2_rem_kwh / avg_net_kw)
    else:
        extrap_hours = survival_hours

    ren_share_pct = (green_served_kwh / total_load_kwh * 100.0) if total_load_kwh > 1e-6 else 100.0

    return {
        "green_survival_hours": round(survival_hours, 2),
        "green_survival_minutes": int(round(survival_hours * 60.0)),
        "green_survival_capped": 1 if capped else 0,
        "green_survival_extrap_hours": round(extrap_hours, 2),
        "green_survival_no_ren_hours": round(no_ren_hours, 2),
        "green_survival_with_h2_hours": round(h2_survival_hours, 2),
        "green_exhaust_slot": exhaust_slot,
        "green_exhaust_time": exhaust_time,
        "green_renewable_share_pct": round(min(100.0, max(0.0, ren_share_pct)), 2),
        "storage_init_soc_pct": round(init_soc * 100.0, 2),
        "storage_min_soc_24h_pct": round(min_soc_24h * 100.0, 2),
        "storage_total_kwh": round(total_kwh, 2),
        "storage_usable_kwh": round(init_usable_kwh, 2),
        "storage_max_discharge_kw": round(max_dis_kw, 2),
        "storage_cold_factor": round(first_cold, 4),
        "deficit_total_kwh": round(deficit_total_kwh, 2),
        "max_deficit_kw": round(max_deficit_kw, 2),
    }


# ==================== 5. 未来 96 点 N-0 / N-1 / 气象扰动安全扫描 ====================

def run_ew_analysis(
    *,
    params: dict[str, Any],
    weather_state: dict[str, Any],
    lf_snap: dict[str, Any] | None,
    ca_snap: dict[str, Any] | None,
    contingencies: list[dict[str, Any]] | None,
    model_tables: dict[str, dict[str, Any]] | None,
    scada_db_path: Path | None,
    workspace_dir: Path | None,
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """执行未来 1 天 96 点预警计算：多源预测融合 + 绿电维生仿真 + 全时段 N-0/N-1/扰动扫描。"""
    t0 = time.perf_counter()
    eff = {**DEFAULT_EW_PARAMS, **(params or {})}
    horizon = max(4, min(96, int(eff.get("horizon_points", 96))))
    step_min = int(eff.get("step_minutes", 15))
    scan_n1 = bool(int(eff.get("scan_n1", 1)))
    scan_weather = bool(int(eff.get("scan_weather", 1)))
    max_n1_dev = max(1, int(eff.get("max_n1_devices", 12)))
    v_min = float(eff.get("v_min_pu", 0.93))
    v_max = float(eff.get("v_max_pu", 1.07))
    warn_pct = float(eff.get("overload_warn_pct", 80.0))
    lim_pct = float(eff.get("overload_limit_pct", 100.0))

    # 1. 基态潮流标定（优先取最新收敛 LF 断面 + CA 结果）
    lf_latest = (lf_snap or {}).get("latest") or {}
    lf_buses = list((lf_snap or {}).get("buses") or [])
    lf_branches = list((lf_snap or {}).get("branches") or [])
    ca_latest = (ca_snap or {}).get("latest") or {}
    source_lf_run_id = int(lf_latest["run_id"]) if lf_latest.get("run_id") is not None else None
    source_ca_run_id = int(ca_latest["run_id"]) if ca_latest.get("run_id") is not None else None

    base_load_kw = max(60.0, _finite(lf_latest.get("total_load_p"), 260.0))
    base_max_loading = _finite(lf_latest.get("max_loading_pct"), _finite(ca_latest.get("max_loading_pct"), 48.0))
    # 过滤停运/弱联络孤岛异常母线，取有效运行主网母线电压作为 96 点推演基态
    active_bus_vs = [
        float(b["v_pu"])
        for b in lf_buses
        if b.get("v_pu") is not None and 0.85 <= _finite(b.get("v_pu"), 0.0) <= 1.15
    ]
    raw_min_v = min(active_bus_vs) if active_bus_vs else _finite(lf_latest.get("min_v_pu"), _finite(ca_latest.get("min_v_pu"), 0.985))
    raw_max_v = max(active_bus_vs) if active_bus_vs else _finite(lf_latest.get("max_v_pu"), _finite(ca_latest.get("max_v_pu"), 1.022))
    base_min_v = raw_min_v if 0.85 <= raw_min_v <= 1.05 else 0.985
    base_max_v = raw_max_v if 0.95 <= raw_max_v <= 1.15 else 1.022

    # 提取关键支路/换流器作为 N-1 评估对象（按基态负载率与优先级排序）
    branch_profiles: list[dict[str, Any]] = []
    for br in lf_branches:
        ld = _finite(br.get("loading_pct"), 0.0)
        btype = str(br.get("branch_type") or br.get("device_type") or "ACBranch")
        bname = str(br.get("name") or br.get("device_name") or f"{btype}-{br.get('idx', '')}")
        # 换流器与高载支路在 N-1 下具有更高功率转移放大系数
        transfer_factor = 1.48 if "Converter" in btype else 1.32
        branch_profiles.append({
            "name": bname,
            "type": btype,
            "base_loading": max(8.0, ld),
            "transfer_factor": transfer_factor,
        })
    branch_profiles.sort(key=lambda x: (-x["base_loading"], x["name"]))
    if not branch_profiles:
        branch_profiles = [
            {"name": "交直流互联换流器-1", "type": "DCACConverter", "base_loading": max(35.0, base_max_loading), "transfer_factor": 1.50},
            {"name": "交流主联络线路-1", "type": "ACBranch", "base_loading": max(28.0, base_max_loading * 0.85), "transfer_factor": 1.35},
            {"name": "直流母线主支路-1", "type": "DCBranch", "base_loading": max(24.0, base_max_loading * 0.78), "transfer_factor": 1.30},
        ]

    # 从 CA 预想故障库提取核心 N-1 设备（优先使用用户启用的设备）
    n1_defs = [c for c in (contingencies or []) if str(c.get("category") or "N-1") == "N-1" and int(c.get("enabled", 1)) == 1]
    n1_defs.sort(key=lambda x: (int(x.get("priority") or 50), str(x.get("name") or "")))
    n1_defs = n1_defs[:max_n1_dev]
    if not n1_defs:
        n1_defs = [
            {"name": f"N-1:{bp['name']}", "target_desc": bp["name"], "priority": 10 + idx}
            for idx, bp in enumerate(branch_profiles[:min(6, max_n1_dev)])
        ]

    # 2. 采集全站实时储能容量与 SOC
    storage = collect_storage_inventory(model_tables, scada_db_path)

    # 3. 尝试直连三大预测数据库（renewgen.db / load.db / weather.db）
    rg_path = _resolve_db_path(eff["renewgen_db_path"], workspace_dir)
    ld_path = _resolve_db_path(eff["load_db_path"], workspace_dir)
    wx_path = _resolve_db_path(eff["weather_db_path"], workspace_dir)
    rg_series, rg_info = _read_forecast_series_from_db(rg_path, "renewgen", horizon)
    ld_series, ld_info = _read_forecast_series_from_db(ld_path, "load", horizon)
    wx_series, wx_info = _read_forecast_series_from_db(wx_path, "weather", horizon)

    connected_cnt = sum(1 for x in (rg_info, ld_info, wx_info) if x["connected"])
    if connected_cnt == 3:
        forecast_source = "forecast_db"
    elif connected_cnt > 0:
        forecast_source = "hybrid_db_polar"
    else:
        forecast_source = "polar_synthesis"

    overrides_map = {int(o["slot_idx"]): o for o in (overrides or [])}
    points, scenario_label = _build_96_forecast_series(
        horizon_points=horizon,
        step_minutes=step_min,
        weather_state=weather_state,
        base_load_kw=base_load_kw,
        model_tables=model_tables,
        scenario=str(eff.get("forecast_scenario") or "auto"),
        overrides_map=overrides_map,
        renewgen_series=rg_series,
        load_series=ld_series,
        weather_series=wx_series,
    )

    # 4. 逐点纯绿电维生时长精确物理仿真
    green_stats = simulate_green_survival(points, storage, eff)

    # 5. 对未来 96 个时间点执行 N-0 + N-1 + 气象突变扰动扫描与潜在风险提取
    risks: list[dict[str, Any]] = []
    soc_min_pct = float(eff.get("storage_min_soc", 0.15)) * 100.0
    soc_warn_pct = min(40.0, soc_min_pct + 12.0)

    global_max_load_pct = 0.0
    global_max_load_slot = 0
    global_max_load_time = points[0]["time_label"] if points else ""
    global_max_load_dev = branch_profiles[0]["name"]
    global_min_v: float | None = None
    global_min_v_slot = 0
    global_min_v_time = points[0]["time_label"] if points else ""
    global_max_v: float | None = None

    worst_slot = 0
    worst_time = points[0]["time_label"] if points else ""
    worst_event = ""
    worst_rank = (-1, 0.0)

    risk_slots_count = 0
    n1_risk_total = 0
    weather_risk_total = 0
    green_risk_total = 0
    sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    green_warn_emitted = False
    green_deplete_emitted = False

    lead_branch = branch_profiles[0]
    for pt in points:
        slot = int(pt["slot_idx"])
        t_lbl = str(pt["time_label"])
        load_kw = float(pt["load_kw"])
        ren_kw = float(pt["renewable_kw"])
        net_kw = abs(float(pt["net_load_kw"]))
        load_ratio = max(0.35, max(load_kw, ren_kw * 0.92, net_kw * 1.15) / max(1.0, base_load_kw))

        # N-0 未来时段基态支路负载与电压偏移模型
        n0_loading = round(min(185.0, lead_branch["base_loading"] * (0.35 + 0.65 * load_ratio)), 2)
        v_drop_base = max(0.008, 1.0 - base_min_v)
        n0_min_v = round(max(0.78, 1.0 - v_drop_base * (0.45 + 0.65 * (load_kw / max(1.0, base_load_kw)))), 4)
        # 新能源大发轻载时电压抬升
        surplus_ratio = max(0.0, (ren_kw - load_kw) / max(1.0, base_load_kw))
        n0_max_v = round(min(1.16, max(base_max_v, 1.01) + 0.032 * surplus_ratio), 4)

        slot_risks: list[dict[str, Any]] = []
        slot_n1_risks = 0
        slot_wx_risks = 0

        # 5.1 N-0 越限检查
        if n0_loading >= warn_pct:
            sev = "critical" if n0_loading >= lim_pct * 1.15 else ("high" if n0_loading >= lim_pct else "medium")
            slot_risks.append({
                "slot_idx": slot, "time_label": t_lbl, "category": "N-0", "risk_category": "overload",
                "severity": sev, "contingency_name": "未来基态 N-0", "device_type": lead_branch["type"],
                "device_name": lead_branch["name"], "metric": "loading_pct",
                "actual_value": n0_loading, "limit_value": lim_pct if n0_loading >= lim_pct else warn_pct,
                "violation_pct": round(max(0.0, n0_loading - warn_pct), 2), "unit": "%",
                "detail": f"{t_lbl} 预测负荷 {load_kw:.1f} kW，{lead_branch['name']} 负载率达 {n0_loading:.1f}%",
                "advice": "提前安排储能错峰放电或调节电制氢负荷，降低通道重载风险",
            })
        if n0_min_v < v_min:
            sev = "critical" if n0_min_v < v_min - 0.04 else "high"
            slot_risks.append({
                "slot_idx": slot, "time_label": t_lbl, "category": "N-0", "risk_category": "undervoltage",
                "severity": sev, "contingency_name": "未来基态 N-0", "device_type": "ACNode",
                "device_name": "站区核心母线", "metric": "v_pu",
                "actual_value": n0_min_v, "limit_value": v_min,
                "violation_pct": round((v_min - n0_min_v) / v_min * 100.0, 2), "unit": "pu",
                "detail": f"{t_lbl} 预测重负荷时段母线电压跌至 {n0_min_v:.4f} pu（下限 {v_min:.2f} pu）",
                "advice": "提前投入换流器无功电压支撑并预留储能有功支撑裕度",
            })
        elif n0_max_v > v_max:
            sev = "high" if n0_max_v > v_max + 0.03 else "medium"
            slot_risks.append({
                "slot_idx": slot, "time_label": t_lbl, "category": "N-0", "risk_category": "overvoltage",
                "severity": sev, "contingency_name": "未来基态 N-0", "device_type": "DCNode",
                "device_name": "新能源汇集母线", "metric": "v_pu",
                "actual_value": n0_max_v, "limit_value": v_max,
                "violation_pct": round((n0_max_v - v_max) / v_max * 100.0, 2), "unit": "pu",
                "detail": f"{t_lbl} 风光大发（{ren_kw:.1f} kW）致母线电压抬升至 {n0_max_v:.4f} pu",
                "advice": "安排储能充电消纳或启动电制氢制荷，必要时平滑限电",
            })

        # 5.2 N-1 预想故障扫描（评估该时段下关键设备退出后的转移负载与电压跌落）
        n1_max_loading = n0_loading
        n1_min_v = n0_min_v
        n1_worst_dev = lead_branch["name"]
        if scan_n1 and n1_defs:
            for c_idx, cdef in enumerate(n1_defs):
                cname = str(cdef.get("name") or f"N-1#{c_idx + 1}")
                is_conv = ("换流" in cname) or ("Converter" in cname) or ("变流" in cname)
                tf = 1.46 if is_conv else 1.28
                # 不同设备随索引微调耦合灵敏度，保证物理分布合理
                sens = max(0.72, 1.0 - c_idx * 0.035)
                cand_load = round(min(210.0, n0_loading * tf * sens), 2)
                cand_v = round(max(0.75, n0_min_v - (0.028 if is_conv else 0.017) * load_ratio * sens), 4)
                if cand_load > n1_max_loading:
                    n1_max_loading = cand_load
                    n1_worst_dev = cname
                if cand_v < n1_min_v:
                    n1_min_v = cand_v
                if cand_load >= lim_pct and slot_n1_risks < 2:
                    sev = "critical" if cand_load >= lim_pct * 1.2 else "high"
                    slot_n1_risks += 1
                    slot_risks.append({
                        "slot_idx": slot, "time_label": t_lbl, "category": "N-1", "risk_category": "overload",
                        "severity": sev, "contingency_name": cname, "device_type": "DCACConverter" if is_conv else "ACBranch",
                        "device_name": str(cdef.get("target_desc") or cname), "metric": "loading_pct",
                        "actual_value": cand_load, "limit_value": lim_pct,
                        "violation_pct": round(cand_load - lim_pct, 2), "unit": "%",
                        "detail": f"{t_lbl} 预想故障 [{cname}] 后重载转移至 {cand_load:.1f}%（限值 {lim_pct:.0f}%）",
                        "advice": "提前降低该通道运行负载率，确保 N-1 发生时备用通道不过载",
                    })
                elif cand_v < v_min and slot_n1_risks < 2:
                    sev = "critical" if cand_v < v_min - 0.04 else "high"
                    slot_n1_risks += 1
                    slot_risks.append({
                        "slot_idx": slot, "time_label": t_lbl, "category": "N-1", "risk_category": "undervoltage",
                        "severity": sev, "contingency_name": cname, "device_type": "ACNode",
                        "device_name": str(cdef.get("target_desc") or cname), "metric": "v_pu",
                        "actual_value": cand_v, "limit_value": v_min,
                        "violation_pct": round((v_min - cand_v) / v_min * 100.0, 2), "unit": "pu",
                        "detail": f"{t_lbl} 预想故障 [{cname}] 后母线最低电压跌至 {cand_v:.4f} pu",
                        "advice": "加强交直流母线无功电压调节，避免单故障引发局部失压",
                    })

        # 5.3 未来时段气象/负荷突发扰动分析（风速超切出、暴风雪骤降、极寒负荷陡升）
        if scan_weather:
            # 突发静风/无光扰动：假设该时刻全部新能源骤降 70%，校核功率缺口与储能放电功率上限
            shock_net_kw = load_kw - ren_kw * 0.30
            max_dis = float(storage["max_discharge_kw"])
            if float(pt["wind_speed_ms"]) >= 28.0 or int(pt["snow_icing_level"]) >= 3:
                sev = "critical" if (float(pt["wind_speed_ms"]) >= 35.0 or int(pt["snow_icing_level"]) >= 3) else "high"
                slot_wx_risks += 1
                slot_risks.append({
                    "slot_idx": slot, "time_label": t_lbl, "category": "Weather", "risk_category": "weather_perturbation",
                    "severity": sev, "contingency_name": "气象:强风超切出/暴风雪冲击", "device_type": "Weather",
                    "device_name": "风电场与光伏阵列", "metric": "wind_speed_ms",
                    "actual_value": float(pt["wind_speed_ms"]), "limit_value": 25.0,
                    "violation_pct": round(max(0.0, (float(pt["wind_speed_ms"]) - 25.0) / 25.0 * 100.0), 1), "unit": "m/s",
                    "detail": f"{t_lbl} 预测风速 {pt['wind_speed_ms']} m/s（覆冰等级 {pt['snow_icing_level']}），存在风机切出停机与光伏积雪遮挡风险",
                    "advice": "提前将储能充至高位 SOC（≥85%），必要时将柴发置热备用",
                })
            elif shock_net_kw > max_dis * 0.85:
                sev = "high" if shock_net_kw > max_dis else "medium"
                slot_wx_risks += 1
                slot_risks.append({
                    "slot_idx": slot, "time_label": t_lbl, "category": "Weather", "risk_category": "weather_perturbation",
                    "severity": sev, "contingency_name": "气象:新能源骤降 70% 扰动", "device_type": "Weather",
                    "device_name": "风光互补发电群", "metric": "net_load_kw",
                    "actual_value": round(shock_net_kw, 1), "limit_value": round(max_dis, 1),
                    "violation_pct": round(max(0.0, (shock_net_kw - max_dis * 0.85) / max(1.0, max_dis) * 100.0), 1), "unit": "kW",
                    "detail": f"{t_lbl} 若突发云遮/静风致新能源骤降 70%，净功率缺口 {shock_net_kw:.1f} kW 逼近储能最大放电能力",
                    "advice": "预留旋转备用与可中断电制氢切荷策略，防范瞬时功率失衡",
                })

        # 5.4 绿电维生告警（储能低 SOC 警戒 & 绿电枯竭时刻）
        soc_pct = float(pt["storage_soc_pct"])
        deficit_kw = float(pt["green_deficit_kw"])
        if deficit_kw > 0.5 and not green_deplete_emitted:
            green_deplete_emitted = True
            green_risk_total += 1
            slot_risks.append({
                "slot_idx": slot, "time_label": t_lbl, "category": "Green", "risk_category": "green_depletion",
                "severity": "critical", "contingency_name": "绿电维生触底耗尽", "device_type": "Storage",
                "device_name": "全站电化学储能群", "metric": "storage_soc_pct",
                "actual_value": soc_pct, "limit_value": soc_min_pct,
                "violation_pct": round(deficit_kw / max(1.0, load_kw) * 100.0, 1), "unit": "%",
                "detail": f"{t_lbl}（+{slot * step_min / 60.0:.2f}h）电化学储能触及保护下限 {soc_min_pct:.0f}%，纯绿电缺口 {deficit_kw:.1f} kW",
                "advice": "提前启动燃料电池/柴发并网补能，或对非关键科考/制氢负荷实施有序分级减载",
            })
        elif soc_pct <= soc_warn_pct and not green_warn_emitted and not green_deplete_emitted:
            green_warn_emitted = True
            green_risk_total += 1
            slot_risks.append({
                "slot_idx": slot, "time_label": t_lbl, "category": "Green", "risk_category": "green_depletion",
                "severity": "high", "contingency_name": "绿电储能 SOC 低位预警", "device_type": "Storage",
                "device_name": "全站电化学储能群", "metric": "storage_soc_pct",
                "actual_value": soc_pct, "limit_value": soc_warn_pct,
                "violation_pct": round(max(0.0, soc_warn_pct - soc_pct), 1), "unit": "%",
                "detail": f"{t_lbl} 储能 SOC 预计降至 {soc_pct:.1f}%（低位警戒线 {soc_warn_pct:.0f}%）",
                "advice": "暂停非必要电制氢负荷，优先保障站区基础生命线供电",
            })

        # 汇总单点风险等级与评分
        top_sev = "normal"
        top_event = ""
        for r in slot_risks:
            sev_counts[r["severity"]] = sev_counts.get(r["severity"], 0) + 1
            if SEVERITY_RANK.get(r["severity"], 0) > SEVERITY_RANK.get(top_sev, 0):
                top_sev = r["severity"]
                top_event = r["contingency_name"]
        if slot_risks:
            risk_slots_count += 1
        n1_risk_total += slot_n1_risks
        weather_risk_total += slot_wx_risks

        # 估算单点综合安全分（0-100）
        pt_score = 100.0
        pt_score -= sum(22.0 if r["severity"] == "critical" else (12.0 if r["severity"] == "high" else 5.0) for r in slot_risks)
        if deficit_kw > 0.5:
            pt_score -= 18.0
        pt_score = round(max(5.0, min(100.0, pt_score)), 1)

        pt["n0_max_loading_pct"] = n0_loading
        pt["n0_min_v_pu"] = n0_min_v
        pt["n0_max_v_pu"] = n0_max_v
        pt["n1_max_loading_pct"] = n1_max_loading
        pt["n1_min_v_pu"] = n1_min_v
        pt["n1_risk_count"] = slot_n1_risks
        pt["weather_risk_count"] = slot_wx_risks
        pt["risk_count"] = len(slot_risks)
        pt["risk_level"] = top_sev
        pt["security_score"] = pt_score
        pt["worst_event"] = top_event
        pt["ac_verified"] = 0

        risks.extend(slot_risks)

        if n1_max_loading > global_max_load_pct:
            global_max_load_pct = n1_max_loading
            global_max_load_slot = slot
            global_max_load_time = t_lbl
            global_max_load_dev = n1_worst_dev
        if global_min_v is None or n1_min_v < global_min_v:
            global_min_v = n1_min_v
            global_min_v_slot = slot
            global_min_v_time = t_lbl
        if global_max_v is None or n0_max_v > global_max_v:
            global_max_v = n0_max_v

        rank_key = (SEVERITY_RANK.get(top_sev, 0), n1_max_loading)
        if rank_key > worst_rank and top_event:
            worst_rank = rank_key
            worst_slot = slot
            worst_time = t_lbl
            worst_event = f"{t_lbl} · {top_event}"

    # 6. 综合预警评分与定级（结合绿电维生时长、96点风险比例与最严重越限）
    avg_pt_score = sum(float(p["security_score"]) for p in points) / max(1, len(points))
    green_factor = min(1.0, float(green_stats["green_survival_hours"]) / 24.0)
    ew_score = round(max(10.0, min(100.0, avg_pt_score * 0.72 + (60.0 + 40.0 * green_factor) * 0.28)), 1)
    if sev_counts["critical"] > 0 or float(green_stats["green_survival_hours"]) < 6.0:
        ew_risk_level = "危急"
    elif sev_counts["high"] > 0 or float(green_stats["green_survival_hours"]) < 12.0:
        ew_risk_level = "警戒"
    elif sev_counts["medium"] > 0 or float(green_stats["green_survival_hours"]) < 24.0:
        ew_risk_level = "关注"
    else:
        ew_risk_level = "安全"

    if ew_score >= 90:
        grade, glabel = "A", "优秀"
    elif ew_score >= 80:
        grade, glabel = "B", "良好"
    elif ew_score >= 68:
        grade, glabel = "C", "关注"
    elif ew_score >= 52:
        grade, glabel = "D", "警戒"
    else:
        grade, glabel = "E", "危急"

    surv_txt = (
        f"≥{green_stats['green_survival_hours']:.1f}h（外推 {green_stats['green_survival_extrap_hours']:.1f}h）"
        if green_stats["green_survival_capped"]
        else f"{green_stats['green_survival_hours']:.2f}h（{green_stats['green_exhaust_time']} 触底）"
    )
    summary_text = (
        f"未来 24h（{horizon}点·{scenario_label}）绿电维生时长 {surv_txt}，"
        f"检出风险时段 {risk_slots_count}/{horizon}，综合预警评分 {ew_score:.1f}（{grade}级·{ew_risk_level}）"
    )

    elapsed = round(time.perf_counter() - t0, 3)
    return {
        "calc_time": utc_now(),
        "source_lf_run_id": source_lf_run_id,
        "source_ca_run_id": source_ca_run_id,
        "forecast_source": forecast_source,
        "forecast_scenario": str(eff.get("forecast_scenario") or "auto"),
        "scenario_label": scenario_label,
        "horizon_points": horizon,
        "step_minutes": step_min,
        "risk_level": ew_risk_level,
        "security_score": ew_score,
        "health_grade": grade,
        "health_label": glabel,
        "risk_slots_count": risk_slots_count,
        "critical_count": sev_counts["critical"],
        "high_count": sev_counts["high"],
        "medium_count": sev_counts["medium"],
        "low_count": sev_counts["low"],
        "n1_risk_count": n1_risk_total,
        "weather_risk_count": weather_risk_total,
        "green_risk_count": green_risk_total,
        "max_loading_pct": round(global_max_load_pct, 2),
        "max_loading_slot": global_max_load_slot,
        "max_loading_time": global_max_load_time,
        "max_loading_dev": global_max_load_dev,
        "min_v_pu": global_min_v,
        "min_v_slot": global_min_v_slot,
        "min_v_time": global_min_v_time,
        "max_v_pu": global_max_v,
        "worst_slot": worst_slot,
        "worst_time": worst_time,
        "worst_event": worst_event,
        **green_stats,
        "forecast_load_peak_kw": round(max((float(p["load_kw"]) for p in points), default=0.0), 2),
        "forecast_ren_peak_kw": round(max((float(p["renewable_kw"]) for p in points), default=0.0), 2),
        "elapsed_seconds": elapsed,
        "weather_snapshot": {
            **(weather_state or DEFAULT_WEATHER_STATE),
            "data_sources": {"renewgen": rg_info, "load": ld_info, "weather": wx_info},
        },
        "storage_units": storage["units"] + storage["h2_units"],
        "summary_text": summary_text,
        "points": points,
        "risks": risks,
    }


def persist_ew_run(conn: sqlite3.Connection, result: dict[str, Any], *, source: str = "manual") -> int:
    """持久化 EW 单次运行结果（ew_run + 96点 ew_forecast_point + ew_risk_detail + 审计日志）。"""
    _ensure_ew_columns(conn)
    cur = conn.execute(
        """INSERT INTO ew_run(
               calc_time, source_lf_run_id, source_ca_run_id, forecast_source, forecast_scenario,
               scenario_label, horizon_points, step_minutes, risk_level, security_score,
               health_grade, health_label, risk_slots_count,
               critical_count, high_count, medium_count, low_count,
               n1_risk_count, weather_risk_count, green_risk_count,
               max_loading_pct, max_loading_slot, max_loading_time, max_loading_dev,
               min_v_pu, min_v_slot, min_v_time, max_v_pu,
               worst_slot, worst_time, worst_event,
               green_survival_hours, green_survival_minutes, green_survival_capped,
               green_survival_extrap_hours, green_survival_no_ren_hours, green_survival_with_h2_hours,
               green_exhaust_slot, green_exhaust_time, green_renewable_share_pct,
               storage_init_soc_pct, storage_min_soc_24h_pct, storage_total_kwh,
               storage_usable_kwh, storage_max_discharge_kw, storage_cold_factor,
               deficit_total_kwh, max_deficit_kw, forecast_load_peak_kw, forecast_ren_peak_kw,
               elapsed_seconds, weather_snapshot_json, storage_units_json, summary_text
           ) VALUES (?,?,?,?,?, ?,?,?,?,?, ?,?,?, ?,?,?,?, ?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?, ?,?,?,?, ?,?,?,?)""",
        (
            result["calc_time"], result.get("source_lf_run_id"), result.get("source_ca_run_id"),
            result["forecast_source"], result["forecast_scenario"], result["scenario_label"],
            result["horizon_points"], result["step_minutes"], result["risk_level"], result["security_score"],
            result["health_grade"], result["health_label"], result["risk_slots_count"],
            result["critical_count"], result["high_count"], result["medium_count"], result["low_count"],
            result["n1_risk_count"], result["weather_risk_count"], result["green_risk_count"],
            result["max_loading_pct"], result.get("max_loading_slot"), result["max_loading_time"], result["max_loading_dev"],
            result.get("min_v_pu"), result.get("min_v_slot"), result["min_v_time"], result.get("max_v_pu"),
            result.get("worst_slot"), result["worst_time"], result["worst_event"],
            result["green_survival_hours"], result["green_survival_minutes"], result["green_survival_capped"],
            result["green_survival_extrap_hours"], result["green_survival_no_ren_hours"], result["green_survival_with_h2_hours"],
            result.get("green_exhaust_slot"), result["green_exhaust_time"], result["green_renewable_share_pct"],
            result["storage_init_soc_pct"], result["storage_min_soc_24h_pct"], result["storage_total_kwh"],
            result["storage_usable_kwh"], result["storage_max_discharge_kw"], result["storage_cold_factor"],
            result["deficit_total_kwh"], result["max_deficit_kw"], result["forecast_load_peak_kw"], result["forecast_ren_peak_kw"],
            result["elapsed_seconds"],
            json.dumps(result.get("weather_snapshot") or {}, ensure_ascii=False, default=str),
            json.dumps(result.get("storage_units") or [], ensure_ascii=False, default=str),
            result["summary_text"],
        ),
    )
    ew_run_id = int(cur.lastrowid or 0)
    conn.executemany(
        """INSERT INTO ew_forecast_point(
               ew_run_id, slot_idx, time_label, timestamp,
               irradiance_wm2, wind_speed_ms, ambient_temp_c, snow_icing_level,
               wind_kw, pv_kw, renewable_kw, load_kw, net_load_kw,
               storage_soc_pct, storage_power_kw, storage_usable_kwh, green_deficit_kw, green_alive,
               n0_max_loading_pct, n0_min_v_pu, n0_max_v_pu,
               n1_max_loading_pct, n1_min_v_pu, n1_risk_count, weather_risk_count,
               risk_count, risk_level, security_score, worst_event, ac_verified
           ) VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?,?, ?,?,?,?,?, ?,?,?, ?,?,?,?, ?,?,?,?,?)""",
        [
            (
                ew_run_id, p["slot_idx"], p["time_label"], p["timestamp"],
                p["irradiance_wm2"], p["wind_speed_ms"], p["ambient_temp_c"], p["snow_icing_level"],
                p["wind_kw"], p["pv_kw"], p["renewable_kw"], p["load_kw"], p["net_load_kw"],
                p["storage_soc_pct"], p["storage_power_kw"], p["storage_usable_kwh"], p["green_deficit_kw"], p["green_alive"],
                p["n0_max_loading_pct"], p.get("n0_min_v_pu"), p.get("n0_max_v_pu"),
                p["n1_max_loading_pct"], p.get("n1_min_v_pu"), p["n1_risk_count"], p["weather_risk_count"],
                p["risk_count"], p["risk_level"], p["security_score"], p["worst_event"], p["ac_verified"],
            )
            for p in result.get("points") or []
        ],
    )
    conn.executemany(
        """INSERT INTO ew_risk_detail(
               ew_run_id, slot_idx, time_label, category, risk_category, severity,
               contingency_name, device_type, device_name, metric,
               actual_value, limit_value, violation_pct, unit, detail, advice
           ) VALUES (?,?,?,?,?,?, ?,?,?,?, ?,?,?,?,?,?)""",
        [
            (
                ew_run_id, r["slot_idx"], r["time_label"], r["category"], r["risk_category"], r["severity"],
                r["contingency_name"], r["device_type"], r["device_name"], r["metric"],
                r.get("actual_value"), r.get("limit_value"), r["violation_pct"], r["unit"], r["detail"], r["advice"],
            )
            for r in result.get("risks") or []
        ],
    )
    record_ew_log(
        conn,
        ew_run_id=ew_run_id,
        level="WARN" if result["risk_level"] in ("警戒", "危急") else "INFO",
        stage="ew_scan",
        source=source,
        elapsed_ms=round(float(result["elapsed_seconds"]) * 1000.0, 1),
        message=result["summary_text"],
        detail={
            "green_survival_hours": result["green_survival_hours"],
            "risk_slots_count": result["risk_slots_count"],
            "forecast_source": result["forecast_source"],
            "forecast_scenario": result["forecast_scenario"],
        },
    )
    # 仅保留最近 120 次 EW 运行避免库膨胀
    conn.execute(
        "DELETE FROM ew_run WHERE ew_run_id NOT IN (SELECT ew_run_id FROM ew_run ORDER BY ew_run_id DESC LIMIT 120)"
    )
    return ew_run_id


def export_ew_risks_csv(rows: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["时段序号", "时刻", "分类", "风险类型", "严重等级", "扰动/事件", "设备", "指标", "预测值", "限值", "越限%", "详情", "处置建议"])
    for r in rows:
        w.writerow([
            r.get("slot_idx"), r.get("time_label"), r.get("category"), r.get("risk_category"),
            r.get("severity"), r.get("contingency_name"), r.get("device_name"), r.get("metric"),
            r.get("actual_value"), r.get("limit_value"), r.get("violation_pct"),
            r.get("detail"), r.get("advice"),
        ])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")
