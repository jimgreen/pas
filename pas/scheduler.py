"""Bounded background execution shared by periodic and operator requests."""
from __future__ import annotations

import hashlib
import logging
import math
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from .config import TASK_NAMES, validate_task_inputs
from .db import Repository

logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _fingerprint(task: Any) -> str:
    digest = hashlib.sha256()
    for name in ("model_file", "measurement_file", "parameter_file", "limit_file"):
        value = getattr(task, name, None)
        if value:
            path = Path(value)
            digest.update(str(path).encode())
            try:
                stat = path.stat()
                digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
            except OSError:
                continue
    return digest.hexdigest()


class Scheduler:
    def __init__(self, config: Any, repository: Repository, runners: dict[str, Callable[[], dict[str, Any]]], repositories: dict[str, Repository] | None = None):
        self.config = config
        self.repository = repository
        self.repositories = repositories or {name: repository for name in TASK_NAMES}
        self.runners = runners
        self._active: set[str] = set()
        self._pending: set[str] = set()
        self._lock = threading.RLock()
        self._next_due: dict[str, float] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="pas-analysis")
        self._daemon_running = False
        self._daemon_stop = threading.Event()
        self._closed = False

    def _record_log(self, level: str, message: str, **context: Any) -> None:
        control = getattr(self.repository, "control", None)
        recorder = getattr(control or self.repository, "record_log", None)
        if callable(recorder):
            try:
                recorder(level, "scheduler", message, context)
            except Exception:
                logger.exception("failed to persist scheduler log")

    def _enabled(self, name: str) -> bool:
        return bool(getattr(self.config.tasks.get(name), "enabled", False))

    def _reserve(self, task: str, source: str) -> dict[str, Any]:
        if task not in TASK_NAMES or source not in {"manual", "schedule"}:
            raise ValueError("invalid task or execution source")
        with self._lock:
            if self._closed:
                return {"accepted": False, "task": task, "reason": "service_stopping"}
            if task not in self.runners:
                return {"accepted": False, "task": task, "reason": "runner_not_configured"}
            if task in self._active or task in self._pending:
                return {"accepted": False, "task": task, "reason": "already_running"}
            # At most one job per task. Retain 100 recent outcomes for polling.
            for key in list(self._jobs):
                if len(self._jobs) < 100:
                    break
                if self._jobs[key]["status"] in {"succeeded", "failed"}:
                    del self._jobs[key]
            job_id = uuid.uuid4().hex
            job = {"job_id": job_id, "task": task, "execution_source": source,
                   "status": "queued", "submitted_at": utc_now(), "run_id": None}
            self._jobs[job_id] = job
            self._pending.add(task)
            return {"accepted": True, **job}

    def _execute(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs[job_id]
            name, source = job["task"], job["execution_source"]
            self._pending.discard(name)
            self._active.add(name)
            job.update(status="running", started_at=utc_now())
            task = self.config.tasks[name]
        repo = self.repositories[name]
        started = time.perf_counter()
        run_id = None
        try:
            with self._lock:
                task = self.config.tasks[name]
                sid = repo.upsert_schedule(name, task.enabled, task.period_seconds, self._task_options(task))
            run_id = repo.start_run(sid, name, job["started_at"], str(self.config.kernel_root), _fingerprint(task), source)
            with self._lock:
                job["run_id"] = run_id
            self._record_log("INFO", "开始执行分析任务", task=name, run_id=run_id, execution_source=source)
            kernel_start = time.perf_counter()
            result = self.runners[name]()
            kernel_seconds = time.perf_counter() - kernel_start
            write_start = time.perf_counter()
            with repo.result_transaction():
                repo.store_result(name, run_id, result)
                writer = getattr(repo, "store_dbdef_result", None)
                if callable(writer):
                    writer(name, run_id, {**result, "elapsed_seconds": kernel_seconds}, job["started_at"], utc_now())
                metric = getattr(repo, "store_metric", None)
                if callable(metric):
                    metric(run_id, "kernel_seconds", kernel_seconds, unit="s")
                    metric(run_id, "persistence_seconds", time.perf_counter() - write_start, unit="s")
                repo.finish_run(run_id, "succeeded", utc_now(), time.perf_counter() - started, 0, commit=False)
            with self._lock:
                job.update(status="succeeded", kernel_seconds=kernel_seconds)
            self._record_log("INFO", "分析任务执行成功", task=name, run_id=run_id, execution_source=source)
            return True
        except Exception as exc:
            logger.exception("analysis failed task=%s run_id=%s", name, run_id)
            if run_id is not None:
                try:
                    repo.finish_run(run_id, "failed", utc_now(), time.perf_counter() - started, 1, type(exc).__name__, str(exc))
                except Exception:
                    logger.exception("failed to persist run failure")
            with self._lock:
                job.update(status="failed", error_type=type(exc).__name__, error_message=str(exc))
            self._record_log("ERROR", "分析任务执行失败", task=name, run_id=run_id, execution_source=source, error_message=str(exc))
            return False
        finally:
            with self._lock:
                job.update(finished_at=utc_now(), elapsed_seconds=time.perf_counter() - started)
                self._active.discard(name)

    @staticmethod
    def _task_options(task: Any) -> dict[str, Any]:
        return {key: str(value) for key, value in vars(task).items() if key not in {"name", "enabled", "period_seconds"} and value is not None}

    def _run_task(self, name: str, execution_source: str = "schedule") -> bool:
        job = self._reserve(name, execution_source)
        return self._execute(job["job_id"]) if job["accepted"] else False

    def run_once(self) -> dict[str, bool]:
        return {name: self._run_task(name) for name in TASK_NAMES if self._enabled(name)}

    def trigger_task(self, name: str, allow_disabled: bool = True) -> bool:
        if name not in TASK_NAMES:
            raise ValueError(f"unsupported task: {name}")
        return self._run_task(name, "manual") if allow_disabled or self._enabled(name) else False

    def run_task(self, name: str) -> bool:
        return self.trigger_task(name)

    def trigger_all(self) -> dict[str, bool]:
        return {name: self.trigger_task(name) for name in TASK_NAMES if name in self.runners}

    def _submit(self, name: str, source: str) -> dict[str, Any]:
        with self._lock:
            job = self._reserve(name, source)
            if job["accepted"]:
                try:
                    self._executor.submit(self._execute, job["job_id"])
                except Exception:
                    self._pending.discard(name)
                    del self._jobs[job["job_id"]]
                    raise
            return job

    def trigger_task_async(self, name: str) -> dict[str, Any]:
        return self._submit(name, "manual")

    def trigger_all_async(self) -> dict[str, Any]:
        items = {name: self.trigger_task_async(name) for name in TASK_NAMES if name in self.runners}
        return {"accepted": any(item["accepted"] for item in items.values()), "tasks": items}

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def status(self) -> dict[str, Any]:
        with self._lock:
            result = {"active_tasks": sorted(self._active), "pending_tasks": sorted(self._pending),
                      "enabled_tasks": [name for name in TASK_NAMES if self._enabled(name)],
                      "next_due_monotonic": dict(self._next_due), "daemon_running": self._daemon_running,
                      "jobs": [dict(job) for job in list(self._jobs.values())[-12:]]}
        result["schedules"] = self.repository.list_schedules() if callable(getattr(self.repository, "list_schedules", None)) else []
        return result

    def update_schedule(self, name: str, enabled: bool, period_seconds: float) -> dict[str, Any]:
        if name not in TASK_NAMES or type(enabled) is not bool:
            raise ValueError("invalid task or enabled flag")
        if isinstance(period_seconds, bool):
            raise ValueError("period_seconds must be a number")
        period = float(period_seconds)
        if not math.isfinite(period) or not 1 <= period <= 604800:
            raise ValueError("period_seconds must be between 1 and 604800")
        with self._lock:
            task = replace(self.config.tasks[name], enabled=enabled, period_seconds=period)
            if enabled:
                validate_task_inputs(task)
            control = getattr(self.repository, "control", None) or self.repository
            overrides = control.get_config("schedule_overrides", {})
            overrides[name] = {"enabled": enabled, "period_seconds": period}
            control.set_config("schedule_overrides", overrides)
            self.config.tasks[name] = task
            self.repositories[name].upsert_schedule(name, enabled, period, self._task_options(task))
            if enabled and self._daemon_running:
                self._set_next_due(name, time.monotonic() + period)
            else:
                self._next_due.pop(name, None)
                self.repositories[name].update_schedule_due(name, None)
        self._record_log("INFO", "更新分析任务调度配置", task=name, enabled=enabled, period_seconds=period)
        return {"task": name, "enabled": enabled, "period_seconds": period}

    def restore_schedules(self) -> None:
        control = getattr(self.repository, "control", None) or self.repository
        overrides = control.get_config("schedule_overrides", {})
        if not isinstance(overrides, dict):
            raise ValueError("stored schedule_overrides must be an object")
        for name, values in overrides.items():
            if name in TASK_NAMES:
                if not isinstance(values, dict) or type(values.get("enabled")) is not bool:
                    raise ValueError(f"invalid stored schedule for {name}")
                period = values.get("period_seconds")
                if isinstance(period, bool) or not isinstance(period, (int, float)) or not math.isfinite(period) or not 1 <= period <= 604800:
                    raise ValueError(f"invalid stored period for {name}")
                task = replace(self.config.tasks[name], enabled=values["enabled"], period_seconds=float(period))
                if task.enabled:
                    validate_task_inputs(task)
                self.config.tasks[name] = task
        for name, task in self.config.tasks.items():
            self.repositories[name].upsert_schedule(name, task.enabled, task.period_seconds, self._task_options(task))
            self.repositories[name].update_schedule_due(name, None)

    def _set_next_due(self, name: str, due: float) -> None:
        self._next_due[name] = due
        due_at = (datetime.now(timezone.utc) + timedelta(seconds=max(0, due - time.monotonic()))).isoformat(timespec="milliseconds")
        updater = getattr(self.repositories[name], "update_schedule_due", None)
        if callable(updater):
            updater(name, due_at)

    def run_daemon(self, stop_event: threading.Event | None = None) -> None:
        stop_event = stop_event or self._daemon_stop
        with self._lock:
            if self._daemon_running or self._closed:
                return
            self._daemon_running = True
            for name in TASK_NAMES:
                if self._enabled(name):
                    self._set_next_due(name, time.monotonic())
        try:
            while not stop_event.is_set() and not self._daemon_stop.is_set():
                with self._lock:
                    for name in TASK_NAMES:
                        if stop_event.is_set() or self._daemon_stop.is_set():
                            break
                        if self._enabled(name) and time.monotonic() >= self._next_due.get(name, float("inf")):
                            self._submit(name, "schedule")
                            # Coalesce missed ticks; never enqueue a backlog for a slow task.
                            self._set_next_due(name, time.monotonic() + self.config.tasks[name].period_seconds)
                stop_event.wait(float(self.config.tick_seconds))
        finally:
            with self._lock:
                self._daemon_running = False
                self._next_due.clear()
                for name in TASK_NAMES:
                    updater = getattr(self.repositories[name], "update_schedule_due", None)
                    if callable(updater):
                        updater(name, None)

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            self._daemon_stop.set()
        # Finish accepted calculations before closing their database connections.
        self._executor.shutdown(wait=True)
