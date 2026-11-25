"""Adapters around the reference SE, LF, and CA calculation kernels."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
import time
import warnings
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
from .se_bad import detect_suspect_statuses
from .se_params import se_parameter_file


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


def run_lf(config: Any, kernel_root: str | Path | None = None, *, use_model_cache: bool = True) -> dict[str, Any]:
    validate_task_inputs(config)
    configure_kernel_path(kernel_root or config.kernel_root)
    from lfcore.hybrid_lf import HybridPowerFlowCalc, _read_lf_network_from_file
    started = time.perf_counter()
    with kernel_model(config.model_file) as model:
        if use_model_cache and model.metadata["format"] != "rtdb_sqlite":
            network, cache_hit = lf_models.load(model.path, _read_lf_network_from_file)
        else:
            network, cache_hit = _read_lf_network_from_file(model.path), False
        read_seconds = time.perf_counter() - started
        started = time.perf_counter()
        calc = HybridPowerFlowCalc(network, parameter_file=config.parameter_file, result_mode="full", verbose=False)
        calc.run()
        solve_seconds = time.perf_counter() - started
        started = time.perf_counter()
        result = normalize_lf(calc)
        result["summary"]["model_input"] = model.metadata
        result["performance"] = {"model_read_seconds": read_seconds, "solve_seconds": solve_seconds,
                                 "normalization_seconds": time.perf_counter() - started, "model_cache_hit": int(cache_hit)}
        return result


def run_ca(config: Any, kernel_root: str | Path | None = None) -> dict[str, Any]:
    validate_task_inputs(config)
    configure_kernel_path(kernel_root or config.kernel_root)
    from cacore.hybrid_ca import run_hybrid_ca
    with kernel_model(config.model_file) as model, tempfile.TemporaryDirectory(prefix="pas_ca_") as temp:
        root = Path(temp)
        scan_count, limit_metadata = None, {'source':str(config.limit_file)}
        if config.limit_file.suffix.lower() in SQLITE_SUFFIXES:
            from efile_read import EBook
            snapshot = {name:block.data for name,block in EBook(model.path).data.items()}
            constraints, limit_metadata = read_limits(config, snapshot)
            n0,n1,scan_count = _ca_with_constraints(model.path,constraints,config.scan_n1,root)
        else:
            if model.metadata["format"] == "rtdb_sqlite":
                validate_references(model.path, config.limit_file)
            n0,n1 = run_hybrid_ca(model.path,config.limit_file,root/'n0.e',root/'n1.e',root/'info.e',scan_n1=config.scan_n1)
    result = normalize_ca(n0, n1, scan_count)[0]
    result["summary"]["limit_input"] = limit_metadata
    result["summary"]["model_input"] = model.metadata
    return result


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
