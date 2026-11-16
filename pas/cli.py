"""Command line entry points for the online analysis service."""

from __future__ import annotations

import argparse
import logging
import threading

from .config import load_config
from .db import Repository
from . import kernels
from .scheduler import Scheduler


def _build_scheduler(config_path: str) -> tuple[Scheduler, Repository]:
    config = load_config(config_path)
    repository = Repository(config.database)
    repository.initialize()
    runners = {}
    if config.tasks["se"].enabled:
        runners["se"] = lambda: kernels.run_se(config.tasks["se"], config.kernel_root)
    if config.tasks["lf"].enabled:
        runners["lf"] = lambda: kernels.run_lf(config.tasks["lf"], config.kernel_root)
    if config.tasks["ca"].enabled:
        runners["ca"] = lambda: kernels.run_ca(config.tasks["ca"], config.kernel_root)
    return Scheduler(config, repository, runners), repository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Periodic online SE/LF/CA analysis service")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init-db", "run-once", "daemon"):
        item = sub.add_parser(command)
        item.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.command == "init-db":
        _, repository = _build_scheduler(args.config)
        repository.close()
        return 0
    scheduler, repository = _build_scheduler(args.config)
    try:
        if args.command == "run-once":
            results = scheduler.run_once()
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
        repository.close()


if __name__ == "__main__":
    raise SystemExit(main())
