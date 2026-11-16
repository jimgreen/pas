"""Configuration loading and validation for the online analysis service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TASK_NAMES = ("se", "lf", "ca")


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
    kernel_root = _path(raw.get("kernel_root"), base)
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
            model_file=_path(values.get("model_file"), base),
            measurement_file=_path(values.get("measurement_file"), base),
            parameter_file=_path(values.get("parameter_file"), base),
            limit_file=_path(values.get("limit_file"), base),
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
