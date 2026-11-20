"""Command line entry points for the online analysis service."""

from __future__ import annotations

import argparse
import logging
import threading

from .config import add_workspace_arguments, load_config
from .db import Repository, RepositoryHub
from . import kernels
from .scheduler import Scheduler
from .input_store import initialize_inputs


def _build_scheduler(config_path: str, **workspace_options) -> tuple[Scheduler, RepositoryHub]:
    config = load_config(config_path, **workspace_options)
    result_repositories = {name: Repository(path) for name, path in config.databases.items()}
    repository = RepositoryHub(result_repositories, Repository(config.database))
    repository.initialize()
    initialize_inputs(config)
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
    runners = {
        "se": lambda: kernels.run_se(config.tasks["se"], config.kernel_root),
        "lf": lambda: kernels.run_lf(config.tasks["lf"], config.kernel_root),
        "ca": lambda: kernels.run_ca(config.tasks["ca"], config.kernel_root),
    }
    scheduler = Scheduler(config, repository, runners, result_repositories)
    scheduler.restore_schedules()
    return scheduler, repository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Periodic online SE/LF/CA analysis service")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init-db", "run-once", "daemon"):
        item = sub.add_parser(command)
        item.add_argument("--config", required=True)
        add_workspace_arguments(item)
    args = parser.parse_args(argv)
    workspace_options = {key: getattr(args, key) for key in ("workspace_root", "runtime", "scenario")}
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
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
