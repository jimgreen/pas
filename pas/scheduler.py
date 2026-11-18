"""Periodic task orchestration and calculation run lifecycle."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .config import TASK_NAMES
from .db import Repository

logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fingerprint(task: Any) -> str:
    digest = hashlib.sha256()
    for name in ("model_file", "measurement_file", "parameter_file", "limit_file"):
        value = getattr(task, name, None)
        if value:
            path = Path(value)
            digest.update(str(path).encode())
            try:
                stat = path.stat()
            except OSError:
                continue
            digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
    return digest.hexdigest()


class Scheduler:
    def __init__(self, config: Any, repository: Repository, runners: dict[str, Callable[[], dict[str, Any]]], repositories: dict[str, Repository] | None = None):
        self.config = config
        self.repository = repository
        self.repositories = repositories or {name: repository for name in TASK_NAMES}
        self.runners = runners
        self._active: set[str] = set()
        self._active_lock = threading.Lock()
        self._next_due: dict[str, float] = {}

    def _record_log(self, level: str, message: str, **context: Any) -> None:
        """Persist lifecycle events in the PAS control database when available."""
        control = getattr(self.repository, "control", None)
        recorder = getattr(control or self.repository, "record_log", None)
        if callable(recorder):
            try:
                recorder(level, "scheduler", message, context)
            except Exception:
                logger.exception("failed to persist scheduler log")

    def _enabled(self, task_name: str) -> bool:
        return bool(getattr(self.config.tasks.get(task_name), "enabled", False))

    def _run_task(self, task_name: str, execution_source: str = "schedule") -> bool:
        if execution_source not in {"schedule", "manual"}:
            raise ValueError(f"unsupported execution source: {execution_source}")
        task = self.config.tasks[task_name]
        repository = self.repositories.get(task_name, self.repository)
        with self._active_lock:
            if task_name in self._active:
                logger.warning("skip re-entry task=%s", task_name)
                self._record_log("WARNING", "跳过重复执行", task=task_name)
                return False
            self._active.add(task_name)
        started_at = utc_now()
        started_clock = time.perf_counter()
        schedule_id = repository.upsert_schedule(task_name, task.enabled, task.period_seconds, {key: str(value) for key, value in vars(task).items() if key not in {"name", "enabled", "period_seconds"} and value is not None})
        try:
            run_id = repository.start_run(schedule_id, task_name, started_at, str(self.config.kernel_root), _fingerprint(task), execution_source)
        except TypeError:
            # Keep small third-party/test repositories compatible with the
            # pre-source start_run signature.
            run_id = repository.start_run(schedule_id, task_name, started_at, str(self.config.kernel_root), _fingerprint(task))
        self._record_log("INFO", "开始执行分析任务", task=task_name, run_id=run_id, execution_source=execution_source)
        try:
            result = self.runners[task_name]()
            finished_at = utc_now()
            elapsed_seconds = time.perf_counter() - started_clock
            persisted_result = dict(result)
            persisted_result["elapsed_seconds"] = elapsed_seconds
            # Keep the normalized result and the legacy dbdef projection in
            # one transaction so the UI never observes a half-written run.
            with repository.result_transaction():
                repository.store_result(task_name, run_id, result)
                store_dbdef = getattr(repository, "store_dbdef_result", None)
                if callable(store_dbdef):
                    store_dbdef(task_name, run_id, persisted_result, started_at, finished_at)
            repository.finish_run(run_id, "succeeded", finished_at, elapsed_seconds, 0)
            self._record_log("INFO", "分析任务执行成功", task=task_name, run_id=run_id, execution_source=execution_source, elapsed_seconds=round(elapsed_seconds, 3))
            return True
        except Exception as exc:
            logger.exception("analysis failed task=%s run_id=%s", task_name, run_id)
            repository.finish_run(run_id, "failed", utc_now(), time.perf_counter() - started_clock, 1, type(exc).__name__, str(exc))
            self._record_log("ERROR", "分析任务执行失败", task=task_name, run_id=run_id, execution_source=execution_source, error_type=type(exc).__name__, error_message=str(exc))
            return False
        finally:
            with self._active_lock:
                self._active.discard(task_name)

    def run_once(self) -> dict[str, bool]:
        results = {}
        for task_name in TASK_NAMES:
            if self._enabled(task_name):
                results[task_name] = self._run_task(task_name, "schedule")
        return results

    def trigger_task(self, task_name: str, allow_disabled: bool = True) -> bool:
        """Run one task from an operator request.

        Manual execution is independent from the periodic enabled flag.  A
        disabled task can therefore be tested or run on demand, while the
        daemon still honors the configured enabled flag.
        """
        if task_name not in TASK_NAMES:
            raise ValueError(f"unsupported task: {task_name}")
        if not allow_disabled and not self._enabled(task_name):
            return False
        if task_name not in self.runners:
            self._record_log("ERROR", "人工触发失败：任务未配置执行器", task=task_name, execution_source="manual")
            return False
        return self._run_task(task_name, "manual")

    def run_task(self, task_name: str) -> bool:
        """Backward-compatible alias for a manual task trigger."""
        return self.trigger_task(task_name)

    def trigger_all(self) -> dict[str, bool]:
        """Run all configured task runners manually, in SE/LF/CA order."""
        return {task_name: self.trigger_task(task_name) for task_name in TASK_NAMES if task_name in self.runners}

    def status(self) -> dict[str, Any]:
        with self._active_lock:
            active = sorted(self._active)
        return {
            "active_tasks": active,
            "enabled_tasks": [name for name in TASK_NAMES if self._enabled(name)],
            "next_due_monotonic": {name: value for name, value in self._next_due.items()},
            "schedules": self.repository.list_schedules() if callable(getattr(self.repository, "list_schedules", None)) else [],
        }

    def _set_next_due(self, task_name: str, due_monotonic: float, due_at: str) -> None:
        self._next_due[task_name] = due_monotonic
        repository = self.repositories.get(task_name, self.repository)
        updater = getattr(repository, "update_schedule_due", None)
        if callable(updater):
            updater(task_name, due_at)

    def run_daemon(self, stop_event: threading.Event | None = None) -> None:
        stop_event = stop_event or threading.Event()
        now = time.monotonic()
        for task_name in TASK_NAMES:
            if self._enabled(task_name):
                self._set_next_due(task_name, now, utc_now())
        while not stop_event.is_set():
            now = time.monotonic()
            for task_name in TASK_NAMES:
                if self._enabled(task_name) and now >= self._next_due.get(task_name, now):
                    self._run_task(task_name, "schedule")
                    period = float(self.config.tasks[task_name].period_seconds)
                    due = time.monotonic() + period
                    due_at = (datetime.now(timezone.utc) + timedelta(seconds=period)).isoformat(timespec="seconds")
                    self._set_next_due(task_name, due, due_at)
            stop_event.wait(float(self.config.tick_seconds))
