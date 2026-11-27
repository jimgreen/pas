"""Adapters around the reference SE, LF, and CA calculation kernels."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .model_cache import lf_models
from .model_input import kernel_model, read_model_tables, validate_references
from .config import validate_task_inputs
from .input_store import (
    SE_DEVICE_RESULT_METRICS,
    SE_SOLVER_METRICS,
    SQLITE_SUFFIXES,
    is_scdfe_d_wide_db,
    measurement_input,
    read_limits,
)
from .ca_online import (
    DEFAULT_CA_PARAMS,
    SEVERITY_RANK,
    compute_grid_health_assessment,
    compute_security_score_and_level,
    evaluate_lf_state_risks,
)
from .lf_online import (
    DEFAULT_LF_PARAMS,
    build_se_base_overrides,
    lf_parameter_file,
    merge_study_overrides,
)
from .se_bad import detect_suspect_statuses
from .se_params import se_parameter_file
from .weather_coupling import (
    build_weather_perturbation_overrides,
    compute_weather_coupling_summary,
)


def configure_kernel_path(kernel_root: str | Path) -> Path:
    root = Path(kernel_root).expanduser().resolve()
    source = root / "src"
    package_source = source / "hybrid_power_system_analysis"
    if package_source.is_dir():
        import_paths = (source, package_source)
    elif all((root / marker).is_file() for marker in ("secore/ac_se.py", "lfcore/hybrid_lf.py", "cacore/hybrid_ca.py")):
        import_paths = (root, root.parent)
    else:
        raise FileNotFoundError(f"kernel source directory does not exist: {package_source}")
    for item in import_paths:
        text = str(item)
        if text not in sys.path:
            sys.path.insert(0, text)
    return root


def input_fingerprint(paths: list[Path | None]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path is None:
            continue
        item = Path(path)
        digest.update(str(item.resolve()).encode())
        stat = item.stat()
        digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
    return digest.hexdigest()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        num = float(value)
        return num if math.isfinite(num) else default
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "tolist"):
        return _json_value(value.tolist())
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _object_row(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return {str(key): _json_value(value) for key, value in row.items()}
    result = {}
    for name in ("idx", "name", "device_type", "device_name", "meas_type", "weight", "valid", "value", "estimated_value", "residual", "normalized_residual", "reason", "source"):
        if hasattr(row, name):
            result[name] = _json_value(getattr(row, name))
    return result


def normalize_se(se_result: Any, estimate_result: Any | None = None) -> dict[str, Any]:
    stats_obj = getattr(se_result, "statistics", None) or SimpleStatistics()
    stats = {name: _json_value(getattr(stats_obj, name, 0)) for name in (
        "converged", "iterations", "objective", "max_correction", "residual_inf", "observable", "rank", "state_count", "measurement_count", "deficiency", "prefiltered_measurement_count", "pseudo_measurement_count", "bad_data_count", "normal_measurement_count")}
    state = _json_value(getattr(estimate_result, "x", getattr(se_result, "state", [])) if estimate_result is not None else getattr(se_result, "state", []))
    rows = []
    for name in ("prefiltered_measurements", "pseudo_measurements", "bad_data", "normal_measurements"):
        table = getattr(se_result, name, ()) or ()
        rows.extend(_object_row(row) for row in table)
    return {"converged": bool(stats["converged"]), "observable": bool(stats["observable"]), "iterations": _int(stats["iterations"]), "objective": _number(stats["objective"]), "max_correction": _number(stats["max_correction"]), "residual_inf": _number(stats["residual_inf"]), "statistics": stats, "state": state if isinstance(state, list) else _json_value(state), "measurements": rows, "summary": {"measurement_rows": len(rows)}}


class SimpleStatistics:
    converged = False
    iterations = 0
    objective = 0.0
    max_correction = 0.0
    residual_inf = 0.0
    observable = False
    rank = 0
    state_count = 0
    measurement_count = 0
    deficiency = 0
    prefiltered_measurement_count = 0
    pseudo_measurement_count = 0
    bad_data_count = 0
    normal_measurement_count = 0


def normalize_lf(calc: Any) -> dict[str, Any]:
    result = getattr(calc, "lf_result", None)
    devices = _extract_lf_devices(calc, result)
    counts = {}
    for row in devices:
        key = f"{row['domain']}.{row['device_type']}"
        counts[key] = counts.get(key, 0) + 1
    arrays = getattr(result, "arrays", {}) or {}
    summary = {key: _json_value(value) for key, value in arrays.items() if value is None or isinstance(value, (str, bool, int, float))}
    summary["device_counts"] = counts
    return {"converged": bool(getattr(calc, "converged", False)), "iterations": _int(getattr(calc, "iterations", 0)), "norm_f": _number(getattr(calc, "normF", 0.0)), "failure_reason": str(getattr(calc, "failure_reason", "") or ""), "ac_converged": getattr(getattr(result, "ac_calc", None), "converged", None), "ac_iterations": getattr(getattr(result, "ac_calc", None), "iterations", None), "ac_norm_f": getattr(getattr(result, "ac_calc", None), "normF", None), "dc_converged": getattr(getattr(result, "dc_calc", None), "converged", None), "dc_iterations": getattr(getattr(result, "dc_calc", None), "iterations", None), "dc_norm_f": getattr(getattr(result, "dc_calc", None), "normF", None), "summary": summary, "devices": devices}


def _extract_lf_devices(calc: Any, result: Any) -> list[dict[str, Any]]:
    """Extract full-mode AC/DC result objects into UI/database rows.

    The reference hybrid kernel exposes ACLFResult/DCLFResult dictionaries;
    lightweight network objects are used only to add terminal node ids.
    """
    if result is None:
        return []
    collection_map = {
        "branches": "branch", "transformers": "transformer",
        "three_winding_transformers": "three_winding_transformer",
        "zero_branches": "zero_branch", "breakers": "break",
        "generators": "generator", "loads": "load",
        "dcdc_converters": "dcdc_converter", "dcac_converters": "dcac_converter",
        "acac_converters": "acac_converter",
    }
    rows: list[dict[str, Any]] = []
    present_domains: set[str] = set()

    for domain, result_obj in (("ac", getattr(result, "ac", None)), ("dc", getattr(result, "dc", None)), ("dcac", getattr(result, "dcac", None)), ("acac", getattr(result, "acac", None))):
        if result_obj is None:
            continue
        present_domains.add(domain)
        part = getattr(getattr(result, "network", None), domain if domain in {"ac", "dc"} else "ac", None)
        for attr, device_type in collection_map.items():
            items = getattr(result_obj, attr, None) or {}
            if not isinstance(items, dict):
                continue
            # Build one lookup per collection instead of scanning for every result.
            network_items = getattr(part, attr, ()) if part is not None else ()
            network_index = {}
            for candidate in network_items or ():
                network_index.setdefault(str(getattr(candidate, "name", getattr(candidate, "idx", ""))), candidate)
            for key, item in items.items():
                raw = dict(vars(item)) if hasattr(item, "__dict__") else {}
                raw = {str(k): _json_value(v) for k, v in raw.items()}
                network_device = network_index.get(str(key))
                if network_device is not None:
                    for name in ("idx", "i_node", "j_node", "node", "i_node_obj", "j_node_obj"):
                        if name not in raw and hasattr(network_device, name):
                            value = getattr(network_device, name)
                            raw[name] = _json_value(getattr(value, "idx", value))
                raw.update({"domain": domain, "device_type": device_type, "device_key": str(key)})
                raw.update({
                    "node_from": raw.get("i_node", raw.get("node")), "node_to": raw.get("j_node"),
                    "voltage_from": raw.get("i_v", raw.get("voltage")), "voltage_to": raw.get("j_v"),
                    "p_from": raw.get("i_p", raw.get("p")), "q_from": raw.get("i_q", raw.get("q")),
                    "p_to": raw.get("j_p"), "q_to": raw.get("j_q"),
                    "current_from": raw.get("i_c", raw.get("current")), "current_to": raw.get("j_c"),
                })
                rows.append(raw)
    # Converter-only full results may omit ACLFResult/DCLFResult while the
    # solved network device lists still contain the AC/DC terminal values.
    network = getattr(result, "network", None) or getattr(calc, "network", None)
    for domain_name in ("ac", "dc"):
        if domain_name in present_domains:
            continue
        part = getattr(network, domain_name, None)
        if part is None:
            continue
        for attr, device_type in (("branches", "branch"), ("transformers", "transformer"), ("generators", "generator"), ("loads", "load"), ("breakers", "break"), ("switches", "switch"), ("zero_branches", "zero_branch")):
            for item in getattr(part, attr, ()) or ():
                row = {"domain": domain_name, "device_type": device_type, "device_key": str(getattr(item, "name", getattr(item, "idx", "")))}
                for key in ("idx", "i_node", "j_node", "i_p", "j_p", "i_q", "j_q", "i_c", "j_c"):
                    row[key] = _json_value(getattr(item, key, None))
                for side in ("i", "j"):
                    node_obj = getattr(item, f"{side}_node_obj", None)
                    row[f"{side}_v"] = _json_value(getattr(node_obj, "voltage", None)) if node_obj is not None else None
                row.update({
                    "node_from": row.get("i_node"), "node_to": row.get("j_node"),
                    "voltage_from": row.get("i_v"), "voltage_to": row.get("j_v"),
                    "p_from": row["i_p"] if row["i_p"] is not None else _json_value(getattr(item, "p", None)), "q_from": row["i_q"] if row["i_q"] is not None else _json_value(getattr(item, "q", None)),
                    "p_to": row.get("j_p"), "q_to": row.get("j_q"),
                    "current_from": row["i_c"] if row["i_c"] is not None else _json_value(getattr(item, "current", None)), "current_to": row.get("j_c"),
                })
                rows.append(row)
    return rows


def _risk_row(risk: Any, contingency: str) -> dict[str, Any]:
    return {"contingency": contingency, "risk_source": str(getattr(risk, "risk_source", "")), "risk_dist": str(getattr(risk, "risk_dist", "")), "risk_type": str(getattr(risk, "risk_type", "")), "risk_value": _json_value(getattr(risk, "risk_value", None)), "risk_info": str(getattr(risk, "risk_info", ""))}


def normalize_ca(n0_risks: list[Any], n1_risks: list[Any], n1_scan_count: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    n0 = [_risk_row(row, "N-0") for row in n0_risks]
    n1 = [_risk_row(row, "N-1") for row in n1_risks]
    combined = n0 + n1
    level = "高" if any(row["risk_type"] in {"潮流发散", "负荷损失"} for row in combined) else ("中" if combined else "无")
    return ({"risk_level": level, "n0_risk_count": len(n0), "n1_scan_count": _int(n1_scan_count, 0), "n1_risk_count": len(n1), "risks": combined, "summary": {"n0": n0, "n1": n1}}, {"n0": n0, "n1": n1})


_U_UNIT_TO_SCALE = {"mV": 1_000_000.0, "V": 1000.0, "kV": 1.0}
_P_UNIT_TO_SCALE = {"W": 1000.0, "kW": 1.0, "MW": 0.001}
_I_UNIT_TO_SCALE = {"mA": 1_000_000.0, "A": 1000.0, "kA": 1.0}
_Q_UNIT_BY_P = {"W": "var", "kW": "kvar", "MW": "Mvar"}


class _ModelUnitConverter:
    """与参考内核 unit_system.py 完全一致的标幺值 <-> 模型工程单位换算器。"""

    def __init__(self, snapshot: dict[str, list[dict[str, Any]]]):
        model_rows = snapshot.get("Model") or snapshot.get("PowerBase") or [{}]
        row = model_rows[0] if model_rows else {}
        self.p_base = _number(row.get("p_base"), 100.0)
        self.u_unit = str(row.get("u_unit") or "kV")
        self.p_unit = str(row.get("p_unit") or "kW")
        self.i_unit = str(row.get("i_unit") or "kA")
        self.q_unit = _Q_UNIT_BY_P.get(self.p_unit, "kvar")
        self.u_scale = _U_UNIT_TO_SCALE.get(self.u_unit, 1.0)
        self.p_scale = _P_UNIT_TO_SCALE.get(self.p_unit, 1.0)
        self.i_scale = _I_UNIT_TO_SCALE.get(self.i_unit, 1.0)
        self.p_base_kw = self.p_base / self.p_scale
        self.ac_vbase = {
            _int(item.get("idx")): _number(item.get("vbase"), 1.0)
            for item in snapshot.get("ACNode") or ()
            if item.get("idx") is not None
        }
        self.dc_vbase = {
            _int(item.get("idx")): _number(item.get("vbase"), 1.0)
            for item in snapshot.get("DCNode") or ()
            if item.get("idx") is not None
        }
        self.devices_by_name: dict[str, dict[str, dict[str, Any]]] = {}
        for table_name, rows in snapshot.items():
            if not rows:
                continue
            mapping: dict[str, dict[str, Any]] = {}
            for item in rows:
                if "name" in item:
                    mapping[str(item["name"])] = item
                if "idx" in item:
                    mapping.setdefault(str(item["idx"]), item)
            if mapping:
                self.devices_by_name[table_name] = mapping

    def unit_for(self, meas_type: str) -> str:
        prefix = str(meas_type or "").split("_", 1)[0]
        if prefix == "V":
            return self.u_unit
        if prefix == "I":
            return self.i_unit
        if prefix == "Q":
            return self.q_unit
        if prefix == "P":
            return self.p_unit
        if prefix in {"ANGLE", "THETA"}:
            return "rad"
        return ""

    def scale_for(self, device_type: str, device_name: str, meas_type: str) -> float:
        mtype = str(meas_type or "")
        if mtype.startswith(("P", "Q")):
            return self.p_base
        if mtype.startswith(("ANGLE", "THETA")):
            return 1.0
        row = self.devices_by_name.get(device_type, {}).get(str(device_name))
        if row is None:
            return 1.0
        is_dc = device_type.startswith("DC") and device_type != "DCACConverter"
        if device_type in {"ACNode", "DCNode"}:
            vbase = _number(row.get("vbase"), 1.0)
        elif device_type in {"ACGenerator", "ACLoad"}:
            vbase = self.ac_vbase.get(_int(row.get("node")), 1.0)
        elif device_type in {"DCGenerator", "DCLoad"}:
            vbase = self.dc_vbase.get(_int(row.get("node")), 1.0)
        elif device_type in {"ACBranch", "ACZeroBranch", "ACBreak", "ACSwitch", "ACTransformer"}:
            node_key = "j_node" if mtype.endswith("_TO") else "i_node"
            vbase = self.ac_vbase.get(_int(row.get(node_key)), 1.0)
        elif device_type in {"DCBranch", "DCZeroBranch", "DCBreak", "DCSwitch", "DCDCConverter"}:
            node_key = "j_node" if mtype.endswith("_TO") else "i_node"
            vbase = self.dc_vbase.get(_int(row.get(node_key)), 1.0)
        elif device_type == "DCACConverter":
            if mtype.endswith("_DC"):
                is_dc = True
                vbase = self.dc_vbase.get(_int(row.get("dc_node")), 1.0)
            else:
                is_dc = False
                vbase = self.ac_vbase.get(_int(row.get("ac_node")), 1.0)
        else:
            return 1.0
        if mtype.startswith("V"):
            return vbase
        if mtype.startswith("I"):
            vbase_kv = abs(vbase) / self.u_scale
            if vbase_kv <= 1e-12:
                return 1.0
            denom = 1000.0 * (vbase_kv if is_dc else math.sqrt(3.0) * vbase_kv)
            return (self.p_base_kw / denom) * self.i_scale
        return 1.0

    def ac_current_from_pqv(self, p_val: float | None, q_val: float | None, v_val: float | None) -> float | None:
        """由交流有功、无功与线电压工程值反算三相平衡电流工程值。"""
        if p_val is None or q_val is None or v_val is None:
            return None
        if abs(v_val) <= 1e-9:
            return 0.0
        p_kw = p_val / self.p_scale
        q_kvar = q_val / self.p_scale
        v_kv = abs(v_val) / self.u_scale
        i_ka = math.hypot(p_kw, q_kvar) / (1000.0 * math.sqrt(3.0) * v_kv)
        return i_ka * self.i_scale

    def dc_current_from_pv(self, p_val: float | None, v_val: float | None) -> float | None:
        """由直流功率与电压工程值反算直流电流工程值。"""
        if p_val is None or v_val is None:
            return None
        if abs(v_val) <= 1e-9:
            return 0.0
        p_kw = p_val / self.p_scale
        v_kv = v_val / self.u_scale
        i_ka = p_kw / (1000.0 * v_kv)
        return i_ka * self.i_scale


def _resolve_pos_device_name(
    device_type: str,
    device_name: str,
    name_arrays: dict[int, Any],
    device_type_codes: dict[str, int],
) -> str:
    if not isinstance(device_name, str) or not device_name.startswith("pos:"):
        return str(device_name or "")
    try:
        pos = int(device_name.split(":", 1)[1])
    except ValueError:
        return device_name
    code = device_type_codes.get(device_type)
    arr = name_arrays.get(code) if code is not None else None
    if arr is not None and 0 <= pos < len(arr):
        return str(arr[pos])
    return device_name


def _evaluate_all_device_se_values(
    estimator: Any,
    snapshot: dict[str, list[dict[str, Any]]],
    converter: _ModelUnitConverter,
    device_meas: dict[tuple[str, int, str], dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """基于求解状态向量 x 评估全网各类设备表的 SE 估计值，并与实测值配对。"""
    import numpy as np
    from model.meas_model import (
        DEVICE_TYPE_CODES,
        Measurement,
        TableBackedMeasurementList,
        measurement_table_from_measurements,
    )
    from model.meas_type import MEAS_TYPE_NAMES
    from secore.se_math import ANGLE_MEASUREMENT_TYPES

    eval_items: list[tuple[str, int, str, str, str]] = []
    eval_measurements: list[Any] = []
    eid = 0
    for table_name, metric_map in SE_DEVICE_RESULT_METRICS.items():
        for dev_row in snapshot.get(table_name) or ():
            dev_idx = _int(dev_row.get("idx"))
            dev_name = str(dev_row.get("name", dev_idx))
            for metric, se_code in metric_map.items():
                eid += 1
                eval_items.append((table_name, dev_idx, dev_name, metric, se_code))
                eval_measurements.append(
                    Measurement(
                        idx=eid,
                        name=f"{table_name}.{dev_idx}.{metric}",
                        device_type=table_name,
                        device_name=dev_name,
                        meas_type=se_code,
                        weight=1.0,
                        valid=True,
                        value=0.0,
                    )
                )

    evaluated_eng: dict[tuple[str, int, str], float | None] = {}
    x_vec = getattr(getattr(estimator, "estimate_result", None), "x", None)
    if eval_measurements and x_vec is not None and len(x_vec) > 0:
        meas_code_by_name = {name: code for code, name in MEAS_TYPE_NAMES.items()}
        name_arrays = estimator._measurement_name_arrays_by_type_code()
        pos_lookup = {
            int(code): {str(name): idx for idx, name in enumerate(arr)}
            for code, arr in name_arrays.items()
        }
        eval_table = measurement_table_from_measurements(
            eval_measurements,
            device_type_codes=DEVICE_TYPE_CODES,
            angle_measurement_types=ANGLE_MEASUREMENT_TYPES,
        )
        eval_table.device_pos = np.asarray(
            [
                pos_lookup.get(int(code), {}).get(str(name), -1)
                for code, name in zip(eval_table.device_type_code, eval_table.device_name)
            ],
            dtype=np.int64,
        )
        eval_table.meas_type_code = np.asarray(
            [meas_code_by_name.get(str(mt), 0) for mt in eval_table.meas_type],
            dtype=np.int16,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            z_pu = estimator.evaluate(x_vec, TableBackedMeasurementList(eval_table))
        for (table_name, dev_idx, dev_name, metric, se_code), pos, raw_pu in zip(
            eval_items, eval_table.device_pos.tolist(), z_pu.tolist()
        ):
            if pos < 0 or not math.isfinite(raw_pu):
                evaluated_eng[(table_name, dev_idx, metric)] = None
            else:
                scale = converter.scale_for(table_name, dev_name, se_code)
                evaluated_eng[(table_name, dev_idx, metric)] = float(raw_pu) * scale

    # 按设备表组装 <metric>_meas 与 <metric>_se，并对内核跳过评估的电流指标按物理公式补算
    device_tables: dict[str, list[dict[str, Any]]] = {}
    for table_name, metric_map in SE_DEVICE_RESULT_METRICS.items():
        model_rows = snapshot.get(table_name) or ()
        if not model_rows:
            continue
        rows_out: list[dict[str, Any]] = []
        for dev_row in model_rows:
            dev_idx = _int(dev_row.get("idx"))
            dev_name = str(dev_row.get("name", dev_idx))
            is_running = _int(dev_row.get("run_stat", 1), 1) != 0 and _int(dev_row.get("status", 1), 1) != 0
            record: dict[str, Any] = {"idx": dev_idx, "name": dev_name}
            for metric in metric_map:
                meas_entry = device_meas.get((table_name, dev_idx, metric))
                record[f"{metric}_meas"] = meas_entry.get("meas_value") if meas_entry else None
                se_val = evaluated_eng.get((table_name, dev_idx, metric))
                if not is_running and se_val is None:
                    se_val = 0.0
                record[f"{metric}_se"] = se_val

            # 补算内核跳过评估的三相交流/直流电流 SE 估计值（如 ACGenerator.ia / ACLoad.ia / DCBreak.i 等）
            if table_name in {"ACGenerator", "ACLoad"}:
                if (record.get("ia_se") is None or abs(record["ia_se"]) <= 1e-12) and is_running:
                    derived = converter.ac_current_from_pqv(record.get("p_se"), record.get("q_se"), record.get("uab_se"))
                    if derived is not None:
                        record["ia_se"] = derived
            elif table_name in {"ACBranch", "ACZeroBranch"}:
                for side in ("i", "j"):
                    key = f"{side}_ia_se"
                    if (record.get(key) is None or abs(record[key]) <= 1e-12) and is_running:
                        derived = converter.ac_current_from_pqv(
                            record.get(f"{side}_p_se"), record.get(f"{side}_q_se"), record.get(f"{side}_uab_se")
                        )
                        if derived is not None:
                            record[key] = derived
            elif table_name == "DCACConverter":
                if (record.get("ac_ia_se") is None or abs(record["ac_ia_se"]) <= 1e-12) and is_running:
                    derived = converter.ac_current_from_pqv(record.get("ac_p_se"), record.get("ac_q_se"), record.get("ac_uab_se"))
                    if derived is not None:
                        record["ac_ia_se"] = derived
                if (record.get("dc_i_se") is None or abs(record["dc_i_se"]) <= 1e-12) and is_running:
                    derived = converter.dc_current_from_pv(record.get("dc_p_se"), record.get("dc_u_se"))
                    if derived is not None:
                        record["dc_i_se"] = derived
            elif table_name in {"DCGenerator", "DCLoad"}:
                if (record.get("i_se") is None or abs(record["i_se"]) <= 1e-12) and is_running:
                    derived = converter.dc_current_from_pv(record.get("p_se"), record.get("u_se"))
                    if derived is not None:
                        record["i_se"] = derived
            elif table_name in {"DCBranch", "DCDCConverter"}:
                for side in ("i", "j"):
                    key = f"{side}_i_se"
                    if (record.get(key) is None or abs(record[key]) <= 1e-12) and is_running:
                        derived = converter.dc_current_from_pv(record.get(f"{side}_p_se"), record.get(f"{side}_u_se"))
                        if derived is not None:
                            record[key] = derived
            rows_out.append(record)
        device_tables[table_name] = rows_out
    return device_tables


def _enrich_se_result(
    result: dict[str, Any],
    estimator: Any,
    snapshot: dict[str, list[dict[str, Any]]],
    measurement_metadata: dict[str, Any],
    model_metadata: dict[str, Any],
    para_used: dict[str, Any],
) -> dict[str, Any]:
    """将 SE 结果反算至工程单位，还原设备/量测元数据并组装全网设备表与统计信息。"""
    from model.meas_model import DEVICE_TYPE_CODES

    converter = _ModelUnitConverter(snapshot)
    name_arrays = estimator._measurement_name_arrays_by_type_code() if hasattr(estimator, "_measurement_name_arrays_by_type_code") else {}
    lookup: dict[int, dict[str, Any]] = measurement_metadata.get("_measurement_lookup") or {}
    device_meas: dict[tuple[str, int, str], dict[str, Any]] = measurement_metadata.get("device_meas") or {}

    # 建立设备名 -> idx 反查表
    dev_idx_by_name = {
        table_name: {str(row.get("name", row.get("idx", ""))): _int(row.get("idx")) for row in rows}
        for table_name, rows in snapshot.items()
    }
    # 若是非宽表来源，从实测 lookup 补齐 device_meas
    if not device_meas and lookup:
        for entry in lookup.values():
            d_type = entry["model_table"]
            d_idx = entry.get("model_idx")
            if d_idx is None:
                d_idx = dev_idx_by_name.get(d_type, {}).get(entry["device_name"])
            metric = entry.get("metric")
            if not metric:
                for m_name, se_code in SE_DEVICE_RESULT_METRICS.get(d_type, {}).items():
                    if se_code == entry["se_type"]:
                        metric = m_name
                        break
            if d_idx is not None and metric:
                device_meas[(d_type, int(d_idx), metric)] = {
                    "meas_value": entry["value"],
                    "unit": entry["unit"],
                    "valid": 1,
                }

    enriched_rows: list[dict[str, Any]] = []
    bad_rows: list[dict[str, Any]] = []
    real_meas_count = 0
    valid_real_count = 0
    good_real_count = 0
    total_residual_abs = 0.0
    max_residual_eng = 0.0

    for row in result.get("measurements") or ():
        item = dict(row)
        idx = _int(item.get("idx"))
        meta = lookup.get(idx)
        source = str(item.get("source") or "")
        is_user_pseudo = bool(meta.get("is_user_pseudo")) if meta is not None else False
        is_pseudo = source == "pseudo" or is_user_pseudo
        is_rule_prefilter = bool(meta.get("rule_prefiltered") if meta is not None else False)
        is_policy_suppress = bool(meta.get("policy_suppressed") if meta is not None else False)
        is_prefiltered = source == "prefiltered" or is_policy_suppress or is_rule_prefilter
        is_bad = source == "bad_data"

        if meta is not None:
            dev_type = meta["model_table"]
            dev_idx = meta.get("model_idx")
            if dev_idx is None:
                dev_idx = dev_idx_by_name.get(dev_type, {}).get(meta["device_name"])
            dev_name = meta["device_name"]
            metric = meta.get("metric") or ""
            meas_name = meta["meas_name"]
            mtype = meta["se_type"]
            unit = meta["unit"]
            orig_eng_value = meta["value"]
            scale = converter.scale_for(dev_type, dev_name, mtype)
        else:
            dev_type = str(item.get("device_type") or "")
            dev_name = _resolve_pos_device_name(dev_type, str(item.get("device_name") or ""), name_arrays, DEVICE_TYPE_CODES)
            dev_idx = dev_idx_by_name.get(dev_type, {}).get(dev_name)
            mtype = str(item.get("meas_type") or "")
            metric = ""
            for m_name, code in SE_DEVICE_RESULT_METRICS.get(dev_type, {}).items():
                if code == mtype:
                    metric = m_name
                    break
            meas_name = str(item.get("name") or f"m{idx}")
            unit = converter.unit_for(mtype)
            scale = converter.scale_for(dev_type, dev_name, mtype)
            orig_eng_value = None

        raw_pu_val = item.get("value")
        est_pu_val = item.get("estimated_value")
        if orig_eng_value is not None:
            meas_val_eng = float(orig_eng_value)
        elif isinstance(raw_pu_val, (int, float)) and math.isfinite(raw_pu_val):
            meas_val_eng = float(raw_pu_val) * scale
        else:
            meas_val_eng = None

        if isinstance(est_pu_val, (int, float)) and math.isfinite(est_pu_val):
            se_val_eng = float(est_pu_val) * scale
        else:
            se_val_eng = None

        if meas_val_eng is not None and se_val_eng is not None:
            residual_eng = meas_val_eng - se_val_eng
        elif isinstance(item.get("residual"), (int, float)) and math.isfinite(item["residual"]):
            residual_eng = float(item["residual"]) * scale
        else:
            residual_eng = None

        norm_res = item.get("normalized_residual")
        norm_res_val = float(norm_res) if isinstance(norm_res, (int, float)) and math.isfinite(norm_res) else None
        is_valid = bool(item.get("valid", True)) and not is_prefiltered
        effective_source = "pseudo" if is_user_pseudo else ("prefiltered" if is_prefiltered and not is_bad else source)
        is_good = (effective_source == "normal") and is_valid and not is_bad
        reason_text = str(item.get("reason") or ("bad_data" if is_bad else ""))
        prefilter_origin = ""
        if is_rule_prefilter:
            prefilter_origin = "rule"
            reason_text = str(meta.get("prefilter_reason") or "rule_prefiltered")
        elif is_policy_suppress:
            prefilter_origin = "policy"
            if not reason_text:
                reason_text = f"policy_suppressed:{meta.get('policy_reason') or 'manual'}"
        elif is_prefiltered:
            prefilter_origin = "kernel"
        elif is_user_pseudo and not reason_text:
            reason_text = str(meta.get("pseudo_note") or "user_defined_pseudo")

        enriched = {
            **item,
            "idx": idx,
            "name": meas_name,
            "device_type": dev_type,
            "device_idx": dev_idx,
            "device_name": dev_name,
            "metric": metric,
            "meas_type": mtype,
            "unit": unit,
            "value": meas_val_eng,
            "min_value": meta.get("prefilter_min_value") if is_rule_prefilter and meta is not None else item.get("min_value"),
            "max_value": meta.get("prefilter_max_value") if is_rule_prefilter and meta is not None else item.get("max_value"),
            "estimated_value": se_val_eng,
            "residual": residual_eng,
            "normalized_residual": norm_res_val,
            "valid": is_valid,
            "is_bad": int(is_bad),
            "is_good": int(is_good),
            "is_pseudo": int(is_pseudo),
            "pseudo_origin": "user_defined" if is_user_pseudo else ("kernel_auto" if is_pseudo else ""),
            "pseudo_define_id": meta.get("pseudo_define_id") if is_user_pseudo and meta is not None else None,
            "prefilter_origin": prefilter_origin,
            "prefilter_rule_id": meta.get("prefilter_rule_id") if is_rule_prefilter and meta is not None else None,
            "source": effective_source,
            "reason": reason_text,
        }
        enriched_rows.append(enriched)

        if not is_pseudo:
            real_meas_count += 1
            if not is_prefiltered:
                valid_real_count += 1
                if is_good:
                    good_real_count += 1
                if residual_eng is not None:
                    abs_res = abs(residual_eng)
                    total_residual_abs += abs_res
                    if abs_res > max_residual_eng:
                        max_residual_eng = abs_res
        if is_bad:
            bad_rows.append(enriched)

    device_tables = _evaluate_all_device_se_values(estimator, snapshot, converter, device_meas)

    # 1) 对正常量测，将最终收敛状态下的内核估计值回填至设备表（O(1) 哈希索引）；
    # 2) 对坏数据，使用最终收敛状态 x 评估出的干净 se 值更新其 se_value / residual，避免展示被坏数据污染的中间值
    dev_rec_lookup: dict[tuple[str, int], dict[str, Any]] = {}
    dev_se_lookup: dict[tuple[str, int, str], float | None] = {}
    for dev_type, rows_for_dev in device_tables.items():
        metrics_for_type = SE_DEVICE_RESULT_METRICS.get(dev_type, ())
        for dev_rec in rows_for_dev:
            d_idx = int(dev_rec["idx"])
            dev_rec_lookup[(dev_type, d_idx)] = dev_rec
            for metric in metrics_for_type:
                dev_se_lookup[(dev_type, d_idx, metric)] = dev_rec.get(f"{metric}_se")

    for item in enriched_rows:
        if not item.get("metric") or item.get("device_idx") is None:
            continue
        d_type = str(item["device_type"])
        d_idx = int(item["device_idx"])
        dev_rec = dev_rec_lookup.get((d_type, d_idx))
        if item["source"] == "normal":
            if dev_rec is not None:
                if item["value"] is not None:
                    dev_rec[f"{item['metric']}_meas"] = item["value"]
                if item["estimated_value"] is not None:
                    dev_rec[f"{item['metric']}_se"] = item["estimated_value"]
        elif item["source"] == "bad_data":
            final_se = dev_se_lookup.get((d_type, d_idx, item["metric"]))
            if final_se is not None:
                item["estimated_value"] = final_se
                if item["value"] is not None:
                    item["residual"] = item["value"] - final_se
            if dev_rec is not None and item["value"] is not None:
                dev_rec[f"{item['metric']}_meas"] = item["value"]

    suspect_statuses = detect_suspect_statuses(
        snapshot,
        device_tables,
        device_meas,
        measurement_metadata.get("topology_overrides"),
    )
    missing_measurements = list(measurement_metadata.get("missing_measurements") or ())
    pseudo_total_count = sum(1 for item in enriched_rows if item.get("is_pseudo"))
    user_pseudo_count = sum(1 for item in enriched_rows if item.get("pseudo_origin") == "user_defined")

    stats = dict(result.get("statistics") or {})
    pass_rate = (good_real_count / valid_real_count) if valid_real_count > 0 else 0.0
    se_statistics = {
        "meas_count": real_meas_count or _int(stats.get("measurement_count")),
        "valid_meas_count": valid_real_count,
        "good_meas_count": good_real_count,
        "pass_rate": pass_rate,
        "total_residual": total_residual_abs,
        "residual_inf": max_residual_eng if valid_real_count > 0 else _number(stats.get("residual_inf")),
        "objective": _number(stats.get("objective")),
        "bad_data_count": len(bad_rows),
        "prefiltered_count": sum(1 for item in enriched_rows if item.get("source") == "prefiltered")
        or _int(stats.get("prefiltered_measurement_count")),
        "pseudo_count": pseudo_total_count or _int(stats.get("pseudo_measurement_count")),
        "converged": bool(result.get("converged")),
        "observable": bool(result.get("observable")),
        "iterations": _int(stats.get("iterations", result.get("iterations", 0))),
        "max_correction": _number(stats.get("max_correction", result.get("max_correction", 0.0))),
        "model_source": str(model_metadata.get("source") or ""),
        "meas_source": str(measurement_metadata.get("source") or ""),
    }

    clean_meas_meta = {
        key: value
        for key, value in measurement_metadata.items()
        if key not in {"topology_overrides", "device_meas", "measurement_lookup", "_measurement_lookup", "missing_measurements"}
    }
    result["measurements"] = enriched_rows
    result["bad_data"] = bad_rows
    result["device_tables"] = device_tables
    result["suspect_statuses"] = suspect_statuses
    result["missing_measurements"] = missing_measurements
    result["se_statistics"] = se_statistics
    result["se_parameters"] = para_used
    result["summary"].update(
        model_input=model_metadata,
        measurement_input=clean_meas_meta,
        se_statistics=se_statistics,
        device_table_counts={name: len(rows) for name, rows in device_tables.items()},
        user_pseudo_count=user_pseudo_count,
        policy_suppressed_count=int(measurement_metadata.get("policy_suppressed_count", 0)),
        pseudo_stat_applied=int(measurement_metadata.get("pseudo_stat_applied", 0)),
        suspect_status_count=len(suspect_statuses),
        missing_measurement_count=len(missing_measurements),
    )
    return result


def run_se(
    config: Any,
    kernel_root: str | Path | None = None,
    *,
    scada_snapshot: bool = False,
    se_params: dict[str, Any] | None = None,
    bad_policies: list[dict[str, Any]] | None = None,
    prefilter_rules: list[dict[str, Any]] | None = None,
    weight_rules: list[dict[str, Any]] | None = None,
    pseudo_meas_defines: list[dict[str, Any]] | None = None,
    pseudo_stat_defines: list[dict[str, Any]] | None = None,
    stage_logger: Any = None,
) -> dict[str, Any]:
    def _log_stage(stage: str, message: str, *, level: str = "INFO", elapsed_ms: float | None = None, detail: dict[str, Any] | None = None) -> None:
        if callable(stage_logger):
            try:
                stage_logger(stage=stage, level=level, message=message, elapsed_ms=elapsed_ms, detail=detail or {})
            except Exception:
                pass

    validate_task_inputs(config, scada_snapshot=scada_snapshot)
    configure_kernel_path(kernel_root or config.kernel_root)
    from secore.hybrid_se import HybridStateEstimator

    wide_mode = is_scdfe_d_wide_db(config.measurement_file)
    t_load = time.perf_counter()
    if wide_mode and Path(config.model_file).suffix.lower() in SQLITE_SUFFIXES:
        raw_model_tables = read_model_tables(Path(config.model_file))
        raw_snapshot = {name: block["rows"] for name, block in raw_model_tables.items()}
        with measurement_input(
            config,
            raw_snapshot,
            scada_snapshot=True,
            bad_policies=bad_policies,
            prefilter_rules=prefilter_rules,
            weight_rules=weight_rules,
            pseudo_meas_defines=pseudo_meas_defines,
            pseudo_stat_defines=pseudo_stat_defines,
        ) as (meas_file, measurement_metadata):
            _log_stage(
                "input_load",
                f"加载模型与 scdfe_d 快照：有效量测 {measurement_metadata.get('se_valid', 0)}，缺测/拒收 {len(measurement_metadata.get('missing_measurements') or ())}",
                elapsed_ms=(time.perf_counter() - t_load) * 1000.0,
                detail={
                    "se_valid": measurement_metadata.get("se_valid", 0),
                    "rejected": measurement_metadata.get("rejected", {}),
                    "missing_count": len(measurement_metadata.get("missing_measurements") or ()),
                },
            )
            if measurement_metadata.get("policy_suppressed_count") or measurement_metadata.get("user_pseudo_injected") or measurement_metadata.get("pseudo_stat_applied"):
                _log_stage(
                    "policy_apply",
                    f"应用在线策略：坏量测屏蔽 {measurement_metadata.get('policy_suppressed_count', 0)}，人工伪量测 {measurement_metadata.get('user_pseudo_injected', 0)}，伪状态 {measurement_metadata.get('pseudo_stat_applied', 0)}",
                    detail={
                        "policy_suppressed_count": measurement_metadata.get("policy_suppressed_count", 0),
                        "user_pseudo_injected": measurement_metadata.get("user_pseudo_injected", 0),
                        "pseudo_stat_applied": measurement_metadata.get("pseudo_stat_applied", 0),
                    },
                )
            topology_overrides = measurement_metadata.get("topology_overrides")
            with kernel_model(
                config.model_file,
                topology_overrides=topology_overrides,
                raw_tables=raw_model_tables,
            ) as model:
                validate_references(model.path, meas_file, measurements=True)
                patched_snapshot = (
                    {name: block["rows"] for name, block in model.tables.items()}
                    if model.tables is not None
                    else raw_snapshot
                )
                with se_parameter_file(config.parameter_file, params=se_params) as (para_path, para_used):
                    t_solve = time.perf_counter()
                    estimator = HybridStateEstimator(
                        e_file=model.path,
                        meas_file=meas_file,
                        parameter_file=para_path,
                        auto_prepare=False,
                    )
                    estimator.prepare()
                    se_result = estimator.run(result_mode="full", verbose=False, final_diagnostics=True)
                    solve_ms = (time.perf_counter() - t_solve) * 1000.0
                    result = normalize_se(se_result, estimator.estimate_result)
                    enriched = _enrich_se_result(
                        result, estimator, patched_snapshot, measurement_metadata, model.metadata, para_used
                    )
                    se_stats = enriched.get("se_statistics") or {}
                    _log_stage(
                        "solve",
                        f"SE 求解完成：收敛={enriched.get('converged')}，可观测={enriched.get('observable')}，迭代={se_stats.get('iterations', 0)}，合格率={se_stats.get('pass_rate', 0.0):.2%}",
                        level="INFO" if enriched.get("converged") else "WARN",
                        elapsed_ms=solve_ms,
                        detail=se_stats,
                    )
                    if se_stats.get("bad_data_count", 0) > 0 or enriched.get("suspect_statuses"):
                        _log_stage(
                            "bad_detect",
                            f"检出坏数据 {se_stats.get('bad_data_count', 0)} 条，可疑遥信 {len(enriched.get('suspect_statuses') or ())} 条",
                            level="WARN",
                            detail={
                                "bad_data_count": se_stats.get("bad_data_count", 0),
                                "suspect_status_count": len(enriched.get("suspect_statuses") or ()),
                            },
                        )
                    return enriched

    with kernel_model(config.model_file) as model:
        from efile_read import EBook
        snapshot = {name: block.data for name, block in EBook(model.path).data.items()}
        with measurement_input(
            config,
            snapshot,
            scada_snapshot=scada_snapshot,
            bad_policies=bad_policies,
            prefilter_rules=prefilter_rules,
            weight_rules=weight_rules,
            pseudo_meas_defines=pseudo_meas_defines,
            pseudo_stat_defines=pseudo_stat_defines,
        ) as (meas_file, measurement_metadata):
            if model.metadata["format"] == "rtdb_sqlite":
                validate_references(model.path, meas_file, measurements=True)
            with se_parameter_file(config.parameter_file, params=se_params) as (para_path, para_used):
                t_solve = time.perf_counter()
                estimator = HybridStateEstimator(
                    e_file=model.path,
                    meas_file=meas_file,
                    parameter_file=para_path,
                    auto_prepare=False,
                )
                estimator.prepare()
                se_result = estimator.run(result_mode="full", verbose=False, final_diagnostics=True)
                solve_ms = (time.perf_counter() - t_solve) * 1000.0
                result = normalize_se(se_result, estimator.estimate_result)
                enriched = _enrich_se_result(
                    result, estimator, snapshot, measurement_metadata, model.metadata, para_used
                )
                se_stats = enriched.get("se_statistics") or {}
                _log_stage(
                    "solve",
                    f"SE 求解完成：收敛={enriched.get('converged')}，迭代={se_stats.get('iterations', 0)}，合格率={se_stats.get('pass_rate', 0.0):.2%}",
                    level="INFO" if enriched.get("converged") else "WARN",
                    elapsed_ms=solve_ms,
                    detail=se_stats,
                )
                return enriched


def _enrich_lf_result(
    calc: Any,
    result: dict[str, Any],
    snapshot: dict[str, list[dict[str, Any]]],
    lf_params: dict[str, Any],
    se_snap: dict[str, Any] | None,
    *,
    source_se_run_id: int | None = None,
    mode: str = "online",
    override_count: int = 0,
) -> dict[str, Any]:
    """将 LF 内核标幺值结果反算至工程单位，提取全网节点/支路/电源负荷表并计算网损、负载率与 SE 偏差。"""
    converter = _ModelUnitConverter(snapshot)
    v_min_pu = _number(lf_params.get("v_min_pu"), 0.93)
    v_max_pu = _number(lf_params.get("v_max_pu"), 1.07)
    ol_limit = _number(lf_params.get("overload_limit_pct"), 100.0)

    # SE 断面基准反查（用于计算 LF - SE 偏差）
    se_dev_map: dict[tuple[str, int], dict[str, Any]] = {}
    if se_snap:
        for dt, rlist in (se_snap.get("devices_by_type") or {}).items():
            for r in rlist:
                if r.get("idx") is not None:
                    se_dev_map[(dt, int(r["idx"]))] = r

    # 模型元数据反查（额定容量、控制方式、端节点）
    model_by_idx: dict[tuple[str, int], dict[str, Any]] = {}
    model_by_name: dict[tuple[str, str], dict[str, Any]] = {}
    for tname, rows in snapshot.items():
        for r in rows or ():
            if r.get("idx") is not None:
                model_by_idx[(tname, int(r["idx"]))] = r
            if r.get("name"):
                model_by_name[(tname, str(r["name"]))] = r

    lf_res = getattr(calc, "lf_result", None)
    network = getattr(lf_res, "network", None) or getattr(calc, "network", None)

    # 1. 提取交直流节点电压（ACNode / DCNode）
    lf_buses: list[dict[str, Any]] = []
    min_v_pu: float | None = None
    max_v_pu: float | None = None
    min_v_bus = ""
    max_v_bus = ""
    v_violation_count = 0

    for domain, attr, tbl_name, v_se_col in (
        ("AC", "ac", "ACNode", "uab_se"),
        ("DC", "dc", "DCNode", "u_se"),
    ):
        part = getattr(network, attr, None) if network is not None else None
        net_nodes = list(getattr(part, "nodes", ()) or ()) if part is not None else []
        node_by_idx: dict[int, Any] = {}
        for nobj in net_nodes:
            nidx = getattr(nobj, "idx", None)
            if nidx is not None:
                node_by_idx[int(nidx)] = nobj
        for mrow in snapshot.get(tbl_name) or ():
            if mrow.get("idx") is None:
                continue
            idx = int(mrow["idx"])
            name = str(mrow.get("name", f"{tbl_name}#{idx}"))
            vbase = _number(mrow.get("vbase"), 1.0)
            nobj = node_by_idx.get(idx)
            v_pu_raw = _json_value(getattr(nobj, "voltage", None)) if nobj is not None else None
            ang_raw = _json_value(getattr(nobj, "angle", None)) if (nobj is not None and domain == "AC") else None
            v_pu = float(v_pu_raw) if isinstance(v_pu_raw, (int, float)) and math.isfinite(v_pu_raw) else None
            v_eng = (v_pu * vbase) if v_pu is not None else None
            ang_deg = (math.degrees(float(ang_raw))) if isinstance(ang_raw, (int, float)) and math.isfinite(ang_raw) else None
            se_rec = se_dev_map.get((tbl_name, idx))
            v_se = _json_value(se_rec.get(v_se_col)) if se_rec else None
            v_diff = (v_eng - float(v_se)) if (v_eng is not None and isinstance(v_se, (int, float))) else None
            v_status = "normal"
            if v_pu is not None and v_pu > 1e-4:
                if v_pu < v_min_pu:
                    v_status = "low"
                    v_violation_count += 1
                elif v_pu > v_max_pu:
                    v_status = "high"
                    v_violation_count += 1
                if min_v_pu is None or v_pu < min_v_pu:
                    min_v_pu = v_pu
                    min_v_bus = name
                if max_v_pu is None or v_pu > max_v_pu:
                    max_v_pu = v_pu
                    max_v_bus = name
            lf_buses.append(
                {
                    "domain": domain,
                    "device_type": tbl_name,
                    "device_idx": idx,
                    "device_name": name,
                    "vbase": vbase,
                    "v_pu": v_pu,
                    "v_eng": v_eng,
                    "angle_deg": ang_deg,
                    "v_se": v_se,
                    "v_diff": v_diff,
                    "v_status": v_status,
                }
            )

    bus_v_eng = {(b["device_type"], b["device_idx"]): b["v_eng"] for b in lf_buses if b["v_eng"] is not None}

    # 2. 将 normalize_lf 提取的设备按工程单位拆分到 lf_branches / lf_units
    type_map = {
        ("ac", "branch"): "ACBranch",
        ("ac", "zero_branch"): "ACZeroBranch",
        ("ac", "transformer"): "ACTransformer",
        ("ac", "break"): "ACBreak",
        ("ac", "switch"): "ACSwitch",
        ("ac", "generator"): "ACGenerator",
        ("ac", "load"): "ACLoad",
        ("dc", "branch"): "DCBranch",
        ("dc", "break"): "DCBreak",
        ("dc", "switch"): "DCSwitch",
        ("dc", "dcdc_converter"): "DCDCConverter",
        ("dc", "generator"): "DCGenerator",
        ("dc", "load"): "DCLoad",
        ("dcac", "dcac_converter"): "DCACConverter",
    }

    def _safe_mul(val: Any, scale: float) -> float | None:
        if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
            return float(val) * scale
        return None

    def _i_scale(tbl: str, dname: str, side_code: str) -> float:
        return converter.scale_for(tbl, dname, side_code)

    lf_branches: list[dict[str, Any]] = []
    lf_units: list[dict[str, Any]] = []
    ac_gen_p = ac_gen_q = ac_load_p = ac_load_q = 0.0
    dc_gen_p = dc_load_p = 0.0
    ac_loss_p = dc_loss_p = 0.0
    max_loading_pct = 0.0
    max_loading_dev = ""
    overload_count = 0

    for row in result.get("devices") or ():
        dom_low = str(row.get("domain") or "").lower()
        dtype_low = str(row.get("device_type") or "").lower()
        tbl = type_map.get((dom_low, dtype_low))
        if not tbl:
            continue
        dkey = str(row.get("device_key") or "")
        mrow = model_by_name.get((tbl, dkey))
        if mrow is None and row.get("idx") is not None:
            mrow = model_by_idx.get((tbl, int(row["idx"])))
        didx = int(mrow["idx"]) if (mrow and mrow.get("idx") is not None) else (_int(row.get("idx")) if row.get("idx") is not None else None)
        dname = str(mrow["name"]) if (mrow and mrow.get("name")) else dkey
        rated_cap = _number(mrow.get("rated_capacity"), 0.0) if mrow else 0.0
        se_rec = se_dev_map.get((tbl, didx)) if didx is not None else None

        if tbl in {"ACGenerator", "DCGenerator", "ACLoad", "DCLoad"}:
            dom = "AC" if tbl.startswith("AC") else "DC"
            n_tbl = "ACNode" if dom == "AC" else "DCNode"
            n_idx = int(mrow["node"]) if (mrow and mrow.get("node") is not None) else (int(row["node_from"]) if row.get("node_from") is not None else None)
            p_lf = _safe_mul(row.get("p_from"), converter.p_base)
            q_lf = _safe_mul(row.get("q_from"), converter.p_base) if dom == "AC" else None
            v_lf = bus_v_eng.get((n_tbl, n_idx)) if n_idx is not None else _safe_mul(row.get("voltage_from"), converter.scale_for(tbl, dname, "V_GEN"))
            i_code = "I_GEN" if "Generator" in tbl else "I_LOAD"
            i_lf = _safe_mul(row.get("current_from"), _i_scale(tbl, dname, i_code))
            if i_lf is None and p_lf is not None and v_lf and v_lf > 1e-6:
                s_val = math.hypot(p_lf, q_lf or 0.0) if dom == "AC" else abs(p_lf)
                i_lf = (s_val * 1000.0 / (math.sqrt(3.0) * v_lf)) if (dom == "AC" and converter.p_unit == "kW" and converter.u_unit == "V") else (s_val / v_lf)
            p_se = _json_value(se_rec.get("p_se")) if se_rec else None
            p_diff = (p_lf - float(p_se)) if (p_lf is not None and isinstance(p_se, (int, float))) else None
            # 负荷不计入热稳定过载统计；发电机按有功出力率计算供明细表展示，不混入支路/换流器最大负载率
            is_gen = "Generator" in tbl
            loading = (abs(p_lf or 0.0) / rated_cap * 100.0) if (is_gen and rated_cap > 1e-6) else None
            is_ol = int(is_gen and loading is not None and loading > ol_limit)
            if tbl == "ACGenerator" and p_lf is not None:
                ac_gen_p += p_lf
                if q_lf is not None:
                    ac_gen_q += q_lf
            elif tbl == "ACLoad" and p_lf is not None:
                ac_load_p += p_lf
                if q_lf is not None:
                    ac_load_q += q_lf
            elif tbl == "DCGenerator" and p_lf is not None:
                dc_gen_p += p_lf
            elif tbl == "DCLoad" and p_lf is not None:
                dc_load_p += p_lf
            lf_units.append(
                {
                    "domain": dom,
                    "device_type": tbl,
                    "device_idx": didx,
                    "device_name": dname,
                    "node_idx": n_idx,
                    "control_type": str((mrow or {}).get("control_type") or ""),
                    "p_lf": p_lf,
                    "q_lf": q_lf,
                    "v_lf": v_lf,
                    "i_lf": i_lf,
                    "p_se": p_se,
                    "p_diff": p_diff,
                    "rated_capacity": rated_cap if rated_cap > 0 else None,
                    "loading_pct": loading,
                    "overload": is_ol,
                }
            )
            continue

        # 支路 / 换流器 / 断路器
        dom = "DCAC" if tbl == "DCACConverter" else ("DC" if tbl.startswith("DC") else "AC")
        if tbl == "DCACConverter":
            # 内核 DCACConverter: i 侧为 DC，j 侧为 AC（核对实库：i_v=1.0(DC), j_q!=None(AC)）
            n_from = int(mrow["dc_node"]) if (mrow and mrow.get("dc_node") is not None) else None
            n_to = int(mrow["ac_node"]) if (mrow and mrow.get("ac_node") is not None) else None
            p_from = _safe_mul(row.get("p_from"), converter.p_base)
            q_from = None
            p_to = _safe_mul(row.get("p_to"), converter.p_base)
            q_to = _safe_mul(row.get("q_to"), converter.p_base)
            v_from = bus_v_eng.get(("DCNode", n_from)) if n_from is not None else _safe_mul(row.get("voltage_from"), converter.scale_for(tbl, dname, "V_DC"))
            v_to = bus_v_eng.get(("ACNode", n_to)) if n_to is not None else _safe_mul(row.get("voltage_to"), converter.scale_for(tbl, dname, "V_AC"))
            i_from = _safe_mul(row.get("current_from"), _i_scale(tbl, dname, "I_DC"))
            i_to = _safe_mul(row.get("current_to"), _i_scale(tbl, dname, "I_AC"))
            p_se = _json_value(se_rec.get("ac_p_se")) if se_rec else None
            p_ref_for_diff = p_to
        else:
            n_tbl = "DCNode" if dom == "DC" else "ACNode"
            n_from = int(mrow["i_node"]) if (mrow and mrow.get("i_node") is not None) else (int(row["node_from"]) if row.get("node_from") is not None else None)
            n_to = int(mrow["j_node"]) if (mrow and mrow.get("j_node") is not None) else (int(row["node_to"]) if row.get("node_to") is not None else None)
            p_from = _safe_mul(row.get("p_from"), converter.p_base)
            q_from = _safe_mul(row.get("q_from"), converter.p_base) if dom == "AC" else None
            p_to = _safe_mul(row.get("p_to"), converter.p_base)
            q_to = _safe_mul(row.get("q_to"), converter.p_base) if dom == "AC" else None
            v_from = bus_v_eng.get((n_tbl, n_from)) if n_from is not None else _safe_mul(row.get("voltage_from"), converter.scale_for(tbl, dname, "V_FROM"))
            v_to = bus_v_eng.get((n_tbl, n_to)) if n_to is not None else _safe_mul(row.get("voltage_to"), converter.scale_for(tbl, dname, "V_TO"))
            i_from = _safe_mul(row.get("current_from"), _i_scale(tbl, dname, "I_FROM"))
            i_to = _safe_mul(row.get("current_to"), _i_scale(tbl, dname, "I_TO"))
            if dom == "DC":
                if i_from is None and p_from is not None and v_from and v_from > 1e-6:
                    i_from = (p_from * 1000.0 / v_from) if (converter.p_unit == "kW" and converter.u_unit == "V") else (p_from / v_from)
                if i_to is None and p_to is not None and v_to and v_to > 1e-6:
                    i_to = (p_to * 1000.0 / v_to) if (converter.p_unit == "kW" and converter.u_unit == "V") else (p_to / v_to)
            p_se = _json_value(se_rec.get("i_p_se")) if se_rec else None
            p_ref_for_diff = p_from

        p_loss = (p_from + p_to) if (p_from is not None and p_to is not None) else None
        if p_loss is not None and tbl in {"ACBranch", "ACZeroBranch", "ACTransformer"}:
            ac_loss_p += max(0.0, p_loss)
        elif p_loss is not None and tbl in {"DCBranch", "DCDCConverter", "DCACConverter"}:
            dc_loss_p += max(0.0, p_loss)

        s_from = math.hypot(p_from or 0.0, q_from or 0.0) if (dom != "DC") else abs(p_from or 0.0)
        s_to = math.hypot(p_to or 0.0, q_to or 0.0) if (dom != "DC") else abs(p_to or 0.0)
        s_max = max(s_from, s_to)
        i_max_limit = _number((mrow or {}).get("i_max"), 0.0)
        i_mag = max(abs(i_from or 0.0), abs(i_to or 0.0))
        loading: float | None = None
        if rated_cap > 1e-6 and s_max >= 0:
            loading = s_max / rated_cap * 100.0
        elif i_max_limit > 1e-6:
            loading = i_mag / i_max_limit * 100.0
        is_ol = int(loading is not None and loading > ol_limit)
        if is_ol:
            overload_count += 1
        if loading is not None and loading > max_loading_pct:
            max_loading_pct = loading
            max_loading_dev = dname
        p_diff = (p_ref_for_diff - float(p_se)) if (p_ref_for_diff is not None and isinstance(p_se, (int, float))) else None

        lf_branches.append(
            {
                "domain": dom,
                "device_type": tbl,
                "device_idx": didx,
                "device_name": dname,
                "node_from": n_from,
                "node_to": n_to,
                "p_from": p_from,
                "q_from": q_from,
                "i_from": i_from,
                "v_from": v_from,
                "p_to": p_to,
                "q_to": q_to,
                "i_to": i_to,
                "v_to": v_to,
                "p_loss": p_loss,
                "rated_capacity": rated_cap if rated_cap > 0 else None,
                "loading_pct": loading,
                "overload": is_ol,
                "p_se": p_se,
                "p_diff": p_diff,
            }
        )

    total_gen_p = ac_gen_p + dc_gen_p
    total_load_p = ac_load_p + dc_load_p
    total_loss_p = ac_loss_p + dc_loss_p
    loss_rate = (total_loss_p / total_gen_p * 100.0) if total_gen_p > 1e-6 else 0.0

    result["lf_buses"] = lf_buses
    result["lf_branches"] = lf_branches
    result["lf_units"] = lf_units
    result["lf_statistics"] = {
        "source_se_run_id": source_se_run_id,
        "mode": mode,
        "converged": int(bool(result.get("converged"))),
        "iterations": int(result.get("iterations", 0)),
        "norm_f": float(result.get("norm_f", 0.0)),
        "ac_converged": result.get("ac_converged"),
        "ac_iterations": result.get("ac_iterations"),
        "ac_norm_f": result.get("ac_norm_f"),
        "dc_converged": result.get("dc_converged"),
        "dc_iterations": result.get("dc_iterations"),
        "dc_norm_f": result.get("dc_norm_f"),
        "ac_gen_p": round(ac_gen_p, 4),
        "ac_gen_q": round(ac_gen_q, 4),
        "ac_load_p": round(ac_load_p, 4),
        "ac_load_q": round(ac_load_q, 4),
        "ac_loss_p": round(ac_loss_p, 4),
        "dc_gen_p": round(dc_gen_p, 4),
        "dc_load_p": round(dc_load_p, 4),
        "dc_loss_p": round(dc_loss_p, 4),
        "total_gen_p": round(total_gen_p, 4),
        "total_load_p": round(total_load_p, 4),
        "total_loss_p": round(total_loss_p, 4),
        "loss_rate": round(loss_rate, 3),
        "min_v_pu": round(min_v_pu, 5) if min_v_pu is not None else None,
        "max_v_pu": round(max_v_pu, 5) if max_v_pu is not None else None,
        "min_v_bus": min_v_bus,
        "max_v_bus": max_v_bus,
        "max_loading_pct": round(max_loading_pct, 2),
        "max_loading_dev": max_loading_dev,
        "v_violation_count": v_violation_count,
        "overload_count": overload_count,
        "device_count": len(lf_buses) + len(lf_branches) + len(lf_units),
        "override_count": override_count,
        "u_unit": converter.u_unit,
        "p_unit": converter.p_unit,
        "i_unit": converter.i_unit,
        "failure_reason": str(result.get("failure_reason", "") or ""),
    }
    return result


def run_lf(
    config: Any,
    kernel_root: str | Path | None = None,
    *,
    use_model_cache: bool = True,
    lf_params: dict[str, Any] | None = None,
    se_snap: dict[str, Any] | None = None,
    breaker_status: dict[tuple[str, int], int] | None = None,
    pseudo_stats: list[dict[str, Any]] | None = None,
    study_overrides: list[dict[str, Any]] | None = None,
    mode: str = "online",
    stage_logger: Any = None,
) -> dict[str, Any]:
    """执行交直流潮流计算（支持消费最新收敛 SE 断面与方式调整，输出工程单位全网结果）。"""
    def _log(stage: str, msg: str, *, level: str = "INFO", elapsed_ms: float | None = None, detail: dict[str, Any] | None = None) -> None:
        if callable(stage_logger):
            try:
                stage_logger(stage=stage, level=level, message=msg, elapsed_ms=elapsed_ms, detail=detail or {})
            except Exception:
                pass

    validate_task_inputs(config)
    configure_kernel_path(kernel_root or config.kernel_root)
    from lfcore.hybrid_lf import HybridPowerFlowCalc, _read_lf_network_from_file

    eff_params = {**DEFAULT_LF_PARAMS, **(lf_params or {})}
    use_se_base = bool(int(eff_params.get("use_se_base", 1)))
    raw_tables: dict[str, dict[str, Any]] | None = None
    merged_overrides: dict[str, dict[int, dict[str, Any]]] | None = None
    se_meta: dict[str, Any] = {"used_se_base": False, "source_se_run_id": None}
    override_count = 0

    t0 = time.perf_counter()
    if Path(config.model_file).suffix.lower() in SQLITE_SUFFIXES:
        raw_tables = read_model_tables(Path(config.model_file))
        base_overrides: dict[str, dict[int, dict[str, Any]]] = {}
        if use_se_base and se_snap is not None:
            base_overrides, se_meta = build_se_base_overrides(
                se_snap,
                raw_tables,
                breaker_status=breaker_status,
                pseudo_stats=pseudo_stats,
            )
            if se_meta["used_se_base"]:
                _log(
                    "se_import",
                    f"注入 SE #{se_meta['source_se_run_id']} 在线基态：设备 {se_meta['applied_devices']} 台，开关 {se_meta['applied_breakers']} 处",
                    elapsed_ms=(time.perf_counter() - t0) * 1000.0,
                    detail=se_meta,
                )
        merged_overrides, override_count = merge_study_overrides(base_overrides, study_overrides, raw_tables)
        if override_count:
            _log(
                "override_apply",
                f"叠加方式调整 {override_count} 项",
                detail={"override_count": override_count},
            )

    started = time.perf_counter()
    with kernel_model(config.model_file, topology_overrides=merged_overrides, raw_tables=raw_tables) as model:
        if use_model_cache and model.metadata["format"] != "rtdb_sqlite" and not merged_overrides:
            network, cache_hit = lf_models.load(model.path, _read_lf_network_from_file)
        else:
            network, cache_hit = _read_lf_network_from_file(model.path), False
        read_seconds = time.perf_counter() - started
        started = time.perf_counter()
        with lf_parameter_file(config.parameter_file, params=eff_params) as (para_path, _para_used):
            calc = HybridPowerFlowCalc(network, parameter_file=para_path, result_mode="full", verbose=False)
            calc.run()
        solve_seconds = time.perf_counter() - started
        started = time.perf_counter()
        result = normalize_lf(calc)
        if model.tables is not None:
            snapshot = {name: block["rows"] for name, block in model.tables.items()}
        else:
            from efile_read import EBook
            snapshot = {name: block.data for name, block in EBook(model.path).data.items()}
        result = _enrich_lf_result(
            calc,
            result,
            snapshot,
            eff_params,
            se_snap,
            source_se_run_id=se_meta.get("source_se_run_id"),
            mode="study" if (mode == "study" or override_count > 0) else "online",
            override_count=override_count,
        )
        result["summary"]["model_input"] = model.metadata
        result["summary"]["se_input"] = se_meta
        result["performance"] = {
            "model_read_seconds": read_seconds,
            "solve_seconds": solve_seconds,
            "normalization_seconds": time.perf_counter() - started,
            "model_cache_hit": int(cache_hit),
        }
        st = result["lf_statistics"]
        _log(
            "solve",
            f"LF 求解完成：收敛={result['converged']}，迭代={st['iterations']}，总发电={st['total_gen_p']:.2f} {st['p_unit']}，网损率={st['loss_rate']:.2f}%",
            level="INFO" if result["converged"] else "WARN",
            elapsed_ms=solve_seconds * 1000.0,
            detail=st,
        )
        return result


def _build_legacy_ca_risks(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """将结构化 ca_risk_detail 转换为兼容旧 ca_risk 表的行格式。"""
    cat_label = {
        "voltage_low": "电压越下限",
        "voltage_high": "电压越上限",
        "overload": "设备过载",
        "heavy_load": "重载预警",
        "load_loss": "负荷损失",
        "divergence": "潮流发散",
    }
    out: list[dict[str, Any]] = []
    for r in details:
        out.append(
            {
                "contingency": r.get("category", "N-0"),
                "risk_source": r.get("contingency_name", "N-0 基态"),
                "risk_dist": f"{r.get('device_type', '')}.{r.get('device_name', '')}.{r.get('metric', '')}".strip("."),
                "risk_type": cat_label.get(str(r.get("risk_category") or ""), str(r.get("risk_category") or "越限")),
                "risk_value": r.get("actual_value"),
                "risk_info": r.get("detail", ""),
            }
        )
    return out


def _solve_single_ca_case(
    model_file: Path,
    raw_tables: dict[str, dict[str, Any]] | None,
    overrides: dict[str, dict[int, dict[str, Any]]] | None,
    lf_para_path: Path,
    eff_lf_params: dict[str, Any],
    se_snap: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str | None, float]:
    """在内存模型上求解单次基态或预想故障潮流，绝不修改只读源模型。"""
    from lfcore.hybrid_lf import HybridPowerFlowCalc, _read_lf_network_from_file

    t0 = time.perf_counter()
    try:
        with kernel_model(model_file, topology_overrides=overrides, raw_tables=raw_tables) as model:
            network = _read_lf_network_from_file(model.path)
            calc = HybridPowerFlowCalc(network, parameter_file=lf_para_path, result_mode="full", verbose=False)
            calc.run()
            res = normalize_lf(calc)
            if not res.get("converged"):
                return None, str(res.get("failure_reason") or "hybrid_power_flow_not_converged"), (time.perf_counter() - t0) * 1000.0
            if model.tables is not None:
                snapshot = {name: block["rows"] for name, block in model.tables.items()}
            else:
                from efile_read import EBook
                snapshot = {name: block.data for name, block in EBook(model.path).data.items()}
            enriched = _enrich_lf_result(calc, res, snapshot, eff_lf_params, se_snap)
            return enriched, None, (time.perf_counter() - t0) * 1000.0
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}", (time.perf_counter() - t0) * 1000.0


def run_ca(
    config: Any,
    kernel_root: str | Path | None = None,
    *,
    ca_params: dict[str, Any] | None = None,
    lf_snap: dict[str, Any] | None = None,
    se_snap: dict[str, Any] | None = None,
    breaker_status: dict[tuple[str, int], int] | None = None,
    pseudo_stats: list[dict[str, Any]] | None = None,
    study_overrides: list[dict[str, Any]] | None = None,
    lf_params: dict[str, Any] | None = None,
    lf_para_file: str | Path | None = None,
    contingencies: list[dict[str, Any]] | None = None,
    device_limits: dict[tuple[str, str, str], dict[str, Any]] | None = None,
    weather_state: dict[str, Any] | None = None,
    stage_logger: Any = None,
) -> dict[str, Any]:
    """执行在线静态安全分析（LF → CA 基态贯通 + 真实 N-0/N-1/N-k/气象扰动潮流扫描）。"""
    # 兼容旧的纯文件/无参单测调用路径
    online_mode = any(
        x is not None
        for x in (ca_params, lf_snap, se_snap, contingencies, device_limits, weather_state, stage_logger)
    )
    if not online_mode:
        validate_task_inputs(config)
        configure_kernel_path(kernel_root or config.kernel_root)
        from cacore.hybrid_ca import run_hybrid_ca
        with kernel_model(config.model_file) as model, tempfile.TemporaryDirectory(prefix="pas_ca_") as temp:
            root = Path(temp)
            scan_count, limit_metadata = None, {"source": str(config.limit_file)}
            if config.limit_file.suffix.lower() in SQLITE_SUFFIXES:
                from efile_read import EBook
                snapshot = {name: block.data for name, block in EBook(model.path).data.items()}
                constraints, limit_metadata = read_limits(config, snapshot)
                n0, n1, scan_count = _ca_with_constraints(model.path, constraints, config.scan_n1, root)
            else:
                if model.metadata["format"] == "rtdb_sqlite":
                    validate_references(model.path, config.limit_file)
                n0, n1 = run_hybrid_ca(model.path, config.limit_file, root / "n0.e", root / "n1.e", root / "info.e", scan_n1=config.scan_n1)
        result = normalize_ca(n0, n1, scan_count)[0]
        result["summary"]["limit_input"] = limit_metadata
        result["summary"]["model_input"] = model.metadata
        return result

    def _log(stage: str, msg: str, *, level: str = "INFO", elapsed_ms: float | None = None, detail: dict[str, Any] | None = None) -> None:
        if callable(stage_logger):
            try:
                stage_logger(stage=stage, level=level, message=msg, elapsed_ms=elapsed_ms, detail=detail or {})
            except Exception:
                pass

    validate_task_inputs(config)
    configure_kernel_path(kernel_root or config.kernel_root)
    t_total = time.perf_counter()

    eff_ca = {**DEFAULT_CA_PARAMS, **(ca_params or {})}
    eff_lf = {**DEFAULT_LF_PARAMS, **(lf_params or {})}
    use_lf_base = bool(int(eff_ca.get("use_lf_base", 1)))
    scan_n1 = bool(int(eff_ca.get("scan_n1", 1)))
    scan_nk = bool(int(eff_ca.get("scan_nk", 1)))
    scan_weather = bool(int(eff_ca.get("scan_weather", 1)))
    max_scan = max(1, int(eff_ca.get("max_scan_count", 40)))
    load_loss_thr = float(eff_ca.get("load_loss_threshold_kw", 0.5))

    model_path = Path(config.model_file)
    raw_tables: dict[str, dict[str, Any]] | None = None
    base_overrides: dict[str, dict[int, dict[str, Any]]] = {}
    if model_path.suffix.lower() in SQLITE_SUFFIXES:
        raw_tables = read_model_tables(model_path)
        if se_snap is not None:
            se_ovr, _ = build_se_base_overrides(
                se_snap,
                raw_tables,
                breaker_status=breaker_status,
                pseudo_stats=pseudo_stats,
            )
            base_overrides, _ = merge_study_overrides(se_ovr, study_overrides, raw_tables)
        elif study_overrides:
            base_overrides, _ = merge_study_overrides({}, study_overrides, raw_tables)

    source_lf_run_id: int | None = None
    source_se_run_id: int | None = None
    base_converged = True
    base_failure = ""
    base_buses: list[dict[str, Any]] = []
    base_branches: list[dict[str, Any]] = []
    base_load_kw = 0.0
    u_unit, p_unit, i_unit = "V", "kW", "A"

    t_base = time.perf_counter()
    lf_latest = (lf_snap or {}).get("latest") if use_lf_base else None
    if lf_latest and int(lf_latest.get("converged") or 0) == 1 and (lf_snap.get("buses") or lf_snap.get("branches")):
        source_lf_run_id = int(lf_latest["run_id"])
        source_se_run_id = int(lf_latest["source_se_run_id"]) if lf_latest.get("source_se_run_id") is not None else None
        base_buses = list(lf_snap.get("buses") or [])
        base_branches = list(lf_snap.get("branches") or [])
        base_load_kw = float(lf_latest.get("total_load_p") or 0.0)
        u_unit = str(lf_latest.get("u_unit") or "V")
        p_unit = str(lf_latest.get("p_unit") or "kW")
        i_unit = str(lf_latest.get("i_unit") or "A")
        _log(
            "lf_import",
            f"注入最新收敛 LF #{source_lf_run_id} 断面（溯源 SE #{source_se_run_id or '—'}）：母线 {len(base_buses)}，支路 {len(base_branches)}，总负荷 {base_load_kw:.2f} {p_unit}",
            elapsed_ms=(time.perf_counter() - t_base) * 1000.0,
            detail={"source_lf_run_id": source_lf_run_id, "source_se_run_id": source_se_run_id, "base_load_kw": base_load_kw},
        )
    else:
        with lf_parameter_file(lf_para_file, params=eff_lf) as (para_path, _):
            solved, err, ms = _solve_single_ca_case(model_path, raw_tables, base_overrides or None, para_path, eff_lf, se_snap)
        if solved is None:
            base_converged = False
            base_failure = str(err or "base_lf_not_converged")
            _log("lf_import", f"基态潮流求解发散：{base_failure}", level="ERROR", elapsed_ms=ms)
        else:
            st = solved["lf_statistics"]
            base_buses = list(solved.get("lf_buses") or [])
            base_branches = list(solved.get("lf_branches") or [])
            base_load_kw = float(st.get("total_load_p") or 0.0)
            u_unit = str(st.get("u_unit") or "V")
            p_unit = str(st.get("p_unit") or "kW")
            i_unit = str(st.get("i_unit") or "A")
            _log(
                "lf_import",
                f"无可用 LF 历史断面，现场重算基态潮流收敛：总负荷 {base_load_kw:.2f} {p_unit}",
                elapsed_ms=ms,
            )

    all_risks: list[dict[str, Any]] = []
    contingency_results: list[dict[str, Any]] = []
    global_max_loading = 0.0
    global_max_loading_dev = ""
    global_min_v: float | None = None
    global_min_v_bus = ""
    global_max_v: float | None = None
    global_max_v_bus = ""
    max_load_loss_kw = 0.0
    worst_contingency = ""
    worst_rank = (-1, -1, 0.0)

    # 1. N-0 基态越限校核
    t_n0 = time.perf_counter()
    if not base_converged:
        all_risks.append(
            {
                "contingency_name": "N-0 基态",
                "category": "N-0",
                "device_type": "System",
                "device_idx": None,
                "device_name": "全网基态",
                "risk_category": "divergence",
                "severity": "critical",
                "metric": "converged",
                "actual_value": 0.0,
                "limit_value": 1.0,
                "violation_pct": 100.0,
                "unit": "",
                "detail": f"基态潮流未收敛：{base_failure}",
            }
        )
        n0_risk_count = 1
    else:
        n0_risks, n0_meta = evaluate_lf_state_risks(
            contingency_name="N-0 基态",
            category="N-0",
            buses=base_buses,
            branches=base_branches,
            params=eff_ca,
            device_limits=device_limits,
            u_unit=u_unit,
        )
        all_risks.extend(n0_risks)
        n0_risk_count = len(n0_risks)
        global_max_loading = float(n0_meta["max_loading_pct"] or 0.0)
        global_max_loading_dev = str(n0_meta["max_loading_dev"] or "")
        global_min_v = n0_meta["min_v_pu"]
        global_min_v_bus = str(n0_meta["min_v_bus"] or "")
        global_max_v = n0_meta["max_v_pu"]
        global_max_v_bus = str(n0_meta["max_v_bus"] or "")
        _log(
            "n0_check",
            f"N-0 基态校核完成：检出风险 {n0_risk_count} 项，最大负载率 {global_max_loading:.2f}%，最低电压 {global_min_v if global_min_v is not None else '—'} pu",
            elapsed_ms=(time.perf_counter() - t_n0) * 1000.0,
            detail={"n0_risk_count": n0_risk_count, **n0_meta},
        )

    # 2. N-1 / N-k / 气象与负荷预想扰动扫描
    n1_total = 0
    n1_converged = 0
    n1_diverged = 0
    n1_risk_count = 0
    nk_total = 0
    nk_risk_count = 0
    weather_total = 0
    weather_converged = 0
    weather_diverged = 0
    weather_risk_count = 0

    weather_snapshot = compute_weather_coupling_summary(weather_state, raw_tables)

    scan_queue: list[dict[str, Any]] = []
    if base_converged and contingencies:
        weather_defs: list[dict[str, Any]] = []
        device_defs: list[dict[str, Any]] = []
        for cdef in contingencies:
            if not int(cdef.get("enabled", 1)):
                continue
            cat = str(cdef.get("category") or "N-1")
            if cat == "Weather":
                if scan_weather:
                    weather_defs.append(cdef)
                continue
            if cat == "N-1" and not scan_n1:
                continue
            if cat == "N-k" and not scan_nk:
                continue
            device_defs.append(cdef)
        # 优先确保启用的气象/负荷扰动全部进入扫描队列，再以剩余配额填充设备 N-1/N-k 场景
        if len(weather_defs) >= max_scan:
            scan_queue = weather_defs[:max_scan]
        else:
            scan_queue = weather_defs + device_defs[: max_scan - len(weather_defs)]

    if scan_queue:
        t_scan = time.perf_counter()
        # 构造名称 -> idx 索引，确保按 name 定义的故障也能准确映射到内存模型行
        name_to_idx: dict[tuple[str, str], int] = {}
        if raw_tables:
            for dt, blk in raw_tables.items():
                for mrow in blk.get("rows") or ():
                    if mrow.get("idx") is not None and mrow.get("name"):
                        name_to_idx[(dt, str(mrow["name"]))] = int(mrow["idx"])

        with lf_parameter_file(lf_para_file, params=eff_lf) as (para_path, _):
            # 预先为每个故障/气象扰动场景构造隔离的内存覆盖字典
            scan_jobs: list[tuple[dict[str, Any], dict[str, dict[int, dict[str, Any]]], dict[str, Any]]] = []
            for cdef in scan_queue:
                cat = str(cdef.get("category") or "N-1")
                if cat == "Weather":
                    pert = cdef.get("perturbation")
                    if not isinstance(pert, dict) or not pert:
                        try:
                            pert = json.loads(cdef.get("perturbation_json") or "{}")
                        except (TypeError, ValueError):
                            pert = {}
                    w_ovr, w_meta = build_weather_perturbation_overrides(
                        pert,
                        weather_state,
                        raw_tables,
                        base_overrides,
                    )
                    scan_jobs.append((cdef, w_ovr, w_meta))
                    continue

                items = cdef.get("items") or []
                outage_ovr: dict[str, dict[int, dict[str, Any]]] = {
                    dt: {idx: dict(fields) for idx, fields in entries.items()}
                    for dt, entries in base_overrides.items()
                }
                for it in items:
                    dt = str(it.get("device_type") or "")
                    didx = it.get("device_idx")
                    if didx is None:
                        didx = name_to_idx.get((dt, str(it.get("device_name") or "")))
                    if didx is None:
                        continue
                    field = "status" if dt in ("ACBreak", "DCBreak") else "run_stat"
                    outage_ovr.setdefault(dt, {}).setdefault(int(didx), {})[field] = 0
                scan_jobs.append((cdef, outage_ovr, {"load_scale_applied": 1.0}))

            def _run_job(job: tuple[dict[str, Any], dict[str, dict[int, dict[str, Any]]], dict[str, Any]]):
                _, job_ovr, _ = job
                return _solve_single_ca_case(
                    model_path,
                    raw_tables,
                    job_ovr,
                    para_path,
                    eff_lf,
                    se_snap,
                )

            max_workers = max(1, min(6, (os.cpu_count() or 4), len(scan_jobs)))
            if max_workers > 1:
                with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ca-scan") as pool:
                    solved_list = list(pool.map(_run_job, scan_jobs))
            else:
                solved_list = [_run_job(job) for job in scan_jobs]

            for (cdef, _, job_meta), (solved, err, case_ms) in zip(scan_jobs, solved_list):
                cname = str(cdef.get("name") or "未命名故障")
                cat = str(cdef.get("category") or "N-1")
                items = cdef.get("items") or []
                target_desc = str(cdef.get("target_desc") or job_meta.get("desc") or "")
                if cat == "N-1":
                    n1_total += 1
                elif cat == "Weather":
                    weather_total += 1
                else:
                    nk_total += 1

                case_risks: list[dict[str, Any]] = []
                case_load_loss = 0.0
                case_max_load = 0.0
                case_max_load_dev = ""
                case_min_v: float | None = None
                case_min_v_bus = ""
                case_max_v: float | None = None
                case_max_v_bus = ""
                case_iters = 0
                case_conv = 1
                case_fail = ""

                if solved is None:
                    case_conv = 0
                    case_fail = str(err or "not_converged")
                    if cat == "N-1":
                        n1_diverged += 1
                    elif cat == "Weather":
                        weather_diverged += 1
                    first_it = items[0] if items else {}
                    div_detail = (
                        f"气象/负荷扰动「{target_desc or cname}」后潮流发散或系统失稳：{case_fail}"
                        if cat == "Weather"
                        else f"开断 {target_desc or cname} 后潮流发散或系统解列：{case_fail}"
                    )
                    case_risks.append(
                        {
                            "contingency_name": cname,
                            "category": cat,
                            "device_type": "Weather" if cat == "Weather" else str(first_it.get("device_type") or "System"),
                            "device_idx": None if cat == "Weather" else first_it.get("device_idx"),
                            "device_name": cname if cat == "Weather" else str(first_it.get("device_name") or cname),
                            "risk_category": "divergence",
                            "severity": "critical",
                            "metric": "converged",
                            "actual_value": 0.0,
                            "limit_value": 1.0,
                            "violation_pct": 100.0,
                            "unit": "",
                            "detail": div_detail,
                        }
                    )
                else:
                    if cat == "N-1":
                        n1_converged += 1
                    elif cat == "Weather":
                        weather_converged += 1
                    st = solved["lf_statistics"]
                    case_iters = int(st.get("iterations") or 0)
                    post_load = float(st.get("total_load_p") or 0.0)
                    expected_load = base_load_kw * float(job_meta.get("load_scale_applied") or 1.0)
                    case_load_loss = round(max(0.0, expected_load - post_load), 3)
                    c_risks, c_meta = evaluate_lf_state_risks(
                        contingency_name=cname,
                        category=cat,
                        buses=solved.get("lf_buses") or [],
                        branches=solved.get("lf_branches") or [],
                        params=eff_ca,
                        device_limits=device_limits,
                        u_unit=u_unit,
                    )
                    case_risks.extend(c_risks)
                    case_max_load = float(c_meta["max_loading_pct"] or 0.0)
                    case_max_load_dev = str(c_meta["max_loading_dev"] or "")
                    case_min_v = c_meta["min_v_pu"]
                    case_min_v_bus = str(c_meta["min_v_bus"] or "")
                    case_max_v = c_meta["max_v_pu"]
                    case_max_v_bus = str(c_meta["max_v_bus"] or "")

                    if case_load_loss > load_loss_thr:
                        loss_pct = (case_load_loss / max(expected_load, 1e-6)) * 100.0
                        l_sev = "critical" if loss_pct >= 20.0 else ("high" if loss_pct >= 5.0 else "medium")
                        first_it = items[0] if items else {}
                        case_risks.append(
                            {
                                "contingency_name": cname,
                                "category": cat,
                                "device_type": "Weather" if cat == "Weather" else str(first_it.get("device_type") or "System"),
                                "device_idx": None if cat == "Weather" else first_it.get("device_idx"),
                                "device_name": cname if cat == "Weather" else str(first_it.get("device_name") or cname),
                                "risk_category": "load_loss",
                                "severity": l_sev,
                                "metric": "load_loss",
                                "actual_value": round(case_load_loss, 2),
                                "limit_value": round(load_loss_thr, 2),
                                "violation_pct": round(loss_pct, 2),
                                "unit": p_unit,
                                "detail": f"扰动后损失负荷 {case_load_loss:.2f} {p_unit}（占目标负荷 {loss_pct:.1f}%）",
                            }
                        )

                    if case_max_load > global_max_loading:
                        global_max_loading = case_max_load
                        global_max_loading_dev = case_max_load_dev
                    if case_min_v is not None and (global_min_v is None or case_min_v < global_min_v):
                        global_min_v = case_min_v
                        global_min_v_bus = case_min_v_bus
                    if case_max_v is not None and (global_max_v is None or case_max_v > global_max_v):
                        global_max_v = case_max_v
                        global_max_v_bus = case_max_v_bus
                    if case_load_loss > max_load_loss_kw:
                        max_load_loss_kw = case_load_loss

                # 确定本次故障最高严重等级
                case_sev = "normal"
                for cr in case_risks:
                    if SEVERITY_RANK.get(cr["severity"], 0) > SEVERITY_RANK.get(case_sev, 0):
                        case_sev = cr["severity"]
                if cat == "N-1":
                    n1_risk_count += len(case_risks)
                elif cat == "Weather":
                    weather_risk_count += len(case_risks)
                else:
                    nk_risk_count += len(case_risks)
                all_risks.extend(case_risks)

                rank_tuple = (SEVERITY_RANK.get(case_sev, 0), len(case_risks), case_load_loss + case_max_load)
                if case_risks and rank_tuple > worst_rank:
                    worst_rank = rank_tuple
                    worst_contingency = cname

                contingency_results.append(
                    {
                        "contingency_name": cname,
                        "category": cat,
                        "target_desc": target_desc,
                        "converged": case_conv,
                        "iterations": case_iters,
                        "elapsed_ms": round(case_ms, 2),
                        "load_loss_kw": round(case_load_loss, 3),
                        "max_loading_pct": round(case_max_load, 2),
                        "max_loading_dev": case_max_load_dev,
                        "min_v_pu": case_min_v,
                        "min_v_bus": case_min_v_bus,
                        "max_v_pu": case_max_v,
                        "max_v_bus": case_max_v_bus,
                        "risk_count": len(case_risks),
                        "severity": case_sev,
                        "failure_reason": case_fail[:300],
                    }
                )

        _log(
            "n1_scan",
            f"预想扰动扫描完成：N-1 {n1_total} 项（收敛 {n1_converged}/发散 {n1_diverged}，风险 {n1_risk_count}），气象 {weather_total} 项（收敛 {weather_converged}/发散 {weather_diverged}，风险 {weather_risk_count}），N-k {nk_total} 项（风险 {nk_risk_count}）",
            level="WARN" if (n1_diverged > 0 or weather_diverged > 0 or n1_risk_count > 0 or weather_risk_count > 0 or nk_risk_count > 0) else "INFO",
            elapsed_ms=(time.perf_counter() - t_scan) * 1000.0,
            detail={
                "n1_total": n1_total,
                "n1_converged": n1_converged,
                "n1_diverged": n1_diverged,
                "n1_risk_count": n1_risk_count,
                "weather_total": weather_total,
                "weather_converged": weather_converged,
                "weather_diverged": weather_diverged,
                "weather_risk_count": weather_risk_count,
                "nk_total": nk_total,
                "nk_risk_count": nk_risk_count,
            },
        )

    # 3. 汇总统计与电网五维健康评分定级
    crit_cnt = sum(1 for r in all_risks if r["severity"] == "critical")
    high_cnt = sum(1 for r in all_risks if r["severity"] == "high")
    med_cnt = sum(1 for r in all_risks if r["severity"] == "medium")
    low_cnt = sum(1 for r in all_risks if r["severity"] == "low")
    affected_devs = len({str(r.get("device_name") or "").strip() for r in all_risks if str(r.get("device_name") or "").strip()})
    total_devs = len(base_buses) + len(base_branches)
    n1_safe_cnt = sum(1 for c in contingency_results if c.get("category") == "N-1" and c.get("converged") and int(c.get("risk_count") or 0) == 0)
    n1_worsened_cnt = sum(
        1
        for c in contingency_results
        if c.get("category") == "N-1" and ((not c.get("converged")) or int(c.get("risk_count") or 0) > n0_risk_count or float(c.get("load_loss_kw") or 0.0) > load_loss_thr)
    )
    weather_worsened_cnt = sum(
        1
        for c in contingency_results
        if c.get("category") == "Weather" and ((not c.get("converged")) or int(c.get("risk_count") or 0) > n0_risk_count or float(c.get("load_loss_kw") or 0.0) > load_loss_thr)
    )
    health = compute_grid_health_assessment(
        base_converged=base_converged,
        n0_risk_count=n0_risk_count,
        n1_total_count=n1_total,
        n1_converged_count=n1_converged,
        n1_diverged_count=n1_diverged,
        n1_risk_count=n1_risk_count,
        nk_total_count=nk_total,
        nk_risk_count=nk_risk_count,
        weather_total_count=weather_total,
        weather_diverged_count=weather_diverged,
        weather_risk_count=weather_risk_count,
        critical_count=crit_cnt,
        high_count=high_cnt,
        medium_count=med_cnt,
        low_count=low_cnt,
        max_loading_pct=global_max_loading,
        min_v_pu=global_min_v,
        max_v_pu=global_max_v,
        max_load_loss_kw=max_load_loss_kw,
        base_load_kw=base_load_kw,
        v_min_pu=float(eff_ca.get("v_min_pu", 0.93)),
        v_max_pu=float(eff_ca.get("v_max_pu", 1.07)),
        overload_warn_pct=float(eff_ca.get("overload_warn_pct", 80.0)),
        overload_limit_pct=float(eff_ca.get("overload_limit_pct", 100.0)),
        affected_devices=affected_devs,
        total_devices=total_devs,
        n1_safe_count=n1_safe_cnt,
        n1_worsened_count=n1_worsened_cnt,
        weather_worsened_count=weather_worsened_cnt,
    )
    score = float(health["health_score"])
    level = str(health["risk_level"])
    health_grade = str(health["health_grade"])
    health_label = str(health["health_label"])
    if not worst_contingency and n0_risk_count > 0:
        worst_contingency = "N-0 基态"

    total_sec = time.perf_counter() - t_total
    ca_stats = {
        "source_lf_run_id": source_lf_run_id,
        "source_se_run_id": source_se_run_id,
        "base_converged": int(base_converged),
        "risk_level": level,
        "security_score": score,
        "health_grade": health_grade,
        "health_label": health_label,
        "health_dims": health["dimensions"],
        "health_summary": health["summary_text"],
        "affected_devices": affected_devs,
        "n0_risk_count": n0_risk_count,
        "n1_total_count": n1_total,
        "n1_converged_count": n1_converged,
        "n1_diverged_count": n1_diverged,
        "n1_risk_count": n1_risk_count,
        "nk_total_count": nk_total,
        "nk_risk_count": nk_risk_count,
        "weather_total_count": weather_total,
        "weather_risk_count": weather_risk_count,
        "weather_snapshot": weather_snapshot,
        "critical_count": crit_cnt,
        "high_count": high_cnt,
        "medium_count": med_cnt,
        "low_count": low_cnt,
        "max_loading_pct": round(global_max_loading, 2),
        "max_loading_dev": global_max_loading_dev,
        "min_v_pu": global_min_v,
        "min_v_bus": global_min_v_bus,
        "max_v_pu": global_max_v,
        "max_v_bus": global_max_v_bus,
        "max_load_loss_kw": round(max_load_loss_kw, 3),
        "worst_contingency": worst_contingency,
        "u_unit": u_unit,
        "p_unit": p_unit,
        "i_unit": i_unit,
        "failure_reason": base_failure,
    }
    legacy_risks = _build_legacy_ca_risks(all_risks)
    return {
        "risk_level": level,
        "n0_risk_count": n0_risk_count,
        "n1_scan_count": n1_total + nk_total + weather_total,
        "n1_risk_count": n1_risk_count + nk_risk_count + weather_risk_count,
        "risks": legacy_risks,
        "ca_statistics": ca_stats,
        "ca_health": health,
        "ca_contingencies": contingency_results,
        "ca_risk_details": all_risks,
        "summary": {
            "risk_level": level,
            "security_score": score,
            "health_grade": health_grade,
            "health_label": health_label,
            "health_dims": health["dimensions"],
            "source_lf_run_id": source_lf_run_id,
            "source_se_run_id": source_se_run_id,
            "n0_risk_count": n0_risk_count,
            "n1_scan_count": n1_total + nk_total + weather_total,
            "n1_risk_count": n1_risk_count + nk_risk_count + weather_risk_count,
            "weather_total_count": weather_total,
            "weather_risk_count": weather_risk_count,
        },
        "performance": {"solve_seconds": total_sec},
    }


def _ca_with_constraints(model, constraints, scan_n1, directory):
    """Use native CA checks with sparse DB bounds (no invented zero bounds)."""
    from cacore.hybrid_ca import (_run_case, collect_limit_risks, _active_load_power,
                                 _contingency_rows, _write_outage_case, CARisk)
    base,error = _run_case(model)
    if error is not None or base is None or not base.converged:
        return [CARisk('BASE','HybridPowerFlow','潮流发散',1,str(error or 'hybrid_power_flow_not_converged'))],[],0
    n0,n1,count = collect_limit_risks(base,constraints,'BASE'),[],0
    base_load = _active_load_power(base)
    if scan_n1:
        for table,source_table,name in _contingency_rows(model):
            count += 1
            source = f'N-1:{source_table}.{name}'
            # Names are display values, never filesystem paths.
            outage = directory/f'outage_{count}.e'
            _write_outage_case(model,outage,table,name)
            result,error = _run_case(outage)
            if error is not None or result is None or not result.converged:
                n1.append(CARisk(source,'HybridPowerFlow','潮流发散',1,str(error or 'hybrid_power_flow_not_converged')))
                continue
            n1.extend(collect_limit_risks(result,constraints,source))
            loss=max(0.,base_load-_active_load_power(result))
            if loss>1e-6: n1.append(CARisk(source,'Load','负荷损失',loss,f'loss={loss};base_load={base_load}'))
    return n0,n1,count
