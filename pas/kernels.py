"""Adapters around the reference SE, LF, and CA calculation kernels."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from .model_cache import lf_models
from .model_input import kernel_model, validate_references
from .config import validate_task_inputs
from .input_store import measurement_input, read_limits, SQLITE_SUFFIXES


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
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
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


def run_se(config: Any, kernel_root: str | Path | None = None) -> dict[str, Any]:
    validate_task_inputs(config)
    configure_kernel_path(kernel_root or config.kernel_root)
    from secore.hybrid_se import HybridStateEstimator
    with kernel_model(config.model_file) as model:
        from efile_read import EBook
        snapshot = {name:block.data for name,block in EBook(model.path).data.items()}
        with measurement_input(config, snapshot) as (meas_file, measurement_metadata):
            if model.metadata["format"] == "rtdb_sqlite":
                validate_references(model.path, meas_file, measurements=True)
            estimator = HybridStateEstimator(e_file=model.path, meas_file=meas_file, parameter_file=config.parameter_file, auto_prepare=False)
            estimator.prepare()
            se_result = estimator.run(result_mode="full", verbose=False, final_diagnostics=True)
            result = normalize_se(se_result, estimator.estimate_result)
            result["summary"].update(model_input=model.metadata,measurement_input=measurement_metadata)
            return result


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
