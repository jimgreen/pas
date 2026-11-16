"""SQLite persistence for scheduled calculation runs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bool(value: Any) -> int:
    return int(bool(value))


class Repository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    def initialize(self) -> None:
        conn = self._connection()
        conn.executescript((Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8"))
        conn.execute("INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (1, ?)", (utc_now(),))
        conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _rows(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        rows = self._connection().execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]

    def list_schedules(self) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM schedule ORDER BY task_type")

    def list_runs(self, limit: int = 50, task_type: str | None = None, offset: int = 0) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        if task_type:
            return self._rows("SELECT * FROM calculation_run WHERE task_type = ? ORDER BY run_id DESC LIMIT ? OFFSET ?", (task_type, limit, offset))
        return self._rows("SELECT * FROM calculation_run ORDER BY run_id DESC LIMIT ? OFFSET ?", (limit, offset))

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        rows = self._rows("SELECT * FROM calculation_run WHERE run_id = ?", (int(run_id),))
        return rows[0] if rows else None

    def get_result(self, task_type: str, run_id: int) -> dict[str, Any] | None:
        run_id = int(run_id)
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
        return {"task_type": table, "summary": main[0], "details": details}

    def overview(self, limit: int = 12) -> dict[str, Any]:
        counts = self._rows("SELECT COUNT(*) AS total_runs, SUM(status = 'succeeded') AS succeeded_runs, SUM(status = 'failed') AS failed_runs, SUM(status = 'running') AS running_runs FROM calculation_run")[0]
        return {"counts": {key: int(value or 0) for key, value in counts.items()}, "recent_runs": self.list_runs(limit), "schedules": self.list_schedules()}

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

    def start_run(self, schedule_id: int, task_type: str, started_at: str, kernel_root: str, input_fingerprint: str) -> int:
        conn = self._connection()
        cur = conn.execute(
            "INSERT INTO calculation_run(schedule_id, task_type, status, started_at, kernel_root, input_fingerprint) VALUES (?, ?, 'running', ?, ?, ?)",
            (schedule_id, task_type, started_at, kernel_root, input_fingerprint),
        )
        conn.commit()
        return int(cur.lastrowid)

    def finish_run(self, run_id: int, status: str, finished_at: str, elapsed_seconds: float, return_code: int | None, error_type: str | None = None, error_message: str | None = None) -> None:
        self._connection().execute(
            "UPDATE calculation_run SET status=?, finished_at=?, elapsed_seconds=?, return_code=?, error_type=?, error_message=? WHERE run_id=?",
            (status, finished_at, float(elapsed_seconds), return_code, error_type, error_message, run_id),
        )
        self._connection().commit()

    @contextmanager
    def result_transaction(self) -> Iterator[None]:
        conn = self._connection()
        try:
            conn.execute("BEGIN")
            yield
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()

    def store_metric(self, run_id: int, name: str, value_real: float | None = None, value_text: str | None = None, unit: str | None = None) -> None:
        self._connection().execute("INSERT INTO calculation_metric(run_id, name, value_real, value_text, unit) VALUES (?, ?, ?, ?, ?)", (run_id, name, value_real, value_text, unit))

    def store_se_result(self, run_id: int, result: dict[str, Any]) -> None:
        stats = result.get("statistics", {})
        conn = self._connection()
        conn.execute("INSERT INTO se_result VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, _bool(result.get("converged")), _bool(result.get("observable")), int(stats.get("iterations", result.get("iterations", 0))), float(stats.get("objective", result.get("objective", 0.0))), float(stats.get("max_correction", result.get("max_correction", 0.0))), float(stats.get("residual_inf", result.get("residual_inf", 0.0))), int(stats.get("rank", 0)), int(stats.get("state_count", 0)), int(stats.get("measurement_count", 0)), int(stats.get("deficiency", 0)), int(stats.get("prefiltered_measurement_count", 0)), int(stats.get("pseudo_measurement_count", 0)), int(stats.get("bad_data_count", 0)), int(stats.get("normal_measurement_count", 0)), json.dumps(result.get("state", []), ensure_ascii=False), json.dumps(result.get("summary", {}), ensure_ascii=False)))
        for row in result.get("measurements", []):
            conn.execute("INSERT INTO se_measurement_result(run_id, measurement_idx, measurement_name, device_type, device_name, measurement_type, value, estimated_value, residual, normalized_residual, valid, source, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, row.get("idx", 0), row.get("name", ""), row.get("device_type", ""), row.get("device_name", ""), row.get("meas_type", ""), row.get("value"), row.get("estimated_value"), row.get("residual"), row.get("normalized_residual"), _bool(row.get("valid", True)), row.get("source", ""), row.get("reason", "")))

    def store_lf_result(self, run_id: int, result: dict[str, Any]) -> None:
        conn = self._connection()
        conn.execute("INSERT INTO lf_result VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, _bool(result.get("converged")), int(result.get("iterations", 0)), float(result.get("norm_f", 0.0)), str(result.get("failure_reason", "") or ""), result.get("ac_converged"), result.get("ac_iterations"), result.get("ac_norm_f"), result.get("dc_converged"), result.get("dc_iterations"), result.get("dc_norm_f"), json.dumps(result.get("summary", {}), ensure_ascii=False)))
        for row in result.get("devices", []):
            conn.execute("INSERT INTO lf_device_result(run_id, domain, device_type, device_key, node_from, node_to, voltage_from, voltage_to, p_from, q_from, p_to, q_to, current_from, current_to, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, row.get("domain", ""), row.get("device_type", ""), row.get("device_key", ""), row.get("node_from"), row.get("node_to"), row.get("voltage_from"), row.get("voltage_to"), row.get("p_from"), row.get("q_from"), row.get("p_to"), row.get("q_to"), row.get("current_from"), row.get("current_to"), json.dumps(row, ensure_ascii=False)))

    def store_ca_result(self, run_id: int, result: dict[str, Any]) -> None:
        conn = self._connection()
        conn.execute("INSERT INTO ca_result VALUES (?, ?, ?, ?, ?, ?)", (run_id, result.get("risk_level", "无"), int(result.get("n0_risk_count", 0)), int(result.get("n1_scan_count", 0)), int(result.get("n1_risk_count", 0)), json.dumps(result.get("summary", {}), ensure_ascii=False)))
        for row in result.get("risks", []):
            value = row.get("risk_value")
            real = value if isinstance(value, (int, float)) else None
            conn.execute("INSERT INTO ca_risk(run_id, contingency, risk_source, risk_dist, risk_type, risk_value_real, risk_value_text, risk_info, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (run_id, str(row.get("contingency", "N-0")), str(row.get("risk_source", "")), str(row.get("risk_dist", "")), str(row.get("risk_type", "")), real, None if real is not None else str(value or ""), str(row.get("risk_info", "")), utc_now()))

    def store_result(self, task_type: str, run_id: int, result: dict[str, Any]) -> None:
        if task_type == "se":
            self.store_se_result(run_id, result)
        elif task_type == "lf":
            self.store_lf_result(run_id, result)
        elif task_type == "ca":
            self.store_ca_result(run_id, result)
        else:
            raise ValueError(f"unsupported task type: {task_type}")
