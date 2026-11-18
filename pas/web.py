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
from urllib.parse import parse_qs, unquote, urlparse

from .db import Repository

logger = logging.getLogger(__name__)


def _int_query(query: dict[str, list[str]], key: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(query.get(key, [default])[0])
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _int_path(value: str) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


class PasWebApp:
    def __init__(self, config: Any, repository: Repository, scheduler: Any, static_root: str | Path):
        self.config = config
        self.repository = repository
        self.scheduler = scheduler
        self.static_root = Path(static_root).resolve()
        self._daemon_thread: threading.Thread | None = None
        self._daemon_stop: threading.Event | None = None
        self._daemon_lock = threading.RLock()

    def start_daemon(self) -> bool:
        """Start periodic scheduling once and report whether it is running."""
        with self._daemon_lock:
            if self._daemon_thread and self._daemon_thread.is_alive():
                return True
            self._daemon_stop = threading.Event()
            self._daemon_thread = threading.Thread(
                target=self.scheduler.run_daemon,
                args=(self._daemon_stop,),
                name="pas-web-daemon",
                daemon=True,
            )
            self._daemon_thread.start()
            return True

    def stop_daemon(self, timeout: float | None = 2.0) -> bool:
        with self._daemon_lock:
            if self._daemon_stop:
                self._daemon_stop.set()
            if self._daemon_thread:
                self._daemon_thread.join(timeout=timeout)
            return bool(self._daemon_thread and self._daemon_thread.is_alive())

    def close(self) -> None:
        self.stop_daemon(timeout=None)
        self.scheduler.shutdown()

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
        if parsed.path == "/api/status":
            scheduler_status = self.scheduler.status() if callable(getattr(self.scheduler, "status", None)) else {}
            scheduler_status.update({"daemon_running": bool(self._daemon_thread and self._daemon_thread.is_alive()), "web_running": True})
            return {"ok": True, "data": scheduler_status}
        if parsed.path == "/api/health":
            scheduler_status = self.scheduler.status() if callable(getattr(self.scheduler, "status", None)) else {}
            raw_databases = self.repository.health() if callable(getattr(self.repository, "health", None)) else {}
            databases = {"pas": raw_databases} if "sqlite" in raw_databases else raw_databases
            tasks = {}
            all_ready = True
            for name, task in self.config.tasks.items():
                required = {
                    "se": ("model_file", "measurement_file", "parameter_file"),
                    "lf": ("model_file", "parameter_file"),
                    "ca": ("model_file", "limit_file"),
                }.get(name, ())
                missing = [field for field in required if not getattr(task, field, None) or not Path(getattr(task, field)).is_file()]
                latest = self.repository.list_runs(1, name) if callable(getattr(self.repository, "list_runs", None)) else []
                tasks[name] = {
                    "enabled": bool(getattr(task, "enabled", False)),
                    "inputs_ready": not missing,
                    "missing_inputs": missing,
                    "latest_run": latest[0] if latest else None,
                }
                all_ready = all_ready and (not tasks[name]["enabled"] or not missing)
            db_ready = all(item.get("sqlite") == "ok" and item.get("exists") for item in databases.values())
            daemon_running = bool(self._daemon_thread and self._daemon_thread.is_alive())
            daemon_ready = daemon_running or not any(item["enabled"] for item in tasks.values())
            return {"ok": True, "data": {
                "status": "ok" if db_ready and all_ready and daemon_ready else "degraded",
                "daemon_running": daemon_running,
                "daemon_ready": daemon_ready,
                "databases": databases,
                "tasks": tasks,
                "active_tasks": scheduler_status.get("active_tasks", []),
                "pending_tasks": scheduler_status.get("pending_tasks", []),
            }}
        if parsed.path == "/api/overview":
            return {"ok": True, "data": self.repository.overview()}
        if parsed.path == "/api/metrics/trend":
            query = parse_qs(parsed.query)
            return {"ok": True, "data": self.repository.trend(_int_query(query, "limit", 24, 1, 168))}
        if parsed.path == "/api/schedules":
            return {"ok": True, "data": self.repository.list_schedules()}
        if parsed.path.startswith("/api/jobs/"):
            job = self.scheduler.get_job(parsed.path.rsplit("/", 1)[-1])
            return {"ok": True, "data": job} if job else {"ok": False, "error": "job_not_found"}
        if parsed.path == "/api/runs":
            query = parse_qs(parsed.query)
            limit = _int_query(query, "limit", 50, 1, 500)
            offset = _int_query(query, "offset", 0, 0, 1_000_000)
            task = query.get("task", [None])[0] or None
            status = query.get("status", [None])[0] or None
            execution_source = query.get("source", [None])[0] or None
            if task and task not in {"se", "lf", "ca"}:
                return {"ok": False, "error": "invalid_task"}
            if status and status not in {"running", "succeeded", "failed"}:
                return {"ok": False, "error": "invalid_status"}
            if execution_source and execution_source not in {"schedule", "manual"}:
                return {"ok": False, "error": "invalid_execution_source"}
            rows = self.repository.list_runs(limit, task, offset, status, execution_source)
            meta = {"limit": limit, "offset": offset, "total": self.repository.count_runs(task, status, execution_source), "task": task, "status": status}
            if execution_source:
                meta["source"] = execution_source
            return {"ok": True, "data": rows, "meta": meta}
        if parsed.path.startswith("/api/runs/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "runs" and parts[2] in {"se", "lf", "ca"}:
                run_id = _int_path(parts[3])
                if run_id is None:
                    return {"ok": False, "error": "invalid_run_id"}
                if getattr(self.repository, "repositories", None) is not None:
                    run = self.repository.get_run(parts[2], run_id)
                else:
                    run = self.repository.get_run(run_id)
                compact = parse_qs(parsed.query).get("compact", ["0"])[0] == "1"
                result = self.repository.get_result(parts[2], run_id, compact=compact)
                if run is None:
                    return {"ok": False, "error": "run_not_found"}
                return {"ok": True, "data": {"run": run, "result": result}}
        if parsed.path.startswith("/api/results/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 5 and parts[2] in {"se", "lf", "ca"} and parts[4] == "details":
                run_id = _int_path(parts[3])
                if run_id is None:
                    return {"ok": False, "error": "invalid_run_id"}
                query = parse_qs(parsed.query)
                try:
                    data = self.repository.browse_details(parts[2], run_id, _int_query(query, "limit", 50, 1, 500), _int_query(query, "offset", 0, 0, 1_000_000), query.get("q", [""])[0], query.get("sort", [""])[0], query.get("direction", ["asc"])[0], query.get("view", ["all"])[0])
                except ValueError as exc:
                    return {"ok": False, "error": str(exc)}
                return {"ok": True, "data": data}
            if len(parts) == 5 and parts[2] in {"se", "lf", "ca"} and parts[4] == "diagnostics":
                run_id = _int_path(parts[3])
                if run_id is None:
                    return {"ok": False, "error": "invalid_run_id"}
                data = self.repository.diagnostics(parts[2], run_id)
                return {"ok": True, "data": data} if data else {"ok": False, "error": "run_not_found"}
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "results" and parts[2] in {"se", "lf", "ca"}:
                run_id = _int_path(parts[3])
                if run_id is None:
                    return {"ok": False, "error": "invalid_run_id"}
                result = self.repository.get_result(parts[2], run_id, compact=parse_qs(parsed.query).get("compact", ["0"])[0] == "1")
                if result is None:
                    return {"ok": False, "error": "result_not_found"}
                return {"ok": True, "data": result}
        if parsed.path.startswith("/api/dbdef/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) in {4, 5} and parts[0] == "api" and parts[1] == "dbdef" and parts[2] in {"se", "lf", "ca"}:
                task = parts[2]
                run_id = _int_path(parts[3])
                if run_id is None:
                    return {"ok": False, "error": "invalid_run_id"}
                repository = self.repository
                try:
                    if len(parts) == 4:
                        tables = repository.list_dbdef_tables(task, run_id)
                        return {"ok": True, "data": {"task_type": task, "run_id": run_id, "tables": tables}}
                    query = parse_qs(parsed.query)
                    limit = _int_query(query, "limit", 50, 1, 500)
                    offset = _int_query(query, "offset", 0, 0, 1_000_000)
                    search = query.get("q", [""])[0]
                    table_name = unquote(parts[4])
                    data = repository.browse_dbdef_table(task, run_id, table_name, limit, offset, search)
                except ValueError as exc:
                    return {"ok": False, "error": str(exc)}
                if data is None:
                    return {"ok": False, "error": "dbdef_table_not_found"}
                return {"ok": True, "data": data}
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
            offset = _int_query(query, "offset", 0, 0, 1_000_000)
            logs = self.repository.list_logs(limit, offset) if callable(getattr(self.repository, "list_logs", None)) else []
            return {"ok": True, "data": logs, "meta": {"total": self.repository.count_logs(), "offset": offset}}
        return {"ok": False, "error": "not_found"}

    def api_post(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "payload_must_be_object"}
        if path.startswith("/api/schedules/"):
            name = path.rsplit("/", 1)[-1]
            try:
                data = self.scheduler.update_schedule(name, payload.get("enabled"), payload.get("period_seconds"))
            except (ValueError, TypeError) as exc:
                return {"ok": False, "error": str(exc)}
            return {"ok": True, "data": data}
        if path == "/api/actions/submit":
            task = payload.get("task")
            if task is not None and task not in ("se", "lf", "ca"):
                return {"ok": False, "error": "invalid_task"}
            data = self.scheduler.trigger_task_async(task) if task else self.scheduler.trigger_all_async()
            return {"ok": bool(data["accepted"]), "data": data, "error": None if data["accepted"] else data.get("reason", "already_running")}
        if path == "/api/actions/retry-failed":
            task = payload.get("task")
            if task is not None and task not in ("se", "lf", "ca"):
                return {"ok": False, "error": "invalid_task"}
            try:
                data = self.scheduler.retry_failed_async(task)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            return {"ok": True, "data": data}
        if path in {"/api/actions/run-once", "/api/actions/trigger"}:
            task = payload.get("task")
            if task is not None and task not in ("se", "lf", "ca"):
                return {"ok": False, "error": "invalid_task"}
            if task in ("se", "lf", "ca"):
                trigger = getattr(self.scheduler, "trigger_task", None)
                ok = bool(trigger(task)) if callable(trigger) else bool(self.scheduler.run_task(task))
                return {"ok": ok, "data": {"task": task, "success": ok, "execution_source": "manual"}}
            trigger_all = getattr(self.scheduler, "trigger_all", None)
            result = trigger_all() if callable(trigger_all) else self.scheduler.run_once()
            return {"ok": bool(result) and all(result.values()), "data": {"results": result, "execution_source": "manual"}}
        if path == "/api/actions/daemon/start":
            return {"ok": True, "data": {"running": self.start_daemon()}}
        if path == "/api/actions/daemon/stop":
            running = self.stop_daemon()
            return {"ok": True, "data": {"running": running, "stopping": running}}
        if path == "/api/actions/daemon/status":
            return {"ok": True, "data": {"running": bool(self._daemon_thread and self._daemon_thread.is_alive())}}
        return {"ok": False, "error": "not_found"}

    def handler_class(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _export(self):
                parsed = urlparse(self.path)
                parts = parsed.path.strip("/").split("/")
                stream = None
                try:
                    if len(parts) != 4 or parts[2] not in {"se", "lf", "ca"} or _int_path(parts[3]) is None:
                        raise ValueError("invalid export request")
                    query = parse_qs(parsed.query)
                    stream = app.repository.export_details(parts[2], int(parts[3]), query.get("q", [""])[0], query.get("sort", [""])[0], query.get("direction", ["asc"])[0], query.get("view", ["all"])[0])
                    first = next(stream)  # Validate before sending any response headers.
                except ValueError as exc:
                    if stream:
                        stream.close()
                    self._send_json({"ok": False, "error": str(exc)}, 400)
                    return
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="{parts[2]}-{parts[3]}-filtered.csv"')
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(first)
                    for chunk in stream:
                        self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    stream.close()

            def _send_json(self, payload: dict[str, Any], status: int = 200):
                body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802
                if self.path.startswith("/api/export/"):
                    self._export()
                    return
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
                status = (202 if self.path == "/api/actions/submit" else 200) if response.get("ok", False) else 400
                self._send_json(response, status)

            def log_message(self, fmt, *args):
                logger.info("web %s", fmt % args)

        return Handler


def serve(config: Any, repository: Repository, scheduler: Any, static_root: str | Path, host: str = "127.0.0.1", port: int = 8080, *, start_daemon: bool = False) -> ThreadingHTTPServer:
    app = PasWebApp(config, repository, scheduler, static_root)
    server = ThreadingHTTPServer((host, int(port)), app.handler_class())
    server.app = app
    if start_daemon:
        app.start_daemon()
    logger.info("PAS web listening on http://%s:%s", host, port)
    return server
