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
            tasks = {name: {"name": name, "enabled": bool(getattr(task, "enabled", False)), "period_seconds": float(getattr(task, "period_seconds", 0)), "model_file": str(getattr(task, "model_file", None)) if getattr(task, "model_file", None) else None, "measurement_file": str(getattr(task, "measurement_file", None)) if getattr(task, "measurement_file", None) else None, "parameter_file": str(getattr(task, "parameter_file", None)) if getattr(task, "parameter_file", None) else None, "limit_file": str(getattr(task, "limit_file", None)) if getattr(task, "limit_file", None) else None, "scan_n1": bool(getattr(task, "scan_n1", True))} for name, task in self.config.tasks.items()}
            result_databases = {name: str(path) for name, path in getattr(self.config, "databases", {}).items()}
            if not result_databases:
                result_databases = {name: str(repository.path) for name, repository in getattr(self.repository, "repositories", {}).items()}
            control = getattr(self.repository, "control", None)
            control_database = getattr(self.config, "database", None) or getattr(control, "path", None)
            config_rows = self.repository.list_config() if callable(getattr(self.repository, "list_config", None)) else []
            return {"ok": True, "data": {"kernel_root": str(self.config.kernel_root), "database": str(control_database or ""), "control_database": str(control_database or ""), "result_databases": result_databases, "pas_config": config_rows, "tasks": tasks}}
        if parsed.path == "/api/logs":
            query = parse_qs(parsed.query)
            try:
                limit = int(query.get("limit", [100])[0])
            except (TypeError, ValueError):
                limit = 100
            logs = self.repository.list_logs(limit) if callable(getattr(self.repository, "list_logs", None)) else []
            return {"ok": True, "data": logs}
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
