"""Web server command for the PAS multi-page interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .cli import _build_scheduler
from .config import add_workspace_arguments
from .web import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PAS web UI and API")
    parser.add_argument("--config", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    add_workspace_arguments(parser)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scheduler, repository = _build_scheduler(args.config, workspace_root=args.workspace_root,
                                            runtime=args.runtime, scenario=args.scenario)
    server = serve(scheduler.config, repository, scheduler, Path(__file__).resolve().parent.parent / "web", args.host, args.port, start_daemon=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.app.close()
        server.server_close()
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
