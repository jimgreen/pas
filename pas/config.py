"""Configuration loading and validation for the online analysis service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TASK_NAMES = ("se", "lf", "ca")
_KERNEL_MARKERS = ("secore/ac_se.py", "lfcore/hybrid_lf.py", "cacore/hybrid_ca.py")


class ConfigError(ValueError):
    """Raised when the service configuration is invalid."""


@dataclass(frozen=True)
class TaskConfig:
    name: str
    enabled: bool = False
    period_seconds: float = 60.0
    model_file: Path | None = None
    measurement_file: Path | None = None
    parameter_file: Path | None = None
    limit_file: Path | None = None
    scan_n1: bool = True


@dataclass(frozen=True)
class AppConfig:
    source: Path
    kernel_root: Path
    database: Path
    tick_seconds: float
    retry_seconds: float
    tasks: dict[str, TaskConfig]


def _path(value: Any, base: Path) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    result = Path(str(value)).expanduser()
    if not result.is_absolute():
        result = base / result
    return result.resolve()


def _kernel_layout(root: Path) -> bool:
    """Return whether *root* contains the reference kernel packages."""
    nested = root / "src" / "hybrid_power_system_analysis"
    package = nested if nested.is_dir() else root
    return all((package / marker).is_file() for marker in _KERNEL_MARKERS)


def _kernel_score(root: Path) -> int:
    if not _kernel_layout(root):
        return -1
    package = root / "src" / "hybrid_power_system_analysis"
    if not package.is_dir():
        package = root
    score = len(_KERNEL_MARKERS)
    for relative in (
        "data/model/ac/ieee14.e",
        "data/meas/ac/ieee14.meas",
        "data/se/se.para",
        "data/model/hybrid/qinling.e",
        "data/lf/lf.para",
        "data/ca/qinling.calmt",
    ):
        if (root / relative).is_file():
            score += 1
    return score


def _discover_kernel_root(configured: Path) -> Path:
    """Resolve a migrated kernel root while preserving explicit valid roots."""
    if _kernel_layout(configured):
        return configured
    candidates: list[Path] = []
    env_root = os.environ.get("PAS_KERNEL_ROOT")
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.extend(
        [
            configured.parent,
            Path("D:/codex"),
            Path("C:/Users/wangbin/Documents/ChatGPT/核心计算"),
        ]
    )
    expanded: list[Path] = []
    for parent in candidates:
        parent = parent.resolve()
        expanded.append(parent)
        try:
            expanded.extend(item for item in parent.iterdir() if item.is_dir())
        except OSError:
            continue
    valid = []
    seen = set()
    for candidate in expanded:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        score = _kernel_score(candidate)
        if score >= 0:
            valid.append((score, candidate))
    if valid:
        valid.sort(key=lambda item: (-item[0], str(item[1])))
        return valid[0][1]
    return configured


def _relocated_path(value: Any, base: Path, old_root: Path, new_root: Path) -> Path | None:
    """Resolve an input path and remap stale absolute paths below old_root."""
    if value is None or str(value).strip() == "":
        return None
    original = Path(str(value)).expanduser()
    candidate = _path(value, base)
    if candidate is not None and candidate.is_file():
        return candidate
    relative = None
    if original.is_absolute():
        try:
            relative = original.resolve().relative_to(old_root)
        except ValueError:
            relative = None
    else:
        relative = original
    if relative is not None:
        relocated = (new_root / relative).resolve()
        if relocated.is_file():
            return relocated
    return candidate


def _positive(value: Any, field: str, default: float) -> float:
    try:
        number = float(default if value is None else value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field} must be a positive number") from exc
    if number <= 0:
        raise ConfigError(f"{field} must be a positive number")
    return number


def load_config(path: str | Path) -> AppConfig:
    source = Path(path).expanduser().resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON configuration: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be an object")
    base = source.parent
    configured_kernel_root = _path(raw.get("kernel_root"), base)
    kernel_root = _discover_kernel_root(configured_kernel_root) if configured_kernel_root is not None else None
    if kernel_root is None:
        raise ConfigError("kernel_root is required")
    database = _path(raw.get("database", "runs.db"), base)
    assert database is not None
    database.parent.mkdir(parents=True, exist_ok=True)
    scheduler = raw.get("scheduler") or {}
    tick_seconds = _positive(scheduler.get("tick_seconds"), "scheduler.tick_seconds", 1.0)
    retry_seconds = _positive(scheduler.get("retry_seconds"), "scheduler.retry_seconds", 60.0)
    raw_tasks = raw.get("tasks") or {}
    if not isinstance(raw_tasks, dict):
        raise ConfigError("tasks must be an object")
    tasks: dict[str, TaskConfig] = {}
    for name in TASK_NAMES:
        values = raw_tasks.get(name) or {}
        if not isinstance(values, dict):
            raise ConfigError(f"tasks.{name} must be an object")
        enabled = bool(values.get("enabled", False))
        task = TaskConfig(
            name=name,
            enabled=enabled,
            period_seconds=_positive(values.get("period_seconds"), f"tasks.{name}.period_seconds", 60.0),
            model_file=_relocated_path(values.get("model_file"), base, configured_kernel_root or kernel_root, kernel_root),
            measurement_file=_relocated_path(values.get("measurement_file"), base, configured_kernel_root or kernel_root, kernel_root),
            parameter_file=_relocated_path(values.get("parameter_file"), base, configured_kernel_root or kernel_root, kernel_root),
            limit_file=_relocated_path(values.get("limit_file"), base, configured_kernel_root or kernel_root, kernel_root),
            scan_n1=bool(values.get("scan_n1", True)),
        )
        if enabled:
            required = {"se": ("model_file", task.model_file, "measurement_file", task.measurement_file, "parameter_file", task.parameter_file),
                        "lf": ("model_file", task.model_file, "parameter_file", task.parameter_file),
                        "ca": ("model_file", task.model_file, "limit_file", task.limit_file)}[name]
            for field, candidate in zip(required[::2], required[1::2]):
                if candidate is None:
                    raise ConfigError(f"tasks.{name}.{field} is required")
                if not candidate.is_file():
                    raise ConfigError(f"tasks.{name}.{field} does not exist: {candidate}")
        tasks[name] = task
    return AppConfig(source, kernel_root, database, tick_seconds, retry_seconds, tasks)
