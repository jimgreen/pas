"""南极极地气象条件与交直流微电网能源系统耦合评估引擎。

负责：
1. 极地气象工况实时状态（pas_weather_state）与历史归档（pas_weather_history）持久化；
2. 南极典型气象预设与风/光/储/荷物理耦合评估；
3. CA 气象/负荷预想扰动（太阳辐照归 0、风速归 0、极端切出、负荷陡升/陡降、暴风雪复合）的
   规范化定义与隔离潮流模型覆盖（overrides）生成。
"""

from __future__ import annotations

import json
import math
import sqlite3
from typing import Any

from .se_log import utc_now

DEFAULT_WEATHER_STATE: dict[str, Any] = {
    "irradiance_wm2": 420.0,
    "wind_speed_ms": 9.5,
    "ambient_temp_c": -18.5,
    "pressure_hpa": 982.0,
    "humidity_pct": 58.0,
    "snow_icing_level": 0,
    "polar_regime": "normal",
    "load_factor": 1.0,
    "source": "preset",
    "note": "南极秦岭站常规风电工况",
}

SNOW_ICING_LABELS: dict[int, str] = {
    0: "晴朗无冰",
    1: "轻度吹雪",
    2: "中度覆冰",
    3: "极端暴风雪",
}

POLAR_REGIME_LABELS: dict[str, str] = {
    "normal": "常规南极工况",
    "polar_day": "极昼高辐照",
    "polar_night": "极夜严寒",
    "katabatic": "强下降风风暴",
    "blizzard": "极端暴风雪",
    "extreme_cold": "极寒静风采暖峰",
}

# 6 套南极秦岭站典型极地环境工况预设
POLAR_WEATHER_PRESETS: dict[str, dict[str, Any]] = {
    "normal": {
        "key": "normal",
        "label": "常规南极风电",
        "polar_regime": "normal",
        "irradiance_wm2": 420.0,
        "wind_speed_ms": 9.5,
        "ambient_temp_c": -18.5,
        "pressure_hpa": 982.0,
        "humidity_pct": 58.0,
        "snow_icing_level": 0,
        "load_factor": 1.0,
        "note": "秦岭站常规风电+光伏互补工况",
    },
    "polar_day": {
        "key": "polar_day",
        "label": "极昼晴朗高光",
        "polar_regime": "polar_day",
        "irradiance_wm2": 820.0,
        "wind_speed_ms": 7.2,
        "ambient_temp_c": -6.0,
        "pressure_hpa": 995.0,
        "humidity_pct": 48.0,
        "snow_icing_level": 0,
        "load_factor": 0.92,
        "note": "南极夏季极昼晴朗，光伏高发、采暖负荷偏低",
    },
    "polar_night": {
        "key": "polar_night",
        "label": "极夜无光严寒",
        "polar_regime": "polar_night",
        "irradiance_wm2": 0.0,
        "wind_speed_ms": 11.0,
        "ambient_temp_c": -34.0,
        "pressure_hpa": 976.0,
        "humidity_pct": 62.0,
        "snow_icing_level": 1,
        "load_factor": 1.22,
        "note": "南极极夜无太阳辐照，全靠风电/储能/柴发支撑",
    },
    "katabatic": {
        "key": "katabatic",
        "label": "强下降风风暴",
        "polar_regime": "katabatic",
        "irradiance_wm2": 120.0,
        "wind_speed_ms": 32.0,
        "ambient_temp_c": -28.0,
        "pressure_hpa": 962.0,
        "humidity_pct": 72.0,
        "snow_icing_level": 2,
        "load_factor": 1.18,
        "note": "恩克斯堡岛强下降风，部分风机逼近或触发切出保护",
    },
    "blizzard": {
        "key": "blizzard",
        "label": "极端暴风雪覆冰",
        "polar_regime": "blizzard",
        "irradiance_wm2": 0.0,
        "wind_speed_ms": 38.0,
        "ambient_temp_c": -42.0,
        "pressure_hpa": 948.0,
        "humidity_pct": 88.0,
        "snow_icing_level": 3,
        "load_factor": 1.35,
        "note": "极端暴风雪：光伏归零、风机超切出停机、采暖负荷激增",
    },
    "extreme_cold": {
        "key": "extreme_cold",
        "label": "极寒静风采暖峰",
        "polar_regime": "extreme_cold",
        "irradiance_wm2": 90.0,
        "wind_speed_ms": 1.8,
        "ambient_temp_c": -52.0,
        "pressure_hpa": 1004.0,
        "humidity_pct": 42.0,
        "snow_icing_level": 1,
        "load_factor": 1.42,
        "note": "极寒静风高压：风速低于切入值、电采暖负荷尖峰、电池低温折减",
    },
}

