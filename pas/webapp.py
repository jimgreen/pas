"""Web server command for the PAS multi-page interface."""

from __future__ import annotations

import argparse
import logging

from .cli import _build_scheduler
from .web import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PAS web UI and API")
    parser.add_argument("--config", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scheduler, repository = _build_scheduler(args.config)
    server = serve(scheduler.config, repository, scheduler, "web", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
