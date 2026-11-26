"""Bounded background execution shared by periodic and operator requests."""
from __future__ import annotations

import hashlib
import inspect
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
                if path.suffix.lower() in {".sqlite3", ".sqlite", ".db"}:
                    wal = Path(str(path) + "-wal")
                    if wal.exists():
                        wal_stat = wal.stat()
                        digest.update(f"wal:{wal_stat.st_size}:{wal_stat.st_mtime_ns}".encode())
            except OSError:
                continue
    return digest.hexdigest()


def persist_completed_run(repo, name, run_id, result, started_at, started, kernel_seconds):
    """Write the result and mark the run complete as one transaction."""
    write_start = time.perf_counter()
    total_elapsed = time.perf_counter() - started
    with repo.result_transaction():
        if name in {"se", "lf"}:
            try:
                repo.store_result(
                    name,
                    run_id,
                    result,
                    calc_time=started_at,
                    elapsed_seconds=total_elapsed,
                    kernel_seconds=kernel_seconds,
                )
            except TypeError:
                repo.store_result(name, run_id, result)
        else:
            repo.store_result(name, run_id, result)
        writer = getattr(repo, "store_dbdef_result", None)
        if callable(writer):
            writer(name, run_id, {**result, "elapsed_seconds": kernel_seconds}, started_at, utc_now())
        metric = getattr(repo, "store_metric", None)
        if callable(metric):
            metric(run_id, "kernel_seconds", kernel_seconds, unit="s")
            metric(run_id, "persistence_seconds", time.perf_counter() - write_start, unit="s")
            for key in ("model_read_seconds", "solve_seconds", "normalization_seconds", "model_cache_hit"):
                if key in result.get("performance", {}):
                    metric(run_id, key, result["performance"][key], unit="" if key == "model_cache_hit" else "s")
        repo.finish_run(run_id, "succeeded", utc_now(), time.perf_counter() - started, 0, commit=False)


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
        if task not in TASK_NAMES or source not in {"manual", "schedule", "chain", "cascade"}:
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
            db_source = "schedule" if source == "schedule" else "manual"
            run_id = repo.start_run(sid, name, job["started_at"], str(self.config.kernel_root), _fingerprint(task), db_source)
            with self._lock:
                job["run_id"] = run_id
            self._record_log("INFO", "开始执行分析任务", task=name, run_id=run_id, execution_source=source)
            se_log_fn = getattr(repo, "record_se_run_log", None) if name == "se" else None
            lf_log_fn = getattr(repo, "record_lf_run_log", None) if name == "lf" else None
            ca_log_fn = getattr(repo, "record_ca_run_log", None) if name == "ca" else None
            task_log_fn = se_log_fn if name == "se" else (lf_log_fn if name == "lf" else ca_log_fn)
            if callable(task_log_fn):
                label = {"se": "状态估计", "lf": "潮流计算", "ca": "静态安全分析"}.get(name, name.upper())
                task_log_fn(
                    level="INFO",
                    stage="trigger",
                    run_id=run_id,
                    source=source,
                    message=f"开始执行{label} #{run_id}（触发方式：{source}）",
                    detail={"execution_source": source},
                )
            kernel_start = time.perf_counter()
            runner = self.runners[name]
            if callable(task_log_fn):
                try:
                    sig = inspect.signature(runner)
                    accepts_ctx = any(
                        p.kind == inspect.Parameter.VAR_KEYWORD or p.name == "stage_logger"
                        for p in sig.parameters.values()
                    )
                except (TypeError, ValueError):
                    accepts_ctx = False
                if accepts_ctx:
                    def _stage_logger(stage: str, level: str = "INFO", message: str = "", elapsed_ms: float | None = None, detail: dict[str, Any] | None = None) -> None:
                        task_log_fn(
                            level=level,
                            stage=stage,
                            run_id=run_id,
                            source=source,
                            elapsed_ms=elapsed_ms,
                            message=message,
                            detail=detail,
                        )
                    result = runner(stage_logger=_stage_logger)
                else:
                    result = runner()
            else:
                result = runner()
            kernel_seconds = time.perf_counter() - kernel_start
            t_persist = time.perf_counter()
            persist_completed_run(repo, name, run_id, result, job["started_at"], started, kernel_seconds)
            if callable(se_log_fn):
                se_stats = result.get("se_statistics") or {}
                se_log_fn(
                    level="INFO",
                    stage="persist",
                    run_id=run_id,
                    source=source,
                    elapsed_ms=(time.perf_counter() - t_persist) * 1000.0,
                    message=f"状态估计 #{run_id} 落库完成：量测 {se_stats.get('meas_count', 0)}，坏数据 {se_stats.get('bad_data_count', 0)}，合格率 {se_stats.get('pass_rate', 0.0):.2%}",
                    detail={
                        "elapsed_seconds": time.perf_counter() - started,
                        "kernel_seconds": kernel_seconds,
                        "bad_data_count": se_stats.get("bad_data_count", 0),
                        "pass_rate": se_stats.get("pass_rate", 0.0),
                    },
                )
                auto_purge = getattr(repo, "se_logs_maybe_auto_purge", None)
                if callable(auto_purge):
                    auto_purge()
            elif callable(lf_log_fn):
                lf_stats = result.get("lf_statistics") or {}
                lf_log_fn(
                    level="INFO",
                    stage="persist",
                    run_id=run_id,
                    source=source,
                    elapsed_ms=(time.perf_counter() - t_persist) * 1000.0,
                    message=f"潮流计算 #{run_id} 落库完成：设备 {lf_stats.get('device_count', 0)}，网损率 {lf_stats.get('loss_rate', 0.0):.2f}%，越限 {lf_stats.get('v_violation_count', 0) + lf_stats.get('overload_count', 0)}",
                    detail={
                        "elapsed_seconds": time.perf_counter() - started,
                        "kernel_seconds": kernel_seconds,
                        "source_se_run_id": lf_stats.get("source_se_run_id"),
                        "loss_rate": lf_stats.get("loss_rate", 0.0),
                    },
                )
            elif callable(ca_log_fn):
                ca_stats = result.get("ca_statistics") or {}
                ca_log_fn(
                    level="INFO",
                    stage="persist",
                    run_id=run_id,
                    source=source,
                    elapsed_ms=(time.perf_counter() - t_persist) * 1000.0,
                    message=(
                        f"静态安全分析 #{run_id} 落库完成：风险等级 {ca_stats.get('risk_level', result.get('risk_level', '安全'))}，"
                        f"评分 {ca_stats.get('security_score', 100.0)}，N-0 风险 {ca_stats.get('n0_risk_count', 0)}，"
                        f"N-1 扫描 {ca_stats.get('n1_total_count', 0)} 项（风险 {ca_stats.get('n1_risk_count', 0)}）"
                    ),
                    detail={
                        "elapsed_seconds": time.perf_counter() - started,
                        "kernel_seconds": kernel_seconds,
                        "source_lf_run_id": ca_stats.get("source_lf_run_id"),
                        "source_se_run_id": ca_stats.get("source_se_run_id"),
                        "risk_level": ca_stats.get("risk_level"),
                        "security_score": ca_stats.get("security_score"),
                    },
                )
            with self._lock:
                job.update(status="succeeded", kernel_seconds=kernel_seconds)
                if not hasattr(self, "_consecutive_failures"):
                    self._consecutive_failures = {}
                self._consecutive_failures[name] = 0
            self._record_log("INFO", "分析任务执行成功", task=name, run_id=run_id, execution_source=source)
            next_cascade = self._resolve_cascade_target(name, result, source)
            if next_cascade:
                # 提前释放当前任务占位后再异步派发下游，避免重复触发与线程争用
                with self._lock:
                    self._active.discard(name)
                try:
                    self._submit(next_cascade, "cascade")
                except Exception:
                    logger.exception("failed to cascade task=%s -> %s", name, next_cascade)
            return True
        except Exception as exc:
            logger.exception("analysis failed task=%s run_id=%s", name, run_id)
            if run_id is not None:
                try:
                    repo.finish_run(run_id, "failed", utc_now(), time.perf_counter() - started, 1, type(exc).__name__, str(exc))
                except Exception:
                    logger.exception("failed to persist run failure")
            if name in ("se", "lf", "ca"):
                err_log_fn = getattr(repo, f"record_{name}_run_log", None)
                if callable(err_log_fn):
                    label = {"se": "状态估计", "lf": "潮流计算", "ca": "静态安全分析"}[name]
                    try:
                        err_log_fn(
                            level="ERROR",
                            stage="error",
                            run_id=run_id,
                            source=source,
                            elapsed_ms=(time.perf_counter() - started) * 1000.0,
                            message=f"{label} #{run_id} 执行失败: {type(exc).__name__}: {exc}",
                            detail={"error_type": type(exc).__name__, "error_message": str(exc)},
                        )
                    except Exception:
                        logger.exception("failed to persist %s run error log", name)
                if name == "se":
                    auto_purge = getattr(repo, "se_logs_maybe_auto_purge", None)
                    if callable(auto_purge):
                        try:
                            auto_purge()
                        except Exception:
                            logger.exception("failed to auto purge se run logs after failure")
            with self._lock:
                job.update(status="failed", error_type=type(exc).__name__, error_message=str(exc))
                if not hasattr(self, "_consecutive_failures"):
                    self._consecutive_failures = {}
                self._consecutive_failures[name] = self._consecutive_failures.get(name, 0) + 1
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

    def retry_failed_async(self, name: str | None = None) -> dict[str, Any]:
        """Retry only tasks whose latest run failed, using current inputs."""
        names = (name,) if name else TASK_NAMES
        if any(item not in TASK_NAMES for item in names):
            raise ValueError("invalid task")
        results = {}
        for item in names:
            latest = self.repositories[item].list_runs(1, item)
            failed = latest and latest[0]["status"] == "failed"
            results[item] = self.trigger_task_async(item) if failed else {"accepted": False, "task": item, "reason": "no_failed_run"}
        return {"accepted": any(item["accepted"] for item in results.values()), "tasks": results}

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
        next_log_purge_check = time.monotonic() + 60.0
        try:
            while not stop_event.is_set() and not self._daemon_stop.is_set():
                now_mono = time.monotonic()
                with self._lock:
                    for name in TASK_NAMES:
                        if stop_event.is_set() or self._daemon_stop.is_set():
                            break
                        if self._enabled(name) and now_mono >= self._next_due.get(name, float("inf")):
                            self._submit(name, "schedule")
                            # 连续失败时按 retry_seconds 阶梯退避（上限 4 倍周期），避免无效轮询刷爆日志与磁盘
                            base_period = float(self.config.tasks[name].period_seconds)
                            fails = getattr(self, "_consecutive_failures", {}).get(name, 0)
                            if fails >= 3:
                                retry_step = float(getattr(self.config, "retry_seconds", 30.0) or 30.0)
                                next_interval = min(max(base_period * 4.0, retry_step * 4.0), base_period + retry_step * min(fails - 2, 4))
                            else:
                                next_interval = base_period
                            self._set_next_due(name, now_mono + next_interval)
                if now_mono >= next_log_purge_check:
                    next_log_purge_check = now_mono + 60.0
                    se_repo = self.repositories.get("se")
                    auto_purge = getattr(se_repo, "se_logs_maybe_auto_purge", None) if se_repo is not None else None
                    if callable(auto_purge):
                        try:
                            auto_purge()
                        except Exception:
                            logger.exception("failed to auto purge se run logs")
                stop_event.wait(float(self.config.tick_seconds))
        finally:
            with self._lock:
                self._daemon_running = False
                self._next_due.clear()
                for name in TASK_NAMES:
                    updater = getattr(self.repositories[name], "update_schedule_due", None)
                    if callable(updater):
                        updater(name, None)

    def get_cascade_policy(self) -> dict[str, bool]:
        """读取 SE → LF → CA 自动级联触发策略。"""
        control = getattr(self.repository, "control", None) or self.repository
        getter = getattr(control, "get_config", None)
        raw = getter("cascade_policy", {}) if callable(getter) else {}
        if not isinstance(raw, dict):
            raw = {}
        se_to_lf = bool(raw.get("se_to_lf", False))
        lf_to_ca = bool(raw.get("lf_to_ca", False))
        # 同时兼容 lf_para.cascade_ca 参数开关
        lf_repo = self.repositories.get("lf")
        if not lf_to_ca and lf_repo is not None and callable(getattr(lf_repo, "lf_params_get", None)):
            try:
                lf_p = lf_repo.lf_params_get()
                if int(lf_p.get("cascade_ca", 0)) == 1:
                    lf_to_ca = True
            except Exception:
                pass
        return {"se_to_lf": se_to_lf, "lf_to_ca": lf_to_ca}

    def update_cascade_policy(self, *, se_to_lf: bool | None = None, lf_to_ca: bool | None = None) -> dict[str, bool]:
        """更新 SE → LF → CA 自动级联触发策略（持久化到 pas_config 并同步 lf_para.cascade_ca）。"""
        cur = self.get_cascade_policy()
        if se_to_lf is not None:
            cur["se_to_lf"] = bool(se_to_lf)
        if lf_to_ca is not None:
            cur["lf_to_ca"] = bool(lf_to_ca)
        control = getattr(self.repository, "control", None) or self.repository
        setter = getattr(control, "set_config", None)
        if callable(setter):
            setter("cascade_policy", cur)
        lf_repo = self.repositories.get("lf")
        if lf_to_ca is not None and lf_repo is not None and callable(getattr(lf_repo, "lf_params_save", None)):
            try:
                lf_repo.lf_params_save({"cascade_ca": 1 if cur["lf_to_ca"] else 0})
            except Exception:
                pass
        self._record_log("INFO", "更新级联联动配置", **cur)
        return cur

    def _resolve_cascade_target(self, name: str, result: dict[str, Any], source: str) -> str | None:
        if source == "chain":
            return None
        policy = self.get_cascade_policy()
        if name == "se" and policy.get("se_to_lf") and "lf" in self.runners:
            if bool(result.get("converged", False)):
                return "lf"
        if name == "lf" and policy.get("lf_to_ca") and "ca" in self.runners:
            if bool(result.get("converged", False)):
                return "ca"
        return None

    def run_chain(self, tasks: tuple[str, ...] = ("se", "lf", "ca")) -> dict[str, Any]:
        """按严格先后顺序同步串联执行 SE → LF → CA，上游失败或不收敛时安全中止下游。"""
        valid = [t for t in tasks if t in TASK_NAMES and t in self.runners]
        started_at = utc_now()
        t0 = time.perf_counter()
        steps: list[dict[str, Any]] = []
        ok_all = True
        for task in valid:
            t_step = time.perf_counter()
            step_ok = self._run_task(task, "chain")
            repo = self.repositories[task]
            latest_runs = repo.list_runs(1, task) if callable(getattr(repo, "list_runs", None)) else []
            run_id = latest_runs[0]["run_id"] if latest_runs else None
            converged = step_ok
            reason = ""
            if step_ok and task == "se" and callable(getattr(repo, "se_topology_snapshot", None)):
                st = (repo.se_topology_snapshot() or {}).get("latest") or {}
                if st and not int(st.get("converged", 1)):
                    converged = False
                    reason = "SE 未收敛，中止下游 LF/CA"
            elif step_ok and task == "lf" and callable(getattr(repo, "lf_snapshot", None)):
                st = (repo.lf_snapshot() or {}).get("latest") or {}
                if st and not int(st.get("converged", 1)):
                    converged = False
                    reason = "LF 未收敛，中止下游 CA"
            elif not step_ok:
                reason = f"{task.upper()} 执行失败或正在运行，中止下游"
            steps.append(
                {
                    "task": task,
                    "ok": bool(step_ok and converged),
                    "run_id": run_id,
                    "converged": bool(converged),
                    "elapsed_seconds": round(time.perf_counter() - t_step, 3),
                    "reason": reason,
                }
            )
            if not (step_ok and converged):
                ok_all = False
                break
        summary = {
            "ok": ok_all,
            "started_at": started_at,
            "finished_at": utc_now(),
            "elapsed_seconds": round(time.perf_counter() - t0, 3),
            "steps": steps,
        }
        with self._lock:
            self._last_chain = summary
        return summary

    def submit_chain_async(self, tasks: tuple[str, ...] = ("se", "lf", "ca")) -> dict[str, Any]:
        """后台异步按顺序串联执行 SE → LF → CA，防止重复并发启动链式任务。"""
        with self._lock:
            if getattr(self, "_chain_running", False):
                return {"accepted": False, "reason": "chain_already_running", "chain": getattr(self, "_last_chain", None)}
            self._chain_running = True
            self._last_chain = {"ok": None, "running": True, "started_at": utc_now(), "steps": []}

        def _worker():
            try:
                res = self.run_chain(tasks)
                with self._lock:
                    self._last_chain = {**res, "running": False}
            finally:
                with self._lock:
                    self._chain_running = False

        threading.Thread(target=_worker, name="pas-chain", daemon=True).start()
        return {"accepted": True, "tasks": list(tasks)}

    def chain_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": bool(getattr(self, "_chain_running", False)),
                "last_chain": dict(getattr(self, "_last_chain", {}) or {}) if getattr(self, "_last_chain", None) else None,
            }

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            self._daemon_stop.set()
        # Finish accepted calculations before closing their database connections.
        self._executor.shutdown(wait=True)
