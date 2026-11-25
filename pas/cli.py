"""Command line entry points for the online analysis service."""

from __future__ import annotations

import argparse
import logging
import sqlite3
import threading
import time
from contextlib import closing
from dataclasses import replace
from pathlib import Path

from .config import add_workspace_arguments, load_config
from .db import Repository, RepositoryHub
from . import kernels
from .scheduler import Scheduler, _fingerprint, persist_completed_run, utc_now
from .input_store import initialize_inputs, is_scdfe_d_wide_db
from .model_input import SQLITE_SUFFIXES
from .rtdb_schema import schema_transaction


def _build_scheduler(config_path: str, **workspace_options) -> tuple[Scheduler, RepositoryHub]:
    config = load_config(config_path, **workspace_options)
    result_repositories = {name: Repository(path) for name, path in config.databases.items()}
    repository = RepositoryHub(result_repositories, Repository(config.database))
    repository.initialize()
    initialize_inputs(config)
    se_task = config.tasks["se"]
    result_repositories["se"].sync_se_parameters(
        se_task.parameter_file,
        do_cycle=se_task.period_seconds,
        overwrite=False,
    )
    if repository.control is not None:
        repository.control.set_config("workspace", {key: str(getattr(config, key) or "") for key in
            ("workspace_root", "runtime", "scenario", "workspace_directory")})
        repository.control.set_config("kernel_root", str(config.kernel_root))
        repository.control.set_config("database", str(config.database))
        repository.control.set_config("result_databases", {name: str(path) for name, path in config.databases.items()})
        repository.control.set_config("scheduler", {"tick_seconds": config.tick_seconds, "retry_seconds": config.retry_seconds})
        repository.control.set_config("tasks", {name: {key: str(value) for key, value in vars(task).items() if key != "name"} for name, task in config.tasks.items()})
    # Build all runners, including disabled schedules.  The enabled flag
    # controls periodic execution; operators may still trigger a disabled
    # analysis manually from the Web/API.
    def _run_se_online(*, stage_logger=None):
        current_task = config.tasks["se"]
        se_repo = result_repositories["se"]
        se_params = se_repo.get_se_parameters(
            current_task.parameter_file,
            do_cycle=current_task.period_seconds,
        )
        bad_policies = se_repo.se_bad_policies(enabled_only=True)
        prefilter_rules = se_repo.se_prefilter_rules(enabled_only=True)
        pseudo_meas = se_repo.se_pseudo_meas_list(enabled_only=True)
        pseudo_stat = se_repo.se_pseudo_stat_list(enabled_only=True)
        return kernels.run_se(
            current_task,
            config.kernel_root,
            se_params=se_params,
            bad_policies=bad_policies,
            prefilter_rules=prefilter_rules,
            pseudo_meas_defines=pseudo_meas,
            pseudo_stat_defines=pseudo_stat,
            stage_logger=stage_logger,
        )

    runners = {
        "se": _run_se_online,
        "lf": lambda: kernels.run_lf(config.tasks["lf"], config.kernel_root),
        "ca": lambda: kernels.run_ca(config.tasks["ca"], config.kernel_root),
    }
    scheduler = Scheduler(config, repository, runners, result_repositories)
    scheduler.restore_schedules()
    return scheduler, repository


