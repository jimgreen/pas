"""Configuration loading and validation for the online analysis service."""

from __future__ import annotations

import json
import math
import os
import re
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
    databases: dict[str, Path]
    tick_seconds: float
    retry_seconds: float
    tasks: dict[str, TaskConfig]
    workspace_root: Path | None = None
    runtime: str | None = None
    scenario: str | None = None
    workspace_directory: Path | None = None


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
    if not math.isfinite(number) or number <= 0:
        raise ConfigError(f"{field} must be a positive number")
    return number


def add_workspace_arguments(parser: Any) -> None:
    parser.add_argument("--workspace-root", help="Workspace root directory")
    parser.add_argument("--runtime", help="Runtime directory, e.g. realtime")
    parser.add_argument("--scenario", help="Scenario directory, e.g. qinling")


def _component(value: Any, field: str) -> str:
    text = str(value or "")
    if (not re.fullmatch(r"[\w-]+", text) or
            text.upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}):
        raise ConfigError(f"{field} must be a single safe directory name")
    return text


def load_config(path: str | Path, *, workspace_root: str | Path | None = None,
                runtime: str | None = None, scenario: str | None = None) -> AppConfig:
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
    workspace_root = _path(workspace_root or raw.get("workspace_root"), base)
    runtime = runtime if runtime is not None else raw.get("runtime")
    scenario = scenario if scenario is not None else raw.get("scenario")
    workspace = None
    if workspace_root is not None or runtime is not None or scenario is not None:
        if workspace_root is None:
            raise ConfigError("workspace_root is required with runtime/scenario")
        runtime, scenario = _component(runtime, "runtime"), _component(scenario, "scenario")
        workspace = (workspace_root / runtime / scenario).resolve()
        if not workspace.is_relative_to(workspace_root):
            raise ConfigError("workspace directory must stay inside workspace_root")
    configured_kernel_root = _path(raw.get("kernel_root"), base)
    kernel_root = _discover_kernel_root(configured_kernel_root) if configured_kernel_root is not None else None
    if kernel_root is None:
        raise ConfigError("kernel_root is required")
    database = (workspace / "sqldb/pas/pas.sqlite3").resolve() if workspace else _path(raw.get("database", "runs.db"), base)
    assert database is not None
    raw_databases = raw.get("databases") or {}
    if not isinstance(raw_databases, dict):
        raise ConfigError("databases must be an object")
    databases: dict[str, Path] = {}
    for name in TASK_NAMES:
        configured = (workspace / f"sqldb/pas/{name}.sqlite3").resolve() if workspace else _path(raw_databases.get(name), base)
        if configured is None:
            suffix = database.suffix or ".db"
            configured = database.with_name(f"{database.stem}.{name}{suffix}")
        databases[name] = configured
    if len(set(databases.values())) != len(TASK_NAMES):
        raise ConfigError("databases.se, databases.lf, and databases.ca must be distinct")
    if database in databases.values():
        raise ConfigError("database (pas control database) must differ from result databases")
    if workspace and any(not target.is_relative_to(workspace) for target in [database, *databases.values()]):
        raise ConfigError("workspace database paths must stay inside workspace directory")
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
        def input_path(field: str) -> Path | None:
            if workspace is not None:
                if field == "model_file":
                    model = (workspace / "sqldb/model/devices.sqlite3").resolve()
                    if not model.is_relative_to(workspace):
                        raise ConfigError("model path must stay inside workspace directory")
                    return model
                defaults = {"measurement_file": "meas/measurements.meas", "parameter_file": f"config/{name}.para", "limit_file": "config/ca.calmt"}
                return _path(values.get(field, defaults[field]), workspace)
            return _relocated_path(values.get(field), base, configured_kernel_root or kernel_root, kernel_root)

        task = TaskConfig(
            name=name,
            enabled=enabled,
            period_seconds=_positive(values.get("period_seconds"), f"tasks.{name}.period_seconds", 60.0),
            model_file=input_path("model_file"),
            measurement_file=input_path("measurement_file") if name == "se" else None,
            parameter_file=input_path("parameter_file") if name != "ca" else None,
            limit_file=input_path("limit_file") if name == "ca" else None,
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
    return AppConfig(source, kernel_root, database, databases, tick_seconds, retry_seconds, tasks,
                     workspace_root, runtime, scenario, workspace)


def validate_task_inputs(task: TaskConfig) -> None:
    required = {"se": ("model_file", "measurement_file", "parameter_file"),
                "lf": ("model_file", "parameter_file"), "ca": ("model_file", "limit_file")}
    for field in required[task.name]:
        value = getattr(task, field, None)
        if value is None or not Path(value).is_file():
            raise ConfigError(f"tasks.{task.name}.{field} does not exist: {value}")
