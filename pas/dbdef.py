"""PAS dbdef catalog loading and normalized result row generation.

The reference PAS definitions are preserved in ``dbdef_catalog.json``.  This
module keeps SQL construction constrained to that catalog and translates the
kernel's normalized SE/LF/CA result dictionaries into the legacy table shapes.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

CATALOG_PATH = Path(__file__).with_name("dbdef_catalog.json")
_INT_TYPES = {"INT", "LONG", "UCHAR"}
_FLOAT_TYPES = {"FLOAT", "DOUBLE"}


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, dict[str, Any]]:
    records = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog: dict[str, dict[str, Any]] = {}
    for record in records:
        name = str(record["table_name"])
        columns = list(record.get("columns", []))
        catalog[name] = {
            **record,
            "columns": columns,
            "column_map": {str(col["name"]): col for col in columns},
            "keys": [str(col["name"]) for col in columns if col.get("is_key")],
        }
    return catalog


def table_names(task_type: str | None = None) -> tuple[str, ...]:
    names = sorted(load_catalog())
    if task_type is None:
        return tuple(names)
    if task_type == "se":
        prefixes = ("pas_se_", "pas_sens_")
    elif task_type == "lf":
        prefixes = ("pas_lf_",)
    elif task_type == "ca":
        # CA writes both risk assessment and legacy LF security result tables.
        prefixes = ("pas_ra_", "pas_lf_secure_")
    else:
        raise ValueError(f"unsupported task type: {task_type}")
    return tuple(name for name in names if name.startswith(prefixes))


def _epoch_seconds(value: Any = None) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if value:
        text = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp())
        except ValueError:
            pass
    return int(datetime.now(timezone.utc).timestamp())


def _finite(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _integer(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _code(value: Any) -> int:
    """Stable positive code for dbdef INT fields that receive kernel labels."""
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        digest = hashlib.sha1(str(value or "").encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _risk_value(row: dict[str, Any]) -> float | None:
    for key in ("risk_value", "serious_value", "serious_value_pu"):
        value = _number(row.get(key))
        if value is not None:
            return value
    return None


def _flatten_scalars(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_scalars(item, name)
    elif isinstance(value, (str, int, float, bool)) or value is None:
        yield prefix, value


def _result_object_rows(result_obj: Any, domain: str) -> list[dict[str, Any]]:
    """Convert ACLF/DCLF result dictionaries to rows for lf_device_result."""
    if result_obj is None:
        return []
    collection_map = {
        "branches": "branch",
        "transformers": "transformer",
        "three_winding_transformers": "three_winding_transformer",
        "zero_branches": "zero_branch",
        "breakers": "break",
        "generators": "generator",
        "loads": "load",
        "dcdc_converters": "dcdc_converter",
        "dcac_converters": "dcac_converter",
        "acac_converters": "acac_converter",
    }
    rows: list[dict[str, Any]] = []
    for attr, device_type in collection_map.items():
        items = getattr(result_obj, attr, None) or {}
        if not isinstance(items, dict):
            continue
        for key, item in items.items():
            raw = {str(k): _finite(v) for k, v in vars(item).items()} if hasattr(item, "__dict__") else {}
            name = str(key)
            raw.update({"domain": domain, "device_type": device_type, "device_key": name})
            raw["node_from"] = _integer(raw.get("i_node", raw.get("node")))
            raw["node_to"] = _integer(raw.get("j_node"))
            raw["voltage_from"] = _number(raw.get("i_v", raw.get("voltage")))
            raw["voltage_to"] = _number(raw.get("j_v"))
            raw["p_from"] = _number(raw.get("i_p", raw.get("p")))
            raw["q_from"] = _number(raw.get("i_q", raw.get("q")))
            raw["p_to"] = _number(raw.get("j_p"))
            raw["q_to"] = _number(raw.get("j_q"))
            raw["current_from"] = _number(raw.get("i_c", raw.get("current")))
            raw["current_to"] = _number(raw.get("j_c"))
            raw["result_json"] = raw.copy()
            rows.append(raw)
    return rows


def _device_rows(calc: Any, result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for domain, result_obj in (("ac", getattr(result, "ac", None)), ("dc", getattr(result, "dc", None))):
        rows.extend(_result_object_rows(result_obj, domain))
    # Converter result objects are separate from AC/DC result records.
    for domain, conv_obj in (("dcac", getattr(result, "dcac", None)), ("acac", getattr(result, "acac", None))):
        rows.extend(_result_object_rows(conv_obj, domain))
    if rows:
        return rows
    # Fallback for lightweight/fake kernels exposing only network collections.
    network = getattr(calc, "network", None)
    for domain_name in ("ac", "dc"):
        part = getattr(network, domain_name, None)
        if part is None:
            continue
        for attr, device_type in (("branches", "branch"), ("transformers", "transformer"), ("generators", "generator"), ("loads", "load"), ("breakers", "break"), ("switches", "switch")):
            for item in getattr(part, attr, ()) or ():
                row = {"domain": domain_name, "device_type": device_type, "device_key": str(getattr(item, "name", getattr(item, "idx", "")))}
                for key in ("i_node", "j_node", "i_v", "j_v", "i_p", "j_p", "i_q", "j_q", "i_c", "j_c"):
                    row[key] = _finite(getattr(item, key, None))
                row.update({"node_from": _integer(row.get("i_node")), "node_to": _integer(row.get("j_node")), "voltage_from": _number(row.get("i_v")), "voltage_to": _number(row.get("j_v")), "p_from": _number(row.get("i_p")), "q_from": _number(row.get("i_q")), "p_to": _number(row.get("j_p")), "q_to": _number(row.get("j_q")), "current_from": _number(row.get("i_c")), "current_to": _number(row.get("j_c"))})
                row["result_json"] = row.copy()
                rows.append(row)
    return rows


def build_dbdef_rows(task_type: str, result: dict[str, Any], run_id: int, started_at: Any = None, finished_at: Any = None) -> dict[str, list[dict[str, Any]]]:
    """Build rows keyed by reference dbdef table name."""
    record_time = _epoch_seconds(started_at)
    begin_time = record_time
    end_time = _epoch_seconds(finished_at) if finished_at else record_time
    elapsed = _number(result.get("elapsed_seconds"), 0.0) or 0.0
    rows: dict[str, list[dict[str, Any]]] = {}
    if task_type == "se":
        stats = result.get("statistics") or {}
        measurements = result.get("measurements") or []
        total = _integer(stats.get("measurement_count"), len(measurements)) or 0
        bad = _integer(stats.get("bad_data_count"), 0) or 0
        good = _integer(stats.get("normal_measurement_count"), max(0, total - bad)) or 0
        info = {"time": record_time, "begin_time": begin_time, "end_time": end_time, "consumer_time": elapsed, "calc_status": int(bool(result.get("converged"))), "good_rate": (good / total if total else 0.0), "total_meas": total, "total_meas_prefilter": _integer(stats.get("prefiltered_measurement_count"), 0), "total_meas_bad": bad, "total_meas_err": _number(stats.get("residual_inf"), 0.0), "total_meas_good": good, "total_calc_count": 1, "total_seconv_rate": int(bool(result.get("converged"))), "total_good_rate": (good / total if total else 0.0), "calc_iters": _integer(stats.get("iterations"), result.get("iterations", 0)), "name": "se", "obj_scaling_factor": _number(stats.get("objective"), result.get("objective", 0.0)), "model_time": record_time, "data_time": record_time, "msg_info": str(result.get("summary", {}).get("message", "") or "")}
        rows["pas_se_info"] = [info]
        for idx, item in enumerate(measurements, 1):
            item = dict(item)
            valid = bool(item.get("valid", True))
            source = str(item.get("source", "") or "")
            reason = str(item.get("reason", "") or "")
            row_id = run_id * 1_000_000 + idx
            base = {"id": row_id, "meas_id": _integer(item.get("idx"), idx), "meas_name": item.get("name", item.get("measurement_name", "")), "dev_name": item.get("device_name", item.get("dev_name", "")), "meas_type": _code(item.get("meas_type", item.get("measurement_type", 0))), "meas_value": _number(item.get("value")), "max_value": _number(item.get("max_value")), "min_value": _number(item.get("min_value")), "meas_status": int(valid), "se_value": _number(item.get("estimated_value", item.get("se_value"))), "is_filter": int("filter" in source.lower() or "filter" in reason.lower()), "is_bad": int((not valid) or "bad" in source.lower() or "bad" in reason.lower()), "is_aval": int(item.get("value") is not None), "is_good": int(valid), "meas_st": _integer(item.get("meas_st"), 0), "meas_mpsys": _integer(item.get("meas_mpsys"), 0), "meas_time": record_time}
            rows.setdefault("pas_se_meas", []).append(base)
            if base["is_bad"]:
                rows.setdefault("pas_se_badmeas", []).append({**base, "filter_reason": reason})
            if base["is_filter"]:
                rows.setdefault("pas_se_filtermeas", []).append({**base, "filter_reason": reason})
            if not valid:
                rows.setdefault("pas_se_notusemeas", []).append({**base})
            if item.get("value") is None:
                rows.setdefault("pas_se_nomeas", []).append({**base, "filter_reason": reason})
            if "pseudo" in source.lower() or "pseudo" in reason.lower():
                pseudo = {**base, "meas_weight": _number(item.get("weight")), "meas_time": record_time}
                rows.setdefault("pas_se_psemeas", []).append(pseudo)
                rows.setdefault("pas_se_psemeas_define", []).append({**pseudo, "meas_useflag": int(valid)})
        for idx, (name, value) in enumerate(_flatten_scalars(stats), 1):
            rows.setdefault("pas_se_statics", []).append({"time": record_time, "idx": idx, "name": name, "value": _number(value) if not isinstance(value, str) else value})
    elif task_type == "lf":
        summary = result.get("summary") or {}
        rows["pas_lf_info"] = [{"time": record_time, "begin_time": begin_time, "end_time": end_time, "consumer_time": elapsed, "calc_status": int(bool(result.get("converged"))), "model_time": record_time, "data_time": record_time, "msg_info": str(result.get("failure_reason", "") or ""), "init": 1, "cbolf": 1}]
        for idx, (name, value) in enumerate(_flatten_scalars(summary), 1):
            rows.setdefault("pas_lf_statics", []).append({"time": record_time, "idx": idx, "name": name, "unit": "", "value": _number(value) if not isinstance(value, str) else value})
        for row in result.get("devices") or []:
            rows.setdefault("pas_lf_result", []).append({"time": record_time, "dev_type": row.get("device_type", ""), "dev_name": row.get("device_key", ""), "type": row.get("domain", ""), "unit": "", "base_value": _number(row.get("p_from")), "calc_value": _number(row.get("p_to", row.get("p_from"))), "diff_value": _number(row.get("p_from"), 0.0) - _number(row.get("p_to"), 0.0) if _number(row.get("p_from")) is not None and _number(row.get("p_to")) is not None else None})
    elif task_type == "ca":
        summary = result.get("summary") or {}
        case_name = str(result.get("case_name") or "default")
        rows["pas_ra_info"] = [{"time": record_time, "case_name": case_name, "model_time": record_time, "start_time": begin_time, "end_time": end_time, "time_consume": elapsed, "lf_number": _integer(result.get("n1_scan_count"), 0), "sta_cal": 1, "pro_cal": 1, "current_point": 0, "current_risk_cause": "", "current_name_dis": ""}]
        for idx, item in enumerate(result.get("risks") or [], 1):
            item = dict(item)
            risk_id = run_id * 1_000_000 + idx
            risk_type = _code(item.get("risk_type", ""))
            value = _risk_value(item)
            base = {"time": record_time, "case_name": case_name, "risk_id": risk_id, "dev_type": item.get("dev_type", ""), "dev_name": item.get("dev_name", ""), "risk_type": risk_type, "serious_value": _number(item.get("serious_value"), value), "serious_value_pu": _number(item.get("serious_value_pu"), value), "risk_prob": _number(item.get("risk_prob")), "risk_value": value, "cause_name": item.get("cause_name", item.get("risk_source", "")), "base_value": _number(item.get("base_value")), "limit_max": _number(item.get("limit_max")), "limit_min": _number(item.get("limit_min")), "current_value": _number(item.get("current_value"), value)}
            rows.setdefault("pas_ra_risk_list", []).append(base)
            rows.setdefault("pas_ra_serious_risk", []).append(base)
            rows.setdefault("pas_lf_secure_result", []).append({"time": record_time, "idx": idx, "dev_type": base["dev_type"], "dev_name": base["dev_name"], "type": item.get("risk_type", ""), "level_name": result.get("risk_level", "无"), "value": value, "limit_min": base["limit_min"], "limit_max": base["limit_max"]})
            rows.setdefault("pas_ra_dev_statics", []).append({"time": record_time, "case_name": case_name, "dev_type": base["dev_type"], "dev_name": base["dev_name"], "risk_type": risk_type, "risk_value": value, "risk_number": 1, "risk_level": result.get("risk_level", "无"), "base_value": base["base_value"], "limit_max": base["limit_max"], "limit_min": base["limit_min"], "risk_name": item.get("risk_type", "")})
            rows.setdefault("pas_ra_cause_statics", []).append({"time": record_time, "case_name": case_name, "dev_type": base["dev_type"], "dev_name": base["dev_name"], "risk_type": risk_type, "risk_value": value, "risk_number": 1, "fault_prob": base["risk_prob"], "base_value": base["base_value"], "risk_name": item.get("risk_type", "")})
        for idx, (name, value) in enumerate(_flatten_scalars(summary), 1):
            rows.setdefault("pas_lf_secure_statics", []).append({"time": record_time, "type": "summary", "idx": idx, "level_name": result.get("risk_level", "无"), "num": _integer(value, 0)})
    return {name: values for name, values in rows.items() if values}


def normalize_dbdef_row(table_name: str, row: dict[str, Any]) -> dict[str, Any]:
    catalog = load_catalog().get(table_name)
    if catalog is None:
        raise ValueError(f"unknown dbdef table: {table_name}")
    normalized: dict[str, Any] = {}
    for col in catalog["columns"]:
        name = str(col["name"])
        value = _finite(row.get(name))
        if value is not None:
            dtype = str(col["type"]).upper()
            if dtype in _INT_TYPES:
                value = _integer(value)
            elif dtype in _FLOAT_TYPES:
                value = _number(value)
            elif dtype == "STRING":
                value = str(value)
        normalized[name] = value
    return normalized


def upsert_dbdef_row(connection: Any, table_name: str, row: dict[str, Any]) -> None:
    catalog = load_catalog().get(table_name)
    if catalog is None:
        raise ValueError(f"unknown dbdef table: {table_name}")
    normalized = normalize_dbdef_row(table_name, row)
    names = [str(col["name"]) for col in catalog["columns"]]
    placeholders = ",".join("?" for _ in names)
    quoted = ",".join(f"[{name}]" for name in names)
    connection.execute(f"INSERT OR REPLACE INTO [{table_name}] ({quoted}) VALUES ({placeholders})", tuple(normalized[name] for name in names))
