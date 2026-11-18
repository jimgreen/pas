"""SQLite persistence for scheduled calculation runs."""

from __future__ import annotations

import json
import sqlite3
import threading
import heapq
import copy
import csv
import io
from collections import OrderedDict
from itertools import islice
from functools import wraps
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from .analytics import DETAILS, detail_query, hour_window, merge_trends
from .dbdef import build_dbdef_rows, load_catalog, normalize_dbdef_row, table_names, upsert_dbdef_row


def synchronized(method):
    """Serialize all access to a repository's shared SQLite connection."""
    @wraps(method)
    def locked(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return locked


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bool(value: Any) -> int:
    return int(bool(value))


class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self._cache = OrderedDict()
        self._cache_revision = None

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            self._conn.execute("PRAGMA synchronous = NORMAL")
            self._conn.execute("PRAGMA busy_timeout = 30000")
            self._conn.execute("PRAGMA mmap_size = 268435456")
        return self._conn

    def _cached(self, key, compute):
        # Called under the repository lock. Detect writes by this or other connections.
        conn = self._connection()
        if conn.in_transaction:
            return compute()
        revision = (conn.total_changes, conn.execute("PRAGMA data_version").fetchone()[0])
        if revision != self._cache_revision:
            self._cache.clear()
            self._cache_revision = revision
        if key not in self._cache:
            value = compute()
            if len(json.dumps(value, default=str)) <= 65536:
                self._cache[key] = copy.deepcopy(value)
                if len(self._cache) > 64:
                    self._cache.popitem(last=False)
            return value
        self._cache.move_to_end(key)
        return copy.deepcopy(self._cache[key])

    @synchronized
    def initialize(self) -> None:
        conn = self._connection()
        conn.executescript((Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8"))
        # Existing deployments predate execution_source.  Apply this additive
        # migration after the idempotent schema script so the four live SQLite
        # files gain the field without being recreated.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(calculation_run)")}
        if "execution_source" not in columns:
            conn.execute("ALTER TABLE calculation_run ADD COLUMN execution_source TEXT NOT NULL DEFAULT 'schedule'")
        if "snapshot_version" not in {row[1] for row in conn.execute("PRAGMA table_info(pas_dbdef_run)")}:
            conn.execute("ALTER TABLE pas_dbdef_run ADD COLUMN snapshot_version INTEGER NOT NULL DEFAULT 0")
        conn.execute("INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (1, ?)", (utc_now(),))
        conn.commit()

    @synchronized
    def get_config(self, key: str, default: Any = None) -> Any:
        rows = self._rows("SELECT config_value FROM pas_config WHERE config_key = ?", (key,))
        return json.loads(rows[0]["config_value"]) if rows else default

    @synchronized
    def set_config(self, key: str, value: Any) -> None:
        self._connection().execute(
            "INSERT INTO pas_config(config_key, config_value, updated_at) VALUES (?, ?, ?) ON CONFLICT(config_key) DO UPDATE SET config_value=excluded.config_value, updated_at=excluded.updated_at",
            (str(key), json.dumps(value, ensure_ascii=False, default=str), utc_now()),
        )
        self._connection().commit()

    @synchronized
    def list_config(self) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM pas_config ORDER BY config_key")
        for row in rows:
            try:
                row["value"] = json.loads(row.pop("config_value"))
            except (TypeError, json.JSONDecodeError):
                row["value"] = row.pop("config_value", "")
        return rows

    @synchronized
    def record_log(self, level: str, component: str, message: str, context: dict[str, Any] | None = None) -> None:
        self._connection().execute(
            "INSERT INTO pas_log(created_at, level, component, message, context_json) VALUES (?, ?, ?, ?, ?)",
            (utc_now(), str(level).upper(), str(component), str(message), json.dumps(context or {}, ensure_ascii=False, default=str)),
        )
        self._connection().commit()

    @synchronized
    def list_logs(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM pas_log ORDER BY log_id DESC LIMIT ? OFFSET ?", (max(1, min(int(limit), 500)), max(0, int(offset))))

    @synchronized
    def count_logs(self) -> int:
        return self._connection().execute("SELECT COUNT(*) FROM pas_log").fetchone()[0]

    @synchronized
    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._cache.clear()
            self._cache_revision = None

    @synchronized
    def _rows(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        rows = self._connection().execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]

    @synchronized
    def list_schedules(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM schedule ORDER BY task_type")

    @synchronized
    def count_runs(self, task_type: str | None = None, status: str | None = None, execution_source: str | None = None) -> int:
        clauses = []
        parameters: list[Any] = []
        if task_type:
            clauses.append("task_type = ?")
            parameters.append(task_type)
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        if execution_source:
            clauses.append("execution_source = ?")
            parameters.append(execution_source)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self._connection().execute(f"SELECT COUNT(*) FROM calculation_run{where}", tuple(parameters)).fetchone()
        return int(row[0] or 0)

    @synchronized
    def list_runs(self, limit: int = 50, task_type: str | None = None, offset: int = 0, status: str | None = None, execution_source: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        clauses = []
        parameters: list[Any] = []
        if task_type:
            clauses.append("task_type = ?")
            parameters.append(task_type)
        if status:
            clauses.append("status = ?")
            parameters.append(status)
        if execution_source:
            clauses.append("execution_source = ?")
            parameters.append(execution_source)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.extend((limit, offset))
        return self._rows(f"SELECT * FROM calculation_run{where} ORDER BY started_at DESC, run_id DESC LIMIT ? OFFSET ?", tuple(parameters))

    @synchronized
    def get_run(self, run_id: int) -> dict[str, Any] | None:
        rows = self._rows("SELECT * FROM calculation_run WHERE run_id = ?", (int(run_id),))
        return rows[0] if rows else None

    @synchronized
    def get_result(self, task_type: str, run_id: int, compact: bool = False) -> dict[str, Any] | None:
        run_id = int(run_id)
        if compact:
            return self._cached(("summary", task_type, run_id), lambda: self._compact_result(task_type, run_id))
        if task_type == "se":
            main = self._rows("SELECT * FROM se_result WHERE run_id = ?", (run_id,))
            details = self._rows("SELECT * FROM se_measurement_result WHERE run_id = ? ORDER BY result_id LIMIT 1000", (run_id,))
            table = "se"
        elif task_type == "lf":
            main = self._rows("SELECT * FROM lf_result WHERE run_id = ?", (run_id,))
            details = self._rows("SELECT * FROM lf_device_result WHERE run_id = ? ORDER BY result_id LIMIT 1000", (run_id,))
            table = "lf"
        elif task_type == "ca":
            main = self._rows("SELECT * FROM ca_result WHERE run_id = ?", (run_id,))
            details = self._rows("SELECT * FROM ca_risk WHERE run_id = ? ORDER BY risk_id LIMIT 2000", (run_id,))
            table = "ca"
        else:
            raise ValueError(f"unsupported task type: {task_type}")
        if not main:
            return None
        dbdef = self.get_dbdef_result(task_type, run_id)
        return {"task_type": table, "summary": main[0], "details": details, "dbdef": dbdef}

    def _compact_result(self, task_type, run_id):
        detail_table, _ = self._detail_table(task_type)
        columns = [row[1] for row in self._connection().execute(f"PRAGMA table_info({task_type}_result)") if row[1] not in {"summary_json", "state_json"}]
        main = self._rows(f"SELECT {','.join(columns)} FROM {task_type}_result WHERE run_id = ?", (run_id,))
        if not main:
            return None
        total = self._connection().execute(f"SELECT COUNT(*) FROM {detail_table} WHERE run_id = ?", (run_id,)).fetchone()[0]
        return {"task_type": task_type, "summary": main[0], "detail_count": total,
                "metrics": self._rows("SELECT name, value_real, unit FROM calculation_metric WHERE run_id = ?", (run_id,))}

    @staticmethod
    def _detail_table(task_type):
        if task_type not in DETAILS:
            raise ValueError("invalid task")
        return DETAILS[task_type][:2]

    @synchronized
    def browse_details(self, task_type, run_id, limit=50, offset=0, search="", sort="", direction="asc", view="all"):
        table, columns, predicate, params, order = detail_query(task_type, run_id, search, sort, direction, view)
        limit, offset = max(1, min(int(limit), 500)), max(0, int(offset))
        def query():
            total = self._connection().execute(f"SELECT COUNT(*) FROM {table} WHERE {predicate}", params).fetchone()[0]
            rows = self._rows(f"SELECT {','.join(columns)} FROM {table} WHERE {predicate} ORDER BY {order} LIMIT ? OFFSET ?", tuple(params + [limit, offset]))
            return {"rows": rows, "columns": [{"name": col} for col in columns], "meta": {"total": total, "limit": limit, "offset": offset, "sort": sort, "direction": direction, "view": view}}
        return self._cached(("details", task_type, run_id, limit, offset, search, sort, direction, view), query)

    def export_details(self, task_type, run_id, search="", sort="", direction="asc", view="all"):
        """Stream all filtered rows from an independent WAL read snapshot."""
        table, columns, predicate, params, order = detail_query(task_type, run_id, search, sort, direction, view)
        conn = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
        try:
            conn.execute("BEGIN")
            if conn.execute(f"SELECT 1 FROM {task_type}_result WHERE run_id = ?", (run_id,)).fetchone() is None:
                raise ValueError("result_not_found")
            if conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {predicate}", params).fetchone()[0] > 100000:
                raise ValueError("export exceeds 100000 rows; narrow the filter")
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow(columns)
            yield ("\ufeff" + output.getvalue()).encode("utf-8")
            cursor = conn.execute(f"SELECT {','.join(columns)} FROM {table} WHERE {predicate} ORDER BY {order}", params)
            def safe(value):
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                    return "'" + value
                return value
            while rows := cursor.fetchmany(500):
                output.seek(0); output.truncate(0)
                writer.writerows(tuple(safe(value) for value in row) for row in rows)
                yield output.getvalue().encode("utf-8")
        finally:
            conn.rollback()
            conn.close()


    @synchronized
    def diagnostics(self, task_type, run_id):
        self._detail_table(task_type)
        def query():
            run = self.get_run(run_id)
            if run is None or run["task_type"] != task_type:
                return None
            if task_type == "se":
                rows = self._rows("SELECT measurement_type AS category, COUNT(*) AS count, SUM(valid = 0) AS invalid, MAX(ABS(residual)) AS max_abs_residual FROM se_measurement_result WHERE run_id = ? GROUP BY measurement_type ORDER BY count DESC", (run_id,))
                metrics = self._rows("SELECT COUNT(*) AS total, COALESCE(SUM(valid = 1), 0) AS valid, COALESCE(SUM(valid = 0), 0) AS invalid, COUNT(residual) AS residual_count, MAX(ABS(residual)) AS max_abs_residual FROM se_measurement_result WHERE run_id = ?", (run_id,))[0]
            elif task_type == "lf":
                rows = self._rows("SELECT domain AS category, device_type, COUNT(*) AS count, MIN(voltage_from) AS min_voltage, MAX(voltage_from) AS max_voltage FROM lf_device_result WHERE run_id = ? GROUP BY domain, device_type ORDER BY count DESC", (run_id,))
                metrics = self._rows("SELECT COUNT(*) AS total, COALESCE(SUM(p_from IS NULL), 0) AS missing_power, MIN(voltage_from) AS min_voltage, MAX(voltage_from) AS max_voltage FROM lf_device_result WHERE run_id = ?", (run_id,))[0]
            else:
                rows = self._rows("SELECT risk_type AS category, contingency, COUNT(*) AS count FROM ca_risk WHERE run_id = ? GROUP BY risk_type, contingency ORDER BY count DESC", (run_id,))
                metrics = self._rows("SELECT COUNT(*) AS total, COALESCE(SUM(contingency = 'N-0'), 0) AS n0, COALESCE(SUM(contingency = 'N-1'), 0) AS n1, COUNT(DISTINCT risk_type) AS risk_types FROM ca_risk WHERE run_id = ?", (run_id,))[0]
            return {"metrics": metrics, "groups": rows}
        return self._cached(("diagnostics", task_type, run_id), query)

    @synchronized
    def get_dbdef_result(self, task_type: str, run_id: int) -> dict[str, Any]:
        """Return the dbdef rows written for one calculation run.

        The legacy tables use ``time`` as their key rather than ``run_id``;
        ``pas_dbdef_run`` supplies the explicit run-to-record-time link.
        """
        links = self._rows("SELECT table_name, record_time, row_count FROM pas_dbdef_run WHERE run_id = ? AND task_type = ? ORDER BY table_name", (int(run_id), task_type))
        if not links:
            return {"record_time": None, "tables": {}}
        record_time = int(links[0]["record_time"])
        tables: dict[str, Any] = {}
        for link in links:
            table_name = str(link["table_name"])
            page = self.browse_dbdef_table(task_type, run_id, table_name, 100)
            if page and page["meta"]["total"]:
                tables[table_name] = {"count": page["meta"]["total"], "rows": page["rows"]}
        return {"record_time": record_time, "tables": tables}

    def _legacy_dbdef_selector(self, table_name: str, run_id: int, record_time: int):
        catalog = load_catalog()[table_name]
        if "time" in catalog["column_map"]:
            predicate = "[time] = ?"
            parameters: tuple[Any, ...] = (record_time,)
        elif "id" in catalog["column_map"]:
            # SE detail ids are namespaced by run_id because their dbdef
            # definitions have no time column.
            predicate = "[id] >= ? AND [id] < ?"
            parameters = (int(run_id) * 1_000_000, (int(run_id) + 1) * 1_000_000)
        else:
            raise ValueError(f"dbdef table has no run selector: {table_name}")
        return predicate, list(parameters)

    @synchronized
    def _dbdef_links(self, task_type: str, run_id: int) -> list[dict[str, Any]]:
        allowed = set(table_names(task_type))
        rows = self._rows(
            "SELECT table_name, record_time, row_count, created_at, snapshot_version FROM pas_dbdef_run WHERE run_id = ? AND task_type = ? ORDER BY table_name",
            (int(run_id), task_type),
        )
        return [row for row in rows if row["table_name"] in allowed]

    @synchronized
    def list_dbdef_tables(self, task_type: str, run_id: int) -> list[dict[str, Any]]:
        """List the dbdef tables and their columns written by a run."""
        links = self._dbdef_links(task_type, run_id)
        catalog = load_catalog()
        result = []
        for link in links:
            definition = catalog[link["table_name"]]
            result.append(
                {
                    "table_name": link["table_name"],
                    "record_time": link["record_time"],
                    "row_count": link["row_count"],
                    "created_at": link["created_at"],
                    "columns": [
                        {"name": col["name"], "type": col["type"], "is_key": bool(col.get("is_key"))}
                        for col in definition["columns"]
                    ],
                }
            )
        return result

    @synchronized
    def browse_dbdef_table(self, task_type: str, run_id: int, table_name: str, limit: int = 50, offset: int = 0, search: str = "") -> dict[str, Any] | None:
        """Return one dbdef table page for a specific calculation run."""
        if table_name not in set(table_names(task_type)):
            raise ValueError(f"unsupported dbdef table for {task_type}: {table_name}")
        catalog = load_catalog()[table_name]
        links = [row for row in self._dbdef_links(task_type, run_id) if row["table_name"] == table_name]
        if not links:
            return None
        record_time = int(links[0]["record_time"])
        snapshot = bool(links[0]["snapshot_version"])
        if snapshot:
            source = "pas_dbdef_snapshot"
            predicate, parameters = "run_id = ? AND table_name = ?", [int(run_id), table_name]
        else:
            source = f"[{table_name}]"
            predicate, parameters = self._legacy_dbdef_selector(table_name, run_id, record_time)
        search = str(search or "").strip()
        if search:
            terms = [(f"CAST(json_extract(row_json, '$.{col['name']}') AS TEXT) LIKE ?" if snapshot else f"CAST([{col['name']}] AS TEXT) LIKE ?") for col in catalog["columns"]]
            predicate += " AND (" + " OR ".join(terms) + ")"
            parameters.extend([f"%{search}%"] * len(terms))
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        conn = self._connection()
        total = int(conn.execute(f"SELECT COUNT(*) FROM {source} WHERE {predicate}", tuple(parameters)).fetchone()[0] or 0)
        rows = self._rows(
            f"SELECT * FROM {source} WHERE {predicate} ORDER BY {'row_index' if snapshot else 'rowid'} LIMIT ? OFFSET ?",
            tuple(parameters + [limit, offset]),
        )
        if snapshot:
            rows = [json.loads(row["row_json"]) for row in rows]
        return {
            "table_name": table_name,
            "record_time": record_time,
            "columns": [
                {"name": col["name"], "type": col["type"], "is_key": bool(col.get("is_key"))}
                for col in catalog["columns"]
            ],
            "rows": rows,
            "meta": {"limit": limit, "offset": offset, "total": total, "search": search},
        }

    @synchronized
    def overview(self, limit: int = 12) -> dict[str, Any]:
        counts = self._rows("SELECT COUNT(*) AS total_runs, SUM(status = 'succeeded') AS succeeded_runs, SUM(status = 'failed') AS failed_runs, SUM(status = 'running') AS running_runs FROM calculation_run")[0]
        return {"counts": {key: int(value or 0) for key, value in counts.items()}, "recent_runs": self.list_runs(limit), "schedules": self.list_schedules()}

    @synchronized
    def trend(self, limit=48, end_at=None):
        start, end = hour_window(limit, end_at)
        def query():
            rows = self._rows("""SELECT strftime('%Y-%m-%dT%H', started_at) AS bucket, task_type,
                COUNT(*) AS runs, SUM(status = 'succeeded') AS succeeded,
                SUM(status = 'failed') AS failed, SUM(status = 'running') AS running,
                COUNT(elapsed_seconds) AS elapsed_count, COALESCE(SUM(elapsed_seconds), 0) AS elapsed_sum
                FROM calculation_run WHERE julianday(started_at) >= julianday(?) AND julianday(started_at) < julianday(?)
                GROUP BY bucket, task_type ORDER BY bucket""", (start.isoformat(), end.isoformat()))
            return merge_trends([[{"bucket": row["bucket"], "tasks": {row["task_type"]: {key: value for key, value in row.items() if key not in {"bucket", "task_type"}}}} for row in rows]], start, end)
        return self._cached(("trend", start.isoformat(), end.isoformat()), query)

    @synchronized
    def upsert_schedule(self, task_type: str, enabled: bool, period_seconds: float, config: dict[str, Any], next_due_at: str | None = None) -> int:
        now = utc_now()
        conn = self._connection()
        conn.execute(
            """INSERT INTO schedule(task_type, enabled, period_seconds, next_due_at, config_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(task_type) DO UPDATE SET enabled=excluded.enabled, period_seconds=excluded.period_seconds,
               next_due_at=COALESCE(excluded.next_due_at, schedule.next_due_at), config_json=excluded.config_json, updated_at=excluded.updated_at""",
            (task_type, _bool(enabled), float(period_seconds), next_due_at, json.dumps(config, ensure_ascii=False, sort_keys=True), now, now),
        )
        conn.commit()
        return int(conn.execute("SELECT schedule_id FROM schedule WHERE task_type = ?", (task_type,)).fetchone()[0])

    @synchronized
    def update_schedule_due(self, task_type: str, next_due_at: str | None) -> None:
        self._connection().execute(
            "UPDATE schedule SET next_due_at = ?, updated_at = ? WHERE task_type = ?",
            (next_due_at, utc_now(), task_type),
        )
        self._connection().commit()

    @synchronized
    def start_run(self, schedule_id: int, task_type: str, started_at: str, kernel_root: str, input_fingerprint: str, execution_source: str = "schedule") -> int:
        if execution_source not in {"schedule", "manual"}:
            raise ValueError(f"unsupported execution source: {execution_source}")
        conn = self._connection()
        cur = conn.execute(
            "INSERT INTO calculation_run(schedule_id, task_type, status, started_at, kernel_root, input_fingerprint, execution_source) VALUES (?, ?, 'running', ?, ?, ?, ?)",
            (schedule_id, task_type, started_at, kernel_root, input_fingerprint, execution_source),
        )
        conn.commit()
        return int(cur.lastrowid)

    @synchronized
    def finish_run(self, run_id: int, status: str, finished_at: str, elapsed_seconds: float, return_code: int | None, error_type: str | None = None, error_message: str | None = None, *, commit: bool = True) -> None:
        self._connection().execute(
            "UPDATE calculation_run SET status=?, finished_at=?, elapsed_seconds=?, return_code=?, error_type=?, error_message=? WHERE run_id=?",
            (status, finished_at, float(elapsed_seconds), return_code, error_type, error_message, run_id),
        )
        if commit:
            self._connection().commit()

    @contextmanager
    def result_transaction(self) -> Iterator[None]:
        with self._lock:
            conn = self._connection()
            try:
                conn.execute("BEGIN")
                yield
            except Exception:
                conn.rollback()
                raise
            else:
                conn.commit()

    @synchronized
    def store_metric(self, run_id: int, name: str, value_real: float | None = None, value_text: str | None = None, unit: str | None = None) -> None:
        self._connection().execute("INSERT INTO calculation_metric(run_id, name, value_real, value_text, unit) VALUES (?, ?, ?, ?, ?)", (run_id, name, value_real, value_text, unit))

    @synchronized
    def store_se_result(self, run_id: int, result: dict[str, Any]) -> None:
        stats = result.get("statistics", {})
        conn = self._connection()
        conn.execute("INSERT INTO se_result VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, _bool(result.get("converged")), _bool(result.get("observable")), int(stats.get("iterations", result.get("iterations", 0))), float(stats.get("objective", result.get("objective", 0.0))), float(stats.get("max_correction", result.get("max_correction", 0.0))), float(stats.get("residual_inf", result.get("residual_inf", 0.0))), int(stats.get("rank", 0)), int(stats.get("state_count", 0)), int(stats.get("measurement_count", 0)), int(stats.get("deficiency", 0)), int(stats.get("prefiltered_measurement_count", 0)), int(stats.get("pseudo_measurement_count", 0)), int(stats.get("bad_data_count", 0)), int(stats.get("normal_measurement_count", 0)), json.dumps(result.get("state", []), ensure_ascii=False), json.dumps(result.get("summary", {}), ensure_ascii=False)))
        conn.executemany("INSERT INTO se_measurement_result(run_id, measurement_idx, measurement_name, device_type, device_name, measurement_type, value, estimated_value, residual, normalized_residual, valid, source, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ((run_id, row.get("idx", 0), row.get("name", ""), row.get("device_type", ""), row.get("device_name", ""), row.get("meas_type", ""), row.get("value"), row.get("estimated_value"), row.get("residual"), row.get("normalized_residual"), _bool(row.get("valid", True)), row.get("source", ""), row.get("reason", "")) for row in result.get("measurements", [])))

    @synchronized
    def store_lf_result(self, run_id: int, result: dict[str, Any]) -> None:
        conn = self._connection()
        conn.execute("INSERT INTO lf_result VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, _bool(result.get("converged")), int(result.get("iterations", 0)), float(result.get("norm_f", 0.0)), str(result.get("failure_reason", "") or ""), result.get("ac_converged"), result.get("ac_iterations"), result.get("ac_norm_f"), result.get("dc_converged"), result.get("dc_iterations"), result.get("dc_norm_f"), json.dumps(result.get("summary", {}), ensure_ascii=False)))
        conn.executemany("INSERT INTO lf_device_result(run_id, domain, device_type, device_key, node_from, node_to, voltage_from, voltage_to, p_from, q_from, p_to, q_to, current_from, current_to, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", ((run_id, row.get("domain", ""), row.get("device_type", ""), row.get("device_key", ""), row.get("node_from"), row.get("node_to"), row.get("voltage_from"), row.get("voltage_to"), row.get("p_from"), row.get("q_from"), row.get("p_to"), row.get("q_to"), row.get("current_from"), row.get("current_to"), json.dumps(row, ensure_ascii=False)) for row in result.get("devices", [])))

    @synchronized
    def store_ca_result(self, run_id: int, result: dict[str, Any]) -> None:
        conn = self._connection()
        conn.execute("INSERT INTO ca_result VALUES (?, ?, ?, ?, ?, ?)", (run_id, result.get("risk_level", "无"), int(result.get("n0_risk_count", 0)), int(result.get("n1_scan_count", 0)), int(result.get("n1_risk_count", 0)), json.dumps(result.get("summary", {}), ensure_ascii=False)))
        conn.executemany("INSERT INTO ca_risk(run_id, contingency, risk_source, risk_dist, risk_type, risk_value_real, risk_value_text, risk_info, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", ((run_id, str(row.get("contingency", "N-0")), str(row.get("risk_source", "")), str(row.get("risk_dist", "")), str(row.get("risk_type", "")), row.get("risk_value") if isinstance(row.get("risk_value"), (int, float)) else None, None if isinstance(row.get("risk_value"), (int, float)) else str(row.get("risk_value") or ""), str(row.get("risk_info", "")), utc_now()) for row in result.get("risks", [])))

    @synchronized
    def store_result(self, task_type: str, run_id: int, result: dict[str, Any]) -> None:
        if task_type == "se":
            self.store_se_result(run_id, result)
        elif task_type == "lf":
            self.store_lf_result(run_id, result)
        elif task_type == "ca":
            self.store_ca_result(run_id, result)
        else:
            raise ValueError(f"unsupported task type: {task_type}")

    @synchronized
    def upsert_dbdef_row(self, table_name: str, row: dict[str, Any]) -> None:
        """Upsert a row after validating it against the generated catalog."""
        upsert_dbdef_row(self._connection(), table_name, row)

    @synchronized
    def record_dbdef_run(self, run_id: int, task_type: str, record_time: int, counts: dict[str, int]) -> None:
        conn = self._connection()
        for table_name, row_count in counts.items():
            conn.execute(
                "INSERT OR REPLACE INTO pas_dbdef_run(run_id, task_type, table_name, record_time, row_count, created_at, snapshot_version) VALUES (?, ?, ?, ?, ?, ?, 1)",
                (int(run_id), task_type, table_name, int(record_time), int(row_count), utc_now()),
            )

    @synchronized
    def store_dbdef_result(self, task_type: str, run_id: int, result: dict[str, Any], started_at: Any = None, finished_at: Any = None) -> dict[str, int]:
        """Write normalized kernel output to its legacy PAS dbdef tables."""
        rows_by_table = build_dbdef_rows(task_type, result, int(run_id), started_at, finished_at)
        for table_name, rows in rows_by_table.items():
            normalized = [normalize_dbdef_row(table_name, row) for row in rows]
            names = [col["name"] for col in load_catalog()[table_name]["columns"]]
            quoted, placeholders = ",".join(f"[{name}]" for name in names), ",".join("?" for _ in names)
            self._connection().executemany(
                f"INSERT OR REPLACE INTO [{table_name}] ({quoted}) VALUES ({placeholders})",
                (tuple(row[name] for name in names) for row in normalized),
            )
            self._connection().executemany(
                "INSERT INTO pas_dbdef_snapshot(run_id, table_name, row_index, row_json) VALUES (?, ?, ?, ?)",
                ((run_id, table_name, idx, json.dumps(row, ensure_ascii=False)) for idx, row in enumerate(normalized)),
            )
        record_time = next((int(row.get("time")) for rows in rows_by_table.values() for row in rows if row.get("time") is not None), 0)
        counts = {table_name: len(rows) for table_name, rows in rows_by_table.items()}
        if counts:
            self.record_dbdef_run(run_id, task_type, record_time, counts)
        return counts


class RepositoryHub:
    """Control PAS database plus one independent result database per task."""

    def __init__(self, repositories: dict[str, Repository], control: Repository | None = None):
        self.repositories = dict(repositories)
        self.control = control

    def initialize(self) -> None:
        if self.control is not None:
            self.control.initialize()
        for repository in self.repositories.values():
            repository.initialize()

    def for_task(self, task_type: str) -> Repository:
        return self.repositories[task_type]

    def list_schedules(self) -> list[dict[str, Any]]:
        rows = []
        for repository in self.repositories.values():
            rows.extend(repository.list_schedules())
        return sorted(rows, key=lambda row: row["task_type"])

    def update_schedule_due(self, task_type: str, next_due_at: str | None) -> None:
        self.for_task(task_type).update_schedule_due(task_type, next_due_at)

    def count_runs(self, task_type: str | None = None, status: str | None = None, execution_source: str | None = None) -> int:
        if task_type:
            return self.for_task(task_type).count_runs(task_type, status, execution_source)
        return sum(repository.count_runs(status=status, execution_source=execution_source) for repository in self.repositories.values())

    def list_runs(self, limit: int = 50, task_type: str | None = None, offset: int = 0, status: str | None = None, execution_source: str | None = None) -> list[dict[str, Any]]:
        if task_type:
            return self.for_task(task_type).list_runs(limit, task_type, offset, status, execution_source)
        limit, offset = max(1, min(int(limit), 500)), max(0, int(offset))
        def pages(repository):
            cursor = 0
            while True:
                rows = repository.list_runs(500, offset=cursor, status=status, execution_source=execution_source)
                yield from rows
                if len(rows) < 500:
                    break
                cursor += 500
        # Merge sorted streams instead of silently truncating each task at 500.
        rows = heapq.merge(*(pages(repo) for repo in self.repositories.values()),
                          key=lambda row: (str(row["started_at"]), int(row["run_id"])), reverse=True)
        return list(islice(rows, offset, offset + limit))

    def get_run(self, task_type: str, run_id: int) -> dict[str, Any] | None:
        return self.for_task(task_type).get_run(run_id)

    def get_result(self, task_type: str, run_id: int, compact: bool = False) -> dict[str, Any] | None:
        return self.for_task(task_type).get_result(task_type, run_id, compact)

    def browse_details(self, task_type, run_id, limit=50, offset=0, search="", sort="", direction="asc", view="all"):
        return self.for_task(task_type).browse_details(task_type, run_id, limit, offset, search, sort, direction, view)

    def diagnostics(self, task_type, run_id):
        return self.for_task(task_type).diagnostics(task_type, run_id)

    def export_details(self, task_type, run_id, search="", sort="", direction="asc", view="all"):
        return self.for_task(task_type).export_details(task_type, run_id, search, sort, direction, view)

    def list_dbdef_tables(self, task_type: str, run_id: int) -> list[dict[str, Any]]:
        return self.for_task(task_type).list_dbdef_tables(task_type, run_id)

    def browse_dbdef_table(self, task_type: str, run_id: int, table_name: str, limit: int = 50, offset: int = 0, search: str = "") -> dict[str, Any] | None:
        return self.for_task(task_type).browse_dbdef_table(task_type, run_id, table_name, limit, offset, search)

    def overview(self, limit: int = 12) -> dict[str, Any]:
        counts = {"total_runs": 0, "succeeded_runs": 0, "failed_runs": 0, "running_runs": 0}
        for repository in self.repositories.values():
            item = repository.overview(0)["counts"]
            for key in counts:
                counts[key] += int(item.get(key, 0))
        return {"counts": counts, "recent_runs": self.list_runs(limit), "schedules": self.list_schedules()}

    def trend(self, limit=48, end_at=None):
        start, end = hour_window(limit, end_at)
        # Same UTC boundary for every result database.
        bound = (end - timedelta(seconds=1)).isoformat()
        return merge_trends([repo.trend(limit, bound) for repo in self.repositories.values()], start, end)

    def list_config(self) -> list[dict[str, Any]]:
        return self.control.list_config() if self.control is not None else []

    def list_logs(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        return self.control.list_logs(limit, offset) if self.control is not None else []

    def count_logs(self) -> int:
        return self.control.count_logs() if self.control is not None else 0

    def close(self) -> None:
        if self.control is not None:
            self.control.close()
        for repository in self.repositories.values():
            repository.close()
