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
from . import input_store
from .model_input import SQLITE_SUFFIXES, read_model_tables

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

    def _se_repo(self) -> Any:
        for_task = getattr(self.repository, "for_task", None)
        return for_task("se") if callable(for_task) else self.repository

    def _se_svg_path(self) -> Path | None:
        workspace = getattr(self.config, "workspace_directory", None)
        scenario = getattr(self.config, "scenario", None)
        candidates: list[Path] = []
        if workspace:
            wpath = Path(workspace)
            if scenario:
                candidates.append(wpath / "model" / f"{scenario}.svg")
            model_dir = wpath / "model"
            if model_dir.is_dir():
                candidates.extend(sorted(model_dir.glob("*.svg")))
        se_task = getattr(self.config, "tasks", {}).get("se")
        model_file = getattr(se_task, "model_file", None)
        if model_file:
            mpath = Path(model_file)
            for parent in (mpath.parent, *list(mpath.parents)[:3]):
                model_dir = parent / "model"
                if model_dir.is_dir():
                    if scenario:
                        candidates.append(model_dir / f"{scenario}.svg")
                    candidates.extend(sorted(model_dir.glob("*.svg")))
        for item in candidates:
            try:
                resolved = item.resolve()
                if resolved.is_file() and resolved.suffix.lower() == ".svg":
                    return resolved
            except OSError:
                continue
        return None

    def _se_model_catalog(self) -> dict[str, Any]:
        """读取只读模型库设备目录与支持指标，供伪量测/坏量测界面下拉选择使用。"""
        se_task = getattr(self.config, "tasks", {}).get("se")
        model_file = getattr(se_task, "model_file", None)
        units = {"u_unit": "V", "p_unit": "kW", "i_unit": "A", "q_unit": "kvar"}
        devices: dict[str, list[dict[str, Any]]] = {}
        if model_file and Path(model_file).is_file() and Path(model_file).suffix.lower() in SQLITE_SUFFIXES:
            try:
                model_tables = read_model_tables(Path(model_file))
                mrows = (model_tables.get("Model") or model_tables.get("PowerBase") or {}).get("rows") or []
                if mrows:
                    mrow = mrows[0]
                    p_u = str(mrow.get("p_unit") or "kW")
                    units = {
                        "u_unit": str(mrow.get("u_unit") or "V"),
                        "p_unit": p_u,
                        "i_unit": str(mrow.get("i_unit") or "A"),
                        "q_unit": {"W": "var", "kW": "kvar", "MW": "Mvar"}.get(p_u, "kvar"),
                    }
                for dev_type in input_store.SE_DEVICE_RESULT_METRICS:
                    rows = (model_tables.get(dev_type) or {}).get("rows") or []
                    if rows:
                        devices[dev_type] = [
                            {"idx": int(r["idx"]), "name": str(r.get("name", r["idx"]))}
                            for r in rows
                            if "idx" in r
                        ]
            except (ValueError, OSError, input_store.sqlite3.Error):
                pass
        if not devices:
            # 若无模型库则回退至最新 se_dev_* 设备表
            se_repo = self._se_repo()
            for dev_type in input_store.SE_DEVICE_RESULT_METRICS:
                try:
                    info = se_repo.se_devices(dev_type)
                    if info.get("rows"):
                        devices[dev_type] = [
                            {"idx": int(r["idx"]), "name": str(r.get("name", r["idx"]))}
                            for r in info["rows"]
                        ]
                except Exception:
                    continue
        from .se_pseudo import PSEUDO_STAT_DEVICE_FIELDS

        return {
            "units": units,
            "devices": devices,
            "meas_metrics": {k: dict(v) for k, v in input_store.SE_SOLVER_METRICS.items()},
            "stat_types": {k: {"metric": v[0], "label": v[1]} for k, v in PSEUDO_STAT_DEVICE_FIELDS.items()},
        }

    def _build_se_topology_values(self) -> dict[str, Any]:
        repo = self._se_repo()
        se_task = getattr(self.config, "tasks", {}).get("se")
        model_file = getattr(se_task, "model_file", None)
        meas_file = getattr(se_task, "measurement_file", None)

        units = {"u_unit": "V", "p_unit": "kW", "i_unit": "A", "q_unit": "kvar"}
        bus_node_map: dict[str, dict[int, tuple[str, int, str]]] = {"ACRealBs": {}, "DCRealBs": {}}
        if model_file and Path(model_file).is_file() and Path(model_file).suffix.lower() in SQLITE_SUFFIXES:
            try:
                model_tables = read_model_tables(Path(model_file))
                mrows = (model_tables.get("Model") or model_tables.get("PowerBase") or {}).get("rows") or []
                if mrows:
                    mrow = mrows[0]
                    p_u = str(mrow.get("p_unit") or "kW")
                    units = {
                        "u_unit": str(mrow.get("u_unit") or "V"),
                        "p_unit": p_u,
                        "i_unit": str(mrow.get("i_unit") or "A"),
                        "q_unit": {"W": "var", "kW": "kvar", "MW": "Mvar"}.get(p_u, "kvar"),
                    }
                for bs_table, node_table in (("ACRealBs", "ACNode"), ("DCRealBs", "DCNode")):
                    for row in (model_tables.get(bs_table) or {}).get("rows") or ():
                        if row.get("idx") is not None and row.get("node") is not None:
                            bus_node_map[bs_table][int(row["idx"])] = (node_table, int(row["node"]), str(row.get("name", "")))
            except (ValueError, OSError, input_store.sqlite3.Error):
                pass

        # 读取断路器实时分合位状态（只读）
        breaker_status: dict[tuple[str, int], int] = {}
        if meas_file and input_store.is_scdfe_d_wide_db(meas_file):
            try:
                with input_store.connect(meas_file, readonly=True) as conn:
                    conn.execute("PRAGMA query_only=ON")
                    for brk_tbl in ("ACBreak", "DCBreak"):
                        cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{brk_tbl}")')}
                        if {"idx", "position", "position_qual"} <= cols:
                            for r in conn.execute(f'SELECT idx, position, position_qual FROM "{brk_tbl}"'):
                                if r["position"] is not None and r["position_qual"] == 0:
                                    breaker_status[(brk_tbl, int(r["idx"]))] = int(r["position"])
            except (OSError, input_store.sqlite3.Error):
                pass

        def unit_for_code(se_code: str) -> str:
            prefix = se_code.split("_", 1)[0]
            return {"V": units["u_unit"], "I": units["i_unit"], "Q": units["q_unit"]}.get(prefix, units["p_unit"])

        overview = repo.se_overview(
            getattr(se_task, "parameter_file", None),
            do_cycle=getattr(se_task, "period_seconds", 60),
        )
        bad_list = overview.get("bad_data") or []
        bad_lookup: dict[tuple[str, int, str], dict[str, Any]] = {}
        for item in bad_list:
            if item.get("device_idx") is not None:
                bad_lookup[(str(item["device_type"]), int(item["device_idx"]), str(item.get("metric") or ""))] = item

        # 从最新 se_measurement 获取标准化残差等扩展信息
        meas_ext: dict[tuple[str, int, str], dict[str, Any]] = {}
        meas_page = repo.se_measurements_browse(source="all", limit=500, offset=0)
        for item in meas_page.get("rows") or ():
            if item.get("device_idx") is not None and item.get("metric"):
                meas_ext[(str(item["device_type"]), int(item["device_idx"]), str(item["metric"]))] = item

        slot_rules: dict[str, dict[str, tuple[str, ...]]] = {
            "ACGenerator": {"activePower": ("p",), "reactivePower": ("q",), "voltage": ("uab",), "current": ("ia",)},
            "DCGenerator": {"activePower": ("p",), "voltage": ("u",), "current": ("i",)},
            "ACLoad": {"activePower": ("p",), "reactivePower": ("q",), "voltage": ("uab",), "current": ("ia",)},
            "DCLoad": {"activePower": ("p",), "voltage": ("u",), "current": ("i",)},
            "ACBranch": {"activePower": ("i_p", "j_p"), "reactivePower": ("i_q", "j_q"), "voltage": ("i_uab", "j_uab"), "current": ("i_ia", "j_ia")},
            "ACZeroBranch": {"activePower": ("i_p", "j_p"), "reactivePower": ("i_q", "j_q"), "voltage": ("i_uab", "j_uab"), "current": ("i_ia", "j_ia")},
            "DCBranch": {"activePower": ("i_p", "j_p"), "voltage": ("i_u", "j_u"), "current": ("i_i", "j_i")},
            "DCDCConverter": {"activePower": ("i_p", "j_p"), "voltage": ("i_u", "j_u"), "current": ("i_i", "j_i")},
            "DCACConverter": {"activePower": ("ac_p", "dc_p"), "reactivePower": ("ac_q",), "voltage": ("ac_uab", "dc_u"), "current": ("ac_ia", "dc_i")},
            "ACBreak": {"current": ("ia",)},
            "DCBreak": {"current": ("i",)},
        }

        devices_out: dict[str, dict[str, Any]] = {}
        node_records: dict[tuple[str, int], dict[str, Any]] = {}
        for dev_type, metric_map in input_store.SE_DEVICE_RESULT_METRICS.items():
            table_data = repo.se_devices(dev_type)
            for row in table_data.get("rows") or ():
                idx = int(row["idx"])
                dev_id = f"{dev_type}-{idx}"
                metrics_dict: dict[str, dict[str, Any]] = {}
                bad_metrics: list[str] = []
                for metric, se_code in metric_map.items():
                    meas_v = row.get(f"{metric}_meas")
                    se_v = row.get(f"{metric}_se")
                    ext = meas_ext.get((dev_type, idx, metric)) or {}
                    bad_hit = bad_lookup.get((dev_type, idx, metric))
                    is_bad = bad_hit is not None or bool(ext.get("is_bad"))
                    if is_bad:
                        bad_metrics.append(metric)
                    residual = (meas_v - se_v) if (meas_v is not None and se_v is not None) else ext.get("residual")
                    metrics_dict[metric] = {
                        "metric": metric,
                        "meas_type": se_code,
                        "unit": ext.get("unit") or unit_for_code(se_code),
                        "meas": meas_v,
                        "se": se_v,
                        "residual": residual,
                        "normalized_residual": bad_hit.get("normalized_residual") if bad_hit else ext.get("normalized_residual"),
                        "is_bad": is_bad,
                    }

                svg_slots: dict[str, dict[str, Any]] = {}
                for mt_name, candidate_metrics in slot_rules.get(dev_type, {}).items():
                    primary = candidate_metrics[0]
                    # 若同组中其他端（如 j_p / dc_p）为坏数据，则优先高亮该坏数据端
                    chosen = next((m for m in candidate_metrics if metrics_dict.get(m, {}).get("is_bad")), primary)
                    if chosen in metrics_dict:
                        svg_slots[mt_name] = {**metrics_dict[chosen], "any_bad": any(metrics_dict.get(m, {}).get("is_bad") for m in candidate_metrics)}
                if dev_type in ("ACBreak", "DCBreak"):
                    pos = breaker_status.get((dev_type, idx))
                    if pos is not None:
                        svg_slots["status"] = {"metric": "position", "meas": pos, "se": pos, "unit": "", "is_bad": False}

                entry = {
                    "dev_id": dev_id,
                    "device_type": dev_type,
                    "idx": idx,
                    "name": str(row.get("name", "")),
                    "has_bad": bool(bad_metrics),
                    "bad_metrics": bad_metrics,
                    "metrics": metrics_dict,
                    "svg_slots": svg_slots,
                }
                devices_out[dev_id] = entry
                if dev_type in ("ACNode", "DCNode"):
                    node_records[(dev_type, idx)] = entry

        # 映射实母线 ACRealBs / DCRealBs 到其对应节点电压
        for bs_table, mapping in bus_node_map.items():
            for bs_idx, (node_table, node_idx, bs_name) in mapping.items():
                node_entry = node_records.get((node_table, node_idx))
                if not node_entry:
                    continue
                v_key = "uab" if node_table == "ACNode" else "u"
                v_metric = node_entry["metrics"].get(v_key)
                if not v_metric:
                    continue
                dev_id = f"{bs_table}-{bs_idx}"
                devices_out[dev_id] = {
                    "dev_id": dev_id,
                    "device_type": bs_table,
                    "idx": bs_idx,
                    "name": bs_name or node_entry["name"],
                    "linked_node": {"device_type": node_table, "idx": node_idx, "name": node_entry["name"]},
                    "has_bad": bool(v_metric.get("is_bad")),
                    "bad_metrics": [v_key] if v_metric.get("is_bad") else [],
                    "metrics": {v_key: v_metric},
                    "svg_slots": {"voltage": {**v_metric, "any_bad": bool(v_metric.get("is_bad"))}},
                }

        return {
            "latest": overview.get("latest"),
            "units": units,
            "svg_available": self._se_svg_path() is not None,
            "bad_data": bad_list,
            "bad_dev_ids": sorted(dev_id for dev_id, item in devices_out.items() if item["has_bad"]),
            "devices": devices_out,
        }

    def api_get(self, path: str) -> dict[str, Any]:
        parsed = urlparse(path)
        if parsed.path.startswith("/api/se/"):
            try:
                se_repo = self._se_repo()
                se_task = getattr(self.config, "tasks", {}).get("se")
                para_file = getattr(se_task, "parameter_file", None)
                period = getattr(se_task, "period_seconds", 60)
                query = parse_qs(parsed.query)
                if parsed.path == "/api/se/overview":
                    return {"ok": True, "data": se_repo.se_overview(para_file, period)}
                if parsed.path == "/api/se/devices":
                    return {
                        "ok": True,
                        "data": se_repo.se_devices(
                            query.get("type", [None])[0] or None,
                            q=query.get("q", [""])[0],
                            bad_only=query.get("bad_only", ["0"])[0] in {"1", "true"},
                        ),
                    }
                if parsed.path == "/api/se/measurements":
                    return {
                        "ok": True,
                        "data": se_repo.se_measurements_browse(
                            source=query.get("source", ["all"])[0],
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                            sort=query.get("sort", ["abs_residual"])[0],
                            direction=query.get("direction", ["desc"])[0],
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/se/history/stats":
                    return {"ok": True, "data": se_repo.se_history_stats(_int_query(query, "limit", 100, 1, 500))}
                if parsed.path == "/api/se/history/points":
                    return {"ok": True, "data": se_repo.se_history_points()}
                if parsed.path == "/api/se/history/point":
                    dtype = query.get("device_type", [""])[0].strip()
                    dname = query.get("device_name", [""])[0].strip()
                    mtype = query.get("meas_type", [""])[0].strip()
                    if not (dtype and dname and mtype):
                        return {"ok": False, "error": "device_type, device_name, meas_type are required"}
                    return {
                        "ok": True,
                        "data": se_repo.se_history_point_series(
                            dtype, dname, mtype, _int_query(query, "limit", 100, 1, 500)
                        ),
                    }
                if parsed.path == "/api/se/history/bad-data":
                    return {"ok": True, "data": se_repo.se_history_bad_data(_int_query(query, "limit", 100, 1, 500))}
                if parsed.path == "/api/se/topology-values":
                    return {"ok": True, "data": self._build_se_topology_values()}
                if parsed.path == "/api/se/params":
                    return {"ok": True, "data": se_repo.get_se_parameters(para_file, do_cycle=period)}
                if parsed.path == "/api/se/model-catalog":
                    return {"ok": True, "data": self._se_model_catalog()}
                # --- 伪量测模块 API ---
                if parsed.path == "/api/se/pseudo/overview":
                    return {"ok": True, "data": se_repo.se_pseudo_overview()}
                if parsed.path == "/api/se/pseudo/meas":
                    return {
                        "ok": True,
                        "data": se_repo.se_pseudo_meas_list(
                            device_type=query.get("device_type", [""])[0],
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                            q=query.get("q", [""])[0],
                        ),
                    }
                if parsed.path == "/api/se/pseudo/stat":
                    return {
                        "ok": True,
                        "data": se_repo.se_pseudo_stat_list(
                            device_type=query.get("device_type", [""])[0],
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                        ),
                    }
                if parsed.path == "/api/se/pseudo/results":
                    return {
                        "ok": True,
                        "data": se_repo.se_pseudo_results(
                            origin=query.get("origin", ["all"])[0],
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                            limit=_int_query(query, "limit", 100, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                # --- 坏量测模块 API ---
                if parsed.path == "/api/se/bad/overview":
                    return {"ok": True, "data": se_repo.se_bad_overview()}
                if parsed.path == "/api/se/bad/current":
                    return {
                        "ok": True,
                        "data": se_repo.se_bad_current(
                            device_type=query.get("device_type", [""])[0],
                            ack_status=query.get("ack_status", ["all"])[0],
                            q=query.get("q", [""])[0],
                        ),
                    }
                if parsed.path == "/api/se/bad/policies":
                    return {
                        "ok": True,
                        "data": se_repo.se_bad_policies(
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                            device_type=query.get("device_type", [""])[0],
                            action=query.get("action", [""])[0],
                            q=query.get("q", [""])[0],
                        ),
                    }
                if parsed.path == "/api/se/bad/abnormal":
                    return {
                        "ok": True,
                        "data": se_repo.se_bad_abnormal(
                            category=query.get("category", ["susstat"])[0],
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                            limit=_int_query(query, "limit", 100, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/se/bad/history":
                    return {
                        "ok": True,
                        "data": {
                            "history": se_repo.se_history_bad_data(_int_query(query, "limit", 100, 1, 500)),
                            "trend": se_repo.se_history_stats(_int_query(query, "limit", 100, 1, 500)),
                        },
                    }
                # --- SE 运行日志模块 API ---
                if parsed.path == "/api/se/logs":
                    run_id_raw = query.get("run_id", [""])[0].strip()
                    run_id_val = _int_path(run_id_raw) if run_id_raw else None
                    if run_id_raw and run_id_val is None:
                        return {"ok": False, "error": "invalid_run_id"}
                    return {
                        "ok": True,
                        "data": se_repo.se_logs_list(
                            level=query.get("level", [""])[0],
                            stage=query.get("stage", [""])[0],
                            source=query.get("source", [""])[0],
                            run_id=run_id_val,
                            date_from=query.get("date_from", [""])[0],
                            date_to=query.get("date_to", [""])[0],
                            q=query.get("q", [""])[0],
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/se/logs/summary":
                    return {"ok": True, "data": se_repo.se_logs_summary()}
                if parsed.path == "/api/se/logs/policy":
                    return {"ok": True, "data": se_repo.se_logs_policy_get()}
            except (ValueError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if parsed.path.startswith('/api/inputs/'):
            try:
                kind=parsed.path.rsplit('/',1)[-1]
                if kind=='limit-options':
                    return {'ok':True,'data':input_store.limit_options(self.config.tasks['ca'])}
                query=parse_qs(parsed.query)
                data=input_store.browse_inputs(self.config,kind,q=query.get('q',[''])[0],
                    page=_int_query(query,'page',0,0,1000000),size=_int_query(query,'size',8,1,100),view=query.get('view',['all'])[0])
                return {'ok':True,'data':data}
            except (ValueError,OSError,input_store.sqlite3.Error) as exc:
                return {'ok':False,'error':str(exc)}
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
                input_path=getattr(task,'measurement_file' if name=='se' else 'limit_file',None)
                if name in ('se','ca') and input_path and Path(input_path).suffix.lower() in input_store.SQLITE_SUFFIXES and Path(input_path).is_file():
                    try:
                        stats=input_store.browse_inputs(self.config,'measurements' if name=='se' else 'limits',size=1)['stats']
                        tasks[name]['input_statistics']=stats
                        tasks[name]['inputs_ready']=not missing and bool(stats.get('se_valid') if name=='se' else stats.get('enabled'))
                        if not tasks[name]['inputs_ready']:
                            tasks[name]['missing_inputs'].append('有效实时量测' if name=='se' else '启用的安全限值')
                    except (ValueError,OSError,input_store.sqlite3.Error) as exc:
                        tasks[name]['inputs_ready']=False
                        tasks[name]['missing_inputs'].append(str(exc))
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
            workspace = {key: str(getattr(self.config, key, None) or "") for key in
                         ("workspace_root", "runtime", "scenario", "workspace_directory")}
            for field in ('scada_source_file','point_catalog_file'):
                value=getattr(self.config.tasks.get('se'),field,None)
                tasks['se'][field]=str(value) if value else None
            return {"ok": True, "data": {"workspace": workspace, "kernel_root": str(self.config.kernel_root), "database": str(control_database or ""), "control_database": str(control_database or ""), "result_databases": result_databases, "pas_config": config_rows, "tasks": tasks}}
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
        if path in {"/api/se/params", "/api/se/params/reset"}:
            try:
                se_repo = self._se_repo()
                se_task = getattr(self.config, "tasks", {}).get("se")
                para_file = getattr(se_task, "parameter_file", None)
                period = getattr(se_task, "period_seconds", 60)
                if path == "/api/se/params/reset" or payload.get("action") == "reset":
                    data = se_repo.sync_se_parameters(para_file, do_cycle=period, overwrite=True)
                    se_repo.record_se_run_log(
                        level="WARN",
                        stage="param_change",
                        source="operator",
                        message="恢复 SE 默认算法参数（来自 se.para）",
                        detail={"action": "reset"},
                    )
                else:
                    data = se_repo.update_se_parameters(payload, para_file=para_file, do_cycle=period)
                return {"ok": True, "data": data}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        # --- 伪量测 / 坏量测 / SE 日志写接口 ---
        if path.startswith("/api/se/"):
            try:
                se_repo = self._se_repo()
                parts = path.strip("/").split("/")
                if path == "/api/se/pseudo/meas":
                    return {"ok": True, "data": se_repo.se_pseudo_meas_save(payload)}
                if len(parts) == 6 and parts[:4] == ["api", "se", "pseudo", "meas"] and parts[5] == "delete":
                    did = _int_path(parts[4])
                    if did is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": se_repo.se_pseudo_meas_delete(did), "id": did}}
                if path == "/api/se/pseudo/stat":
                    return {"ok": True, "data": se_repo.se_pseudo_stat_save(payload)}
                if len(parts) == 6 and parts[:4] == ["api", "se", "pseudo", "stat"] and parts[5] == "delete":
                    did = _int_path(parts[4])
                    if did is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": se_repo.se_pseudo_stat_delete(did), "id": did}}
                if path == "/api/se/bad/ack":
                    bad_id = payload.get("id", payload.get("bad_id"))
                    if bad_id is None:
                        return {"ok": False, "error": "id is required"}
                    return {
                        "ok": True,
                        "data": se_repo.se_bad_ack(
                            int(bad_id),
                            ack_status=str(payload.get("ack_status") or "acked"),
                            ack_note=str(payload.get("ack_note") or ""),
                        ),
                    }
                if path == "/api/se/bad/policies":
                    return {"ok": True, "data": se_repo.se_bad_policy_save(payload)}
                if len(parts) == 6 and parts[:4] == ["api", "se", "bad", "policies"] and parts[5] == "delete":
                    pid = _int_path(parts[4])
                    if pid is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": se_repo.se_bad_policy_delete(pid), "id": pid}}
                if path == "/api/se/bad/convert-pseudo":
                    return {
                        "ok": True,
                        "data": se_repo.se_bad_convert_pseudo(
                            bad_id=int(payload["bad_id"]) if payload.get("bad_id") not in (None, "") else None,
                            device_type=str(payload.get("device_type") or ""),
                            device_idx=int(payload["device_idx"]) if payload.get("device_idx") not in (None, "") else None,
                            device_name=str(payload.get("device_name") or ""),
                            metric=str(payload.get("metric") or ""),
                            pseudo_value=float(payload["pseudo_value"]) if payload.get("pseudo_value") not in (None, "") else None,
                            weight=float(payload.get("weight", 1e-3)),
                            note=str(payload.get("note") or ""),
                        ),
                    }
                if path == "/api/se/logs/policy":
                    return {"ok": True, "data": se_repo.se_logs_policy_update(payload)}
                if path == "/api/se/logs/purge":
                    return {
                        "ok": True,
                        "data": se_repo.se_logs_purge(
                            dry_run=bool(payload.get("dry_run", False)),
                            retention_days=int(payload["retention_days"]) if payload.get("retention_days") not in (None, "") else None,
                            keep_error_days=int(payload["keep_error_days"]) if payload.get("keep_error_days") not in (None, "") else None,
                            max_rows=int(payload["max_rows"]) if payload.get("max_rows") not in (None, "") else None,
                            source="operator",
                        ),
                    }
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if path.startswith('/api/inputs/'):
            try:
                action=path.removeprefix('/api/inputs/')
                if action=='sync':
                    data=input_store.sync_measurements(self.config.tasks['se'])
                elif action=='refresh':
                    data=input_store.refresh_measurements(self.config.tasks['se']);data.pop('rows',None)
                elif action=='seed-limits':
                    data=input_store.seed_limits(self.config.tasks['ca'])
                elif action=='limits':
                    data=input_store.save_limit(self.config.tasks['ca'],payload)
                elif action.startswith(('measurement/','mapping/')):
                    entity,identity=action.split('/')
                    data=input_store.update_measurement(self.config.tasks['se'],entity,int(identity),payload)
                else: raise ValueError('Unknown input action')
                return {'ok':True,'data':data}
            except (ValueError,TypeError,OSError,input_store.sqlite3.Error) as exc:
                return {'ok':False,'error':str(exc)}
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

    def api_put(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """支持 RESTful PUT 更新伪量测、伪状态与坏量测策略。"""
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            return {"ok": False, "error": "payload_must_be_object"}
        parts = path.strip("/").split("/")
        try:
            se_repo = self._se_repo()
            if len(parts) == 5 and parts[:4] == ["api", "se", "pseudo", "meas"]:
                did = _int_path(parts[4])
                if did is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": se_repo.se_pseudo_meas_save(payload, define_id=did)}
            if len(parts) == 5 and parts[:4] == ["api", "se", "pseudo", "stat"]:
                did = _int_path(parts[4])
                if did is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": se_repo.se_pseudo_stat_save(payload, define_id=did)}
            if len(parts) == 5 and parts[:4] == ["api", "se", "bad", "policies"]:
                pid = _int_path(parts[4])
                if pid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": se_repo.se_bad_policy_save(payload, policy_id=pid)}
        except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": False, "error": "not_found"}

    def api_delete(self, path: str) -> dict[str, Any]:
        """支持 RESTful DELETE 删除伪量测、伪状态与坏量测策略。"""
        parts = path.strip("/").split("/")
        try:
            se_repo = self._se_repo()
            if len(parts) == 5 and parts[:4] == ["api", "se", "pseudo", "meas"]:
                did = _int_path(parts[4])
                if did is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": se_repo.se_pseudo_meas_delete(did), "id": did}}
            if len(parts) == 5 and parts[:4] == ["api", "se", "pseudo", "stat"]:
                did = _int_path(parts[4])
                if did is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": se_repo.se_pseudo_stat_delete(did), "id": did}}
            if len(parts) == 5 and parts[:4] == ["api", "se", "bad", "policies"]:
                pid = _int_path(parts[4])
                if pid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": se_repo.se_bad_policy_delete(pid), "id": pid}}
        except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
            return {"ok": False, "error": str(exc)}
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
                parsed_get = urlparse(self.path)
                if parsed_get.path == "/api/se/svg":
                    svg_path = app._se_svg_path()
                    if svg_path is None:
                        self._send_json({"ok": False, "error": "svg_not_found"}, 404)
                        return
                    body = svg_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed_get.path == "/api/se/logs/export":
                    query = parse_qs(parsed_get.query)
                    run_id_raw = query.get("run_id", [""])[0].strip()
                    run_id_val = _int_path(run_id_raw) if run_id_raw else None
                    csv_text = app._se_repo().se_logs_export_csv(
                        level=query.get("level", [""])[0],
                        stage=query.get("stage", [""])[0],
                        source=query.get("source", [""])[0],
                        run_id=run_id_val,
                        date_from=query.get("date_from", [""])[0],
                        date_to=query.get("date_to", [""])[0],
                        q=query.get("q", [""])[0],
                    )
                    body = csv_text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", 'attachment; filename="se-run-logs.csv"')
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
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

            def do_PUT(self):  # noqa: N802
                if not self.path.startswith("/api/"):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    size = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
                    payload = json.loads(self.rfile.read(size) or b"{}")
                    response = app.api_put(self.path, payload)
                except (ValueError, json.JSONDecodeError) as exc:
                    response = {"ok": False, "error": str(exc)}
                self._send_json(response, 200 if response.get("ok", False) else 400)

            def do_DELETE(self):  # noqa: N802
                if not self.path.startswith("/api/"):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                response = app.api_delete(self.path)
                self._send_json(response, 200 if response.get("ok", False) else 400)

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
