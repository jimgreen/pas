"""Adapters around the reference SE, LF, and CA calculation kernels."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any


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
    return {"converged": bool(getattr(calc, "converged", False)), "iterations": _int(getattr(calc, "iterations", 0)), "norm_f": _number(getattr(calc, "normF", 0.0)), "failure_reason": str(getattr(calc, "failure_reason", "") or ""), "ac_converged": getattr(getattr(result, "ac_calc", None), "converged", None), "ac_iterations": getattr(getattr(result, "ac_calc", None), "iterations", None), "ac_norm_f": getattr(getattr(result, "ac_calc", None), "normF", None), "dc_converged": getattr(getattr(result, "dc_calc", None), "converged", None), "dc_iterations": getattr(getattr(result, "dc_calc", None), "iterations", None), "dc_norm_f": getattr(getattr(result, "dc_calc", None), "normF", None), "summary": _json_value(getattr(result, "arrays", {}) if result is not None else {}), "devices": []}


def _risk_row(risk: Any, contingency: str) -> dict[str, Any]:
    return {"contingency": contingency, "risk_source": str(getattr(risk, "risk_source", "")), "risk_dist": str(getattr(risk, "risk_dist", "")), "risk_type": str(getattr(risk, "risk_type", "")), "risk_value": _json_value(getattr(risk, "risk_value", None)), "risk_info": str(getattr(risk, "risk_info", ""))}


def normalize_ca(n0_risks: list[Any], n1_risks: list[Any], n1_scan_count: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    n0 = [_risk_row(row, "N-0") for row in n0_risks]
    n1 = [_risk_row(row, "N-1") for row in n1_risks]
    combined = n0 + n1
    level = "高" if any(row["risk_type"] in {"潮流发散", "负荷损失"} for row in combined) else ("中" if combined else "无")
    return ({"risk_level": level, "n0_risk_count": len(n0), "n1_scan_count": _int(n1_scan_count, 0), "n1_risk_count": len(n1), "risks": combined, "summary": {"n0": n0, "n1": n1}}, {"n0": n0, "n1": n1})


def run_se(config: Any, kernel_root: str | Path | None = None) -> dict[str, Any]:
    configure_kernel_path(kernel_root or config.kernel_root)
    from secore.ac_se import ACStateEstimator
    estimator = ACStateEstimator(e_file=config.model_file, meas_file=config.measurement_file, parameter_file=config.parameter_file, auto_prepare=False)
    estimator.prepare()
    se_result = estimator.run(result_mode="full", verbose=False, final_diagnostics=True)
    return normalize_se(se_result, estimator.estimate_result)


def run_lf(config: Any, kernel_root: str | Path | None = None) -> dict[str, Any]:
    configure_kernel_path(kernel_root or config.kernel_root)
    from lfcore.hybrid_lf import HybridPowerFlowCalc, _read_lf_network_from_file
    network = _read_lf_network_from_file(config.model_file)
    calc = HybridPowerFlowCalc(network, parameter_file=config.parameter_file, result_mode="summary", verbose=False)
    calc.run()
    return normalize_lf(calc)


def run_ca(config: Any, kernel_root: str | Path | None = None) -> dict[str, Any]:
    configure_kernel_path(kernel_root or config.kernel_root)
    from cacore.hybrid_ca import run_hybrid_ca
    with tempfile.TemporaryDirectory(prefix="pas_ca_") as temp:
        root = Path(temp)
        n0, n1 = run_hybrid_ca(config.model_file, config.limit_file, root / "n0.e", root / "n1.e", root / "info.e", scan_n1=config.scan_n1)
    return normalize_ca(n0, n1, None)[0]