WEATHER_PERTURBATION_KINDS: dict[str, str] = {
    "irradiance_zero": "太阳辐照归 0（极夜/强云遮）",
    "wind_zero": "风速归 0（静风骤停）",
    "wind_cutout": "强下降风超切出保护",
    "load_surge": "站区负荷陡升",
    "load_drop": "站区负荷陡降",
    "blizzard_combo": "暴风雪极端复合冲击",
    "custom": "自定义气象/负荷组合",
}

# 标准南极气象与负荷预想扰动集（纳入 CA 扫描）
DEFAULT_WEATHER_CONTINGENCIES: tuple[dict[str, Any], ...] = (
    {
        "name": "气象:太阳辐照归0",
        "category": "Weather",
        "priority": 12,
        "perturbation": {
            "kind": "irradiance_zero",
            "irradiance_wm2": 0.0,
            "pv_scale": 0.0,
            "label": "太阳辐照归 0（光伏出力归零）",
        },
        "note": "极夜/厚云遮蔽或强吹雪致光伏出力骤降至 0",
    },
    {
        "name": "气象:风速归0（静风骤停）",
        "category": "Weather",
        "priority": 13,
        "perturbation": {
            "kind": "wind_zero",
            "wind_speed_ms": 0.0,
            "wind_scale": 0.0,
            "label": "风速归 0（风电出力归零）",
        },
        "note": "南极冷高压静风过程导致全部风电机组出力归零",
    },
    {
        "name": "气象:极端下降风切出（38m/s）",
        "category": "Weather",
        "priority": 14,
        "perturbation": {
            "kind": "wind_cutout",
            "wind_speed_ms": 38.0,
            "snow_icing_level": 2,
            "label": "风速 38 m/s 超切出保护",
        },
        "note": "秦岭站强下降风超风机切出风速触发全停保护",
    },
    {
        "name": "气象:极寒负荷陡升（+35%）",
        "category": "Weather",
        "priority": 15,
        "perturbation": {
            "kind": "load_surge",
            "load_scale": 1.35,
            "ambient_temp_c": -42.0,
            "label": "极寒采暖负荷陡升 +35%",
        },
        "note": "气温骤降至 -42℃ 引发站区电采暖与防冻伴热负荷陡升 35%",
    },
    {
        "name": "气象:站区负荷陡降（-40%）",
        "category": "Weather",
        "priority": 16,
        "perturbation": {
            "kind": "load_drop",
            "load_scale": 0.60,
            "label": "站区大负荷骤降 -40%",
        },
        "note": "大型科考/电制氢/采暖负荷突卸 40%，校核电压越上限风险",
    },
    {
        "name": "气象:暴风雪极端复合",
        "category": "Weather",
        "priority": 17,
        "perturbation": {
            "kind": "blizzard_combo",
            "irradiance_wm2": 0.0,
            "wind_speed_ms": 38.0,
            "pv_scale": 0.0,
            "wind_scale": 0.0,
            "load_scale": 1.25,
            "ambient_temp_c": -42.0,
            "snow_icing_level": 3,
            "label": "暴风雪：无光+超切出+负荷+25%",
        },
        "note": "南极最严酷暴风雪复合冲击：风光双归零叠加采暖负荷陡升 25%",
    },
)


def _finite_float(val: Any, default: float) -> float:
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def validate_weather_payload(payload: dict[str, Any], base: dict[str, Any] | None = None) -> dict[str, Any]:
    """校验并规范化环境气象工况参数（支持 preset 一键填充 + 单字段覆写）。"""
    out = dict(DEFAULT_WEATHER_STATE)
    if base:
        out.update({k: base[k] for k in DEFAULT_WEATHER_STATE if k in base and base[k] is not None})

    preset_key = str(payload.get("preset") or "").strip()
    if preset_key and preset_key in POLAR_WEATHER_PRESETS:
        preset = POLAR_WEATHER_PRESETS[preset_key]
        for k in DEFAULT_WEATHER_STATE:
            if k in preset:
                out[k] = preset[k]
        out["source"] = "preset"

    float_ranges = {
        "irradiance_wm2": (0.0, 1400.0),
        "wind_speed_ms": (0.0, 65.0),
        "ambient_temp_c": (-85.0, 30.0),
        "pressure_hpa": (850.0, 1060.0),
        "humidity_pct": (0.0, 100.0),
        "load_factor": (0.2, 2.5),
    }
    for k, (lo, hi) in float_ranges.items():
        if k in payload and payload[k] not in (None, ""):
            val = float(payload[k])
            if not math.isfinite(val) or not (lo <= val <= hi):
                raise ValueError(f"气象参数 {k} 超出允许范围 [{lo}, {hi}]")
            out[k] = round(val, 3)

    if "snow_icing_level" in payload and payload["snow_icing_level"] not in (None, ""):
        lvl = int(float(payload["snow_icing_level"]))
        if not (0 <= lvl <= 3):
            raise ValueError("吹雪/覆冰等级 snow_icing_level 必须在 0–3 之间")
        out["snow_icing_level"] = lvl

    if "polar_regime" in payload and str(payload["polar_regime"]).strip():
        reg = str(payload["polar_regime"]).strip()
        if reg not in POLAR_REGIME_LABELS:
            reg = "normal"
        out["polar_regime"] = reg
    elif not preset_key:
        # 根据气象特征自动推断极地工况标签
        if out["snow_icing_level"] >= 3 or (out["wind_speed_ms"] >= 30.0 and out["irradiance_wm2"] <= 20.0):
            out["polar_regime"] = "blizzard"
        elif out["wind_speed_ms"] >= 25.0:
            out["polar_regime"] = "katabatic"
        elif out["ambient_temp_c"] <= -45.0:
            out["polar_regime"] = "extreme_cold"
        elif out["irradiance_wm2"] <= 5.0:
            out["polar_regime"] = "polar_night"
        elif out["irradiance_wm2"] >= 700.0:
            out["polar_regime"] = "polar_day"
        else:
            out["polar_regime"] = "normal"

    if "source" in payload and str(payload["source"]).strip():
        out["source"] = str(payload["source"]).strip()[:32]
    elif not preset_key:
        out["source"] = "manual"

    if "note" in payload and payload["note"] is not None:
        out["note"] = str(payload["note"]).strip()[:240]
    return out