def run_se_snapshot(config, measurement_db: Path | None = None) -> int:
    result_db = config.databases["se"].resolve()
    target_meas = (measurement_db or config.tasks["se"].measurement_file)
    if target_meas is None:
        raise ValueError("必须提供 SE 量测库路径")
    target_meas = Path(target_meas).resolve()
    if result_db == target_meas:
        raise ValueError("SE 结果库必须与 SCADA 量测库分开")
    task = replace(config.tasks["se"], measurement_file=target_meas)
    with closing(Repository(result_db)) as repo:
        repo.initialize()
        se_params = repo.get_se_parameters(task.parameter_file, do_cycle=task.period_seconds)
        schedule = next((row for row in repo.list_schedules() if row["task_type"] == "se"), None)
        schedule_id = schedule["schedule_id"] if schedule else repo.upsert_schedule("se", False, task.period_seconds, {})
        started_at, started = utc_now(), time.perf_counter()
        run_id = repo.start_run(schedule_id, "se", started_at, str(config.kernel_root), _fingerprint(task), "manual")
        repo.record_se_run_log(
            level="INFO",
            stage="trigger",
            run_id=run_id,
            source="manual",
            message=f"CLI 触发状态估计 #{run_id}",
            detail={"measurement_db": str(target_meas)},
        )
        try:
            kernel_start = time.perf_counter()
            bad_policies = repo.se_bad_policies(enabled_only=True)
            prefilter_rules = repo.se_prefilter_rules(enabled_only=True)
            pseudo_meas = repo.se_pseudo_meas_list(enabled_only=True)
            pseudo_stat = repo.se_pseudo_stat_list(enabled_only=True)
            result = kernels.run_se(
                task,
                config.kernel_root,
                scada_snapshot=True,
                se_params=se_params,
                bad_policies=bad_policies,
                prefilter_rules=prefilter_rules,
                pseudo_meas_defines=pseudo_meas,
                pseudo_stat_defines=pseudo_stat,
                stage_logger=lambda stage, level="INFO", message="", elapsed_ms=None, detail=None: repo.record_se_run_log(
                    level=level, stage=stage, run_id=run_id, source="manual", elapsed_ms=elapsed_ms, message=message, detail=detail
                ),
            )
            t_persist = time.perf_counter()
            persist_completed_run(repo, "se", run_id, result, started_at, started, time.perf_counter() - kernel_start)
            se_stats = result.get("se_statistics") or {}
            repo.record_se_run_log(
                level="INFO",
                stage="persist",
                run_id=run_id,
                source="manual",
                elapsed_ms=(time.perf_counter() - t_persist) * 1000.0,
                message=f"状态估计 #{run_id} 落库完成：量测 {se_stats.get('meas_count', 0)}，坏数据 {se_stats.get('bad_data_count', 0)}，合格率 {se_stats.get('pass_rate', 0.0):.2%}",
                detail=se_stats,
            )
            repo.se_logs_maybe_auto_purge()
        except Exception as error:
            repo.finish_run(run_id, "failed", utc_now(), time.perf_counter() - started, 1, type(error).__name__, str(error))
            repo.record_se_run_log(
                level="ERROR",
                stage="error",
                run_id=run_id,
                source="manual",
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
                message=f"CLI 状态估计 #{run_id} 失败: {type(error).__name__}: {error}",
                detail={"error_type": type(error).__name__, "error_message": str(error)},
            )
            logging.error("SE #%s 失败：%s", run_id, error)
            return 1
        se_stats = result.get("se_statistics") or {}
        print(
            f"SE #{run_id} 已写入 {repo.path}。收敛={result['converged']}，可观测={result['observable']}，"
            f"量测={se_stats.get('meas_count', 0)}，合格率={se_stats.get('pass_rate', 0.0):.2%}，"
            f"坏数据={se_stats.get('bad_data_count', 0)}，总残差={se_stats.get('total_residual', 0.0):.4f}"
        )
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Periodic online SE/LF/CA analysis service")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init-db", "run-once", "run-se-once", "daemon", "sync-rtdb-schema"):
        item = sub.add_parser(command)
        item.add_argument("--config", required=True)
        add_workspace_arguments(item)
        if command == "run-se-once":
            item.add_argument("--measurement-db", type=Path, default=None, help="SCDFE-D measurement database (read-only)")
    args = parser.parse_args(argv)
    workspace_options = {key: getattr(args, key) for key in ("workspace_root", "runtime", "scenario")}
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "run-se-once":
        return run_se_snapshot(load_config(args.config, **workspace_options), args.measurement_db)
    if args.command == "sync-rtdb-schema":
        config = load_config(args.config, **workspace_options)
        paths = dict.fromkeys([config.database, *config.databases.values(),
                               config.tasks["se"].measurement_file, config.tasks["ca"].limit_file])
        for path in paths:
            if path is None or path.suffix.lower() not in SQLITE_SUFFIXES:
                continue
            if is_scdfe_d_wide_db(path) or path.name.lower() == "scdfe_d.sqlite3":
                logging.info("Skipping read-only external SCADA database %s", path)
                continue
            if not path.is_file():
                logging.info("Skipping absent PAS database %s", path)
                continue
            with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=30)) as connection:
                connection.execute("PRAGMA foreign_keys=ON")
                with schema_transaction(connection, path):
                    pass
                count = connection.execute("SELECT COUNT(*) FROM rtdb_schema_tables").fetchone()[0]
                logging.info("Synchronized %d RTDB definitions in %s", count, path)
        return 0
    if args.command == "init-db":
        scheduler, repository = _build_scheduler(args.config, **workspace_options)
        scheduler.shutdown()
        repository.close()
        return 0
    scheduler, repository = _build_scheduler(args.config, **workspace_options)
    try:
        if args.command == "run-once":
            results = scheduler.trigger_all()
            for task_name, success in results.items():
                print(f"{task_name}: {'succeeded' if success else 'failed'}")
            return 0 if all(results.values()) else 1
        stop_event = threading.Event()
        try:
            scheduler.run_daemon(stop_event)
        except KeyboardInterrupt:
            stop_event.set()
        return 0
    finally:
        scheduler.shutdown()
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
