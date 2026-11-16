"""Periodic task orchestration and calculation run lifecycle."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from datetime import datetime, timezone
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
    def __init__(self, config: Any, repository: Repository, runners: dict[str, Callable[[], dict[str, Any]]]):
        self.config = config
        self.repository = repository
        self.runners = runners
        self._active: set[str] = set()
        self._active_lock = threading.Lock()
        self._next_due: dict[str, float] = {}

    def _enabled(self, task_name: str) -> bool:
        return bool(getattr(self.config.tasks.get(task_name), "enabled", False))

    def _run_task(self, task_name: str) -> bool:
        task = self.config.tasks[task_name]
        with self._active_lock:
            if task_name in self._active:
                logger.warning("skip re-entry task=%s", task_name)
                return False
            self._active.add(task_name)
        started_at = utc_now()
        started_clock = time.perf_counter()
        schedule_id = self.repository.upsert_schedule(task_name, task.enabled, task.period_seconds, {key: str(value) for key, value in vars(task).items() if key not in {"name", "enabled", "period_seconds"} and value is not None})
        run_id = self.repository.start_run(schedule_id, task_name, started_at, str(self.config.kernel_root), _fingerprint(task))
        try:
            result = self.runners[task_name]()
            with self.repository.result_transaction():
                self.repository.store_result(task_name, run_id, result)
            self.repository.finish_run(run_id, "succeeded", utc_now(), time.perf_counter() - started_clock, 0)
            return True
        except Exception as exc:
            logger.exception("analysis failed task=%s run_id=%s", task_name, run_id)
            self.repository.finish_run(run_id, "failed", utc_now(), time.perf_counter() - started_clock, 1, type(exc).__name__, str(exc))
            return False
        finally:
            with self._active_lock:
                self._active.discard(task_name)

    def run_once(self) -> dict[str, bool]:
        results = {}
        for task_name in TASK_NAMES:
            if self._enabled(task_name):
                results[task_name] = self._run_task(task_name)
        return results

    def run_daemon(self, stop_event: threading.Event | None = None) -> None:
        stop_event = stop_event or threading.Event()
        now = time.monotonic()
        for task_name in TASK_NAMES:
            if self._enabled(task_name):
                self._next_due[task_name] = now
        while not stop_event.is_set():
            now = time.monotonic()
            for task_name in TASK_NAMES:
                if self._enabled(task_name) and now >= self._next_due.get(task_name, now):
                    self._run_task(task_name)
                    self._next_due[task_name] = time.monotonic() + float(self.config.tasks[task_name].period_seconds)
            stop_event.wait(float(self.config.tick_seconds))
