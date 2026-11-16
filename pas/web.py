"""Dependency-free HTTP API and static web application for PAS."""

from __future__ import annotations

import json
import logging
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .db import Repository

logger = logging.getLogger(__name__)


class PasWebApp:
    def __init__(self, config: Any, repository: Repository, scheduler: Any, static_root: str | Path):
        self.config = config
        self.repository = repository
        self.scheduler = scheduler
        self.static_root = Path(static_root).resolve()
        self._daemon_thread: threading.Thread | None = None
        self._daemon_stop: threading.Event | None = None

    def static_path(self, request_path: str) -> Path | None:
        raw_path = urlparse(request_path).path
        relative = "index.html" if raw_path in {"", "/"} else raw_path.lstrip("/")
        candidate = (self.static_root / relative).resolve()
        try:
            candidate.relative_to(self.static_root)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def api_get(self, path: str) -> dict[str, Any]:
        parsed = urlparse(path)
        if parsed.path == "/api/overview":
            return {"ok": True, "data": self.repository.overview()}
        if parsed.path == "/api/runs":
            query = parse_qs(parsed.query)
            return {"ok": True, "data": self.repository.list_runs(int(query.get("limit", [50])[0]), query.get("task", [None])[0], int(query.get("offset", [0])[0]))}
        if parsed.path.startswith("/api/results/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "results" and parts[2] in {"se", "lf", "ca"}:
                result = self.repository.get_result(parts[2], int(parts[3]))
                if result is None:
                    return {"ok": False, "error": "result_not_found"}
                return {"ok": True, "data": result}
        if parsed.path == "/api/config":
            tasks = {name: {"name": name, "enabled": task.enabled, "period_seconds": task.period_seconds, "model_file": str(task.model_file) if task.model_file else None, "measurement_file": str(task.measurement_file) if task.measurement_file else None, "parameter_file": str(task.parameter_file) if task.parameter_file else None, "limit_file": str(task.limit_file) if task.limit_file else None, "scan_n1": task.scan_n1} for name, task in self.config.tasks.items()}
            return {"ok": True, "data": {"kernel_root": str(self.config.kernel_root), "database": str(self.config.database), "tasks": tasks}}
        return {"ok": False, "error": "not_found"}

    def api_post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        if path == "/api/actions/run-once":
            task = payload.get("task")
            if task in {"se", "lf", "ca"}:
                ok = bool(self.scheduler.run_task(task))
                return {"ok": ok, "data": {"task": task, "success": ok}}
            result = self.scheduler.run_once()
            return {"ok": all(result.values()), "data": {"results": result}}
        if path == "/api/actions/daemon/start":
            if self._daemon_thread and self._daemon_thread.is_alive():
                return {"ok": True, "data": {"running": True}}
            self._daemon_stop = threading.Event()
            self._daemon_thread = threading.Thread(target=self.scheduler.run_daemon, args=(self._daemon_stop,), daemon=True)
            self._daemon_thread.start()
            return {"ok": True, "data": {"running": True}}
        if path == "/api/actions/daemon/stop":
            if self._daemon_stop:
                self._daemon_stop.set()
            return {"ok": True, "data": {"running": False}}
        return {"ok": False, "error": "not_found"}

    def handler_class(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _send_json(self, payload: dict[str, Any], status: int = 200):
                body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                if self.path.startswith("/api/"):
                    payload = app.api_get(self.path)
                    self._send_json(payload, 200 if payload.get("ok", False) else 404)
                    return
                path = app.static_path(self.path)
                if path is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                body = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):  # noqa: N802
                if not self.path.startswith("/api/"):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    size = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
                    payload = json.loads(self.rfile.read(size) or b"{}")
                    response = app.api_post(self.path, payload)
                except (ValueError, json.JSONDecodeError) as exc:
                    response = {"ok": False, "error": str(exc)}
                self._send_json(response, 200 if response.get("ok", False) else 400)

            def log_message(self, fmt, *args):
                logger.info("web %s", fmt % args)

        return Handler


def serve(config: Any, repository: Repository, scheduler: Any, static_root: str | Path, host: str = "127.0.0.1", port: int = 8080) -> ThreadingHTTPServer:
    app = PasWebApp(config, repository, scheduler, static_root)
    server = ThreadingHTTPServer((host, int(port)), app.handler_class())
    logger.info("PAS web listening on http://%s:%s", host, port)
    return server
