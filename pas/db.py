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
from .ca_online import (
    bulk_toggle_ca_contingencies,
    ca_log_summary,
    clear_ca_contingencies,
    delete_ca_contingency,
    ensure_ca_log_policy,
    ensure_ca_params,
    export_ca_logs_csv,
    list_ca_contingencies,
    list_ca_logs,
    purge_ca_logs,
    record_ca_log,
    reset_ca_params,
    save_ca_contingency,
    save_ca_params,
    sync_ca_contingencies_from_model,
    update_ca_log_policy,
)
from .dbdef import build_dbdef_rows, load_catalog, normalize_dbdef_row, table_names, upsert_dbdef_row
from .input_store import SE_DEVICE_RESULT_METRICS
from .rtdb_schema import execute_schema, schema_transaction
from .se_bad import (
    ack_bad_data,
    bad_overview,
    convert_bad_to_pseudo,
    delete_bad_meas_policy,
    ensure_se_bad_columns,
    list_abnormal_measurements,
    list_bad_meas_policies,
    list_current_bad_data,
    save_bad_meas_policy,
    store_se_suspect_statuses,
)
from .se_log import (
    ensure_se_log_policy,
    export_se_logs_csv,
    list_se_logs,
    maybe_auto_purge_se_logs,
    preview_purge_se_logs,
    purge_se_logs,
    record_se_log,
    se_log_summary,
    update_se_log_policy,
)
from .se_params import ensure_se_para_columns, sync_se_parameters_table
from .se_prefilter import (
    delete_prefilter_rule,
    list_prefilter_results,
    list_prefilter_rules,
    prefilter_analysis,
    prefilter_overview,
    save_prefilter_rule,
    store_se_prefilter_results,
)
from .se_pseudo import (
    delete_pseudo_meas_define,
    delete_pseudo_stat_define,
    ensure_se_pseudo_columns,
    list_pseudo_meas_defines,
    list_pseudo_stat_defines,
    list_se_pseudo_results,
    pseudo_overview,
    save_pseudo_meas_define,
    save_pseudo_stat_define,
    store_se_pseudo_results,
)
from .lf_online import (
    clear_lf_overrides,
    delete_lf_override,
    ensure_lf_log_policy,
    ensure_lf_params,
    export_lf_logs_csv,
    lf_log_summary,
    list_lf_logs,
    list_lf_overrides,
    purge_lf_logs,
    record_lf_log,
    reset_lf_params,
    save_lf_override,
    save_lf_params,
    update_lf_log_policy,
)
from .se_weight import delete_weight_rule, list_weight_rules, save_weight_rule


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
        with schema_transaction(conn, self.path):
            # Upgrade old runs before the schema attempts to index this field.
            columns = {row[1] for row in conn.execute("PRAGMA table_info(calculation_run)")}
            if columns and "execution_source" not in columns:
                conn.execute("ALTER TABLE calculation_run ADD COLUMN execution_source TEXT NOT NULL DEFAULT 'schedule'")
            execute_schema(conn, Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            ensure_se_para_columns(conn)
            ensure_se_pseudo_columns(conn)
            ensure_se_bad_columns(conn)
            ensure_se_log_policy(conn)
            if "snapshot_version" not in {row[1] for row in conn.execute("PRAGMA table_info(pas_dbdef_run)")}:
                conn.execute("ALTER TABLE pas_dbdef_run ADD COLUMN snapshot_version INTEGER NOT NULL DEFAULT 0")
            # 回收服务异常退出遗留的僵尸 running 任务，避免前端长期显示假运行态
            conn.execute(
                """UPDATE calculation_run
                   SET status = 'failed',
                       finished_at = COALESCE(finished_at, ?),
                       return_code = COALESCE(return_code, 1),
                       error_type = COALESCE(error_type, 'InterruptedError'),
                       error_message = COALESCE(error_message, '服务重启，已自动回收未完成的历史任务')
                   WHERE status = 'running'""",
                (utc_now(),),
            )
            conn.execute("INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (1, ?)", (utc_now(),))

    @synchronized
    def sync_se_parameters(
        self,
        para_file: str | Path | None,
        *,
        do_cycle: int | float = 60,
        calc_trigger: int = 1,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """从 se.para 提取算法参数并幂等同步至 pas_se_para（不覆盖已有在线修改，除非 overwrite=True）。"""
        conn = self._connection()
        params = sync_se_parameters_table(
            conn,
            para_file,
            do_cycle=do_cycle,
            calc_trigger=calc_trigger,
            overwrite=overwrite,
        )
        conn.commit()
        return params

    @synchronized
    def get_se_parameters(
        self,
        para_file: str | Path | None = None,
        *,
        do_cycle: int | float = 60,
    ) -> dict[str, Any]:
        """优先只读查询 pas_se_para 当前生效的 SE 算法参数；仅当表为空时从 para_file 幂等初始化。"""
        rows = self._rows("SELECT * FROM pas_se_para ORDER BY id LIMIT 1")
        if rows:
            return rows[0]
        return self.sync_se_parameters(para_file, do_cycle=do_cycle, overwrite=False)

    @synchronized
    def update_se_parameters(
        self,
        payload: dict[str, Any],
        *,
        para_file: str | Path | None = None,
        do_cycle: int | float = 60,
    ) -> dict[str, Any]:
        """在线校验并更新 pas_se_para 中的 SE 算法参数。"""
        import math

        current = self.sync_se_parameters(para_file, do_cycle=do_cycle, overwrite=False)
        int_limits = {
            "max_iterator": (1, 1000),
            "badnum_max": (0, 500),
            "badnum_step": (1, 100),
            "do_cycle": (1, 604800),
            "calc_trigger": (0, 10),
            "flat_start": (0, 1),
            "targeted_pseudo_measurement_max": (0, 100000),
            "targeted_pseudo_measurement_step": (1, 10000),
            "power_flow_max_iter": (1, 5000),
        }
        float_limits = {
            "baderr_eps": (1e-6, 1e6),
            "measqual_eps": (1e-14, 1.0),
            "obj_scaling_factor": (1e-9, 1e9),
            "tol": (1e-14, 1.0),
            "diff_step": (1e-12, 1.0),
            "pseudo_measurement_weight": (1e-12, 1e6),
            "targeted_pseudo_measurement_redundancy_ratio": (0.0, 100.0),
            "voltage_floor": (1e-4, 1.0),
            "min_current_voltage": (1e-6, 1.0),
            "power_flow_tol": (1e-14, 1.0),
            "power_flow_min_voltage": (1e-6, 1.0),
        }
        allowed = set(int_limits) | set(float_limits)
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"不支持的 SE 算法参数字段: {', '.join(sorted(unknown))}")
        updated = dict(current)
        for key, raw_val in payload.items():
            if raw_val is None or isinstance(raw_val, bool) and key != "flat_start":
                raise ValueError(f"参数 {key} 必须为有效数值")
            if key in int_limits:
                lo, hi = int_limits[key]
                try:
                    num = int(raw_val) if isinstance(raw_val, bool) else int(float(raw_val))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"参数 {key} 必须为整数") from exc
                if not lo <= num <= hi:
                    raise ValueError(f"参数 {key} 超出允许范围 [{lo}, {hi}]")
                updated[key] = num
            else:
                lo, hi = float_limits[key]
                try:
                    num = float(raw_val)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"参数 {key} 必须为数值") from exc
                if not math.isfinite(num) or not lo <= num <= hi:
                    raise ValueError(f"参数 {key} 超出允许范围 [{lo}, {hi}]")
                updated[key] = num
        if "tol" in payload and "measqual_eps" not in payload:
            updated["measqual_eps"] = updated["tol"]
        elif "measqual_eps" in payload and "tol" not in payload:
            updated["tol"] = updated["measqual_eps"]
        updated["updated_at"] = utc_now()
        conn = self._connection()
        cols = [col for col in updated if col != "id"]
        assignments = ",".join(f"[{col}]=?" for col in cols)
        conn.execute(
            f"UPDATE [pas_se_para] SET {assignments} WHERE id=?",
            tuple(updated[col] for col in cols) + (updated["id"],),
        )
        record_se_log(
            conn,
            level="INFO",
            stage="param_change",
            source="operator",
            message=f"更新 SE 算法参数 ({len(payload)} 项)",
            detail={"changed": payload},
        )
        conn.commit()
        return updated

    @synchronized
    def se_overview(self, para_file: str | Path | None = None, do_cycle: int | float = 60) -> dict[str, Any]:
        """汇总在线 SE 主画面顶部 KPI、坏数据告警、设备表行数、参数及最近运行。"""
        conn = self._connection()
        latest_rows = self._rows("SELECT * FROM se_statistics ORDER BY run_id DESC LIMIT 1")
        latest = latest_rows[0] if latest_rows else None
        bad_data = self._rows(
            "SELECT * FROM se_bad_data ORDER BY ABS(COALESCE(normalized_residual, 0)) DESC, id ASC"
        )
        device_counts: dict[str, int] = {}
        for dev_type in SE_DEVICE_RESULT_METRICS:
            table_name = f"se_dev_{dev_type}"
            device_counts[dev_type] = int(conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0] or 0)
        params = self.get_se_parameters(para_file, do_cycle=do_cycle)
        recent_runs = self._rows(
            """SELECT r.run_id, r.status, r.started_at, r.finished_at, r.elapsed_seconds,
                      r.execution_source, r.error_type, r.error_message,
                      s.pass_rate, s.bad_data_count, s.total_residual, s.converged, s.observable, s.meas_count
               FROM calculation_run r
               LEFT JOIN se_statistics s ON s.run_id = r.run_id
               WHERE r.task_type = 'se'
               ORDER BY r.run_id DESC LIMIT 15"""
        )
        return {
            "latest": latest,
            "bad_data": bad_data,
            "device_counts": device_counts,
            "params": params,
            "recent_runs": recent_runs,
        }

    @synchronized
    def se_topology_snapshot(self) -> dict[str, Any]:
        """单次锁内聚合最新断面全部设备表、全部量测与坏数据，彻底消除潮流图 N+1 查询与 500 条截断。"""
        latest_rows = self._rows("SELECT * FROM se_statistics ORDER BY run_id DESC LIMIT 1")
        latest = latest_rows[0] if latest_rows else None
        bad_data = self._rows(
            "SELECT * FROM se_bad_data ORDER BY ABS(COALESCE(normalized_residual, 0)) DESC, id ASC"
        )
        measurements = self._rows(
            """SELECT device_type, device_idx, metric, unit, residual, normalized_residual, is_bad, source
               FROM se_measurement"""
        )
        devices_by_type: dict[str, list[dict[str, Any]]] = {}
        for dev_type in SE_DEVICE_RESULT_METRICS:
            devices_by_type[dev_type] = self._rows(f"SELECT * FROM [se_dev_{dev_type}] ORDER BY idx ASC")
        return {
            "latest": latest,
            "bad_data": bad_data,
            "measurements": measurements,
            "devices_by_type": devices_by_type,
        }

    @synchronized
    def se_converged_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        """返回最近 N 次收敛/成功的历史 SE 断面摘要，供潮流图、全量测分析等页历史回放选择。"""
        limit = max(1, min(int(limit), 200))
        return self._rows(
            """SELECT s.run_id, s.calc_time, s.pass_rate, s.bad_data_count, s.meas_count,
                      s.valid_meas_count, s.good_meas_count, s.elapsed_seconds,
                      s.iterations, s.objective, s.converged, s.observable
               FROM se_statistics s
               ORDER BY s.run_id DESC LIMIT ?""",
            (limit,),
        )

    @synchronized
    def se_run_measurements_raw(self, run_id: int) -> dict[str, Any]:
        """读取指定历史 run_id 的统计摘要与完整 se_measurement_result，用于历史断面潮流图回放。"""
        rid = int(run_id)
        stat_rows = self._rows("SELECT * FROM se_statistics WHERE run_id = ? LIMIT 1", (rid,))
        stat = stat_rows[0] if stat_rows else None
        rows = self._rows(
            """SELECT result_id AS meas_id, run_id, measurement_name AS meas_name,
                      device_type, device_name, measurement_type AS meas_type,
                      value AS meas_value, estimated_value AS se_value,
                      residual, normalized_residual, valid, source, reason
               FROM se_measurement_result
               WHERE run_id = ?
               ORDER BY result_id ASC""",
            (rid,),
        )
        return {"stat": stat, "rows": rows}

    @synchronized
    def se_home_summary(self, para_file: str | Path | None = None, do_cycle: int | float = 60) -> dict[str, Any]:
        """聚合新版三栏状态估计主画面所需的全量真实指标、今日/昨日合格率曲线、参数与最新运行日志。"""
        conn = self._connection()
        was_in_tx = conn.in_transaction
        latest_rows = self._rows(
            """SELECT s.*, r.started_at, r.finished_at, r.status AS run_status, r.execution_source,
                      COALESCE(sr.deficiency, 0) AS deficiency,
                      COALESCE(sr.rank, 0) AS rank,
                      COALESCE(sr.state_count, 0) AS state_count
               FROM se_statistics s
               LEFT JOIN calculation_run r ON r.run_id = s.run_id
               LEFT JOIN se_result sr ON sr.run_id = s.run_id
               ORDER BY s.run_id DESC LIMIT 1"""
        )
        latest = latest_rows[0] if latest_rows else None

        device_counts: dict[str, int] = {}
        for dev_type in SE_DEVICE_RESULT_METRICS:
            table_name = f"se_dev_{dev_type}"
            device_counts[dev_type] = int(conn.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0] or 0)
        bus_count = device_counts.get("ACNode", 0) + device_counts.get("DCNode", 0)
        ac_bus_count = device_counts.get("ACNode", 0)
        dc_bus_count = device_counts.get("DCNode", 0)
        branch_count = (
            device_counts.get("ACBranch", 0)
            + device_counts.get("DCBranch", 0)
            + device_counts.get("ACZeroBranch", 0)
        )
        converter_count = device_counts.get("DCDCConverter", 0) + device_counts.get("DCACConverter", 0)
        total_devices = sum(device_counts.values())

        pf_ov = prefilter_overview(conn)
        ps_ov = pseudo_overview(conn)
        bd_ov = bad_overview(conn)
        params = self.get_se_parameters(para_file, do_cycle=do_cycle)
        sched_rows = self._rows("SELECT * FROM schedule WHERE task_type = 'se' LIMIT 1")
        schedule = sched_rows[0] if sched_rows else None

        # 按本地自然日聚合今日/昨日合格率曲线与当日运行统计
        local_now = datetime.now().astimezone()
        today_str = local_now.strftime("%Y-%m-%d")
        yesterday_str = (local_now - timedelta(days=1)).strftime("%Y-%m-%d")

        def _parse_local(stamp: str | None) -> datetime | None:
            if not stamp:
                return None
            txt = str(stamp).strip()
            if txt.endswith("Z"):
                txt = txt[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(txt)
            except ValueError:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone()

        stat_rows = self._rows(
            """SELECT run_id, calc_time, pass_rate, converged, bad_data_count
               FROM se_statistics
               ORDER BY run_id DESC LIMIT 1200"""
        )
        by_day: dict[str, list[dict[str, Any]]] = {}
        for row in reversed(stat_rows):
            dt = _parse_local(row.get("calc_time"))
            if dt is None:
                continue
            day_key = dt.strftime("%Y-%m-%d")
            minute = dt.hour * 60 + dt.minute + dt.second / 60.0
            by_day.setdefault(day_key, []).append(
                {
                    "run_id": int(row["run_id"]),
                    "calc_time": row["calc_time"],
                    "time_hm": dt.strftime("%H:%M"),
                    "minute": round(minute, 2),
                    "pass_rate": round(float(row.get("pass_rate") or 0.0) * 100.0, 3),
                    "converged": int(row.get("converged") or 0),
                    "bad_data_count": int(row.get("bad_data_count") or 0),
                }
            )

        today_series = by_day.get(today_str, [])
        compare_day = yesterday_str
        yesterday_series = by_day.get(yesterday_str, [])
        if not yesterday_series:
            other_days = sorted((d for d in by_day if d < today_str), reverse=True)
            if other_days:
                compare_day = other_days[0]
                yesterday_series = by_day[compare_day]

        # 当日总运行次数（包含成功与失败，真实反映调度执行频次）
        run_rows = self._rows(
            """SELECT run_id, status, started_at FROM calculation_run
               WHERE task_type = 'se' ORDER BY run_id DESC LIMIT 1200"""
        )
        today_total_runs = 0
        for r in run_rows:
            dt = _parse_local(r.get("started_at"))
            if dt is not None and dt.strftime("%Y-%m-%d") == today_str:
                today_total_runs += 1
        today_conv_runs = sum(1 for item in today_series if item["converged"])
        denom_runs = max(today_total_runs, len(today_series))
        today_conv_rate = (today_conv_runs / denom_runs * 100.0) if denom_runs > 0 else (
            100.0 if latest and latest.get("converged") else 0.0
        )
        today_avg_pass = (
            sum(item["pass_rate"] for item in today_series) / len(today_series)
            if today_series
            else (float(latest["pass_rate"]) * 100.0 if latest and latest.get("pass_rate") is not None else None)
        )
        yesterday_avg_pass = (
            sum(item["pass_rate"] for item in yesterday_series) / len(yesterday_series)
            if yesterday_series
            else None
        )

        # 最近运行日志（显示在主画面底部通栏）
        latest_logs = self._rows(
            "SELECT log_id, run_id, calc_time, level, stage, source, message FROM se_run_log ORDER BY log_id DESC LIMIT 1"
        )
        latest_log = latest_logs[0] if latest_logs else None

        if not was_in_tx and conn.in_transaction:
            conn.commit()

        meas_count_val = int(latest.get("meas_count") or 0) if latest else 0
        valid_meas_val = int(latest.get("valid_meas_count") or 0) if latest else 0
        state_count_val = int(latest.get("state_count") or 0) if latest else 0
        rank_val = int(latest.get("rank") or 0) if latest else 0
        redundancy = round(valid_meas_val / state_count_val, 2) if state_count_val > 0 else None
        prefilter_rate = round(pf_ov["total"] / meas_count_val * 100.0, 2) if meas_count_val > 0 else 0.0

        return {
            "latest": latest,
            "observability": {
                "bus_count": bus_count,
                "ac_bus_count": ac_bus_count,
                "dc_bus_count": dc_bus_count,
                "total_devices": total_devices,
                "meas_count": meas_count_val,
                "valid_meas_count": valid_meas_val,
                "good_meas_count": int(latest.get("good_meas_count") or 0) if latest else 0,
                "state_count": state_count_val,
                "rank": rank_val,
                "redundancy": redundancy,
                "deficiency": int(latest.get("deficiency") or 0) if latest else 0,
                "observable": bool(latest.get("observable")) if latest else False,
            },
            "prefilter": {
                "total": pf_ov["total"],
                "prefilter_rate": prefilter_rate,
                "by_rule": pf_ov["by_rule"],
                "by_kernel": pf_ov["by_kernel"],
                "rule_enabled": pf_ov["rule_enabled"],
                "rule_total": pf_ov["rule_total"],
                "nomeas_count": bd_ov["nomeas_count"],
                "suspect_count": bd_ov["suspect_count"],
            },
            "control": {
                "pseudo_stat_enabled": ps_ov["stat_enabled"],
                "pseudo_stat_total": ps_ov["stat_total"],
                "pseudo_meas_enabled": ps_ov["defined_enabled"],
                "pseudo_meas_total": ps_ov["defined_total"],
                "pseudo_result_total": ps_ov["result_total"],
                "policy_enabled": bd_ov["policy_enabled"],
                "policy_total": bd_ov["policy_total"],
                "bad_total": bd_ov["bad_total"],
                "bad_unacked": bd_ov["unacked_count"],
                "branch_count": branch_count,
                "converter_count": converter_count,
                "total_devices": total_devices,
            },
            "params": params,
            "schedule": schedule,
            "today_stats": {
                "today_date": today_str,
                "compare_date": compare_day,
                "today_runs": denom_runs,
                "today_converged": today_conv_runs,
                "today_conv_rate": round(today_conv_rate, 2),
                "today_avg_pass_rate": round(today_avg_pass, 2) if today_avg_pass is not None else None,
                "yesterday_avg_pass_rate": round(yesterday_avg_pass, 2) if yesterday_avg_pass is not None else None,
                "current_pass_rate": round(float(latest["pass_rate"]) * 100.0, 2) if latest and latest.get("pass_rate") is not None else None,
            },
            "pass_rate_series": {
                "today_date": today_str,
                "compare_date": compare_day,
                "today": today_series,
                "yesterday": yesterday_series,
            },
            "latest_log": latest_log,
        }

    @synchronized
    def se_devices(
        self,
        device_type: str | None = None,
        *,
        q: str = "",
        bad_only: bool = False,
        run_id: int | None = None,
    ) -> dict[str, Any]:
        """读取最新断面（或指定历史 run_id 断面）各类设备表 se_dev_*，并标注坏数据指标。"""
        conn = self._connection()
        latest_row = conn.execute("SELECT MAX(run_id) FROM se_measurement").fetchone()
        latest_rid = int(latest_row[0]) if latest_row and latest_row[0] is not None else None
        is_history = run_id is not None and (latest_rid is None or int(run_id) != latest_rid)

        hist_map: dict[tuple[str, str, str], dict[str, Any]] = {}
        bad_by_name: dict[tuple[str, str], set[str]] = {}
        bad_by_dev: dict[tuple[str, int], set[str]] = {}
        bad_type_devs: dict[str, set[Any]] = {}

        if is_history:
            hist_rows = self._rows(
                """SELECT device_type, device_name, measurement_type, value, estimated_value, source
                   FROM se_measurement_result WHERE run_id = ?""",
                (int(run_id),),
            )
            # 反向查 (device_type, measurement_type) -> metric 列表
            code_to_metric: dict[tuple[str, str], str] = {
                (dt, code): mk
                for dt, mmap in SE_DEVICE_RESULT_METRICS.items()
                for mk, code in mmap.items()
            }
            for hrow in hist_rows:
                dt = str(hrow.get("device_type") or "")
                dn = str(hrow.get("device_name") or "")
                mt = str(hrow.get("measurement_type") or "")
                hist_map[(dt, dn, mt)] = hrow
                if str(hrow.get("source") or "") == "bad_data":
                    mk = code_to_metric.get((dt, mt), mt)
                    bad_by_name.setdefault((dt, dn), set()).add(mk)
                    bad_type_devs.setdefault(dt, set()).add(dn)
        else:
            bad_rows = self._rows("SELECT device_type, device_idx, device_name, metric FROM se_bad_data")
            for row in bad_rows:
                if row["device_idx"] is not None:
                    key = (str(row["device_type"]), int(row["device_idx"]))
                    bad_by_dev.setdefault(key, set()).add(str(row["metric"] or ""))
                    bad_type_devs.setdefault(str(row["device_type"]), set()).add(int(row["device_idx"]))

        available = []
        for dtype in SE_DEVICE_RESULT_METRICS:
            cnt = int(conn.execute(f"SELECT COUNT(*) FROM [se_dev_{dtype}]").fetchone()[0] or 0)
            available.append({
                "device_type": dtype,
                "count": cnt,
                "bad_device_count": len(bad_type_devs.get(dtype, set())),
            })

        selected = device_type if device_type in SE_DEVICE_RESULT_METRICS else next(
            (item["device_type"] for item in available if item["count"] > 0),
            "ACNode",
        )
        metric_map = SE_DEVICE_RESULT_METRICS[selected]
        metrics = list(metric_map.keys())
        rows = self._rows(f"SELECT * FROM [se_dev_{selected}] ORDER BY idx ASC")
        search = str(q or "").strip().casefold()
        result_rows = []
        for row in rows:
            if is_history:
                dname = str(row.get("name", ""))
                item_row: dict[str, Any] = {"idx": row["idx"], "name": dname}
                for mk, se_code in metric_map.items():
                    hrow = hist_map.get((selected, dname, se_code))
                    item_row[f"{mk}_meas"] = hrow.get("value") if hrow else None
                    item_row[f"{mk}_se"] = hrow.get("estimated_value") if hrow else None
                bad_metrics = sorted(bad_by_name.get((selected, dname), set()))
                row = item_row
            else:
                bad_metrics = sorted(bad_by_dev.get((selected, int(row["idx"])), set()))
            row["bad_metrics"] = bad_metrics
            row["has_bad"] = bool(bad_metrics)
            if bad_only and not row["has_bad"]:
                continue
            if search and search not in f"{row['idx']} {row['name']}".casefold():
                continue
            result_rows.append(row)
        return {
            "device_type": selected,
            "metrics": metrics,
            "meas_type_map": dict(metric_map),
            "rows": result_rows,
            "available_types": available,
            "run_id": int(run_id) if is_history else latest_rid,
            "is_history": is_history,
        }

    @synchronized
    def se_measurements_browse(
        self,
        *,
        source: str = "all",
        device_type: str = "",
        q: str = "",
        sort: str = "abs_residual",
        direction: str = "desc",
        high_residual_only: bool = False,
        run_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """分页筛选最新断面（或指定历史 run_id 断面）量测，支持来源过滤、大残差过滤与多字段排序。"""
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        direction = "asc" if str(direction).lower() == "asc" else "desc"
        conn = self._connection()
        latest_row = conn.execute("SELECT MAX(run_id) FROM se_measurement").fetchone()
        latest_rid = int(latest_row[0]) if latest_row and latest_row[0] is not None else None
        use_history = run_id is not None and (latest_rid is None or int(run_id) != latest_rid)

        if use_history:
            return self._se_history_measurements_browse(
                run_id=int(run_id),
                source=source,
                device_type=device_type,
                q=q,
                sort=sort,
                direction=direction,
                high_residual_only=high_residual_only,
                limit=limit,
                offset=offset,
            )

        clauses: list[str] = []
        params: list[Any] = []
        if source == "bad_data":
            clauses.append("(is_bad = 1 OR source = 'bad_data')")
        elif source in {"normal", "prefiltered", "pseudo"}:
            clauses.append("source = ?")
            params.append(source)
        elif source != "all":
            raise ValueError(f"无效的量测来源筛选: {source}")
        if device_type:
            clauses.append("device_type = ?")
            params.append(device_type)
        if high_residual_only:
            clauses.append("(ABS(COALESCE(normalized_residual, 0)) >= 2.0 OR is_bad = 1)")
        search = str(q or "").strip()
        if search:
            clauses.append("(meas_name LIKE ? OR device_name LIKE ? OR device_type LIKE ? OR metric LIKE ? OR meas_type LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like, like, like])
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sort_map = {
            "abs_residual": "ABS(residual)",
            "abs_norm_residual": "ABS(normalized_residual)",
            "meas_value": "meas_value",
            "se_value": "se_value",
            "residual": "residual",
            "normalized_residual": "normalized_residual",
            "meas_id": "meas_id",
            "device_name": "device_name",
        }
        expr = sort_map.get(sort, "ABS(residual)")
        order = f"{expr} IS NULL, {expr} {direction}, meas_id ASC"
        total = int(conn.execute(f"SELECT COUNT(*) FROM se_measurement{where}", tuple(params)).fetchone()[0] or 0)
        rows = self._rows(
            f"SELECT * FROM se_measurement{where} ORDER BY {order} LIMIT ? OFFSET ?",
            tuple(params + [limit, offset]),
        )
        counts = self._rows(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(is_bad = 1), 0) AS bad_data,
                      COALESCE(SUM(source = 'normal'), 0) AS normal,
                      COALESCE(SUM(source = 'prefiltered'), 0) AS prefiltered,
                      COALESCE(SUM(source = 'pseudo'), 0) AS pseudo,
                      COALESCE(SUM(ABS(COALESCE(normalized_residual, 0)) >= 2.0 OR is_bad = 1), 0) AS high_residual
               FROM se_measurement"""
        )[0]
        return {
            "rows": rows,
            "counts": {k: int(v or 0) for k, v in counts.items()},
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "source": source,
                "sort": sort,
                "direction": direction,
                "high_residual_only": bool(high_residual_only),
                "run_id": latest_rid,
                "is_history": False,
            },
        }

    def _se_history_measurements_browse(
        self,
        *,
        run_id: int,
        source: str,
        device_type: str,
        q: str,
        sort: str,
        direction: str,
        high_residual_only: bool,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """从历史表 se_measurement_result 分页查询指定历史 run_id 的量测明细。"""
        conn = self._connection()
        clauses: list[str] = ["run_id = ?"]
        params: list[Any] = [int(run_id)]
        if source == "bad_data":
            clauses.append("(source = 'bad_data' OR valid = 0)")
        elif source in {"normal", "prefiltered", "pseudo"}:
            clauses.append("source = ?")
            params.append(source)
        elif source != "all":
            raise ValueError(f"无效的量测来源筛选: {source}")
        if device_type:
            clauses.append("device_type = ?")
            params.append(device_type)
        if high_residual_only:
            clauses.append("(ABS(COALESCE(normalized_residual, 0)) >= 2.0 OR source = 'bad_data')")
        search = str(q or "").strip()
        if search:
            clauses.append("(measurement_name LIKE ? OR device_name LIKE ? OR device_type LIKE ? OR measurement_type LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like, like])
        where = " WHERE " + " AND ".join(clauses)
        sort_map = {
            "abs_residual": "ABS(residual)",
            "abs_norm_residual": "ABS(normalized_residual)",
            "meas_value": "value",
            "se_value": "estimated_value",
            "residual": "residual",
            "normalized_residual": "normalized_residual",
            "meas_id": "result_id",
            "device_name": "device_name",
        }
        expr = sort_map.get(sort, "ABS(residual)")
        order = f"{expr} IS NULL, {expr} {direction}, result_id ASC"
        total = int(conn.execute(f"SELECT COUNT(*) FROM se_measurement_result{where}", tuple(params)).fetchone()[0] or 0)
        stat_row = conn.execute("SELECT calc_time FROM se_statistics WHERE run_id = ? LIMIT 1", (int(run_id),)).fetchone()
        calc_time = str(stat_row[0]) if stat_row else ""
        # 反查最新 se_measurement 映射 (device_type, device_name, meas_type) -> (device_idx, metric, unit, weight)
        meta_rows = self._rows("SELECT device_type, device_name, meas_type, device_idx, metric, unit, weight FROM se_measurement")
        meta_map = {
            (str(r["device_type"]), str(r["device_name"]), str(r["meas_type"])): (r["device_idx"], r["metric"], r["unit"], r["weight"])
            for r in meta_rows
        }
        raw_rows = self._rows(
            f"""SELECT result_id AS meas_id, run_id, measurement_name AS meas_name,
                       device_type, device_name, measurement_type AS meas_type,
                       value AS meas_value, estimated_value AS se_value,
                       residual, normalized_residual, valid, source, reason
                FROM se_measurement_result{where}
                ORDER BY {order} LIMIT ? OFFSET ?""",
            tuple(params + [limit, offset]),
        )
        rows = []
        for r in raw_rows:
            d_idx, metric, unit, weight = meta_map.get((str(r["device_type"]), str(r["device_name"]), str(r["meas_type"])), (None, "", "", None))
            r["device_idx"] = d_idx
            r["metric"] = metric
            r["unit"] = unit
            r["weight"] = weight
            r["calc_time"] = calc_time
            r["is_bad"] = int(str(r.get("source") or "") == "bad_data")
            rows.append(r)
        counts = self._rows(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(source = 'bad_data'), 0) AS bad_data,
                      COALESCE(SUM(source = 'normal'), 0) AS normal,
                      COALESCE(SUM(source = 'prefiltered'), 0) AS prefiltered,
                      COALESCE(SUM(source = 'pseudo'), 0) AS pseudo,
                      COALESCE(SUM(ABS(COALESCE(normalized_residual, 0)) >= 2.0 OR source = 'bad_data'), 0) AS high_residual
               FROM se_measurement_result WHERE run_id = ?""",
            (int(run_id),),
        )[0]
        return {
            "rows": rows,
            "counts": {k: int(v or 0) for k, v in counts.items()},
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "source": source,
                "sort": sort,
                "direction": direction,
                "high_residual_only": bool(high_residual_only),
                "run_id": int(run_id),
                "calc_time": calc_time,
                "is_history": True,
            },
        }

    @synchronized
    def se_measurements_export_csv(
        self,
        *,
        source: str = "all",
        device_type: str = "",
        q: str = "",
        sort: str = "abs_residual",
        direction: str = "desc",
        high_residual_only: bool = False,
        run_id: int | None = None,
    ) -> bytes:
        """导出当前筛选条件下的全量匹配量测（支持最新或历史 run_id 断面）为 UTF-8 BOM CSV。"""
        page = self.se_measurements_browse(
            source=source,
            device_type=device_type,
            q=q,
            sort=sort,
            direction=direction,
            high_residual_only=high_residual_only,
            run_id=run_id,
            limit=500,
            offset=0,
        )
        rows = list(page["rows"])
        total = int(page["meta"]["total"])
        offset = len(rows)
        while offset < min(total, 20000):
            nxt = self.se_measurements_browse(
                source=source,
                device_type=device_type,
                q=q,
                sort=sort,
                direction=direction,
                high_residual_only=high_residual_only,
                run_id=run_id,
                limit=500,
                offset=offset,
            )
            if not nxt["rows"]:
                break
            rows.extend(nxt["rows"])
            offset += len(nxt["rows"])
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "meas_id", "device_type", "device_idx", "device_name", "metric", "meas_type",
            "unit", "meas_value", "se_value", "residual", "normalized_residual", "weight",
            "source", "is_bad", "reason", "calc_time",
        ])
        for r in rows:
            writer.writerow([
                r.get("meas_id"), r.get("device_type"), r.get("device_idx"), r.get("device_name"),
                r.get("metric"), r.get("meas_type"), r.get("unit"), r.get("meas_value"),
                r.get("se_value"), r.get("residual"), r.get("normalized_residual"), r.get("weight"),
                r.get("source"), r.get("is_bad"), r.get("reason"), r.get("calc_time"),
            ])
        return ("\ufeff" + buf.getvalue()).encode("utf-8")

    @synchronized
    def se_pseudo_overview(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        data = pseudo_overview(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return data

    @synchronized
    def se_pseudo_meas_list(self, *, device_type: str = "", enabled_only: bool = False, q: str = "") -> list[dict[str, Any]]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        rows = list_pseudo_meas_defines(conn, device_type=device_type, enabled_only=enabled_only, q=q)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return rows

    @synchronized
    def se_pseudo_meas_save(self, payload: dict[str, Any], *, define_id: int | None = None, units: dict[str, Any] | None = None) -> dict[str, Any]:
        conn = self._connection()
        row = save_pseudo_meas_define(conn, payload, define_id=define_id, units=units)
        conn.commit()
        return row

    @synchronized
    def se_pseudo_meas_delete(self, define_id: int) -> bool:
        conn = self._connection()
        ok = delete_pseudo_meas_define(conn, define_id)
        conn.commit()
        return ok

    @synchronized
    def se_pseudo_stat_list(self, *, device_type: str = "", enabled_only: bool = False) -> list[dict[str, Any]]:
        return list_pseudo_stat_defines(self._connection(), device_type=device_type, enabled_only=enabled_only)

    @synchronized
    def se_pseudo_stat_save(self, payload: dict[str, Any], *, define_id: int | None = None) -> dict[str, Any]:
        conn = self._connection()
        row = save_pseudo_stat_define(conn, payload, define_id=define_id)
        conn.commit()
        return row

    @synchronized
    def se_pseudo_stat_delete(self, define_id: int) -> bool:
        conn = self._connection()
        ok = delete_pseudo_stat_define(conn, define_id)
        conn.commit()
        return ok

    @synchronized
    def se_pseudo_results(self, *, origin: str = "all", device_type: str = "", q: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return list_se_pseudo_results(self._connection(), origin=origin, device_type=device_type, q=q, limit=limit, offset=offset)

    @synchronized
    def se_bad_overview(self) -> dict[str, Any]:
        return bad_overview(self._connection())

    @synchronized
    def se_bad_current(self, *, device_type: str = "", ack_status: str = "all", q: str = "") -> list[dict[str, Any]]:
        return list_current_bad_data(self._connection(), device_type=device_type, ack_status=ack_status, q=q)

    @synchronized
    def se_bad_ack(self, bad_id: int, *, ack_status: str = "acked", ack_note: str = "") -> dict[str, Any]:
        conn = self._connection()
        row = ack_bad_data(conn, bad_id=bad_id, ack_status=ack_status, ack_note=ack_note)
        conn.commit()
        return row

    @synchronized
    def se_bad_policies(self, *, enabled_only: bool = False, device_type: str = "", action: str = "", q: str = "") -> list[dict[str, Any]]:
        return list_bad_meas_policies(self._connection(), enabled_only=enabled_only, device_type=device_type, action=action, q=q)

    @synchronized
    def se_bad_policy_save(self, payload: dict[str, Any], *, policy_id: int | None = None, units: dict[str, Any] | None = None) -> dict[str, Any]:
        conn = self._connection()
        row = save_bad_meas_policy(conn, payload, policy_id=policy_id, units=units)
        conn.commit()
        return row

    @synchronized
    def se_bad_policy_batch_save(self, items: list[dict[str, Any]], *, units: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not items or not isinstance(items, list):
            raise ValueError("items 必须为非空列表")
        conn = self._connection()
        saved = [save_bad_meas_policy(conn, item, units=units) for item in items]
        conn.commit()
        return saved

    @synchronized
    def se_prefilter_rule_batch_save(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not items or not isinstance(items, list):
            raise ValueError("items 必须为非空列表")
        conn = self._connection()
        saved = [save_prefilter_rule(conn, item) for item in items]
        conn.commit()
        return saved

    @synchronized
    def se_weight_rules(self, *, enabled_only: bool = False, device_type: str = "", q: str = "") -> list[dict[str, Any]]:
        return list_weight_rules(self._connection(), enabled_only=enabled_only, device_type=device_type, q=q)

    @synchronized
    def se_weight_rule_save(self, payload: dict[str, Any], *, rule_id: int | None = None) -> dict[str, Any]:
        conn = self._connection()
        row = save_weight_rule(conn, payload, rule_id=rule_id)
        conn.commit()
        return row

    @synchronized
    def se_weight_rule_delete(self, rule_id: int) -> bool:
        conn = self._connection()
        ok = delete_weight_rule(conn, rule_id)
        conn.commit()
        return ok

    @synchronized
    def se_bad_policy_delete(self, policy_id: int) -> bool:
        conn = self._connection()
        ok = delete_bad_meas_policy(conn, policy_id)
        conn.commit()
        return ok

    @synchronized
    def se_bad_convert_pseudo(self, **kwargs) -> dict[str, Any]:
        conn = self._connection()
        res = convert_bad_to_pseudo(conn, **kwargs)
        conn.commit()
        return res

    @synchronized
    def se_bad_abnormal(self, *, category: str = "susstat", device_type: str = "", q: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return list_abnormal_measurements(self._connection(), category=category, device_type=device_type, q=q, limit=limit, offset=offset)

    @synchronized
    def se_prefilter_overview(self) -> dict[str, Any]:
        return prefilter_overview(self._connection())

    @synchronized
    def se_prefilter_results(self, *, origin: str = "all", device_type: str = "", q: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return list_prefilter_results(self._connection(), origin=origin, device_type=device_type, q=q, limit=limit, offset=offset)

    @synchronized
    def se_prefilter_rules(self, *, enabled_only: bool = False, device_type: str = "", rule_type: str = "", q: str = "") -> list[dict[str, Any]]:
        return list_prefilter_rules(self._connection(), enabled_only=enabled_only, device_type=device_type, rule_type=rule_type, q=q)

    @synchronized
    def se_prefilter_rule_save(self, payload: dict[str, Any], *, rule_id: int | None = None, units: dict[str, Any] | None = None) -> dict[str, Any]:
        conn = self._connection()
        row = save_prefilter_rule(conn, payload, rule_id=rule_id, units=units)
        conn.commit()
        return row

    @synchronized
    def se_prefilter_rule_delete(self, rule_id: int) -> bool:
        conn = self._connection()
        ok = delete_prefilter_rule(conn, rule_id)
        conn.commit()
        return ok

    @synchronized
    def se_prefilter_analysis(self, *, limit: int = 60) -> dict[str, Any]:
        return prefilter_analysis(self._connection(), limit=limit)

    @synchronized
    def record_se_run_log(
        self,
        *,
        level: str = "INFO",
        stage: str = "system",
        message: str = "",
        run_id: int | None = None,
        source: str = "system",
        elapsed_ms: float | None = None,
        detail: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> int | None:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        lid = record_se_log(
            conn,
            level=level,
            stage=stage,
            message=message,
            run_id=run_id,
            source=source,
            elapsed_ms=elapsed_ms,
            detail=detail,
        )
        if commit and not was_in_tx:
            conn.commit()
        return lid

    @synchronized
    def se_logs_list(self, **kwargs) -> dict[str, Any]:
        return list_se_logs(self._connection(), **kwargs)

    @synchronized
    def se_logs_summary(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        data = se_log_summary(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return data

    @synchronized
    def se_logs_policy_get(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        pol = ensure_se_log_policy(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return pol

    @synchronized
    def se_logs_policy_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self._connection()
        pol = update_se_log_policy(conn, payload)
        record_se_log(
            conn,
            level="INFO",
            stage="param_change",
            source="operator",
            message=f"更新 SE 日志保留策略：保留 {pol['retention_days']} 天，最大 {pol['max_rows']} 条，间隔 {pol['cleanup_interval_hours']}h",
            detail=pol,
        )
        conn.commit()
        return pol

    @synchronized
    def se_logs_purge(
        self,
        *,
        dry_run: bool = False,
        retention_days: int | None = None,
        keep_error_days: int | None = None,
        max_rows: int | None = None,
        source: str = "operator",
    ) -> dict[str, Any]:
        conn = self._connection()
        if dry_run:
            return preview_purge_se_logs(
                conn,
                retention_days=retention_days,
                keep_error_days=keep_error_days,
                max_rows=max_rows,
            )
        res = purge_se_logs(
            conn,
            retention_days=retention_days,
            keep_error_days=keep_error_days,
            max_rows=max_rows,
            source=source,
        )
        conn.commit()
        return res

    @synchronized
    def se_logs_maybe_auto_purge(self) -> dict[str, Any] | None:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = maybe_auto_purge_se_logs(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def se_logs_export_csv(self, **kwargs) -> str:
        return export_se_logs_csv(self._connection(), **kwargs)

    @synchronized
    def se_history_stats(self, limit: int = 100) -> list[dict[str, Any]]:
        """返回按时间正序排列的 SE 历史统计曲线数据。"""
        limit = max(1, min(int(limit), 500))
        rows = self._rows(
            """SELECT run_id, calc_time, elapsed_seconds, kernel_seconds,
                      meas_count, valid_meas_count, good_meas_count, pass_rate,
                      total_residual, residual_inf, objective,
                      bad_data_count, prefiltered_count, pseudo_count,
                      converged, observable, iterations, max_correction
               FROM se_statistics
               ORDER BY run_id DESC LIMIT ?""",
            (limit,),
        )
        rows.reverse()
        return rows

    @synchronized
    def se_history_points(self) -> dict[str, Any]:
        """返回可选量测点目录（按设备类型/设备/指标组织），并附历史坏数据命中统计。"""
        bad_counts_rows = self._rows(
            """SELECT device_type, device_name, measurement_type, COUNT(*) AS bad_hits
               FROM se_measurement_result
               WHERE source = 'bad_data'
               GROUP BY device_type, device_name, measurement_type"""
        )
        bad_map = {
            (r["device_type"], r["device_name"], r["measurement_type"]): int(r["bad_hits"])
            for r in bad_counts_rows
        }
        latest = self._rows(
            """SELECT device_type, device_idx, device_name, metric, meas_type, unit,
                      meas_name, meas_value, se_value, residual, normalized_residual, is_bad, source
               FROM se_measurement
               WHERE source IN ('normal', 'bad_data')
               ORDER BY device_type, device_idx, meas_id"""
        )
        points = []
        seen: set[tuple[str, str, str]] = set()
        for row in latest:
            key = (str(row["device_type"]), str(row["device_name"]), str(row["meas_type"]))
            if key in seen:
                continue
            seen.add(key)
            points.append({
                "device_type": key[0],
                "device_idx": row["device_idx"],
                "device_name": key[1],
                "metric": str(row["metric"] or ""),
                "meas_type": key[2],
                "unit": str(row["unit"] or ""),
                "meas_name": str(row["meas_name"] or ""),
                "latest_meas": row["meas_value"],
                "latest_se": row["se_value"],
                "latest_residual": row["residual"],
                "latest_norm_residual": row["normalized_residual"],
                "is_bad": int(row["is_bad"] or 0),
                "bad_hits": bad_map.get(key, 0),
            })
        if not points:
            fallback = self._rows(
                """SELECT DISTINCT device_type, device_name, measurement_type
                   FROM se_measurement_result
                   WHERE source IN ('normal', 'bad_data', '') AND device_name != ''
                   ORDER BY device_type, device_name, measurement_type LIMIT 1000"""
            )
            for row in fallback:
                key = (str(row["device_type"]), str(row["device_name"]), str(row["measurement_type"]))
                points.append({
                    "device_type": key[0],
                    "device_idx": None,
                    "device_name": key[1],
                    "metric": "",
                    "meas_type": key[2],
                    "unit": "",
                    "meas_name": f"{key[0]}.{key[1]}.{key[2]}",
                    "latest_meas": None,
                    "latest_se": None,
                    "latest_residual": None,
                    "latest_norm_residual": None,
                    "is_bad": 0,
                    "bad_hits": bad_map.get(key, 0),
                })
        return {"points": points}

    @synchronized
    def se_history_point_series(
        self,
        device_type: str,
        device_name: str,
        meas_type: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        """查询单个量测点的历史实测值、估计值、残差、标准化残差与坏数据标记曲线。"""
        limit = max(1, min(int(limit), 500))
        rows = self._rows(
            """SELECT m.run_id, COALESCE(s.calc_time, r.started_at) AS calc_time,
                      m.measurement_name, m.value AS meas_value, m.estimated_value AS se_value,
                      m.residual, m.normalized_residual, m.valid, m.source, m.reason
               FROM se_measurement_result m
               JOIN calculation_run r ON r.run_id = m.run_id
               LEFT JOIN se_statistics s ON s.run_id = m.run_id
               WHERE m.device_type = ? AND m.device_name = ? AND m.measurement_type = ?
                 AND r.status = 'succeeded'
               ORDER BY m.run_id DESC LIMIT ?""",
            (str(device_type), str(device_name), str(meas_type), limit),
        )
        rows.reverse()
        for row in rows:
            row["is_bad"] = int(str(row.get("source") or "") == "bad_data" or not row.get("valid"))
        meta_rows = self._rows(
            "SELECT metric, unit, meas_name FROM se_measurement WHERE device_type = ? AND device_name = ? AND meas_type = ? LIMIT 1",
            (str(device_type), str(device_name), str(meas_type)),
        )
        para_rows = self._rows("SELECT baderr_eps FROM pas_se_para ORDER BY id LIMIT 1")
        return {
            "device_type": device_type,
            "device_name": device_name,
            "meas_type": meas_type,
            "metric": meta_rows[0]["metric"] if meta_rows else "",
            "unit": meta_rows[0]["unit"] if meta_rows else "",
            "meas_name": meta_rows[0]["meas_name"] if meta_rows else (rows[-1]["measurement_name"] if rows else ""),
            "bad_threshold": float(para_rows[0]["baderr_eps"]) if para_rows and para_rows[0]["baderr_eps"] is not None else 3.0,
            "points": rows,
        }

    @synchronized
    def se_history_bad_data(self, limit: int = 100) -> dict[str, Any]:
        """返回历史坏数据数量曲线及高频坏数据量测点统计。"""
        series = self.se_history_stats(limit)
        hotspots = self._rows(
            """SELECT m.device_type, m.device_name, m.measurement_type AS meas_type,
                      COUNT(*) AS bad_hits,
                      MAX(ABS(COALESCE(m.normalized_residual, 0))) AS max_norm_residual,
                      MAX(ABS(COALESCE(m.residual, 0))) AS max_abs_residual,
                      MAX(COALESCE(s.calc_time, r.started_at)) AS last_seen_at
               FROM se_measurement_result m
               JOIN calculation_run r ON r.run_id = m.run_id
               LEFT JOIN se_statistics s ON s.run_id = m.run_id
               WHERE m.source = 'bad_data' AND r.status = 'succeeded'
               GROUP BY m.device_type, m.device_name, m.measurement_type
               ORDER BY bad_hits DESC, max_norm_residual DESC LIMIT 50"""
        )
        current_bad = self._rows(
            "SELECT * FROM se_bad_data ORDER BY ABS(COALESCE(normalized_residual, 0)) DESC, id ASC"
        )
        return {"series": series, "hotspots": hotspots, "current": current_bad}

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
        conn = self._connection()
        conn.execute(
            "INSERT INTO pas_log(created_at, level, component, message, context_json) VALUES (?, ?, ?, ?, ?)",
            (utc_now(), str(level).upper(), str(component), str(message), json.dumps(context or {}, ensure_ascii=False, default=str)),
        )
        # 轻量上限保护：防止 pas_log 长期运行无限膨胀（超 10,000 行保留最新 8,000 行）
        total = int(conn.execute("SELECT COUNT(*) FROM pas_log").fetchone()[0] or 0)
        if total > 10000:
            conn.execute(
                "DELETE FROM pas_log WHERE log_id IN (SELECT log_id FROM pas_log ORDER BY log_id ASC LIMIT ?)",
                (total - 8000,),
            )
        conn.commit()

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
    def health(self, *, lite: bool = False) -> dict[str, Any]:
        """Return a lightweight SQLite readiness check for the operations page."""
        conn = self._connection()
        try:
            if lite:
                conn.execute("SELECT 1").fetchone()
                check = "ok"
            else:
                check = str(conn.execute("PRAGMA quick_check").fetchone()[0])
        except sqlite3.DatabaseError as exc:
            check = str(exc)
        return {
            "path": str(self.path),
            "exists": self.path.is_file(),
            "sqlite": "ok" if check.lower() == "ok" else check,
        }

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
        recent = self.list_runs(limit) if int(limit) > 0 else []
        return {"counts": {key: int(value or 0) for key, value in counts.items()}, "recent_runs": recent, "schedules": self.list_schedules()}

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
    def store_se_result(
        self,
        run_id: int,
        result: dict[str, Any],
        *,
        calc_time: str | None = None,
        elapsed_seconds: float | None = None,
        kernel_seconds: float | None = None,
    ) -> None:
        stats = result.get("statistics", {})
        se_stats = result.get("se_statistics") or {}
        stamp = str(calc_time or utc_now())
        conn = self._connection()
        conn.execute(
            "INSERT INTO se_result VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                _bool(result.get("converged")),
                _bool(result.get("observable")),
                int(stats.get("iterations", result.get("iterations", 0))),
                float(stats.get("objective", result.get("objective", 0.0))),
                float(stats.get("max_correction", result.get("max_correction", 0.0))),
                float(stats.get("residual_inf", result.get("residual_inf", 0.0))),
                int(stats.get("rank", 0)),
                int(stats.get("state_count", 0)),
                int(stats.get("measurement_count", 0)),
                int(stats.get("deficiency", 0)),
                int(stats.get("prefiltered_measurement_count", 0)),
                int(stats.get("pseudo_measurement_count", 0)),
                int(stats.get("bad_data_count", 0)),
                int(stats.get("normal_measurement_count", 0)),
                json.dumps(result.get("state", []), ensure_ascii=False),
                json.dumps(result.get("summary", {}), ensure_ascii=False),
            ),
        )
        measurements = result.get("measurements") or []
        conn.executemany(
            "INSERT INTO se_measurement_result(run_id, measurement_idx, measurement_name, device_type, device_name, measurement_type, value, estimated_value, residual, normalized_residual, valid, source, reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    run_id,
                    row.get("idx", 0),
                    row.get("name", ""),
                    row.get("device_type", ""),
                    row.get("device_name", ""),
                    row.get("meas_type", ""),
                    row.get("value"),
                    row.get("estimated_value"),
                    row.get("residual"),
                    row.get("normalized_residual"),
                    _bool(row.get("valid", True)),
                    row.get("source", ""),
                    row.get("reason", ""),
                )
                for row in measurements
            ),
        )

        # 1. 统计表 se_statistics（按 run_id 追加保留历史）
        meas_count = int(se_stats.get("meas_count", stats.get("measurement_count", len(measurements))))
        bad_count = int(se_stats.get("bad_data_count", stats.get("bad_data_count", 0)))
        valid_count = int(se_stats.get("valid_meas_count", max(0, meas_count - int(stats.get("prefiltered_measurement_count", 0)))))
        good_count = int(se_stats.get("good_meas_count", stats.get("normal_measurement_count", max(0, valid_count - bad_count))))
        pass_rate = float(se_stats.get("pass_rate", (good_count / valid_count) if valid_count > 0 else 0.0))
        total_res = float(se_stats.get("total_residual", sum(abs(float(r["residual"])) for r in measurements if isinstance(r.get("residual"), (int, float)))))
        k_sec = float(kernel_seconds if kernel_seconds is not None else result.get("elapsed_seconds", 0.0) or 0.0)
        e_sec = float(elapsed_seconds if elapsed_seconds is not None else k_sec)
        conn.execute(
            """INSERT OR REPLACE INTO se_statistics(
                   run_id, calc_time, elapsed_seconds, kernel_seconds,
                   meas_count, valid_meas_count, good_meas_count, pass_rate,
                   total_residual, residual_inf, objective,
                   bad_data_count, prefiltered_count, pseudo_count,
                   converged, observable, iterations, max_correction,
                   model_source, meas_source
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                stamp,
                e_sec,
                k_sec,
                meas_count,
                valid_count,
                good_count,
                pass_rate,
                total_res,
                float(se_stats.get("residual_inf", stats.get("residual_inf", result.get("residual_inf", 0.0)))),
                float(se_stats.get("objective", stats.get("objective", result.get("objective", 0.0)))),
                bad_count,
                int(se_stats.get("prefiltered_count", stats.get("prefiltered_measurement_count", 0))),
                int(se_stats.get("pseudo_count", stats.get("pseudo_measurement_count", 0))),
                _bool(se_stats.get("converged", result.get("converged"))),
                _bool(se_stats.get("observable", result.get("observable"))),
                int(se_stats.get("iterations", stats.get("iterations", result.get("iterations", 0)))),
                float(se_stats.get("max_correction", stats.get("max_correction", result.get("max_correction", 0.0)))),
                str(se_stats.get("model_source", (result.get("summary") or {}).get("model_input", {}).get("source", ""))),
                str(se_stats.get("meas_source", (result.get("summary") or {}).get("measurement_input", {}).get("source", ""))),
            ),
        )

        # 2. 量测表 se_measurement（原子刷新为最新一次计算全量量测）
        conn.execute("DELETE FROM se_measurement")
        conn.executemany(
            """INSERT INTO se_measurement(
                   meas_id, run_id, calc_time, meas_name, device_type, device_idx, device_name,
                   metric, meas_type, unit, meas_value, se_value, residual, normalized_residual,
                   weight, valid, is_bad, is_good, source, reason
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                (
                    idx_seq,
                    run_id,
                    stamp,
                    str(row.get("name", "")),
                    str(row.get("device_type", "")),
                    row.get("device_idx"),
                    str(row.get("device_name", "")),
                    str(row.get("metric", "")),
                    str(row.get("meas_type", "")),
                    str(row.get("unit", "")),
                    row.get("value"),
                    row.get("estimated_value"),
                    row.get("residual"),
                    row.get("normalized_residual"),
                    row.get("weight"),
                    _bool(row.get("valid", True)),
                    int(row.get("is_bad", str(row.get("source", "")) == "bad_data")),
                    int(row.get("is_good", _bool(row.get("valid", True)) and str(row.get("source", "")) != "bad_data")),
                    str(row.get("source", "")),
                    str(row.get("reason", "")),
                )
                for idx_seq, row in enumerate(measurements, 1)
            ),
        )

        # 3. 坏数据表 se_bad_data（原子刷新为最新一次计算识别出的坏数据，保留已人工确认状态）
        ensure_se_bad_columns(conn)
        prev_acks = {
            (str(r["device_type"]), str(r["device_name"]), str(r["metric"])): (
                str(r["ack_status"] or "unacked"),
                str(r["ack_time"] or ""),
                str(r["ack_note"] or ""),
                r["policy_id"],
            )
            for r in conn.execute(
                "SELECT device_type, device_name, metric, ack_status, ack_time, ack_note, policy_id FROM se_bad_data"
            )
            if str(r["ack_status"] or "unacked") != "unacked"
        }
        bad_rows = result.get("bad_data")
        if bad_rows is None:
            bad_rows = [
                row
                for row in measurements
                if row.get("is_bad") or str(row.get("source", "")).lower() == "bad_data" or not row.get("valid", True)
            ]
        conn.execute("DELETE FROM se_bad_data")
        conn.executemany(
            """INSERT INTO se_bad_data(
                   id, run_id, calc_time, meas_id, meas_name, device_type, device_idx, device_name,
                   metric, meas_type, unit, meas_value, se_value, residual, normalized_residual,
                   weight, reason, ack_status, ack_time, ack_note, policy_id
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                (
                    seq,
                    run_id,
                    stamp,
                    int(row.get("idx", seq)),
                    str(row.get("name", "")),
                    str(row.get("device_type", "")),
                    row.get("device_idx"),
                    str(row.get("device_name", "")),
                    str(row.get("metric", "")),
                    str(row.get("meas_type", "")),
                    str(row.get("unit", "")),
                    row.get("value"),
                    row.get("estimated_value"),
                    row.get("residual"),
                    row.get("normalized_residual"),
                    row.get("weight"),
                    str(row.get("reason") or "bad_data"),
                    *prev_acks.get(
                        (str(row.get("device_type", "")), str(row.get("device_name", "")), str(row.get("metric", ""))),
                        ("unacked", "", "", None),
                    ),
                )
                for seq, row in enumerate(bad_rows, 1)
            ),
        )

        # 3.1 伪量测结果表 se_pseudo_result（原子刷新为最新一次计算伪量测集合）
        store_se_pseudo_results(conn, run_id, stamp, measurements)

        # 3.2 预过滤量测结果表 se_prefilter_result（原子刷新为最新一次计算预过滤集合）
        store_se_prefilter_results(conn, run_id, stamp, measurements)

        # 3.3 可疑遥信表 se_suspect_status 与兼容表 pas_se_susstat
        store_se_suspect_statuses(conn, run_id, stamp, result.get("suspect_statuses") or [])

        # 4. 各类设备表 se_dev_*（按模型设备类原子刷新为最新断面，含 <metric>_meas 与 <metric>_se）
        device_tables = result.get("device_tables") or {}
        for dev_type, metric_map in SE_DEVICE_RESULT_METRICS.items():
            rows_for_dev = device_tables.get(dev_type)
            if rows_for_dev is None:
                continue
            table_name = f"se_dev_{dev_type}"
            metric_cols: list[str] = []
            for metric in metric_map:
                metric_cols.extend((f"{metric}_meas", f"{metric}_se"))
            all_cols = ["idx", "name", "run_id", "calc_time", *metric_cols]
            quoted = ",".join(f"[{col}]" for col in all_cols)
            placeholders = ",".join("?" for _ in all_cols)
            conn.execute(f"DELETE FROM [{table_name}]")
            conn.executemany(
                f"INSERT INTO [{table_name}] ({quoted}) VALUES ({placeholders})",
                (
                    tuple(
                        [
                            int(rec["idx"]),
                            str(rec["name"]),
                            run_id,
                            stamp,
                            *[rec.get(col) for col in metric_cols],
                        ]
                    )
                    for rec in rows_for_dev
                ),
            )

    @synchronized
    def store_lf_result(
        self,
        run_id: int,
        result: dict[str, Any],
        *,
        calc_time: str | None = None,
        elapsed_seconds: float | None = None,
        kernel_seconds: float | None = None,
    ) -> None:
        conn = self._connection()
        stamp = calc_time or utc_now()
        conn.execute(
            "INSERT INTO lf_result VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                _bool(result.get("converged")),
                int(result.get("iterations", 0)),
                float(result.get("norm_f", 0.0)),
                str(result.get("failure_reason", "") or ""),
                result.get("ac_converged"),
                result.get("ac_iterations"),
                result.get("ac_norm_f"),
                result.get("dc_converged"),
                result.get("dc_iterations"),
                result.get("dc_norm_f"),
                json.dumps(result.get("summary", {}), ensure_ascii=False),
            ),
        )
        conn.executemany(
            "INSERT INTO lf_device_result(run_id, domain, device_type, device_key, node_from, node_to, voltage_from, voltage_to, p_from, q_from, p_to, q_to, current_from, current_to, result_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    run_id,
                    row.get("domain", ""),
                    row.get("device_type", ""),
                    row.get("device_key", ""),
                    row.get("node_from"),
                    row.get("node_to"),
                    row.get("voltage_from"),
                    row.get("voltage_to"),
                    row.get("p_from"),
                    row.get("q_from"),
                    row.get("p_to"),
                    row.get("q_to"),
                    row.get("current_from"),
                    row.get("current_to"),
                    json.dumps(row, ensure_ascii=False),
                )
                for row in result.get("devices", [])
            ),
        )

        # 写入在线潮流工程单位结果表与统计表（lf_statistics / lf_bus_result / lf_branch_result / lf_unit_result）
        st = result.get("lf_statistics") or {}
        k_sec = float(kernel_seconds if kernel_seconds is not None else (result.get("performance") or {}).get("solve_seconds", 0.0) or 0.0)
        e_sec = float(elapsed_seconds if elapsed_seconds is not None else k_sec)
        conn.execute(
            """INSERT OR REPLACE INTO lf_statistics(
                   run_id, calc_time, source_se_run_id, mode, elapsed_seconds, kernel_seconds,
                   converged, iterations, norm_f,
                   ac_converged, ac_iterations, ac_norm_f,
                   dc_converged, dc_iterations, dc_norm_f,
                   ac_gen_p, ac_gen_q, ac_load_p, ac_load_q, ac_loss_p,
                   dc_gen_p, dc_load_p, dc_loss_p,
                   total_gen_p, total_load_p, total_loss_p, loss_rate,
                   min_v_pu, max_v_pu, min_v_bus, max_v_bus,
                   max_loading_pct, max_loading_dev,
                   v_violation_count, overload_count, device_count, override_count,
                   u_unit, p_unit, i_unit, failure_reason
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id,
                stamp,
                st.get("source_se_run_id"),
                str(st.get("mode") or "online"),
                e_sec,
                k_sec,
                _bool(st.get("converged", result.get("converged"))),
                int(st.get("iterations", result.get("iterations", 0))),
                float(st.get("norm_f", result.get("norm_f", 0.0))),
                st.get("ac_converged", result.get("ac_converged")),
                st.get("ac_iterations", result.get("ac_iterations")),
                st.get("ac_norm_f", result.get("ac_norm_f")),
                st.get("dc_converged", result.get("dc_converged")),
                st.get("dc_iterations", result.get("dc_iterations")),
                st.get("dc_norm_f", result.get("dc_norm_f")),
                float(st.get("ac_gen_p", 0.0)),
                float(st.get("ac_gen_q", 0.0)),
                float(st.get("ac_load_p", 0.0)),
                float(st.get("ac_load_q", 0.0)),
                float(st.get("ac_loss_p", 0.0)),
                float(st.get("dc_gen_p", 0.0)),
                float(st.get("dc_load_p", 0.0)),
                float(st.get("dc_loss_p", 0.0)),
                float(st.get("total_gen_p", 0.0)),
                float(st.get("total_load_p", 0.0)),
                float(st.get("total_loss_p", 0.0)),
                float(st.get("loss_rate", 0.0)),
                st.get("min_v_pu"),
                st.get("max_v_pu"),
                str(st.get("min_v_bus") or ""),
                str(st.get("max_v_bus") or ""),
                float(st.get("max_loading_pct", 0.0)),
                str(st.get("max_loading_dev") or ""),
                int(st.get("v_violation_count", 0)),
                int(st.get("overload_count", 0)),
                int(st.get("device_count", len(result.get("devices") or ()))),
                int(st.get("override_count", 0)),
                str(st.get("u_unit") or "V"),
                str(st.get("p_unit") or "kW"),
                str(st.get("i_unit") or "A"),
                str(st.get("failure_reason", result.get("failure_reason", "")) or ""),
            ),
        )
        lf_buses = result.get("lf_buses") or ()
        if lf_buses:
            conn.executemany(
                """INSERT INTO lf_bus_result(
                       run_id, domain, device_type, device_idx, device_name,
                       vbase, v_pu, v_eng, angle_deg, v_se, v_diff, v_status
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        run_id,
                        b["domain"],
                        b["device_type"],
                        int(b["device_idx"]),
                        b["device_name"],
                        b.get("vbase"),
                        b.get("v_pu"),
                        b.get("v_eng"),
                        b.get("angle_deg"),
                        b.get("v_se"),
                        b.get("v_diff"),
                        b.get("v_status", "normal"),
                    )
                    for b in lf_buses
                ),
            )
        lf_branches = result.get("lf_branches") or ()
        if lf_branches:
            conn.executemany(
                """INSERT INTO lf_branch_result(
                       run_id, domain, device_type, device_idx, device_name,
                       node_from, node_to, p_from, q_from, i_from, v_from,
                       p_to, q_to, i_to, v_to, p_loss, rated_capacity,
                       loading_pct, overload, p_se, p_diff
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        run_id,
                        b["domain"],
                        b["device_type"],
                        b.get("device_idx"),
                        b["device_name"],
                        b.get("node_from"),
                        b.get("node_to"),
                        b.get("p_from"),
                        b.get("q_from"),
                        b.get("i_from"),
                        b.get("v_from"),
                        b.get("p_to"),
                        b.get("q_to"),
                        b.get("i_to"),
                        b.get("v_to"),
                        b.get("p_loss"),
                        b.get("rated_capacity"),
                        b.get("loading_pct"),
                        int(b.get("overload", 0)),
                        b.get("p_se"),
                        b.get("p_diff"),
                    )
                    for b in lf_branches
                ),
            )
        lf_units = result.get("lf_units") or ()
        if lf_units:
            conn.executemany(
                """INSERT INTO lf_unit_result(
                       run_id, domain, device_type, device_idx, device_name,
                       node_idx, control_type, p_lf, q_lf, v_lf, i_lf,
                       p_se, p_diff, rated_capacity, loading_pct, overload
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        run_id,
                        u["domain"],
                        u["device_type"],
                        u.get("device_idx"),
                        u["device_name"],
                        u.get("node_idx"),
                        u.get("control_type", ""),
                        u.get("p_lf"),
                        u.get("q_lf"),
                        u.get("v_lf"),
                        u.get("i_lf"),
                        u.get("p_se"),
                        u.get("p_diff"),
                        u.get("rated_capacity"),
                        u.get("loading_pct"),
                        int(u.get("overload", 0)),
                    )
                    for u in lf_units
                ),
            )

    @synchronized
    def store_ca_result(
        self,
        run_id: int,
        result: dict[str, Any],
        *,
        calc_time: str | None = None,
        elapsed_seconds: float | None = None,
        kernel_seconds: float | None = None,
    ) -> None:
        conn = self._connection()
        conn.execute(
            "INSERT INTO ca_result VALUES (?, ?, ?, ?, ?, ?)",
            (
                run_id,
                result.get("risk_level", "安全"),
                int(result.get("n0_risk_count", 0)),
                int(result.get("n1_scan_count", 0)),
                int(result.get("n1_risk_count", 0)),
                json.dumps(result.get("summary", {}), ensure_ascii=False),
            ),
        )
        conn.executemany(
            "INSERT INTO ca_risk(run_id, contingency, risk_source, risk_dist, risk_type, risk_value_real, risk_value_text, risk_info, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    run_id,
                    str(row.get("contingency", "N-0")),
                    str(row.get("risk_source", "")),
                    str(row.get("risk_dist", "")),
                    str(row.get("risk_type", "")),
                    row.get("risk_value") if isinstance(row.get("risk_value"), (int, float)) else None,
                    None if isinstance(row.get("risk_value"), (int, float)) else str(row.get("risk_value") or ""),
                    str(row.get("risk_info", "")),
                    utc_now(),
                )
                for row in result.get("risks", [])
            ),
        )
        st = result.get("ca_statistics")
        if isinstance(st, dict):
            stamp = calc_time or utc_now()
            k_sec = float(kernel_seconds if kernel_seconds is not None else (result.get("performance") or {}).get("solve_seconds", 0.0) or 0.0)
            e_sec = float(elapsed_seconds if elapsed_seconds is not None else k_sec)
            conn.execute(
                """INSERT OR REPLACE INTO ca_statistics(
                       run_id, calc_time, source_lf_run_id, source_se_run_id, base_converged,
                       risk_level, security_score, n0_risk_count,
                       n1_total_count, n1_converged_count, n1_diverged_count, n1_risk_count,
                       nk_total_count, nk_risk_count,
                       critical_count, high_count, medium_count, low_count,
                       max_loading_pct, max_loading_dev,
                       min_v_pu, min_v_bus, max_v_pu, max_v_bus,
                       max_load_loss_kw, worst_contingency,
                       elapsed_seconds, kernel_seconds,
                       u_unit, p_unit, i_unit, failure_reason
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    stamp,
                    st.get("source_lf_run_id"),
                    st.get("source_se_run_id"),
                    int(st.get("base_converged", 1)),
                    str(st.get("risk_level") or result.get("risk_level") or "安全"),
                    float(st.get("security_score", 100.0)),
                    int(st.get("n0_risk_count", 0)),
                    int(st.get("n1_total_count", 0)),
                    int(st.get("n1_converged_count", 0)),
                    int(st.get("n1_diverged_count", 0)),
                    int(st.get("n1_risk_count", 0)),
                    int(st.get("nk_total_count", 0)),
                    int(st.get("nk_risk_count", 0)),
                    int(st.get("critical_count", 0)),
                    int(st.get("high_count", 0)),
                    int(st.get("medium_count", 0)),
                    int(st.get("low_count", 0)),
                    float(st.get("max_loading_pct", 0.0)),
                    str(st.get("max_loading_dev") or ""),
                    st.get("min_v_pu"),
                    str(st.get("min_v_bus") or ""),
                    st.get("max_v_pu"),
                    str(st.get("max_v_bus") or ""),
                    float(st.get("max_load_loss_kw", 0.0)),
                    str(st.get("worst_contingency") or ""),
                    e_sec,
                    k_sec,
                    str(st.get("u_unit") or "V"),
                    str(st.get("p_unit") or "kW"),
                    str(st.get("i_unit") or "A"),
                    str(st.get("failure_reason") or ""),
                ),
            )
        conts = result.get("ca_contingencies") or ()
        if conts:
            conn.executemany(
                """INSERT INTO ca_contingency_result(
                       run_id, contingency_name, category, target_desc, converged, iterations,
                       elapsed_ms, load_loss_kw, max_loading_pct, max_loading_dev,
                       min_v_pu, min_v_bus, max_v_pu, max_v_bus, risk_count, severity, failure_reason
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        run_id,
                        str(c.get("contingency_name") or ""),
                        str(c.get("category") or "N-1"),
                        str(c.get("target_desc") or ""),
                        int(c.get("converged", 1)),
                        int(c.get("iterations", 0)),
                        float(c.get("elapsed_ms", 0.0)),
                        float(c.get("load_loss_kw", 0.0)),
                        float(c.get("max_loading_pct", 0.0)),
                        str(c.get("max_loading_dev") or ""),
                        c.get("min_v_pu"),
                        str(c.get("min_v_bus") or ""),
                        c.get("max_v_pu"),
                        str(c.get("max_v_bus") or ""),
                        int(c.get("risk_count", 0)),
                        str(c.get("severity") or "normal"),
                        str(c.get("failure_reason") or ""),
                    )
                    for c in conts
                ),
            )
        details = result.get("ca_risk_details") or ()
        if details:
            conn.executemany(
                """INSERT INTO ca_risk_detail(
                       run_id, contingency_name, category, device_type, device_idx, device_name,
                       risk_category, severity, metric, actual_value, limit_value, violation_pct, unit, detail
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    (
                        run_id,
                        str(d.get("contingency_name") or "N-0 基态"),
                        str(d.get("category") or "N-0"),
                        str(d.get("device_type") or ""),
                        d.get("device_idx"),
                        str(d.get("device_name") or ""),
                        str(d.get("risk_category") or "overload"),
                        str(d.get("severity") or "medium"),
                        str(d.get("metric") or ""),
                        d.get("actual_value"),
                        d.get("limit_value"),
                        float(d.get("violation_pct", 0.0)),
                        str(d.get("unit") or ""),
                        str(d.get("detail") or ""),
                    )
                    for d in details
                ),
            )

    @synchronized
    def store_result(
        self,
        task_type: str,
        run_id: int,
        result: dict[str, Any],
        *,
        calc_time: str | None = None,
        elapsed_seconds: float | None = None,
        kernel_seconds: float | None = None,
    ) -> None:
        if task_type == "se":
            self.store_se_result(
                run_id,
                result,
                calc_time=calc_time,
                elapsed_seconds=elapsed_seconds,
                kernel_seconds=kernel_seconds,
            )
        elif task_type == "lf":
            self.store_lf_result(
                run_id,
                result,
                calc_time=calc_time,
                elapsed_seconds=elapsed_seconds,
                kernel_seconds=kernel_seconds,
            )
        elif task_type == "ca":
            self.store_ca_result(
                run_id,
                result,
                calc_time=calc_time,
                elapsed_seconds=elapsed_seconds,
                kernel_seconds=kernel_seconds,
            )
        else:
            raise ValueError(f"unsupported task type: {task_type}")

    # ======================== 在线潮流分析 (LF) 查询与管理接口 ========================

    @synchronized
    def lf_params_get(self, para_file: str | Path | None = None, *, do_cycle: int | float = 60) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = ensure_lf_params(conn, para_file, do_cycle=do_cycle)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def lf_params_save(self, payload: dict[str, Any], para_file: str | Path | None = None) -> dict[str, Any]:
        conn = self._connection()
        res = save_lf_params(conn, payload, para_file)
        conn.commit()
        return res

    @synchronized
    def lf_params_reset(self, para_file: str | Path | None = None) -> dict[str, Any]:
        conn = self._connection()
        res = reset_lf_params(conn, para_file)
        conn.commit()
        return res

    @synchronized
    def lf_overrides_list(self, *, scheme_name: str = "", enabled_only: bool = False, device_type: str = "", q: str = "") -> list[dict[str, Any]]:
        return list_lf_overrides(self._connection(), scheme_name=scheme_name, enabled_only=enabled_only, device_type=device_type, q=q)

    @synchronized
    def lf_override_save(self, payload: dict[str, Any], *, override_id: int | None = None) -> dict[str, Any]:
        conn = self._connection()
        res = save_lf_override(conn, payload, override_id=override_id)
        conn.commit()
        return res

    @synchronized
    def lf_override_delete(self, override_id: int) -> bool:
        conn = self._connection()
        ok = delete_lf_override(conn, override_id)
        conn.commit()
        return ok

    @synchronized
    def lf_overrides_clear(self, *, scheme_name: str = "") -> int:
        conn = self._connection()
        cnt = clear_lf_overrides(conn, scheme_name=scheme_name)
        conn.commit()
        return cnt

    @synchronized
    def record_lf_run_log(
        self,
        *,
        level: str = "INFO",
        stage: str = "system",
        message: str = "",
        run_id: int | None = None,
        source: str = "system",
        elapsed_ms: float | None = None,
        detail: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> int | None:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        lid = record_lf_log(
            conn,
            level=level,
            stage=stage,
            message=message,
            run_id=run_id,
            source=source,
            elapsed_ms=elapsed_ms,
            detail=detail,
        )
        if commit and not was_in_tx:
            conn.commit()
        return lid

    @synchronized
    def lf_logs_list(self, **kwargs) -> dict[str, Any]:
        return list_lf_logs(self._connection(), **kwargs)

    @synchronized
    def lf_logs_summary(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = lf_log_summary(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def lf_logs_policy_get(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = ensure_lf_log_policy(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def lf_logs_policy_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self._connection()
        res = update_lf_log_policy(conn, payload)
        conn.commit()
        return res

    @synchronized
    def lf_logs_purge(self, **kwargs) -> dict[str, Any]:
        conn = self._connection()
        res = purge_lf_logs(conn, **kwargs)
        conn.commit()
        return res

    @synchronized
    def lf_logs_export_csv(self, **kwargs) -> str:
        return export_lf_logs_csv(self._connection(), **kwargs)

    @synchronized
    def lf_converged_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        return self._rows(
            """SELECT run_id, calc_time, source_se_run_id, mode, converged, iterations,
                      total_gen_p, total_load_p, total_loss_p, loss_rate,
                      min_v_pu, max_v_pu, max_loading_pct,
                      v_violation_count, overload_count, elapsed_seconds, p_unit
               FROM lf_statistics
               ORDER BY run_id DESC LIMIT ?""",
            (limit,),
        )

    @synchronized
    def lf_history_stats(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        rows = self._rows(
            """SELECT run_id, calc_time, source_se_run_id, mode, converged, iterations,
                      norm_f, total_gen_p, total_load_p, total_loss_p, loss_rate,
                      min_v_pu, max_v_pu, max_loading_pct, v_violation_count, overload_count,
                      elapsed_seconds, kernel_seconds, p_unit
               FROM lf_statistics
               ORDER BY run_id DESC LIMIT ?""",
            (limit,),
        )
        rows.reverse()
        return rows

    @synchronized
    def lf_snapshot(self, run_id: int | None = None) -> dict[str, Any]:
        """单次锁内读取指定或最新 LF 运行的统计、节点、支路与电源负荷完整快照。"""
        if run_id is None:
            srows = self._rows("SELECT * FROM lf_statistics ORDER BY run_id DESC LIMIT 1")
            stat = srows[0] if srows else None
            rid = int(stat["run_id"]) if stat else None
        else:
            rid = int(run_id)
            srows = self._rows("SELECT * FROM lf_statistics WHERE run_id = ? LIMIT 1", (rid,))
            stat = srows[0] if srows else None
        if rid is None:
            return {"latest": None, "run_id": None, "buses": [], "branches": [], "units": []}
        buses = self._rows("SELECT * FROM lf_bus_result WHERE run_id = ? ORDER BY domain, device_idx", (rid,))
        branches = self._rows("SELECT * FROM lf_branch_result WHERE run_id = ? ORDER BY COALESCE(loading_pct, -1) DESC, device_type, device_idx", (rid,))
        units = self._rows("SELECT * FROM lf_unit_result WHERE run_id = ? ORDER BY device_type, device_idx", (rid,))
        return {"latest": stat, "run_id": rid, "buses": buses, "branches": branches, "units": units}

    @synchronized
    def lf_home_summary(self, para_file: str | Path | None = None, do_cycle: int | float = 60) -> dict[str, Any]:
        """聚合 LF 三栏主画面数据：统计、网损与极值、24h 趋势曲线、重载/越限排行、方式调整计数与最新日志。"""
        conn = self._connection()
        was_in_tx = conn.in_transaction
        snap = self.lf_snapshot()
        latest = snap["latest"]
        params = ensure_lf_params(conn, para_file, do_cycle=do_cycle)
        sched_rows = self._rows("SELECT * FROM schedule WHERE task_type = 'lf' LIMIT 1")
        schedule = sched_rows[0] if sched_rows else None
        ov_counts = conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(enabled = 1), 0) AS enabled FROM lf_study_override"
        ).fetchone()
        recent_runs = self._rows(
            """SELECT r.run_id, r.status, r.started_at, r.elapsed_seconds, r.execution_source,
                      s.converged, s.iterations, s.source_se_run_id, s.total_gen_p, s.total_load_p,
                      s.total_loss_p, s.loss_rate, s.v_violation_count, s.overload_count
               FROM calculation_run r
               LEFT JOIN lf_statistics s ON s.run_id = r.run_id
               WHERE r.task_type = 'lf'
               ORDER BY r.run_id DESC LIMIT 30"""
        )
        # 24h 网损率与负载率曲线（最多 120 点）
        series = self._rows(
            """SELECT run_id, calc_time, converged, loss_rate, max_loading_pct,
                      total_gen_p, total_load_p, total_loss_p, min_v_pu, max_v_pu
               FROM lf_statistics
               ORDER BY run_id DESC LIMIT 120"""
        )
        series.reverse()
        top_loading = [b for b in snap["branches"] if b.get("loading_pct") is not None][:8]
        v_alerts = [b for b in snap["buses"] if b.get("v_status") != "normal"][:8]
        if not v_alerts:
            v_alerts = sorted(
                [b for b in snap["buses"] if b.get("v_pu") is not None],
                key=lambda x: abs(float(x["v_pu"]) - 1.0),
                reverse=True,
            )[:8]
        log_rows = self._rows("SELECT * FROM lf_run_log ORDER BY log_id DESC LIMIT 1")
        latest_log = log_rows[0] if log_rows else None
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return {
            "latest": latest,
            "params": params,
            "schedule": schedule,
            "overrides": {"total": int(ov_counts["total"] or 0), "enabled": int(ov_counts["enabled"] or 0)},
            "recent_runs": recent_runs,
            "trend_series": series,
            "top_loading": top_loading,
            "voltage_extremes": v_alerts,
            "latest_log": latest_log,
        }

    @synchronized
    def lf_results_browse(
        self,
        *,
        kind: str = "branches",
        domain: str = "all",
        device_type: str = "",
        only_abnormal: bool = False,
        q: str = "",
        run_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """分页浏览指定或最新 LF 断面的节点/支路/电源负荷结果。"""
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        snap = self.lf_snapshot(run_id=run_id)
        latest = snap["latest"]
        rid = snap["run_id"]
        if kind == "buses":
            rows = list(snap["buses"])
        elif kind == "units":
            rows = list(snap["units"])
        else:
            kind = "branches"
            rows = list(snap["branches"])

        search = str(q or "").strip().casefold()
        filtered = []
        for r in rows:
            if domain and domain != "all" and str(r.get("domain") or "").upper() != domain.upper():
                continue
            if device_type and str(r.get("device_type") or "") != device_type:
                continue
            if only_abnormal:
                if kind == "buses":
                    if r.get("v_status") == "normal":
                        continue
                else:
                    if not r.get("overload") and (r.get("loading_pct") is None or float(r["loading_pct"]) < 80.0):
                        continue
            if search and search not in f"{r.get('device_idx','')} {r.get('device_name','')} {r.get('device_type','')}".casefold():
                continue
            filtered.append(r)

        avail_types = sorted({str(r.get("device_type") or "") for r in rows if r.get("device_type")})
        return {
            "kind": kind,
            "run_id": rid,
            "latest": latest,
            "available_types": avail_types,
            "rows": filtered[offset : offset + limit],
            "meta": {"total": len(filtered), "limit": limit, "offset": offset, "run_id": rid},
        }

    @synchronized
    def lf_results_export_csv(
        self,
        *,
        kind: str = "branches",
        domain: str = "all",
        device_type: str = "",
        only_abnormal: bool = False,
        q: str = "",
        run_id: int | None = None,
    ) -> bytes:
        page = self.lf_results_browse(
            kind=kind,
            domain=domain,
            device_type=device_type,
            only_abnormal=only_abnormal,
            q=q,
            run_id=run_id,
            limit=10000,
            offset=0,
        )
        rows = page["rows"]
        buf = io.StringIO()
        w = csv.writer(buf)
        if kind == "buses":
            cols = ["device_idx", "domain", "device_name", "vbase", "v_pu", "v_eng", "angle_deg", "v_se", "v_diff", "v_status"]
        elif kind == "units":
            cols = ["device_idx", "domain", "device_type", "device_name", "control_type", "p_lf", "q_lf", "v_lf", "i_lf", "p_se", "p_diff", "rated_capacity", "loading_pct", "overload"]
        else:
            cols = ["device_idx", "domain", "device_type", "device_name", "p_from", "q_from", "i_from", "p_to", "q_to", "i_to", "p_loss", "rated_capacity", "loading_pct", "overload", "p_se", "p_diff"]
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c) for c in cols])
        return ("\ufeff" + buf.getvalue()).encode("utf-8")

    # ======================== 在线静态安全分析 (CA) 查询与管理接口 ========================

    @synchronized
    def ca_params_get(self, *, do_cycle: int | float = 300) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = ensure_ca_params(conn, do_cycle=do_cycle)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def ca_params_save(self, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self._connection()
        res = save_ca_params(conn, payload)
        conn.commit()
        return res

    @synchronized
    def ca_params_reset(self) -> dict[str, Any]:
        conn = self._connection()
        res = reset_ca_params(conn)
        conn.commit()
        return res

    @synchronized
    def ca_contingencies_list(self, *, category: str = "", enabled_only: bool = False, device_type: str = "", q: str = "") -> list[dict[str, Any]]:
        return list_ca_contingencies(self._connection(), category=category, enabled_only=enabled_only, device_type=device_type, q=q)

    @synchronized
    def ca_contingency_save(self, payload: dict[str, Any], *, contingency_id: int | None = None) -> dict[str, Any]:
        conn = self._connection()
        res = save_ca_contingency(conn, payload, contingency_id=contingency_id)
        conn.commit()
        return res

    @synchronized
    def ca_contingency_delete(self, contingency_id: int) -> bool:
        conn = self._connection()
        ok = delete_ca_contingency(conn, contingency_id)
        conn.commit()
        return ok

    @synchronized
    def ca_contingencies_clear(self, *, only_auto: bool = False) -> int:
        conn = self._connection()
        cnt = clear_ca_contingencies(conn, only_auto=only_auto)
        conn.commit()
        return cnt

    @synchronized
    def ca_contingencies_sync(self, model_tables: dict[str, dict[str, Any]], *, device_types: list[str] | None = None, overwrite: bool = False) -> dict[str, Any]:
        conn = self._connection()
        res = sync_ca_contingencies_from_model(conn, model_tables, device_types=device_types, overwrite=overwrite)
        conn.commit()
        return res

    @synchronized
    def ca_contingencies_bulk_toggle(self, *, enabled: bool, category: str = "", device_type: str = "") -> int:
        conn = self._connection()
        cnt = bulk_toggle_ca_contingencies(conn, enabled=enabled, category=category, device_type=device_type)
        conn.commit()
        return cnt

    @synchronized
    def ca_device_limits_map(self) -> dict[tuple[str, str, str], dict[str, Any]]:
        """从 ca_limit 表读取启用的设备级限值，返回 {(device_type, device_name, metric): row}。"""
        conn = self._connection()
        tbl = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ca_limit'").fetchone()
        if not tbl:
            return {}
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(ca_limit)")}
        if {"model_table", "device_name", "field"} <= cols:
            rows = conn.execute(
                "SELECT model_table AS device_type, device_name, field AS metric, lower_value AS min_value, upper_value AS max_value, unit FROM ca_limit WHERE enabled = 1"
            ).fetchall()
        elif {"device_type", "device_name", "metric"} <= cols:
            rows = conn.execute(
                "SELECT device_type, device_name, metric, min_value, max_value, unit FROM ca_limit WHERE enabled = 1"
            ).fetchall()
        else:
            return {}
        out: dict[tuple[str, str, str], dict[str, Any]] = {}
        for r in rows:
            out[(str(r["device_type"]), str(r["device_name"]), str(r["metric"]))] = dict(r)
        return out

    @synchronized
    def record_ca_run_log(
        self,
        *,
        level: str = "INFO",
        stage: str = "system",
        message: str = "",
        run_id: int | None = None,
        source: str = "system",
        elapsed_ms: float | None = None,
        detail: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> int | None:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        lid = record_ca_log(
            conn,
            level=level,
            stage=stage,
            message=message,
            run_id=run_id,
            source=source,
            elapsed_ms=elapsed_ms,
            detail=detail,
        )
        if commit and not was_in_tx:
            conn.commit()
        return lid

    @synchronized
    def ca_logs_list(self, **kwargs) -> dict[str, Any]:
        return list_ca_logs(self._connection(), **kwargs)

    @synchronized
    def ca_logs_summary(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = ca_log_summary(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def ca_logs_policy_get(self) -> dict[str, Any]:
        conn = self._connection()
        was_in_tx = conn.in_transaction
        res = ensure_ca_log_policy(conn)
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return res

    @synchronized
    def ca_logs_policy_update(self, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self._connection()
        res = update_ca_log_policy(conn, payload)
        conn.commit()
        return res

    @synchronized
    def ca_logs_purge(self, **kwargs) -> dict[str, Any]:
        conn = self._connection()
        res = purge_ca_logs(conn, **kwargs)
        conn.commit()
        return res

    @synchronized
    def ca_logs_export_csv(self, **kwargs) -> str:
        return export_ca_logs_csv(self._connection(), **kwargs)

    @synchronized
    def ca_runs_history(self, limit: int = 30) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 200))
        return self._rows(
            """SELECT run_id, calc_time, source_lf_run_id, source_se_run_id, base_converged,
                      risk_level, security_score, n0_risk_count, n1_total_count, n1_risk_count,
                      nk_total_count, nk_risk_count, critical_count, high_count, medium_count, low_count,
                      worst_contingency, elapsed_seconds
               FROM ca_statistics
               ORDER BY run_id DESC LIMIT ?""",
            (limit,),
        )

    @synchronized
    def ca_history_stats(self, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        rows = self._rows(
            """SELECT run_id, calc_time, source_lf_run_id, source_se_run_id, risk_level, security_score,
                      n0_risk_count, n1_total_count, n1_risk_count, nk_total_count, nk_risk_count,
                      critical_count, high_count, medium_count, low_count,
                      max_loading_pct, min_v_pu, max_load_loss_kw, elapsed_seconds
               FROM ca_statistics
               ORDER BY run_id DESC LIMIT ?""",
            (limit,),
        )
        rows.reverse()
        return rows

    @synchronized
    def ca_snapshot(self, run_id: int | None = None) -> dict[str, Any]:
        """读取最新或指定历史 run_id 的 CA 完整断面（统计、故障扫描结果、结构化风险）。"""
        if run_id is not None:
            stats = self._rows("SELECT * FROM ca_statistics WHERE run_id = ? LIMIT 1", (int(run_id),))
        else:
            stats = self._rows("SELECT * FROM ca_statistics ORDER BY run_id DESC LIMIT 1")
        if not stats:
            return {"latest": None, "run_id": None, "contingencies": [], "risks": []}
        latest = stats[0]
        rid = int(latest["run_id"])
        conts = self._rows(
            """SELECT * FROM ca_contingency_result WHERE run_id = ?
               ORDER BY CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
                        risk_count DESC, load_loss_kw DESC, max_loading_pct DESC""",
            (rid,),
        )
        risks = self._rows(
            """SELECT * FROM ca_risk_detail WHERE run_id = ?
               ORDER BY CASE severity WHEN 'critical' THEN 4 WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
                        violation_pct DESC, id ASC""",
            (rid,),
        )
        return {"latest": latest, "run_id": rid, "contingencies": conts, "risks": risks}

    @synchronized
    def ca_home_summary(self, *, do_cycle: int | float = 300) -> dict[str, Any]:
        """聚合 CA 三栏主画面数据：安全评分与风险统计、LF/SE 溯源、趋势曲线、最严重风险与故障排行。"""
        conn = self._connection()
        was_in_tx = conn.in_transaction
        snap = self.ca_snapshot()
        latest = snap["latest"]
        params = ensure_ca_params(conn, do_cycle=do_cycle)
        sched_rows = self._rows("SELECT * FROM schedule WHERE task_type = 'ca' LIMIT 1")
        schedule = sched_rows[0] if sched_rows else None
        def_counts = conn.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(enabled = 1), 0) AS enabled, COALESCE(SUM(category = 'N-1'), 0) AS n1, COALESCE(SUM(category = 'N-k'), 0) AS nk FROM ca_contingency_def"
        ).fetchone()
        recent_runs = self._rows(
            """SELECT r.run_id, r.status, r.started_at, r.elapsed_seconds, r.execution_source,
                      s.risk_level, s.security_score, s.source_lf_run_id, s.source_se_run_id,
                      s.n0_risk_count, s.n1_total_count, s.n1_risk_count, s.critical_count, s.high_count
               FROM calculation_run r
               LEFT JOIN ca_statistics s ON s.run_id = r.run_id
               WHERE r.task_type = 'ca'
               ORDER BY r.run_id DESC LIMIT 30"""
        )
        trend = self._rows(
            """SELECT run_id, calc_time, security_score, risk_level,
                      n0_risk_count, n1_risk_count, nk_risk_count,
                      critical_count, high_count, max_loading_pct, max_load_loss_kw
               FROM ca_statistics ORDER BY run_id DESC LIMIT 120"""
        )
        trend.reverse()
        top_risks = snap["risks"][:10]
        top_contingencies = snap["contingencies"][:10]
        log_rows = self._rows("SELECT * FROM ca_run_log ORDER BY log_id DESC LIMIT 1")
        latest_log = log_rows[0] if log_rows else None
        if not was_in_tx and conn.in_transaction:
            conn.commit()
        return {
            "latest": latest,
            "params": params,
            "schedule": schedule,
            "contingency_defs": {
                "total": int(def_counts["total"] or 0),
                "enabled": int(def_counts["enabled"] or 0),
                "n1": int(def_counts["n1"] or 0),
                "nk": int(def_counts["nk"] or 0),
            },
            "recent_runs": recent_runs,
            "trend_series": trend,
            "top_risks": top_risks,
            "top_contingencies": top_contingencies,
            "latest_log": latest_log,
        }

    @synchronized
    def ca_risks_browse(
        self,
        *,
        category: str = "all",
        severity: str = "all",
        risk_category: str = "all",
        q: str = "",
        run_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        snap = self.ca_snapshot(run_id=run_id)
        rows = list(snap["risks"])
        search = str(q or "").strip().casefold()
        filtered = []
        for r in rows:
            if category and category != "all" and str(r.get("category") or "") != category:
                continue
            if severity and severity != "all" and str(r.get("severity") or "") != severity:
                continue
            if risk_category and risk_category != "all" and str(r.get("risk_category") or "") != risk_category:
                continue
            if search:
                hay = f"{r.get('contingency_name','')} {r.get('device_type','')} {r.get('device_name','')} {r.get('detail','')}".casefold()
                if search not in hay:
                    continue
            filtered.append(r)
        return {
            "run_id": snap["run_id"],
            "latest": snap["latest"],
            "rows": filtered[offset : offset + limit],
            "meta": {"total": len(filtered), "limit": limit, "offset": offset, "run_id": snap["run_id"]},
        }

    @synchronized
    def ca_contingency_results_browse(
        self,
        *,
        category: str = "all",
        severity: str = "all",
        only_risk: bool = False,
        q: str = "",
        run_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        snap = self.ca_snapshot(run_id=run_id)
        rows = list(snap["contingencies"])
        search = str(q or "").strip().casefold()
        filtered = []
        for r in rows:
            if category and category != "all" and str(r.get("category") or "") != category:
                continue
            if severity and severity != "all" and str(r.get("severity") or "") != severity:
                continue
            if only_risk and int(r.get("risk_count") or 0) == 0 and int(r.get("converged", 1)) == 1:
                continue
            if search:
                hay = f"{r.get('contingency_name','')} {r.get('target_desc','')} {r.get('max_loading_dev','')} {r.get('min_v_bus','')}".casefold()
                if search not in hay:
                    continue
            filtered.append(r)
        return {
            "run_id": snap["run_id"],
            "latest": snap["latest"],
            "rows": filtered[offset : offset + limit],
            "meta": {"total": len(filtered), "limit": limit, "offset": offset, "run_id": snap["run_id"]},
        }

    @synchronized
    def ca_risks_export_csv(self, **kwargs) -> bytes:
        page = self.ca_risks_browse(**{**kwargs, "limit": 10000, "offset": 0})
        buf = io.StringIO()
        w = csv.writer(buf)
        cols = ["category", "contingency_name", "severity", "risk_category", "device_type", "device_name", "metric", "actual_value", "limit_value", "violation_pct", "unit", "detail"]
        w.writerow(cols)
        for r in page["rows"]:
            w.writerow([r.get(c) for c in cols])
        return ("\ufeff" + buf.getvalue()).encode("utf-8")

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

    def health(self, *, lite: bool = False) -> dict[str, Any]:
        databases = {}
        if self.control is not None:
            databases["pas"] = self.control.health(lite=lite)
        databases.update({name: repository.health(lite=lite) for name, repository in self.repositories.items()})
        return databases

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

    def sync_se_parameters(self, para_file=None, *, do_cycle=60, calc_trigger=1, overwrite=False):
        return self.for_task("se").sync_se_parameters(para_file, do_cycle=do_cycle, calc_trigger=calc_trigger, overwrite=overwrite)

    def get_se_parameters(self, para_file=None, *, do_cycle=60):
        return self.for_task("se").get_se_parameters(para_file, do_cycle=do_cycle)

    def update_se_parameters(self, payload, *, para_file=None, do_cycle=60):
        return self.for_task("se").update_se_parameters(payload, para_file=para_file, do_cycle=do_cycle)

    def se_overview(self, para_file=None, do_cycle=60):
        return self.for_task("se").se_overview(para_file, do_cycle)

    def se_topology_snapshot(self):
        return self.for_task("se").se_topology_snapshot()

    def se_converged_runs(self, limit=30):
        return self.for_task("se").se_converged_runs(limit)

    def se_run_measurements_raw(self, run_id):
        return self.for_task("se").se_run_measurements_raw(run_id)

    def se_bad_policy_batch_save(self, items, **kwargs):
        return self.for_task("se").se_bad_policy_batch_save(items, **kwargs)

    def se_prefilter_rule_batch_save(self, items):
        return self.for_task("se").se_prefilter_rule_batch_save(items)

    def se_weight_rules(self, **kwargs):
        return self.for_task("se").se_weight_rules(**kwargs)

    def se_weight_rule_save(self, payload, **kwargs):
        return self.for_task("se").se_weight_rule_save(payload, **kwargs)

    def se_weight_rule_delete(self, rule_id):
        return self.for_task("se").se_weight_rule_delete(rule_id)

    def se_home_summary(self, para_file=None, do_cycle=60):
        return self.for_task("se").se_home_summary(para_file, do_cycle)

    def se_devices(self, device_type=None, *, q="", bad_only=False, run_id=None):
        return self.for_task("se").se_devices(device_type, q=q, bad_only=bad_only, run_id=run_id)

    def se_measurements_browse(self, **kwargs):
        return self.for_task("se").se_measurements_browse(**kwargs)

    def se_measurements_export_csv(self, **kwargs):
        return self.for_task("se").se_measurements_export_csv(**kwargs)

    def se_history_stats(self, limit=100):
        return self.for_task("se").se_history_stats(limit)

    def se_history_points(self):
        return self.for_task("se").se_history_points()

    def se_history_point_series(self, device_type, device_name, meas_type, limit=100):
        return self.for_task("se").se_history_point_series(device_type, device_name, meas_type, limit)

    def se_history_bad_data(self, limit=100):
        return self.for_task("se").se_history_bad_data(limit)

    def se_pseudo_overview(self):
        return self.for_task("se").se_pseudo_overview()

    def se_pseudo_meas_list(self, **kwargs):
        return self.for_task("se").se_pseudo_meas_list(**kwargs)

    def se_pseudo_meas_save(self, payload, **kwargs):
        return self.for_task("se").se_pseudo_meas_save(payload, **kwargs)

    def se_pseudo_meas_delete(self, define_id):
        return self.for_task("se").se_pseudo_meas_delete(define_id)

    def se_pseudo_stat_list(self, **kwargs):
        return self.for_task("se").se_pseudo_stat_list(**kwargs)

    def se_pseudo_stat_save(self, payload, **kwargs):
        return self.for_task("se").se_pseudo_stat_save(payload, **kwargs)

    def se_pseudo_stat_delete(self, define_id):
        return self.for_task("se").se_pseudo_stat_delete(define_id)

    def se_pseudo_results(self, **kwargs):
        return self.for_task("se").se_pseudo_results(**kwargs)

    def se_bad_overview(self):
        return self.for_task("se").se_bad_overview()

    def se_bad_current(self, **kwargs):
        return self.for_task("se").se_bad_current(**kwargs)

    def se_bad_ack(self, bad_id, **kwargs):
        return self.for_task("se").se_bad_ack(bad_id, **kwargs)

    def se_bad_policies(self, **kwargs):
        return self.for_task("se").se_bad_policies(**kwargs)

    def se_bad_policy_save(self, payload, **kwargs):
        return self.for_task("se").se_bad_policy_save(payload, **kwargs)

    def se_bad_policy_delete(self, policy_id):
        return self.for_task("se").se_bad_policy_delete(policy_id)

    def se_bad_convert_pseudo(self, **kwargs):
        return self.for_task("se").se_bad_convert_pseudo(**kwargs)

    def se_bad_abnormal(self, **kwargs):
        return self.for_task("se").se_bad_abnormal(**kwargs)

    def se_prefilter_overview(self):
        return self.for_task("se").se_prefilter_overview()

    def se_prefilter_results(self, **kwargs):
        return self.for_task("se").se_prefilter_results(**kwargs)

    def se_prefilter_rules(self, **kwargs):
        return self.for_task("se").se_prefilter_rules(**kwargs)

    def se_prefilter_rule_save(self, payload, **kwargs):
        return self.for_task("se").se_prefilter_rule_save(payload, **kwargs)

    def se_prefilter_rule_delete(self, rule_id):
        return self.for_task("se").se_prefilter_rule_delete(rule_id)

    def se_prefilter_analysis(self, **kwargs):
        return self.for_task("se").se_prefilter_analysis(**kwargs)

    def record_se_run_log(self, **kwargs):
        return self.for_task("se").record_se_run_log(**kwargs)

    def se_logs_list(self, **kwargs):
        return self.for_task("se").se_logs_list(**kwargs)

    def se_logs_summary(self):
        return self.for_task("se").se_logs_summary()

    def se_logs_policy_get(self):
        return self.for_task("se").se_logs_policy_get()

    def se_logs_policy_update(self, payload):
        return self.for_task("se").se_logs_policy_update(payload)

    def se_logs_purge(self, **kwargs):
        return self.for_task("se").se_logs_purge(**kwargs)

    def se_logs_maybe_auto_purge(self):
        return self.for_task("se").se_logs_maybe_auto_purge()

    def se_logs_export_csv(self, **kwargs):
        return self.for_task("se").se_logs_export_csv(**kwargs)

    # --- LF 代理方法 ---
    def lf_params_get(self, para_file=None, *, do_cycle=60):
        return self.for_task("lf").lf_params_get(para_file, do_cycle=do_cycle)

    def lf_params_save(self, payload, para_file=None):
        return self.for_task("lf").lf_params_save(payload, para_file)

    def lf_params_reset(self, para_file=None):
        return self.for_task("lf").lf_params_reset(para_file)

    def lf_overrides_list(self, **kwargs):
        return self.for_task("lf").lf_overrides_list(**kwargs)

    def lf_override_save(self, payload, **kwargs):
        return self.for_task("lf").lf_override_save(payload, **kwargs)

    def lf_override_delete(self, override_id):
        return self.for_task("lf").lf_override_delete(override_id)

    def lf_overrides_clear(self, **kwargs):
        return self.for_task("lf").lf_overrides_clear(**kwargs)

    def record_lf_run_log(self, **kwargs):
        return self.for_task("lf").record_lf_run_log(**kwargs)

    def lf_logs_list(self, **kwargs):
        return self.for_task("lf").lf_logs_list(**kwargs)

    def lf_logs_summary(self):
        return self.for_task("lf").lf_logs_summary()

    def lf_logs_policy_get(self):
        return self.for_task("lf").lf_logs_policy_get()

    def lf_logs_policy_update(self, payload):
        return self.for_task("lf").lf_logs_policy_update(payload)

    def lf_logs_purge(self, **kwargs):
        return self.for_task("lf").lf_logs_purge(**kwargs)

    def lf_logs_export_csv(self, **kwargs):
        return self.for_task("lf").lf_logs_export_csv(**kwargs)

    def lf_converged_runs(self, limit=30):
        return self.for_task("lf").lf_converged_runs(limit)

    def lf_history_stats(self, limit=100):
        return self.for_task("lf").lf_history_stats(limit)

    def lf_snapshot(self, run_id=None):
        return self.for_task("lf").lf_snapshot(run_id)

    def lf_home_summary(self, para_file=None, do_cycle=60):
        return self.for_task("lf").lf_home_summary(para_file, do_cycle)

    def lf_results_browse(self, **kwargs):
        return self.for_task("lf").lf_results_browse(**kwargs)

    def lf_results_export_csv(self, **kwargs):
        return self.for_task("lf").lf_results_export_csv(**kwargs)

    def ca_params_get(self, *, do_cycle=300):
        return self.for_task("ca").ca_params_get(do_cycle=do_cycle)

    def ca_params_save(self, payload):
        return self.for_task("ca").ca_params_save(payload)

    def ca_params_reset(self):
        return self.for_task("ca").ca_params_reset()

    def ca_contingencies_list(self, **kwargs):
        return self.for_task("ca").ca_contingencies_list(**kwargs)

    def ca_contingency_save(self, payload, **kwargs):
        return self.for_task("ca").ca_contingency_save(payload, **kwargs)

    def ca_contingency_delete(self, contingency_id):
        return self.for_task("ca").ca_contingency_delete(contingency_id)

    def ca_contingencies_clear(self, **kwargs):
        return self.for_task("ca").ca_contingencies_clear(**kwargs)

    def ca_contingencies_sync(self, model_tables, **kwargs):
        return self.for_task("ca").ca_contingencies_sync(model_tables, **kwargs)

    def ca_contingencies_bulk_toggle(self, **kwargs):
        return self.for_task("ca").ca_contingencies_bulk_toggle(**kwargs)

    def ca_device_limits_map(self):
        return self.for_task("ca").ca_device_limits_map()

    def record_ca_run_log(self, **kwargs):
        return self.for_task("ca").record_ca_run_log(**kwargs)

    def ca_logs_list(self, **kwargs):
        return self.for_task("ca").ca_logs_list(**kwargs)

    def ca_logs_summary(self):
        return self.for_task("ca").ca_logs_summary()

    def ca_logs_policy_get(self):
        return self.for_task("ca").ca_logs_policy_get()

    def ca_logs_policy_update(self, payload):
        return self.for_task("ca").ca_logs_policy_update(payload)

    def ca_logs_purge(self, **kwargs):
        return self.for_task("ca").ca_logs_purge(**kwargs)

    def ca_logs_export_csv(self, **kwargs):
        return self.for_task("ca").ca_logs_export_csv(**kwargs)

    def ca_runs_history(self, limit=30):
        return self.for_task("ca").ca_runs_history(limit)

    def ca_history_stats(self, limit=100):
        return self.for_task("ca").ca_history_stats(limit)

    def ca_snapshot(self, run_id=None):
        return self.for_task("ca").ca_snapshot(run_id)

    def ca_home_summary(self, *, do_cycle=300):
        return self.for_task("ca").ca_home_summary(do_cycle=do_cycle)

    def ca_risks_browse(self, **kwargs):
        return self.for_task("ca").ca_risks_browse(**kwargs)

    def ca_contingency_results_browse(self, **kwargs):
        return self.for_task("ca").ca_contingency_results_browse(**kwargs)

    def ca_risks_export_csv(self, **kwargs):
        return self.for_task("ca").ca_risks_export_csv(**kwargs)

    def close(self) -> None:
        if self.control is not None:
            self.control.close()
        for repository in self.repositories.values():
            repository.close()