def ensure_weather_state(conn: sqlite3.Connection) -> dict[str, Any]:
    """读取或初始化实时环境气象工况表 pas_weather_state（单行 id=1）。"""
    row = conn.execute("SELECT * FROM pas_weather_state WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    now = utc_now()
    d = dict(DEFAULT_WEATHER_STATE)
    conn.execute(
        """INSERT OR REPLACE INTO pas_weather_state(
               id, irradiance_wm2, wind_speed_ms, ambient_temp_c, pressure_hpa,
               humidity_pct, snow_icing_level, polar_regime, load_factor, source, note, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            d["irradiance_wm2"],
            d["wind_speed_ms"],
            d["ambient_temp_c"],
            d["pressure_hpa"],
            d["humidity_pct"],
            d["snow_icing_level"],
            d["polar_regime"],
            d["load_factor"],
            d["source"],
            d["note"],
            now,
        ),
    )
    conn.execute(
        """INSERT INTO pas_weather_history(
               recorded_at, irradiance_wm2, wind_speed_ms, ambient_temp_c, pressure_hpa,
               humidity_pct, snow_icing_level, polar_regime, load_factor, source, note
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            now,
            d["irradiance_wm2"],
            d["wind_speed_ms"],
            d["ambient_temp_c"],
            d["pressure_hpa"],
            d["humidity_pct"],
            d["snow_icing_level"],
            d["polar_regime"],
            d["load_factor"],
            d["source"],
            d["note"],
        ),
    )
    return dict(conn.execute("SELECT * FROM pas_weather_state WHERE id = 1").fetchone())


def save_weather_state(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    """校验并更新当前气象工况，同时向 pas_weather_history 追加历史记录。"""
    current = ensure_weather_state(conn)
    updated = validate_weather_payload(payload, current)
    now = utc_now()
    conn.execute(
        """INSERT OR REPLACE INTO pas_weather_state(
               id, irradiance_wm2, wind_speed_ms, ambient_temp_c, pressure_hpa,
               humidity_pct, snow_icing_level, polar_regime, load_factor, source, note, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            updated["irradiance_wm2"],
            updated["wind_speed_ms"],
            updated["ambient_temp_c"],
            updated["pressure_hpa"],
            updated["humidity_pct"],
            updated["snow_icing_level"],
            updated["polar_regime"],
            updated["load_factor"],
            updated["source"],
            updated["note"],
            now,
        ),
    )
    conn.execute(
        """INSERT INTO pas_weather_history(
               recorded_at, irradiance_wm2, wind_speed_ms, ambient_temp_c, pressure_hpa,
               humidity_pct, snow_icing_level, polar_regime, load_factor, source, note
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            now,
            updated["irradiance_wm2"],
            updated["wind_speed_ms"],
            updated["ambient_temp_c"],
            updated["pressure_hpa"],
            updated["humidity_pct"],
            updated["snow_icing_level"],
            updated["polar_regime"],
            updated["load_factor"],
            updated["source"],
            updated["note"],
        ),
    )
    return dict(conn.execute("SELECT * FROM pas_weather_state WHERE id = 1").fetchone())


def list_weather_history(conn: sqlite3.Connection, *, limit: int = 60) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 500))
    rows = conn.execute(
        "SELECT * FROM pas_weather_history ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    out = [dict(r) for r in rows]
    out.reverse()
    return out


def _wind_unit_power_ratio(
    wind_speed: float,
    cut_in: float = 3.0,
    rated: float = 12.0,
    cut_out: float = 35.0,
    snow_icing_level: int = 0,
) -> tuple[float, str]:
    """根据标准风电立方功率曲线计算单机出力标幺系数 [0, 1] 与工况状态。"""
    v = max(0.0, float(wind_speed))
    v_in = max(0.5, float(cut_in or 3.0))
    v_r = max(v_in + 1.0, float(rated or 12.0))
    v_out = max(v_r + 1.0, float(cut_out or 35.0))
    icing_loss = {0: 0.0, 1: 0.06, 2: 0.18, 3: 0.45}.get(int(snow_icing_level), 0.0)

    if v < v_in:
        return 0.0, "calm"
    if v >= v_out:
        return 0.0, "cutout"
    if v >= v_r:
        ratio = 1.0
    else:
        ratio = max(0.0, min(1.0, (v**3 - v_in**3) / max(1e-6, v_r**3 - v_in**3)))
    return max(0.0, ratio * (1.0 - icing_loss)), "running"


def _pv_unit_power_ratio(
    irradiance_wm2: float,
    ambient_temp_c: float,
    ref_irradiance: float = 1000.0,
    ref_temp_c: float = 25.0,
    temp_coeff: float = -0.004,
    snow_icing_level: int = 0,
) -> float:
    """根据太阳辐照度、南极低温增益与覆雪遮挡系数计算光伏出力标幺系数 [0, 1.15]。"""
    g = max(0.0, float(irradiance_wm2))
    if g <= 1e-6:
        return 0.0
    g_ref = max(100.0, float(ref_irradiance or 1000.0))
    t_cell = float(ambient_temp_c) + 0.025 * g
    t_factor = max(0.3, min(1.18, 1.0 + float(temp_coeff or -0.004) * (t_cell - float(ref_temp_c or 25.0))))
    snow_loss = {0: 0.0, 1: 0.12, 2: 0.35, 3: 0.85}.get(int(snow_icing_level), 0.0)
    return max(0.0, min(1.15, (g / g_ref) * t_factor * (1.0 - snow_loss)))


def compute_weather_coupling_summary(
    weather: dict[str, Any] | None,
    model_tables: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """计算当前南极气象条件对秦岭站风电、光伏、储能与采暖负荷的实时物理耦合影响。"""
    w = {**DEFAULT_WEATHER_STATE, **(weather or {})}
    g = float(w.get("irradiance_wm2") or 0.0)
    v = float(w.get("wind_speed_ms") or 0.0)
    t = float(w.get("ambient_temp_c") if w.get("ambient_temp_c") is not None else -18.5)
    p_hpa = float(w.get("pressure_hpa") or 982.0)
    hum = float(w.get("humidity_pct") or 58.0)
    icing = int(w.get("snow_icing_level") or 0)
    regime = str(w.get("polar_regime") or "normal")
    lf_fac = float(w.get("load_factor") or 1.0)

    tables = model_tables or {}
    ac_gens = (tables.get("ACGenerator") or {}).get("rows") or ()
    dc_gens = (tables.get("DCGenerator") or {}).get("rows") or ()
    wind_meta_by_gen = {
        int(r["idx_acgenerator"]): r
        for r in ((tables.get("ACWindGen") or {}).get("rows") or ())
        if r.get("idx_acgenerator") is not None
    }
    ac_pv_meta_by_gen = {
        int(r["idx_acgenerator"]): r
        for r in ((tables.get("ACPVGen") or {}).get("rows") or ())
        if r.get("idx_acgenerator") is not None
    }
    dc_pv_meta_by_gen = {
        int(r["idx_dcgenerator"]): r
        for r in ((tables.get("DCPVGen") or {}).get("rows") or ())
        if r.get("idx_dcgenerator") is not None
    }

    wind_rated = 0.0
    wind_avail = 0.0
    wind_units = 0
    wind_cutout = 0
    wind_calm = 0
    pv_rated = 0.0
    pv_avail = 0.0
    pv_units = 0

    for row in ac_gens:
        if int(row.get("run_stat", 1)) == 0:
            continue
        idx = int(row.get("idx") or 0)
        dtype = str(row.get("dev_type") or "").lower()
        name = str(row.get("name") or "")
        rated = _finite_float(row.get("rated_capacity"), 0.0) or _finite_float(row.get("p_max"), 0.0) or _finite_float(row.get("p_set"), 0.0)
        if "wind" in dtype or idx in wind_meta_by_gen or "风" in name:
            wind_units += 1
            meta = wind_meta_by_gen.get(idx) or {}
            ratio, status = _wind_unit_power_ratio(
                v,
                cut_in=_finite_float(meta.get("cut_in_wind_speed"), 3.0),
                rated=_finite_float(meta.get("rated_wind_speed"), 12.0),
                cut_out=_finite_float(meta.get("cut_out_wind_speed"), 35.0),
                snow_icing_level=icing,
            )
            wind_rated += rated
            wind_avail += rated * ratio
            if status == "cutout":
                wind_cutout += 1
            elif status == "calm":
                wind_calm += 1
        elif "pv" in dtype or idx in ac_pv_meta_by_gen or "光伏" in name:
            pv_units += 1
            meta = ac_pv_meta_by_gen.get(idx) or {}
            ratio = _pv_unit_power_ratio(
                g,
                t,
                ref_irradiance=_finite_float(meta.get("reference_irradiance"), 1000.0),
                ref_temp_c=_finite_float(meta.get("reference_temperature"), 25.0),
                temp_coeff=_finite_float(meta.get("temperature_coefficient"), -0.004),
                snow_icing_level=icing,
            )
            pv_rated += rated
            pv_avail += rated * ratio

    for row in dc_gens:
        if int(row.get("run_stat", 1)) == 0:
            continue
        idx = int(row.get("idx") or 0)
        dtype = str(row.get("dev_type") or "").lower()
        name = str(row.get("name") or "")
        rated = _finite_float(row.get("rated_capacity"), 0.0) or _finite_float(row.get("p_max"), 0.0) or _finite_float(row.get("p_set"), 0.0)
        if "pv" in dtype or idx in dc_pv_meta_by_gen or "光伏" in name:
            pv_units += 1
            meta = dc_pv_meta_by_gen.get(idx) or {}
            ratio = _pv_unit_power_ratio(
                g,
                t,
                ref_irradiance=_finite_float(meta.get("reference_irradiance"), 1000.0),
                ref_temp_c=_finite_float(meta.get("reference_temperature"), 25.0),
                temp_coeff=_finite_float(meta.get("temperature_coefficient"), -0.004),
                snow_icing_level=icing,
            )
            pv_rated += rated
            pv_avail += rated * ratio

    # 无模型表时的安全标称估算（保证非模型上下文也可展示耦合比例）
    if wind_units == 0:
        w_ratio, w_stat = _wind_unit_power_ratio(v, snow_icing_level=icing)
        wind_avail_pct = round(w_ratio * 100.0, 1)
    else:
        wind_avail_pct = round((wind_avail / max(wind_rated, 1e-6)) * 100.0, 1)

    if pv_units == 0:
        pv_avail_pct = round(_pv_unit_power_ratio(g, t, snow_icing_level=icing) * 100.0, 1)
    else:
        pv_avail_pct = round((pv_avail / max(pv_rated, 1e-6)) * 100.0, 1)

    # 极寒储能电池可用率（低温导致锂电内阻升高与可用放电倍率折减）
    if t >= -10.0:
        storage_avail_pct = 100.0
    else:
        storage_avail_pct = round(max(50.0, 100.0 - (-10.0 - t) * 0.85), 1)

    # 低温采暖热负荷耦合估算（低于 -20℃ 时每降 10℃ 增加 ~8% 采暖需求）
    cold_heating_delta_pct = round(max(0.0, (-20.0 - t) * 0.8), 1)

    # 南极极端气象告警等级
    if icing >= 3 or v >= 32.0 or t <= -48.0 or (g <= 5.0 and (v < 3.0 or v >= 30.0)):
        alert_level = "extreme"
        alert_label = "极端严酷"
    elif icing >= 2 or v >= 24.0 or t <= -35.0 or g <= 5.0:
        alert_level = "warning"
        alert_label = "气象警戒"
    elif icing == 1 or v < 3.0 or t <= -25.0:
        alert_level = "advisory"
        alert_label = "工况关注"
    else:
        alert_level = "normal"
        alert_label = "气象适宜"

    return {
        "irradiance_wm2": round(g, 1),
        "wind_speed_ms": round(v, 1),
        "ambient_temp_c": round(t, 1),
        "pressure_hpa": round(p_hpa, 1),
        "humidity_pct": round(hum, 1),
        "snow_icing_level": icing,
        "snow_icing_label": SNOW_ICING_LABELS.get(icing, "晴朗无冰"),
        "polar_regime": regime,
        "polar_regime_label": POLAR_REGIME_LABELS.get(regime, "常规南极工况"),
        "load_factor": round(lf_fac, 2),
        "source": str(w.get("source") or "preset"),
        "note": str(w.get("note") or ""),
        "updated_at": str(w.get("updated_at") or ""),
        "alert_level": alert_level,
        "alert_label": alert_label,
        "coupling": {
            "wind_units": wind_units,
            "wind_rated_kw": round(wind_rated, 1),
            "wind_avail_kw": round(wind_avail, 1),
            "wind_avail_pct": wind_avail_pct,
            "wind_cutout_count": wind_cutout,
            "wind_calm_count": wind_calm,
            "pv_units": pv_units,
            "pv_rated_kw": round(pv_rated, 1),
            "pv_avail_kw": round(pv_avail, 1),
            "pv_avail_pct": pv_avail_pct,
            "storage_avail_pct": storage_avail_pct,
            "cold_heating_delta_pct": cold_heating_delta_pct,
            "renewable_avail_kw": round(wind_avail + pv_avail, 1),
        },
    }


def normalize_weather_perturbation(raw: Any) -> dict[str, Any]:
    """校验并规范化 CA 气象/负荷预想扰动参数对象。"""
    if isinstance(raw, str):
        raw = json.loads(raw or "{}")
    if not isinstance(raw, dict):
        raise ValueError("气象扰动参数 perturbation 必须为 JSON 对象")
    kind = str(raw.get("kind") or "custom").strip()
    if kind not in WEATHER_PERTURBATION_KINDS:
        kind = "custom"
    out: dict[str, Any] = {"kind": kind}

    # 按预设 kind 填充合理缺省值，同时允许调用方覆写具体数值
    if kind == "irradiance_zero":
        out["irradiance_wm2"] = 0.0
        out["pv_scale"] = 0.0
    elif kind == "wind_zero":
        out["wind_speed_ms"] = 0.0
        out["wind_scale"] = 0.0
    elif kind == "wind_cutout":
        out["wind_speed_ms"] = 38.0
        out["snow_icing_level"] = 2
    elif kind == "load_surge":
        out["load_scale"] = 1.35
        out["ambient_temp_c"] = -42.0
    elif kind == "load_drop":
        out["load_scale"] = 0.60
    elif kind == "blizzard_combo":
        out["irradiance_wm2"] = 0.0
        out["wind_speed_ms"] = 38.0
        out["pv_scale"] = 0.0
        out["wind_scale"] = 0.0
        out["load_scale"] = 1.25
        out["ambient_temp_c"] = -42.0
        out["snow_icing_level"] = 3

    for key, (lo, hi) in (
        ("irradiance_wm2", (0.0, 1400.0)),
        ("wind_speed_ms", (0.0, 65.0)),
        ("ambient_temp_c", (-85.0, 30.0)),
        ("pv_scale", (0.0, 2.0)),
        ("wind_scale", (0.0, 2.0)),
        ("load_scale", (0.1, 3.0)),
    ):
        if key in raw and raw[key] not in (None, ""):
            val = float(raw[key])
            if not math.isfinite(val) or not (lo <= val <= hi):
                raise ValueError(f"气象扰动参数 {key} 超出范围 [{lo}, {hi}]")
            out[key] = round(val, 3)

    if "snow_icing_level" in raw and raw["snow_icing_level"] not in (None, ""):
        lvl = int(float(raw["snow_icing_level"]))
        if not (0 <= lvl <= 3):
            raise ValueError("snow_icing_level 必须在 0–3 之间")
        out["snow_icing_level"] = lvl

    if raw.get("label"):
        out["label"] = str(raw["label"]).strip()[:120]
    else:
        out["label"] = format_perturbation_desc(out)
    return out


def format_perturbation_desc(pert: dict[str, Any]) -> str:
    """将气象/负荷扰动对象格式化为高密度可读短描述。"""
    parts: list[str] = []
    if "irradiance_wm2" in pert:
        g = float(pert["irradiance_wm2"])
        parts.append("辐照归0" if g <= 1e-6 else f"辐照 {g:g}W/m²")
    elif "pv_scale" in pert:
        parts.append(f"光伏×{float(pert['pv_scale']):g}")

    if "wind_speed_ms" in pert:
        v = float(pert["wind_speed_ms"])
        parts.append("风速归0" if v <= 1e-6 else f"风速 {v:g}m/s")
    elif "wind_scale" in pert:
        parts.append(f"风电×{float(pert['wind_scale']):g}")

    if "load_scale" in pert:
        ls = float(pert["load_scale"])
        pct = round((ls - 1.0) * 100.0, 1)
        sign = "+" if pct >= 0 else ""
        parts.append(f"负荷 {sign}{pct:g}%")

    if "ambient_temp_c" in pert:
        parts.append(f"气温 {float(pert['ambient_temp_c']):g}℃")

    if "snow_icing_level" in pert and int(pert["snow_icing_level"]) > 0:
        parts.append(SNOW_ICING_LABELS.get(int(pert["snow_icing_level"]), ""))

    return " · ".join(p for p in parts if p) or WEATHER_PERTURBATION_KINDS.get(str(pert.get("kind") or "custom"), "气象扰动")


def build_weather_perturbation_overrides(
    perturbation: dict[str, Any],
    weather_state: dict[str, Any] | None,
    raw_tables: dict[str, dict[str, Any]] | None,
    base_overrides: dict[str, dict[int, dict[str, Any]]] | None = None,
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, Any]]:
    """将气象/负荷预想扰动翻译为隔离的内存潮流模型覆盖字典（绝不修改源模型）。

    返回 (overrides, meta)，其中 meta 包含 load_scale_applied 供 CA 精准区分主动降载与真实失电。
    """
    out: dict[str, dict[int, dict[str, Any]]] = {
        dt: {idx: dict(fields) for idx, fields in entries.items()}
        for dt, entries in (base_overrides or {}).items()
    }
    if not raw_tables:
        return out, {"load_scale_applied": float(perturbation.get("load_scale") or 1.0), "affected_devices": 0}

    cur_w = {**DEFAULT_WEATHER_STATE, **(weather_state or {})}
    base_g = float(cur_w.get("irradiance_wm2") or 420.0)
    base_v = float(cur_w.get("wind_speed_ms") or 9.5)
    base_t = float(cur_w.get("ambient_temp_c") if cur_w.get("ambient_temp_c") is not None else -18.5)
    base_icing = int(cur_w.get("snow_icing_level") or 0)

    tgt_g = float(perturbation["irradiance_wm2"]) if "irradiance_wm2" in perturbation else None
    tgt_v = float(perturbation["wind_speed_ms"]) if "wind_speed_ms" in perturbation else None
    tgt_t = float(perturbation["ambient_temp_c"]) if "ambient_temp_c" in perturbation else base_t
    tgt_icing = int(perturbation["snow_icing_level"]) if "snow_icing_level" in perturbation else base_icing
    pv_scale_explicit = float(perturbation["pv_scale"]) if "pv_scale" in perturbation else None
    wind_scale_explicit = float(perturbation["wind_scale"]) if "wind_scale" in perturbation else None
    load_scale = float(perturbation["load_scale"]) if "load_scale" in perturbation else 1.0

    wind_meta = {
        int(r["idx_acgenerator"]): r
        for r in ((raw_tables.get("ACWindGen") or {}).get("rows") or ())
        if r.get("idx_acgenerator") is not None
    }
    ac_pv_meta = {
        int(r["idx_acgenerator"]): r
        for r in ((raw_tables.get("ACPVGen") or {}).get("rows") or ())
        if r.get("idx_acgenerator") is not None
    }
    dc_pv_meta = {
        int(r["idx_dcgenerator"]): r
        for r in ((raw_tables.get("DCPVGen") or {}).get("rows") or ())
        if r.get("idx_dcgenerator") is not None
    }

    affected = 0

    def _current_val(table: str, idx: int, row: dict[str, Any], field: str, default: float = 0.0) -> float:
        ov = out.get(table, {}).get(idx, {})
        if field in ov and ov[field] is not None:
            return _finite_float(ov[field], default)
        return _finite_float(row.get(field), default)

    # 1. 交流电源（风机 + 交流光伏）
    for row in (raw_tables.get("ACGenerator") or {}).get("rows") or ():
        if row.get("idx") is None or int(row.get("run_stat", 1)) == 0:
            continue
        idx = int(row["idx"])
        dtype = str(row.get("dev_type") or "").lower()
        name = str(row.get("name") or "")
        ctrl = str(row.get("control_type") or "").upper()
        if ctrl in ("SL", "SLACK", "VTHETA", "PH"):
            # 平衡节点/V-theta 机组承担功率平衡，不做有功强行置零
            continue

        is_wind = ("wind" in dtype) or (idx in wind_meta) or ("风" in name)
        is_pv = ("pv" in dtype) or (idx in ac_pv_meta) or ("光伏" in name)

        if is_wind and (tgt_v is not None or wind_scale_explicit is not None):
            cur_p = _current_val("ACGenerator", idx, row, "p_set", 0.0)
            cur_q = _current_val("ACGenerator", idx, row, "q_set", 0.0)
            if wind_scale_explicit is not None:
                scale = max(0.0, wind_scale_explicit)
                new_p = cur_p * scale
                new_q = cur_q * scale
            else:
                meta = wind_meta.get(idx) or {}
                c_in = _finite_float(meta.get("cut_in_wind_speed"), 3.0)
                c_rt = _finite_float(meta.get("rated_wind_speed"), 12.0)
                c_out = _finite_float(meta.get("cut_out_wind_speed"), 35.0)
                r_tgt, _ = _wind_unit_power_ratio(tgt_v or 0.0, c_in, c_rt, c_out, tgt_icing)
                if r_tgt <= 1e-6:
                    new_p, new_q = 0.0, 0.0
                else:
                    r_base, _ = _wind_unit_power_ratio(base_v, c_in, c_rt, c_out, base_icing)
                    if r_base > 1e-4 and abs(cur_p) > 1e-4:
                        ratio = r_tgt / r_base
                        new_p = cur_p * ratio
                        new_q = cur_q * ratio
                    else:
                        rated = _finite_float(row.get("rated_capacity"), 0.0) or _finite_float(row.get("p_max"), 0.0)
                        new_p = rated * r_tgt
                        new_q = cur_q
            ent = out.setdefault("ACGenerator", {}).setdefault(idx, {})
            ent["p_set"] = round(new_p, 4)
            ent["q_set"] = round(new_q, 4)
            affected += 1
        elif is_pv and (tgt_g is not None or pv_scale_explicit is not None):
            cur_p = _current_val("ACGenerator", idx, row, "p_set", 0.0)
            cur_q = _current_val("ACGenerator", idx, row, "q_set", 0.0)
            if pv_scale_explicit is not None:
                scale = max(0.0, pv_scale_explicit)
                new_p = cur_p * scale
                new_q = cur_q * scale
            else:
                meta = ac_pv_meta.get(idx) or {}
                r_tgt = _pv_unit_power_ratio(
                    tgt_g or 0.0,
                    tgt_t,
                    _finite_float(meta.get("reference_irradiance"), 1000.0),
                    _finite_float(meta.get("reference_temperature"), 25.0),
                    _finite_float(meta.get("temperature_coefficient"), -0.004),
                    tgt_icing,
                )
                if r_tgt <= 1e-6:
                    new_p, new_q = 0.0, 0.0
                else:
                    r_base = _pv_unit_power_ratio(
                        base_g,
                        base_t,
                        _finite_float(meta.get("reference_irradiance"), 1000.0),
                        _finite_float(meta.get("reference_temperature"), 25.0),
                        _finite_float(meta.get("temperature_coefficient"), -0.004),
                        base_icing,
                    )
                    if r_base > 1e-4 and abs(cur_p) > 1e-4:
                        ratio = r_tgt / r_base
                        new_p = cur_p * ratio
                        new_q = cur_q * ratio
                    else:
                        rated = _finite_float(row.get("rated_capacity"), 0.0)
                        new_p = rated * r_tgt
                        new_q = cur_q
            ent = out.setdefault("ACGenerator", {}).setdefault(idx, {})
            ent["p_set"] = round(new_p, 4)
            ent["q_set"] = round(new_q, 4)
            affected += 1

    # 2. 直流光伏电源
    if tgt_g is not None or pv_scale_explicit is not None:
        for row in (raw_tables.get("DCGenerator") or {}).get("rows") or ():
            if row.get("idx") is None or int(row.get("run_stat", 1)) == 0:
                continue
            idx = int(row["idx"])
            dtype = str(row.get("dev_type") or "").lower()
            name = str(row.get("name") or "")
            if not ("pv" in dtype or idx in dc_pv_meta or "光伏" in name):
                continue
            cur_p = _current_val("DCGenerator", idx, row, "p_set", 0.0)
            if pv_scale_explicit is not None:
                new_p = cur_p * max(0.0, pv_scale_explicit)
            else:
                meta = dc_pv_meta.get(idx) or {}
                r_tgt = _pv_unit_power_ratio(
                    tgt_g or 0.0,
                    tgt_t,
                    _finite_float(meta.get("reference_irradiance"), 1000.0),
                    _finite_float(meta.get("reference_temperature"), 25.0),
                    _finite_float(meta.get("temperature_coefficient"), -0.004),
                    tgt_icing,
                )
                if r_tgt <= 1e-6:
                    new_p = 0.0
                else:
                    r_base = _pv_unit_power_ratio(
                        base_g,
                        base_t,
                        _finite_float(meta.get("reference_irradiance"), 1000.0),
                        _finite_float(meta.get("reference_temperature"), 25.0),
                        _finite_float(meta.get("temperature_coefficient"), -0.004),
                        base_icing,
                    )
                    if r_base > 1e-4 and abs(cur_p) > 1e-4:
                        new_p = cur_p * (r_tgt / r_base)
                    else:
                        rated = _finite_float(row.get("rated_capacity"), 0.0)
                        new_p = rated * r_tgt
            out.setdefault("DCGenerator", {}).setdefault(idx, {})["p_set"] = round(new_p, 4)
            affected += 1

    # 3. 交直流负荷陡升 / 陡降
    if abs(load_scale - 1.0) > 1e-4:
        for row in (raw_tables.get("ACLoad") or {}).get("rows") or ():
            if row.get("idx") is None or int(row.get("run_stat", 1)) == 0:
                continue
            idx = int(row["idx"])
            cur_pbase = _current_val("ACLoad", idx, row, "pbase", 0.0)
            cur_pset = _current_val("ACLoad", idx, row, "p_set", cur_pbase)
            cur_qbase = _current_val("ACLoad", idx, row, "qbase", 0.0)
            if abs(cur_pbase) <= 1e-6 and abs(cur_pset) <= 1e-6:
                continue
            ent = out.setdefault("ACLoad", {}).setdefault(idx, {})
            ent["pbase"] = round(cur_pbase * load_scale, 4)
            ent["p_set"] = round(cur_pset * load_scale, 4)
            ent["qbase"] = round(cur_qbase * load_scale, 4)
            affected += 1

        for row in (raw_tables.get("DCLoad") or {}).get("rows") or ():
            if row.get("idx") is None or int(row.get("run_stat", 1)) == 0:
                continue
            idx = int(row["idx"])
            cur_pbase = _current_val("DCLoad", idx, row, "pbase", 0.0)
            if abs(cur_pbase) <= 1e-6:
                continue
            out.setdefault("DCLoad", {}).setdefault(idx, {})["pbase"] = round(cur_pbase * load_scale, 4)
            affected += 1

    return out, {
        "load_scale_applied": round(load_scale, 4),
        "affected_devices": affected,
        "desc": format_perturbation_desc(perturbation),
    }
