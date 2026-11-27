"""Dependency-free HTTP API and static web application for PAS."""

from __future__ import annotations

import gzip
import json
import logging
import math
import mimetypes
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .db import Repository
from . import input_store, platform_insights
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


def _sanitize_json(value: Any) -> Any:
    """递归将非有限浮点数（NaN/Inf）清洗为 None，确保输出严格合法的 JSON。"""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _sanitize_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_json(item) for item in value]
    return value


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

    def _lf_repo(self) -> Any:
        for_task = getattr(self.repository, "for_task", None)
        return for_task("lf") if callable(for_task) else self.repository

    def _ca_repo(self) -> Any:
        for_task = getattr(self.repository, "for_task", None)
        return for_task("ca") if callable(for_task) else self.repository

    def _weather_repo(self) -> Any:
        ctrl = getattr(self.repository, "control", None)
        if ctrl is not None and callable(getattr(ctrl, "weather_state_get", None)):
            return ctrl
        if callable(getattr(self.repository, "weather_state_get", None)):
            return self.repository
        return self._ca_repo()

    def _weather_model_tables(self) -> dict[str, dict[str, Any]] | None:
        ca_task = getattr(self.config, "tasks", {}).get("ca") or getattr(self.config, "tasks", {}).get("lf")
        model_file = getattr(ca_task, "model_file", None)
        if not model_file:
            return None
        path = Path(model_file)
        if not path.is_file() or path.suffix.lower() not in SQLITE_SUFFIXES:
            return None
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        cache = getattr(self, "_weather_mt_cache", None)
        if cache and cache[0] == str(path) and cache[1] == mtime:
            return cache[2]
        try:
            mt = read_model_tables(path)
            self._weather_mt_cache = (str(path), mtime, mt)
            return mt
        except (ValueError, OSError, input_store.sqlite3.Error):
            return None

    @staticmethod
    def _default_ui_branding() -> dict[str, Any]:
        """返回顶栏中央主标题徽牌默认配置与预设列表。"""
        return {
            "title": "南极秦岭站综合能量管理系统",
            "badge": "秦岭站",
            "enabled": True,
            "presets": [
                {"title": "南极秦岭站综合能量管理系统", "badge": "秦岭站"},
                {"title": "极地微电网在线分析主控台", "badge": "PAS"},
                {"title": "交直流混合微电网能量管理系统", "badge": "EMS"},
            ],
        }

    def _get_ui_branding(self) -> dict[str, Any]:
        """从 pas_config 读取持久化的顶栏中央主标题配置。"""
        base = self._default_ui_branding()
        saved: Any = None
        if callable(getattr(self.repository, "get_config", None)):
            try:
                saved = self.repository.get_config("ui.branding", None)
            except (ValueError, OSError, input_store.sqlite3.Error):
                saved = None
        if isinstance(saved, dict):
            if isinstance(saved.get("title"), str) and saved["title"].strip():
                base["title"] = saved["title"].strip()[:40]
            if isinstance(saved.get("badge"), str):
                base["badge"] = saved["badge"].strip()[:16]
            if "enabled" in saved:
                base["enabled"] = bool(saved["enabled"])
        return base

    def _save_ui_branding(self, payload: dict[str, Any]) -> dict[str, Any]:
        """校验并持久化顶栏中央主标题配置至 pas_config。"""
        if not isinstance(payload, dict):
            raise ValueError("配置内容必须为 JSON 对象")
        defaults = self._default_ui_branding()
        if payload.get("reset"):
            stored = {
                "title": defaults["title"],
                "badge": defaults["badge"],
                "enabled": True,
            }
        else:
            title = str(payload.get("title", defaults["title"])).strip()[:40]
            if not title:
                raise ValueError("主标题不能为空")
            badge = str(payload.get("badge", "")).strip()[:16]
            enabled = bool(payload.get("enabled", True))
            stored = {"title": title, "badge": badge, "enabled": enabled}
        if callable(getattr(self.repository, "set_config", None)):
            self.repository.set_config("ui.branding", stored)
        return {**defaults, **stored}

    def _weather_summary(
        self,
        *,
        include_presets: bool = False,
        state_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from .weather_coupling import (
            POLAR_WEATHER_PRESETS,
            WEATHER_PERTURBATION_KINDS,
            compute_weather_coupling_summary,
        )
        state = state_override if state_override is not None else self._weather_repo().weather_state_get()
        summary = compute_weather_coupling_summary(state, self._weather_model_tables())
        if include_presets:
            summary["presets"] = list(POLAR_WEATHER_PRESETS.values())
            summary["perturbation_kinds"] = [
                {"kind": k, "label": v} for k, v in WEATHER_PERTURBATION_KINDS.items()
            ]
        return summary

    def _build_ca_topology_risks(self, *, run_id: int | None = None) -> dict[str, Any]:
        """构建 CA 接线图风险叠加数据（按最新/历史 CA 断面映射每个受影响设备与实母线的风险等级）。"""
        ca_repo = self._ca_repo()
        snap = ca_repo.ca_snapshot(run_id=run_id)
        latest = snap.get("latest")
        ca_task = getattr(self.config, "tasks", {}).get("ca")
        model_file = getattr(ca_task, "model_file", None)

        # 建立 ACNode/DCNode -> 关联实母线 dev_id 映射，便于母线风险同步点亮 SVG 实母线
        node_to_real_bs: dict[tuple[str, int], list[str]] = {}
        if model_file and Path(model_file).is_file() and Path(model_file).suffix.lower() in SQLITE_SUFFIXES:
            try:
                mt = read_model_tables(Path(model_file))
                for bs_tbl, node_tbl in (("ACRealBs", "ACNode"), ("DCRealBs", "DCNode")):
                    for row in (mt.get(bs_tbl) or {}).get("rows") or ():
                        if row.get("idx") is not None and row.get("node") is not None:
                            node_to_real_bs.setdefault((node_tbl, int(row["node"])), []).append(f"{bs_tbl}-{int(row['idx'])}")
            except (ValueError, OSError, input_store.sqlite3.Error):
                pass

        rank = {"critical": 4, "high": 3, "medium": 2, "low": 1, "normal": 0}
        devices: dict[str, dict[str, Any]] = {}

        def _attach(dev_id: str, risk: dict[str, Any]) -> None:
            entry = devices.setdefault(
                dev_id,
                {
                    "dev_id": dev_id,
                    "device_type": risk.get("device_type", ""),
                    "device_idx": risk.get("device_idx"),
                    "device_name": risk.get("device_name", ""),
                    "severity": "normal",
                    "risk_count": 0,
                    "risks": [],
                },
            )
            entry["risk_count"] += 1
            if rank.get(str(risk.get("severity")), 0) > rank.get(entry["severity"], 0):
                entry["severity"] = str(risk.get("severity"))
            if len(entry["risks"]) < 12:
                entry["risks"].append(risk)

        for r in snap.get("risks") or ():
            dt = str(r.get("device_type") or "")
            didx = r.get("device_idx")
            if dt and didx is not None:
                _attach(f"{dt}-{int(didx)}", r)
                for rb_id in node_to_real_bs.get((dt, int(didx)), ()):
                    _attach(rb_id, r)

        return {
            "latest": latest,
            "run_id": snap.get("run_id"),
            "is_history": bool(run_id is not None),
            "svg_available": self._se_svg_path() is not None,
            "risk_dev_ids": sorted(devices.keys()),
            "devices": devices,
            "risks": (snap.get("risks") or [])[:200],
        }

    def _build_pipeline_overview(self) -> dict[str, Any]:
        """聚合全平台 SE → LF → CA 链路状态、版本溯源一致性、三模块摘要与跨模块告警。"""
        se_repo = self._se_repo()
        lf_repo = self._lf_repo()
        ca_repo = self._ca_repo()
        se_task = getattr(self.config, "tasks", {}).get("se")
        lf_task = getattr(self.config, "tasks", {}).get("lf")
        ca_task = getattr(self.config, "tasks", {}).get("ca")

        se_ov = se_repo.se_overview(getattr(se_task, "parameter_file", None), do_cycle=getattr(se_task, "period_seconds", 60))
        lf_home = lf_repo.lf_home_summary(getattr(lf_task, "parameter_file", None), do_cycle=getattr(lf_task, "period_seconds", 60))
        ca_home = ca_repo.ca_home_summary(do_cycle=getattr(ca_task, "period_seconds", 300))

        se_lat = se_ov.get("latest")
        lf_lat = lf_home.get("latest")
        ca_lat = ca_home.get("latest")

        se_id = int(se_lat["run_id"]) if se_lat and se_lat.get("run_id") is not None else None
        lf_id = int(lf_lat["run_id"]) if lf_lat and lf_lat.get("run_id") is not None else None
        ca_id = int(ca_lat["run_id"]) if ca_lat and ca_lat.get("run_id") is not None else None

        lf_from_se = lf_lat.get("source_se_run_id") if lf_lat else None
        ca_from_lf = ca_lat.get("source_lf_run_id") if ca_lat else None
        ca_from_se = ca_lat.get("source_se_run_id") if ca_lat else None

        se_lf_synced = bool(se_id is not None and lf_from_se is not None and int(lf_from_se) == se_id)
        lf_ca_synced = bool(lf_id is not None and ca_from_lf is not None and int(ca_from_lf) == lf_id)

        # 聚合跨模块重点告警（SE 坏数据 + LF 越限 + CA 严重/高风险）
        alerts: list[dict[str, Any]] = []
        for b in (se_ov.get("bad_data") or [])[:6]:
            alerts.append({
                "module": "SE",
                "severity": "medium",
                "target": f"{b.get('device_name', '')} · {b.get('meas_type', '')}",
                "detail": f"归一化残差 {b.get('norm_residual', 0):.2f}（实测 {b.get('meas_value')} / 估计 {b.get('est_value')}）",
                "href": "/se-bad.html",
            })
        for v in (lf_home.get("voltage_extremes") or [])[:6]:
            if v.get("v_status") != "normal":
                alerts.append({
                    "module": "LF",
                    "severity": "high",
                    "target": str(v.get("device_name") or ""),
                    "detail": f"母线电压越限：{v.get('v_pu'):.4f} pu ({v.get('v_status')})",
                    "href": "/lf-flow.html",
                })
        for br in (lf_home.get("top_loading") or [])[:6]:
            if br.get("overload"):
                alerts.append({
                    "module": "LF",
                    "severity": "high",
                    "target": str(br.get("device_name") or ""),
                    "detail": f"支路/换流器过载：{br.get('loading_pct'):.1f}%",
                    "href": "/lf-results.html",
                })
        for r in (ca_home.get("top_risks") or [])[:8]:
            alerts.append({
                "module": "CA",
                "severity": str(r.get("severity") or "medium"),
                "target": f"[{r.get('category', 'N-0')}] {r.get('contingency_name', '')} → {r.get('device_name', '')}",
                "detail": str(r.get("detail") or ""),
                "href": "/ca-risks.html",
            })

        # 合并最近联合运行历史
        recent_runs: list[dict[str, Any]] = []
        for r in (se_ov.get("recent_runs") or [])[:8]:
            recent_runs.append({
                "module": "SE",
                "run_id": r.get("run_id"),
                "status": r.get("status"),
                "started_at": r.get("started_at"),
                "elapsed_seconds": r.get("elapsed_seconds"),
                "source": r.get("execution_source"),
                "summary": f"合格率 {(r.get('pass_rate') or 0)*100:.1f}% · 坏数据 {r.get('bad_data_count') or 0}",
                "href": "/se-logs.html",
            })
        for r in (lf_home.get("recent_runs") or [])[:8]:
            recent_runs.append({
                "module": "LF",
                "run_id": r.get("run_id"),
                "status": r.get("status"),
                "started_at": r.get("started_at"),
                "elapsed_seconds": r.get("elapsed_seconds"),
                "source": r.get("execution_source"),
                "summary": f"SE #{r.get('source_se_run_id') or '—'} · 网损率 {(r.get('loss_rate') or 0):.2f}%",
                "href": "/lf-logs.html",
            })
        for r in (ca_home.get("recent_runs") or [])[:8]:
            recent_runs.append({
                "module": "CA",
                "run_id": r.get("run_id"),
                "status": r.get("status"),
                "started_at": r.get("started_at"),
                "elapsed_seconds": r.get("elapsed_seconds"),
                "source": r.get("execution_source"),
                "summary": f"LF #{r.get('source_lf_run_id') or '—'} · 风险 {r.get('risk_level') or '—'} ({r.get('security_score') if r.get('security_score') is not None else '—'})",
                "href": "/ca-logs.html",
            })
        recent_runs.sort(key=lambda x: str(x.get("started_at") or ""), reverse=True)

        get_pol = getattr(self.scheduler, "get_cascade_policy", None)
        chain_st = getattr(self.scheduler, "chain_status", None)
        sched_st = self.scheduler.status() if callable(getattr(self.scheduler, "status", None)) else {}

        return {
            "workspace": {
                "scenario": getattr(self.config, "scenario", ""),
                "runtime": getattr(self.config, "runtime", ""),
                "workspace_directory": str(getattr(self.config, "workspace_directory", "") or ""),
            },
            "cascade_policy": get_pol() if callable(get_pol) else {"se_to_lf": False, "lf_to_ca": False},
            "chain": chain_st() if callable(chain_st) else {"running": False, "last_chain": None},
            "scheduler": {
                "daemon_running": bool(sched_st.get("daemon_running", False)),
                "active_tasks": sched_st.get("active_tasks") or [],
                "pending_tasks": sched_st.get("pending_tasks") or [],
            },
            "linkage": {
                "se_run_id": se_id,
                "lf_run_id": lf_id,
                "lf_source_se_run_id": lf_from_se,
                "ca_run_id": ca_id,
                "ca_source_lf_run_id": ca_from_lf,
                "ca_source_se_run_id": ca_from_se,
                "se_lf_synced": se_lf_synced,
                "lf_ca_synced": lf_ca_synced,
                "all_synced": se_lf_synced and lf_ca_synced,
            },
            "se": {
                "latest": se_lat,
                "trend": (se_ov.get("trend_series") or [])[-30:],
            },
            "lf": {
                "latest": lf_lat,
                "overrides": lf_home.get("overrides"),
                "trend": (lf_home.get("trend_series") or [])[-30:],
            },
            "ca": {
                "latest": ca_lat,
                "contingency_defs": ca_home.get("contingency_defs"),
                "trend": (ca_home.get("trend_series") or [])[-30:],
            },
            "alerts": alerts[:20],
            "recent_runs": recent_runs[:20],
        }

    def _build_lf_topology_values(self, *, run_id: int | None = None) -> dict[str, Any]:
        """构建 LF 潮流图 SVG 绑定数据（支持最新/历史断面、LF 值 / 负载率 % / LF−SE 偏差及越限高亮）。"""
        repo = self._lf_repo()
        lf_task = getattr(self.config, "tasks", {}).get("lf")
        model_file = getattr(lf_task, "model_file", None)
        se_task = getattr(self.config, "tasks", {}).get("se")
        meas_file = getattr(se_task, "measurement_file", None)

        snap = repo.lf_snapshot(run_id=run_id)
        latest_stat = snap.get("latest")
        units = {
            "u_unit": (latest_stat or {}).get("u_unit") or "V",
            "p_unit": (latest_stat or {}).get("p_unit") or "kW",
            "i_unit": (latest_stat or {}).get("i_unit") or "A",
            "q_unit": {"W": "var", "kW": "kvar", "MW": "Mvar"}.get((latest_stat or {}).get("p_unit") or "kW", "kvar"),
        }
        bus_node_map: dict[str, dict[int, tuple[str, int, str]]] = {"ACRealBs": {}, "DCRealBs": {}}
        if model_file and Path(model_file).is_file() and Path(model_file).suffix.lower() in SQLITE_SUFFIXES:
            try:
                model_tables = read_model_tables(Path(model_file))
                for bs_tbl, node_tbl in (("ACRealBs", "ACNode"), ("DCRealBs", "DCNode")):
                    for row in (model_tables.get(bs_tbl) or {}).get("rows") or ():
                        if row.get("idx") is not None and row.get("node") is not None:
                            bus_node_map[bs_tbl][int(row["idx"])] = (node_tbl, int(row["node"]), str(row.get("name", "")))
            except (ValueError, OSError, input_store.sqlite3.Error):
                pass

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

        devices_out: dict[str, dict[str, Any]] = {}
        node_records: dict[tuple[str, int], dict[str, Any]] = {}
        alerts: list[dict[str, Any]] = []

        # 1. 节点电压（ACNode / DCNode）
        for b in snap.get("buses") or ():
            dt = str(b["device_type"])
            idx = int(b["device_idx"])
            dev_id = f"{dt}-{idx}"
            is_alert = b.get("v_status") != "normal"
            v_slot = {
                "metric": "uab" if dt == "ACNode" else "u",
                "unit": units["u_unit"],
                "lf": b.get("v_eng"),
                "se": b.get("v_se"),
                "diff": b.get("v_diff"),
                "v_pu": b.get("v_pu"),
                "angle_deg": b.get("angle_deg"),
                "loading_pct": None,
                "is_alert": is_alert,
            }
            entry = {
                "dev_id": dev_id,
                "device_type": dt,
                "idx": idx,
                "name": str(b.get("device_name", "")),
                "has_alert": is_alert,
                "alert_reason": f"V={b.get('v_pu'):.4f}pu ({b.get('v_status')})" if (is_alert and b.get("v_pu") is not None) else "",
                "metrics": {v_slot["metric"]: v_slot},
                "svg_slots": {"voltage": v_slot},
            }
            devices_out[dev_id] = entry
            node_records[(dt, idx)] = entry
            if is_alert:
                alerts.append({
                    "dev_id": dev_id,
                    "device_type": dt,
                    "device_name": entry["name"],
                    "kind": "voltage",
                    "value": b.get("v_eng"),
                    "unit": units["u_unit"],
                    "detail": entry["alert_reason"],
                })

        # 2. 电源与负荷（ACGenerator / DCGenerator / ACLoad / DCLoad）
        for u in snap.get("units") or ():
            if u.get("device_idx") is None:
                continue
            dt = str(u["device_type"])
            idx = int(u["device_idx"])
            dev_id = f"{dt}-{idx}"
            is_ol = bool(u.get("overload"))
            lp = u.get("loading_pct")
            p_slot = {"metric": "p", "unit": units["p_unit"], "lf": u.get("p_lf"), "se": u.get("p_se"), "diff": u.get("p_diff"), "loading_pct": lp, "is_alert": is_ol}
            q_slot = {"metric": "q", "unit": units["q_unit"], "lf": u.get("q_lf"), "se": None, "diff": None, "loading_pct": lp, "is_alert": False}
            v_slot = {"metric": "uab" if dt.startswith("AC") else "u", "unit": units["u_unit"], "lf": u.get("v_lf"), "se": None, "diff": None, "loading_pct": None, "is_alert": False}
            i_slot = {"metric": "ia" if dt.startswith("AC") else "i", "unit": units["i_unit"], "lf": u.get("i_lf"), "se": None, "diff": None, "loading_pct": lp, "is_alert": is_ol}
            metrics = {"p": p_slot, v_slot["metric"]: v_slot, i_slot["metric"]: i_slot}
            svg_slots = {"activePower": p_slot, "voltage": v_slot, "current": i_slot}
            if dt.startswith("AC"):
                metrics["q"] = q_slot
                svg_slots["reactivePower"] = q_slot
            devices_out[dev_id] = {
                "dev_id": dev_id,
                "device_type": dt,
                "idx": idx,
                "name": str(u.get("device_name", "")),
                "control_type": u.get("control_type") or "",
                "rated_capacity": u.get("rated_capacity"),
                "loading_pct": lp,
                "has_alert": is_ol,
                "alert_reason": f"负载率 {lp:.1f}%" if (is_ol and lp is not None) else "",
                "metrics": metrics,
                "svg_slots": svg_slots,
            }
            if is_ol:
                p_txt = f"{float(u['p_lf']):.2f}" if isinstance(u.get("p_lf"), (int, float)) else "—"
                alerts.append({
                    "dev_id": dev_id,
                    "device_type": dt,
                    "device_name": str(u.get("device_name", "")),
                    "kind": "overload",
                    "value": lp,
                    "unit": "%",
                    "detail": f"P={p_txt} {units['p_unit']}",
                })

        # 3. 支路、换流器与断路器
        for br in snap.get("branches") or ():
            if br.get("device_idx") is None:
                continue
            dt = str(br["device_type"])
            idx = int(br["device_idx"])
            dev_id = f"{dt}-{idx}"
            is_ol = bool(br.get("overload"))
            lp = br.get("loading_pct")
            p_slot = {"metric": "ac_p" if dt == "DCACConverter" else "i_p", "unit": units["p_unit"], "lf": br.get("p_to") if dt == "DCACConverter" else br.get("p_from"), "se": br.get("p_se"), "diff": br.get("p_diff"), "loading_pct": lp, "is_alert": is_ol}
            q_slot = {"metric": "ac_q" if dt == "DCACConverter" else "i_q", "unit": units["q_unit"], "lf": br.get("q_to") if dt == "DCACConverter" else br.get("q_from"), "se": None, "diff": None, "loading_pct": lp, "is_alert": False}
            v_slot = {"metric": "ac_uab" if dt == "DCACConverter" else "i_uab", "unit": units["u_unit"], "lf": br.get("v_to") if dt == "DCACConverter" else br.get("v_from"), "se": None, "diff": None, "loading_pct": None, "is_alert": False}
            i_slot = {"metric": "ac_ia" if dt == "DCACConverter" else ("i_ia" if dt.startswith("AC") else "i_i"), "unit": units["i_unit"], "lf": br.get("i_to") if dt == "DCACConverter" else br.get("i_from"), "se": None, "diff": None, "loading_pct": lp, "is_alert": is_ol}
            metrics = {p_slot["metric"]: p_slot, v_slot["metric"]: v_slot, i_slot["metric"]: i_slot}
            svg_slots: dict[str, Any] = {"activePower": p_slot, "voltage": v_slot, "current": i_slot}
            if dt.startswith("AC") or dt == "DCACConverter":
                metrics[q_slot["metric"]] = q_slot
                svg_slots["reactivePower"] = q_slot
            if dt in ("ACBreak", "DCBreak"):
                pos = breaker_status.get((dt, idx))
                if pos is not None:
                    svg_slots["status"] = {"metric": "position", "lf": pos, "se": pos, "unit": "", "is_alert": False}
            devices_out[dev_id] = {
                "dev_id": dev_id,
                "device_type": dt,
                "idx": idx,
                "name": str(br.get("device_name", "")),
                "rated_capacity": br.get("rated_capacity"),
                "loading_pct": lp,
                "p_loss": br.get("p_loss"),
                "has_alert": is_ol,
                "alert_reason": f"负载率 {lp:.1f}%" if (is_ol and lp is not None) else "",
                "metrics": metrics,
                "svg_slots": svg_slots,
            }
            if is_ol:
                p_txt = f"{float(p_slot['lf']):.2f}" if isinstance(p_slot.get("lf"), (int, float)) else "—"
                alerts.append({
                    "dev_id": dev_id,
                    "device_type": dt,
                    "device_name": str(br.get("device_name", "")),
                    "kind": "overload",
                    "value": lp,
                    "unit": "%",
                    "detail": f"P={p_txt} {units['p_unit']}",
                })

        # 4. 映射实母线 ACRealBs / DCRealBs
        for bs_tbl, mapping in bus_node_map.items():
            for bs_idx, (node_tbl, node_idx, bs_name) in mapping.items():
                node_entry = node_records.get((node_tbl, node_idx))
                if not node_entry:
                    continue
                v_slot = node_entry["svg_slots"]["voltage"]
                dev_id = f"{bs_tbl}-{bs_idx}"
                devices_out[dev_id] = {
                    "dev_id": dev_id,
                    "device_type": bs_tbl,
                    "idx": bs_idx,
                    "name": bs_name or node_entry["name"],
                    "linked_node": {"device_type": node_tbl, "idx": node_idx, "name": node_entry["name"]},
                    "has_alert": node_entry["has_alert"],
                    "alert_reason": node_entry["alert_reason"],
                    "metrics": {v_slot["metric"]: v_slot},
                    "svg_slots": {"voltage": v_slot},
                }

        return {
            "latest": latest_stat,
            "run_id": snap.get("run_id"),
            "is_history": bool(run_id is not None),
            "units": units,
            "svg_available": self._se_svg_path() is not None,
            "alerts": alerts,
            "alert_dev_ids": sorted(did for did, item in devices_out.items() if item.get("has_alert")),
            "devices": devices_out,
        }

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

    def _build_se_topology_values(self, *, run_id: int | None = None) -> dict[str, Any]:
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

        # 单次锁内聚合最新断面全部设备表、全部量测与坏数据（消除 N+1 查询与 500 条截断）
        snap = repo.se_topology_snapshot()
        latest_stat = snap.get("latest")
        latest_rid = int(latest_stat["run_id"]) if latest_stat and latest_stat.get("run_id") is not None else None
        is_history = run_id is not None and (latest_rid is None or int(run_id) != latest_rid)

        bad_list = snap.get("bad_data") or []
        bad_lookup: dict[tuple[str, int, str], dict[str, Any]] = {}
        meas_ext: dict[tuple[str, int, str], dict[str, Any]] = {}
        hist_by_name_code: dict[tuple[str, str, str], dict[str, Any]] = {}
        if is_history:
            hist_pack = repo.se_run_measurements_raw(int(run_id))
            if hist_pack.get("stat"):
                latest_stat = hist_pack["stat"]
            bad_list = []
            for hrow in hist_pack.get("rows") or ():
                key = (str(hrow.get("device_type") or ""), str(hrow.get("device_name") or ""), str(hrow.get("meas_type") or ""))
                hist_by_name_code[key] = hrow
                if str(hrow.get("source") or "") == "bad_data":
                    bad_list.append({
                        "device_type": hrow.get("device_type"),
                        "device_name": hrow.get("device_name"),
                        "meas_type": hrow.get("meas_type"),
                        "meas_value": hrow.get("meas_value"),
                        "se_value": hrow.get("se_value"),
                        "residual": hrow.get("residual"),
                        "normalized_residual": hrow.get("normalized_residual"),
                    })
        else:
            for item in bad_list:
                if item.get("device_idx") is not None:
                    bad_lookup[(str(item["device_type"]), int(item["device_idx"]), str(item.get("metric") or ""))] = item
            for item in snap.get("measurements") or ():
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

        devices_by_type = snap.get("devices_by_type") or {}
        devices_out: dict[str, dict[str, Any]] = {}
        node_records: dict[tuple[str, int], dict[str, Any]] = {}
        for dev_type, metric_map in input_store.SE_DEVICE_RESULT_METRICS.items():
            for row in devices_by_type.get(dev_type) or ():
                idx = int(row["idx"])
                dev_id = f"{dev_type}-{idx}"
                metrics_dict: dict[str, dict[str, Any]] = {}
                bad_metrics: list[str] = []
                for metric, se_code in metric_map.items():
                    if is_history:
                        hrow = hist_by_name_code.get((dev_type, str(row.get("name", "")), se_code))
                        meas_v = hrow.get("meas_value") if hrow else None
                        se_v = hrow.get("se_value") if hrow else None
                        ext = hrow or {}
                        is_bad = bool(hrow and str(hrow.get("source") or "") == "bad_data")
                        bad_hit = hrow if is_bad else None
                    else:
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
            "latest": latest_stat,
            "run_id": int(run_id) if is_history else (latest_stat.get("run_id") if latest_stat else None),
            "is_history": is_history,
            "units": units,
            "svg_available": self._se_svg_path() is not None,
            "bad_data": bad_list,
            "bad_dev_ids": sorted(dev_id for dev_id, item in devices_out.items() if item["has_bad"]),
            "devices": devices_out,
        }

    def _build_se_balance(self, *, run_id: int | None = None) -> dict[str, Any]:
        """按合位开关归并拓扑计算母线，计算全网交/直流母线 KCL 功率平衡（实测与估计）及可观测诊断，支持历史断面回放。"""
        repo = self._se_repo()
        se_task = getattr(self.config, "tasks", {}).get("se")
        model_file = getattr(se_task, "model_file", None)
        meas_file = getattr(se_task, "measurement_file", None)
        snap = repo.se_topology_snapshot()
        latest_stat = snap.get("latest")
        latest_rid = int(latest_stat["run_id"]) if latest_stat and latest_stat.get("run_id") is not None else None
        is_history = run_id is not None and (latest_rid is None or int(run_id) != latest_rid)

        devices_by_type = snap.get("devices_by_type") or {}
        units = {"u_unit": "V", "p_unit": "kW", "i_unit": "A", "q_unit": "kvar"}
        model_tables: dict[str, dict] = {}
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
            except (ValueError, OSError, input_store.sqlite3.Error):
                pass

        # 1. 构建各设备 (device_type, idx) -> 实测/估计指标字典（兼容历史断面回放）
        dev_se_map: dict[tuple[str, int], dict[str, Any]] = {}
        bad_dev_set: set[tuple[str, int]] = set()
        if is_history:
            hist_pack = repo.se_run_measurements_raw(int(run_id))
            if hist_pack.get("stat"):
                latest_stat = hist_pack["stat"]
            hist_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
            for hrow in hist_pack.get("rows") or ():
                hist_by_key[(str(hrow.get("device_type") or ""), str(hrow.get("device_name") or ""), str(hrow.get("meas_type") or ""))] = hrow
            for dt, metric_map in input_store.SE_DEVICE_RESULT_METRICS.items():
                for r in devices_by_type.get(dt) or ():
                    if r.get("idx") is None:
                        continue
                    idx = int(r["idx"])
                    dname = str(r.get("name", ""))
                    rec: dict[str, Any] = {"idx": idx, "name": dname}
                    for mk, se_code in metric_map.items():
                        hrow = hist_by_key.get((dt, dname, se_code))
                        rec[f"{mk}_meas"] = hrow.get("meas_value") if hrow else None
                        rec[f"{mk}_se"] = hrow.get("se_value") if hrow else None
                        if hrow and str(hrow.get("source") or "") == "bad_data":
                            bad_dev_set.add((dt, idx))
                    dev_se_map[(dt, idx)] = rec
        else:
            dev_se_map = {
                (dt, int(r["idx"])): r
                for dt, rlist in devices_by_type.items()
                for r in rlist
                if r.get("idx") is not None
            }
            bad_dev_set = {
                (str(b.get("device_type") or ""), int(b["device_idx"]))
                for b in (snap.get("bad_data") or ())
                if b.get("device_idx") is not None
            }

        # 2. 收集物理节点集合（来自最新设备表 + 模型表）
        node_info: dict[tuple[str, int], dict[str, Any]] = {}
        for node_tbl, domain, v_key in (("ACNode", "AC", "uab"), ("DCNode", "DC", "u")):
            for row in devices_by_type.get(node_tbl) or ():
                idx = int(row["idx"])
                rec = dev_se_map.get((node_tbl, idx)) or row
                node_info[(node_tbl, idx)] = {
                    "device_type": node_tbl,
                    "domain": domain,
                    "idx": idx,
                    "name": str(row.get("name", "")),
                    "v_meas": rec.get(f"{v_key}_meas"),
                    "v_se": rec.get(f"{v_key}_se"),
                }
            for mrow in (model_tables.get(node_tbl) or {}).get("rows") or ():
                if mrow.get("idx") is None:
                    continue
                idx = int(mrow["idx"])
                if (node_tbl, idx) not in node_info:
                    node_info[(node_tbl, idx)] = {
                        "device_type": node_tbl,
                        "domain": domain,
                        "idx": idx,
                        "name": str(mrow.get("name", "")),
                        "v_meas": None,
                        "v_se": None,
                    }

        # 3. 收集开关实时状态（优先级：人工伪状态 > SCADA 遥信 > 模型默认 status）并用并查集归并拓扑母线
        scada_brk_status: dict[tuple[str, int], int] = {}
        if meas_file and input_store.is_scdfe_d_wide_db(meas_file):
            try:
                with input_store.connect(meas_file, readonly=True) as conn:
                    conn.execute("PRAGMA query_only=ON")
                    for brk_tbl in ("ACBreak", "DCBreak"):
                        cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{brk_tbl}")')}
                        if {"idx", "position", "position_qual"} <= cols:
                            notuse_expr = '"position_notuse"' if "position_notuse" in cols else "0"
                            for r in conn.execute(f'SELECT idx, position, position_qual, {notuse_expr} AS nu FROM "{brk_tbl}"'):
                                if r["position"] is not None and r["position_qual"] == 0 and not r["nu"]:
                                    scada_brk_status[(brk_tbl, int(r["idx"]))] = int(r["position"])
            except (OSError, input_store.sqlite3.Error):
                pass

        pseudo_stat_by_idx: dict[tuple[str, int], int] = {}
        pseudo_stat_by_name: dict[tuple[str, str], int] = {}
        try:
            for ps in repo.se_pseudo_stat_list(enabled_only=True):
                dt = str(ps.get("device_type") or "")
                sv = int(ps.get("stat_value", 1))
                if ps.get("device_idx") is not None:
                    pseudo_stat_by_idx[(dt, int(ps["device_idx"]))] = sv
                if ps.get("dev_name"):
                    pseudo_stat_by_name[(dt, str(ps["dev_name"]))] = sv
        except (OSError, input_store.sqlite3.Error, AttributeError):
            pass

        parent: dict[tuple[str, int], tuple[str, int]] = {k: k for k in node_info}

        def _find(k: tuple[str, int]) -> tuple[str, int]:
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        def _union(a: tuple[str, int], b: tuple[str, int]) -> None:
            if a in parent and b in parent:
                ra, rb = _find(a), _find(b)
                if ra != rb:
                    if ra[1] < rb[1]:
                        parent[rb] = ra
                    else:
                        parent[ra] = rb

        for sw_tbl, node_tbl in (("ACBreak", "ACNode"), ("ACSwitch", "ACNode"), ("DCBreak", "DCNode"), ("DCSwitch", "DCNode")):
            for mrow in (model_tables.get(sw_tbl) or {}).get("rows") or ():
                i_n = mrow.get("i_node")
                j_n = mrow.get("j_node")
                if i_n is None or j_n is None:
                    continue
                d_idx = int(mrow["idx"]) if mrow.get("idx") is not None else None
                d_name = str(mrow.get("name") or "")
                raw_st = mrow.get("status", mrow.get("run_stat", 1))
                st = int(raw_st) if raw_st is not None else 1
                if d_idx is not None and (sw_tbl, d_idx) in scada_brk_status:
                    st = scada_brk_status[(sw_tbl, d_idx)]
                if d_idx is not None and (sw_tbl, d_idx) in pseudo_stat_by_idx:
                    st = pseudo_stat_by_idx[(sw_tbl, d_idx)]
                elif d_name and (sw_tbl, d_name) in pseudo_stat_by_name:
                    st = pseudo_stat_by_name[(sw_tbl, d_name)]
                if st != 0:
                    _union((node_tbl, int(i_n)), (node_tbl, int(j_n)))

        # 收集实母线映射（用于命名计算母线与潮流图定位）
        real_bus_by_node: dict[tuple[str, int], list[tuple[str, str]]] = {}
        for bs_tbl, node_tbl in (("ACRealBs", "ACNode"), ("DCRealBs", "DCNode")):
            for mrow in (model_tables.get(bs_tbl) or {}).get("rows") or ():
                if mrow.get("idx") is not None and mrow.get("node") is not None:
                    real_bus_by_node.setdefault((node_tbl, int(mrow["node"])), []).append(
                        (f"{bs_tbl}-{int(mrow['idx'])}", str(mrow.get("name") or f"{bs_tbl}#{mrow['idx']}"))
                    )

        # 按根归组生成拓扑计算母线容器
        groups: dict[tuple[str, int], list[tuple[str, int]]] = {}
        for nk in node_info:
            groups.setdefault(_find(nk), []).append(nk)

        buses: dict[tuple[str, int], dict[str, Any]] = {}
        for root, members in groups.items():
            members.sort(key=lambda x: x[1])
            node_tbl = root[0]
            domain = "AC" if node_tbl == "ACNode" else "DC"
            real_hits: list[tuple[str, str, tuple[str, int]]] = []
            for mk in members:
                for rb_id, rb_name in real_bus_by_node.get(mk, ()):
                    real_hits.append((rb_id, rb_name, mk))

            rep_key = real_hits[0][2] if real_hits else members[0]
            rep_info = node_info[rep_key]
            bus_name = " / ".join(dict.fromkeys(h[1] for h in real_hits)) if real_hits else rep_info["name"]
            focus_dev_id = real_hits[0][0] if real_hits else f"{node_tbl}-{rep_info['idx']}"

            v_meas = rep_info["v_meas"]
            v_se = rep_info["v_se"]
            v_cnt = 0
            bad_cnt = 0
            for mk in members:
                ni = node_info[mk]
                if ni["v_meas"] is not None:
                    v_cnt += 1
                    if v_meas is None:
                        v_meas = ni["v_meas"]
                if ni["v_se"] is not None and v_se is None:
                    v_se = ni["v_se"]
                if mk in bad_dev_set:
                    bad_cnt += 1

            buses[root] = {
                "dev_id": f"{node_tbl}-{rep_info['idx']}",
                "focus_dev_id": focus_dev_id,
                "member_node_ids": [f"{mk[0]}-{mk[1]}" for mk in members],
                "node_cnt": len(members),
                "device_type": node_tbl,
                "domain": domain,
                "idx": rep_info["idx"],
                "name": bus_name,
                "v_meas": v_meas,
                "v_se": v_se,
                "p_in_meas": 0.0,
                "p_out_meas": 0.0,
                "p_in_se": 0.0,
                "p_out_se": 0.0,
                "q_in_meas": 0.0,
                "q_out_meas": 0.0,
                "q_in_se": 0.0,
                "q_out_se": 0.0,
                "p_meas_cnt": 0,
                "q_meas_cnt": 0,
                "meas_cnt": v_cnt,
                "branch_cnt": 0,
                "bad_cnt": bad_cnt,
            }

        def _bus_of(node_tbl: str, node_idx: Any) -> tuple[str, int] | None:
            if node_idx is None:
                return None
            key = (node_tbl, int(node_idx))
            return _find(key) if key in parent else None

        def _add_flow(root_key: tuple[str, int] | None, *, sign: float, p_m: Any, p_s: Any, q_m: Any = None, q_s: Any = None, is_branch: bool = False, has_bad: bool = False):
            if root_key is None:
                return
            bus = buses.get(root_key)
            if bus is None:
                return
            if is_branch:
                bus["branch_cnt"] += 1
            if has_bad:
                bus["bad_cnt"] += 1
            if isinstance(p_m, (int, float)) and math.isfinite(p_m):
                bus["p_meas_cnt"] += 1
                bus["meas_cnt"] += 1
                net_pm = sign * float(p_m)
                if net_pm >= 0:
                    bus["p_in_meas"] += net_pm
                else:
                    bus["p_out_meas"] += -net_pm
            if isinstance(p_s, (int, float)) and math.isfinite(p_s):
                net_ps = sign * float(p_s)
                if net_ps >= 0:
                    bus["p_in_se"] += net_ps
                else:
                    bus["p_out_se"] += -net_ps
            if isinstance(q_m, (int, float)) and math.isfinite(q_m):
                bus["q_meas_cnt"] += 1
                bus["meas_cnt"] += 1
                net_qm = sign * float(q_m)
                if net_qm >= 0:
                    bus["q_in_meas"] += net_qm
                else:
                    bus["q_out_meas"] += -net_qm
            if isinstance(q_s, (int, float)) and math.isfinite(q_s):
                net_qs = sign * float(q_s)
                if net_qs >= 0:
                    bus["q_in_se"] += net_qs
                else:
                    bus["q_out_se"] += -net_qs

        # 4. 汇总电源（注入 +1）与负荷（汇出 -1）
        for dev_tbl, node_tbl, sign, has_q in (
            ("ACGenerator", "ACNode", +1.0, True),
            ("DCGenerator", "DCNode", +1.0, False),
            ("ACLoad", "ACNode", -1.0, True),
            ("DCLoad", "DCNode", -1.0, False),
        ):
            for mrow in (model_tables.get(dev_tbl) or {}).get("rows") or ():
                d_idx = mrow.get("idx")
                if d_idx is None:
                    continue
                rec = dev_se_map.get((dev_tbl, int(d_idx))) or {}
                _add_flow(
                    _bus_of(node_tbl, mrow.get("node")),
                    sign=sign,
                    p_m=rec.get("p_meas"),
                    p_s=rec.get("p_se"),
                    q_m=rec.get("q_meas") if has_q else None,
                    q_s=rec.get("q_se") if has_q else None,
                    has_bad=(dev_tbl, int(d_idx)) in bad_dev_set,
                )

        # 5. 汇总支路与 DC/DC 换流器（离开母线为汇出 -1；忽略两端归并到同一母线的内部环）
        for dev_tbl, node_tbl, has_q in (
            ("ACBranch", "ACNode", True),
            ("ACZeroBranch", "ACNode", True),
            ("DCBranch", "DCNode", False),
            ("DCDCConverter", "DCNode", False),
        ):
            for mrow in (model_tables.get(dev_tbl) or {}).get("rows") or ():
                d_idx = mrow.get("idx")
                if d_idx is None:
                    continue
                ri = _bus_of(node_tbl, mrow.get("i_node"))
                rj = _bus_of(node_tbl, mrow.get("j_node"))
                if ri is not None and ri == rj:
                    continue
                rec = dev_se_map.get((dev_tbl, int(d_idx))) or {}
                hb = (dev_tbl, int(d_idx)) in bad_dev_set
                _add_flow(ri, sign=-1.0, p_m=rec.get("i_p_meas"), p_s=rec.get("i_p_se"), q_m=rec.get("i_q_meas") if has_q else None, q_s=rec.get("i_q_se") if has_q else None, is_branch=True, has_bad=hb)
                _add_flow(rj, sign=-1.0, p_m=rec.get("j_p_meas"), p_s=rec.get("j_p_se"), q_m=rec.get("j_q_meas") if has_q else None, q_s=rec.get("j_q_se") if has_q else None, is_branch=True, has_bad=hb)

        # 6. 汇总交直流换流器 DCACConverter
        for mrow in (model_tables.get("DCACConverter") or {}).get("rows") or ():
            d_idx = mrow.get("idx")
            if d_idx is None:
                continue
            rec = dev_se_map.get(("DCACConverter", int(d_idx))) or {}
            hb = ("DCACConverter", int(d_idx)) in bad_dev_set
            _add_flow(_bus_of("ACNode", mrow.get("ac_node")), sign=-1.0, p_m=rec.get("ac_p_meas"), p_s=rec.get("ac_p_se"), q_m=rec.get("ac_q_meas"), q_s=rec.get("ac_q_se"), is_branch=True, has_bad=hb)
            _add_flow(_bus_of("DCNode", mrow.get("dc_node")), sign=-1.0, p_m=rec.get("dc_p_meas"), p_s=rec.get("dc_p_se"), is_branch=True, has_bad=hb)

        p_thresh = {"W": 5000.0, "kW": 5.0, "MW": 0.005}.get(units["p_unit"], 5.0)
        out_rows = []
        imbalanced_cnt = 0
        low_obs_cnt = 0
        max_dp_meas = 0.0
        for b in buses.values():
            dp_meas = (b["p_in_meas"] - b["p_out_meas"]) if b["p_meas_cnt"] > 0 else None
            dp_se = b["p_in_se"] - b["p_out_se"]
            dq_meas = (b["q_in_meas"] - b["q_out_meas"]) if (b["domain"] == "AC" and b["q_meas_cnt"] > 0) else None
            dq_se = (b["q_in_se"] - b["q_out_se"]) if b["domain"] == "AC" else None
            scale = max(abs(b["p_in_meas"]), abs(b["p_out_meas"]), abs(b["p_in_se"]), abs(b["p_out_se"]), 1.0)
            is_imb = dp_meas is not None and abs(dp_meas) > max(p_thresh, 0.08 * scale)
            low_obs = b["meas_cnt"] == 0
            if is_imb:
                imbalanced_cnt += 1
            if low_obs:
                low_obs_cnt += 1
            if dp_meas is not None and abs(dp_meas) > max_dp_meas:
                max_dp_meas = abs(dp_meas)
            out_rows.append({
                **b,
                "dp_meas": dp_meas,
                "dp_se": dp_se,
                "dq_meas": dq_meas,
                "dq_se": dq_se,
                "imbalanced": is_imb,
                "low_obs": low_obs,
            })
        out_rows.sort(key=lambda r: (0 if r["imbalanced"] else 1, -(abs(r["dp_meas"]) if r["dp_meas"] is not None else -1.0), r["device_type"], r["idx"]))
        return {
            "latest": latest_stat,
            "run_id": int(run_id) if is_history else latest_rid,
            "is_history": is_history,
            "units": units,
            "summary": {
                "bus_total": len(out_rows),
                "raw_node_total": len(node_info),
                "imbalanced_count": imbalanced_cnt,
                "low_obs_count": low_obs_cnt,
                "max_dp_meas": round(max_dp_meas, 3),
                "p_threshold": p_thresh,
            },
            "rows": out_rows,
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
                if parsed.path == "/api/se/home":
                    import socket

                    summary = se_repo.se_home_summary(para_file, period)
                    st = self.scheduler.status() if callable(getattr(self.scheduler, "status", None)) else {}
                    summary["runtime"] = {
                        "host": socket.gethostname(),
                        "scenario": str(getattr(self.config, "scenario", "") or ""),
                        "runtime": str(getattr(self.config, "runtime", "") or ""),
                        "daemon_running": bool(self._daemon_thread and self._daemon_thread.is_alive()),
                        "se_busy": "se" in set(st.get("active_tasks") or ()) | set(st.get("pending_tasks") or ()),
                    }
                    return {"ok": True, "data": summary}
                if parsed.path == "/api/se/devices":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": se_repo.se_devices(
                            query.get("type", [None])[0] or None,
                            q=query.get("q", [""])[0],
                            bad_only=query.get("bad_only", ["0"])[0] in {"1", "true"},
                            run_id=rid_val,
                        ),
                    }
                if parsed.path == "/api/se/measurements":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": se_repo.se_measurements_browse(
                            source=query.get("source", ["all"])[0],
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                            sort=query.get("sort", ["abs_residual"])[0],
                            direction=query.get("direction", ["desc"])[0],
                            high_residual_only=query.get("high_residual_only", ["0"])[0] in {"1", "true"},
                            run_id=rid_val,
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/se/runs/converged":
                    return {"ok": True, "data": se_repo.se_converged_runs(_int_query(query, "limit", 30, 1, 200))}
                if parsed.path == "/api/se/balance":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {"ok": True, "data": self._build_se_balance(run_id=rid_val)}
                if parsed.path == "/api/se/weights":
                    return {
                        "ok": True,
                        "data": se_repo.se_weight_rules(
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
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
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {"ok": True, "data": self._build_se_topology_values(run_id=rid_val)}
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
                    bad_hist = se_repo.se_history_bad_data(_int_query(query, "limit", 100, 1, 500))
                    return {
                        "ok": True,
                        "data": {
                            "history": bad_hist,
                            "trend": bad_hist.get("series") or [],
                        },
                    }
                # --- 预过滤量测模块 API ---
                if parsed.path == "/api/se/prefilter/overview":
                    return {"ok": True, "data": se_repo.se_prefilter_overview()}
                if parsed.path == "/api/se/prefilter/results":
                    return {
                        "ok": True,
                        "data": se_repo.se_prefilter_results(
                            origin=query.get("origin", ["all"])[0],
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                            limit=_int_query(query, "limit", 100, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/se/prefilter/rules":
                    return {
                        "ok": True,
                        "data": se_repo.se_prefilter_rules(
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                            device_type=query.get("device_type", [""])[0],
                            rule_type=query.get("rule_type", [""])[0],
                            q=query.get("q", [""])[0],
                        ),
                    }
                if parsed.path == "/api/se/prefilter/analysis":
                    return {
                        "ok": True,
                        "data": se_repo.se_prefilter_analysis(limit=_int_query(query, "limit", 60, 1, 300)),
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
        # --- 在线潮流分析（LF）专用只读 API ---
        if parsed.path.startswith("/api/lf/"):
            lf_repo = self._lf_repo()
            lf_task = getattr(self.config, "tasks", {}).get("lf")
            lf_para_file = getattr(lf_task, "parameter_file", None)
            lf_period = getattr(lf_task, "period_seconds", 60)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/lf/home":
                    return {"ok": True, "data": lf_repo.lf_home_summary(lf_para_file, do_cycle=lf_period)}
                if parsed.path == "/api/lf/runs/converged":
                    return {"ok": True, "data": lf_repo.lf_converged_runs(_int_query(query, "limit", 30, 1, 200))}
                if parsed.path == "/api/lf/topology-values":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {"ok": True, "data": self._build_lf_topology_values(run_id=rid_val)}
                if parsed.path == "/api/lf/results":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": lf_repo.lf_results_browse(
                            kind=query.get("kind", ["branches"])[0],
                            domain=query.get("domain", ["all"])[0],
                            device_type=query.get("device_type", [""])[0],
                            only_abnormal=query.get("only_abnormal", ["0"])[0] in {"1", "true"},
                            q=query.get("q", [""])[0],
                            run_id=rid_val,
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/lf/history/stats":
                    return {"ok": True, "data": lf_repo.lf_history_stats(_int_query(query, "limit", 100, 1, 500))}
                if parsed.path == "/api/lf/params":
                    return {"ok": True, "data": lf_repo.lf_params_get(lf_para_file, do_cycle=lf_period)}
                if parsed.path == "/api/lf/overrides":
                    return {
                        "ok": True,
                        "data": lf_repo.lf_overrides_list(
                            scheme_name=query.get("scheme_name", [""])[0],
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                        ),
                    }
                if parsed.path == "/api/lf/model-catalog":
                    from .lf_online import LF_OVERRIDE_FIELDS
                    cat = self._se_model_catalog()
                    return {"ok": True, "data": {**cat, "override_fields": {k: list(v) for k, v in LF_OVERRIDE_FIELDS.items()}}}
                if parsed.path == "/api/lf/logs":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": lf_repo.lf_logs_list(
                            level=query.get("level", [""])[0],
                            stage=query.get("stage", [""])[0],
                            source=query.get("source", [""])[0],
                            run_id=rid_val,
                            window=query.get("window", ["all"])[0],
                            q=query.get("q", [""])[0],
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/lf/logs/summary":
                    return {"ok": True, "data": lf_repo.lf_logs_summary()}
                if parsed.path == "/api/lf/logs/policy":
                    return {"ok": True, "data": lf_repo.lf_logs_policy_get()}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        # --- 南极气象条件与环境工况耦合只读 API ---
        if parsed.path == "/api/weather/current":
            try:
                return {"ok": True, "data": self._weather_summary(include_presets=True)}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        # --- 顶栏中央主标题徽牌定制配置（持久化至 pas_config） ---
        if parsed.path == "/api/ui/branding":
            return {"ok": True, "data": self._get_ui_branding()}
        if parsed.path == "/api/weather/history":
            try:
                query = parse_qs(parsed.query)
                limit = _int_query(query, "limit", 60, 1, 500)
                return {"ok": True, "data": self._weather_repo().weather_history_list(limit=limit)}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        # --- 全平台 SE → LF → CA 链路态势与深度洞察只读 API ---
        if parsed.path == "/api/pipeline/status":
            try:
                overview = self._build_pipeline_overview()
                enriched = platform_insights.enrich_pipeline_status(self, overview)
                enriched["weather"] = self._weather_summary(include_presets=False)
                return {"ok": True, "data": enriched}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if parsed.path == "/api/device/profile":
            try:
                query = parse_qs(parsed.query)
                dev_name = query.get("name", [""])[0].strip()
                return {"ok": True, "data": platform_insights.build_device_profile(self, dev_name)}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if parsed.path == "/api/diff":
            try:
                query = parse_qs(parsed.query)
                mod = query.get("module", ["lf"])[0]
                a_raw = query.get("a", [""])[0].strip()
                b_raw = query.get("b", [""])[0].strip()
                return {
                    "ok": True,
                    "data": platform_insights.build_snapshot_diff(
                        self,
                        mod,
                        run_a=_int_path(a_raw) if a_raw else None,
                        run_b=_int_path(b_raw) if b_raw else None,
                    ),
                }
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if parsed.path == "/api/datasources/health":
            try:
                return {"ok": True, "data": platform_insights.build_datasource_health(self)}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        # --- 在线静态安全分析（CA）专用只读 API ---
        if parsed.path.startswith("/api/ca/"):
            ca_repo = self._ca_repo()
            ca_task = getattr(self.config, "tasks", {}).get("ca")
            ca_period = getattr(ca_task, "period_seconds", 300)
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/ca/home":
                    data = ca_repo.ca_home_summary(do_cycle=ca_period)
                    data["weather"] = self._weather_summary(include_presets=False)
                    return {"ok": True, "data": data}
                if parsed.path == "/api/ca/health/history":
                    return {"ok": True, "data": ca_repo.ca_health_history(_int_query(query, "limit", 100, 1, 500))}
                if parsed.path == "/api/ca/runs/history":
                    return {"ok": True, "data": ca_repo.ca_runs_history(_int_query(query, "limit", 30, 1, 200))}
                if parsed.path == "/api/ca/topology-risks":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {"ok": True, "data": self._build_ca_topology_risks(run_id=rid_val)}
                if parsed.path == "/api/ca/risks":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": ca_repo.ca_risks_browse(
                            category=query.get("category", ["all"])[0],
                            severity=query.get("severity", ["all"])[0],
                            risk_category=query.get("risk_category", ["all"])[0],
                            q=query.get("q", [""])[0],
                            run_id=rid_val,
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/ca/contingencies/results":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": ca_repo.ca_contingency_results_browse(
                            category=query.get("category", ["all"])[0],
                            severity=query.get("severity", ["all"])[0],
                            only_risk=query.get("only_risk", ["0"])[0] in {"1", "true"},
                            q=query.get("q", [""])[0],
                            run_id=rid_val,
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/ca/contingencies/defs":
                    return {
                        "ok": True,
                        "data": ca_repo.ca_contingencies_list(
                            category=query.get("category", [""])[0],
                            enabled_only=query.get("enabled_only", ["0"])[0] in {"1", "true"},
                            device_type=query.get("device_type", [""])[0],
                            q=query.get("q", [""])[0],
                        ),
                    }
                if parsed.path == "/api/ca/model-catalog":
                    from .ca_online import CONTINGENCY_DEVICE_TABLES
                    from .weather_coupling import WEATHER_PERTURBATION_KINDS
                    cat = self._se_model_catalog()
                    return {
                        "ok": True,
                        "data": {
                            **cat,
                            "contingency_types": [
                                {"type": k, "label": v[0], "priority": v[1]}
                                for k, v in CONTINGENCY_DEVICE_TABLES.items()
                            ],
                            "weather_kinds": [
                                {"kind": k, "label": v}
                                for k, v in WEATHER_PERTURBATION_KINDS.items()
                            ],
                        },
                    }
                if parsed.path == "/api/ca/params":
                    return {"ok": True, "data": ca_repo.ca_params_get(do_cycle=ca_period)}
                if parsed.path == "/api/ca/history/stats":
                    return {"ok": True, "data": ca_repo.ca_history_stats(_int_query(query, "limit", 100, 1, 500))}
                if parsed.path == "/api/ca/logs":
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    return {
                        "ok": True,
                        "data": ca_repo.ca_logs_list(
                            level=query.get("level", [""])[0],
                            stage=query.get("stage", [""])[0],
                            source=query.get("source", [""])[0],
                            run_id=rid_val,
                            window=query.get("window", ["all"])[0],
                            q=query.get("q", [""])[0],
                            limit=_int_query(query, "limit", 50, 1, 500),
                            offset=_int_query(query, "offset", 0, 0, 1_000_000),
                        ),
                    }
                if parsed.path == "/api/ca/logs/summary":
                    return {"ok": True, "data": ca_repo.ca_logs_summary()}
                if parsed.path == "/api/ca/logs/policy":
                    return {"ok": True, "data": ca_repo.ca_logs_policy_get()}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
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
            query = parse_qs(parsed.query)
            lite = query.get("lite", ["0"])[0] in {"1", "true"}
            scheduler_status = self.scheduler.status() if callable(getattr(self.scheduler, "status", None)) else {}
            health_fn = getattr(self.repository, "health", None)
            if callable(health_fn):
                try:
                    raw_databases = health_fn(lite=lite)
                except TypeError:
                    raw_databases = health_fn()
            else:
                raw_databases = {}
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
                latest = self.repository.list_runs(1, name) if (not lite and callable(getattr(self.repository, "list_runs", None))) else []
                tasks[name] = {
                    "enabled": bool(getattr(task, "enabled", False)),
                    "inputs_ready": not missing,
                    "missing_inputs": missing,
                    "latest_run": latest[0] if latest else None,
                }
                input_path=getattr(task,'measurement_file' if name=='se' else 'limit_file',None)
                if not lite and name in ('se','ca') and input_path and Path(input_path).suffix.lower() in input_store.SQLITE_SUFFIXES and Path(input_path).is_file():
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
                if path == "/api/se/bad/policies/batch":
                    items = payload.get("items") or []
                    return {"ok": True, "data": se_repo.se_bad_policy_batch_save(items)}
                if path == "/api/se/prefilter/rules/batch":
                    items = payload.get("items") or []
                    return {"ok": True, "data": se_repo.se_prefilter_rule_batch_save(items)}
                if path == "/api/se/weights":
                    return {"ok": True, "data": se_repo.se_weight_rule_save(payload)}
                if len(parts) == 5 and parts[:3] == ["api", "se", "weights"] and parts[4] == "delete":
                    wid = _int_path(parts[3])
                    if wid is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": se_repo.se_weight_rule_delete(wid), "id": wid}}
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
                if path == "/api/se/prefilter/rules":
                    return {"ok": True, "data": se_repo.se_prefilter_rule_save(payload)}
                if len(parts) == 6 and parts[:4] == ["api", "se", "prefilter", "rules"] and parts[5] == "delete":
                    rid = _int_path(parts[4])
                    if rid is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": se_repo.se_prefilter_rule_delete(rid), "id": rid}}
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
        # --- 在线潮流分析（LF）写接口 ---
        if path.startswith("/api/lf/"):
            lf_repo = self._lf_repo()
            lf_task = getattr(self.config, "tasks", {}).get("lf")
            lf_para_file = getattr(lf_task, "parameter_file", None)
            parts = path.strip("/").split("/")
            try:
                if path == "/api/lf/params":
                    return {"ok": True, "data": lf_repo.lf_params_save(payload, lf_para_file)}
                if path == "/api/lf/params/reset":
                    return {"ok": True, "data": lf_repo.lf_params_reset(lf_para_file)}
                if path == "/api/lf/overrides":
                    return {"ok": True, "data": lf_repo.lf_override_save(payload)}
                if path == "/api/lf/overrides/clear":
                    return {"ok": True, "data": {"deleted": lf_repo.lf_overrides_clear(scheme_name=str(payload.get("scheme_name") or ""))}}
                if len(parts) == 5 and parts[:3] == ["api", "lf", "overrides"] and parts[4] == "delete":
                    oid = _int_path(parts[3])
                    if oid is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": lf_repo.lf_override_delete(oid), "id": oid}}
                if path == "/api/lf/logs/policy":
                    return {"ok": True, "data": lf_repo.lf_logs_policy_update(payload)}
                if path == "/api/lf/logs/purge":
                    return {
                        "ok": True,
                        "data": lf_repo.lf_logs_purge(
                            dry_run=bool(payload.get("dry_run", False)),
                            retention_days=int(payload["retention_days"]) if payload.get("retention_days") not in (None, "") else None,
                            keep_error_days=int(payload["keep_error_days"]) if payload.get("keep_error_days") not in (None, "") else None,
                            max_rows=int(payload["max_rows"]) if payload.get("max_rows") not in (None, "") else None,
                            source="operator",
                        ),
                    }
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        # --- 全平台 SE → LF → CA 级联配置与一键串联写接口 ---
        if path == "/api/pipeline/cascade":
            updater = getattr(self.scheduler, "update_cascade_policy", None)
            if not callable(updater):
                return {"ok": False, "error": "cascade_not_supported"}
            try:
                res = updater(
                    se_to_lf=bool(payload["se_to_lf"]) if "se_to_lf" in payload else None,
                    lf_to_ca=bool(payload["lf_to_ca"]) if "lf_to_ca" in payload else None,
                )
                return {"ok": True, "data": res}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if path == "/api/actions/run-chain":
            raw_tasks = payload.get("tasks")
            if isinstance(raw_tasks, list) and raw_tasks:
                tasks = tuple(str(t) for t in raw_tasks if str(t) in ("se", "lf", "ca"))
            else:
                tasks = ("se", "lf", "ca")
            if not tasks:
                return {"ok": False, "error": "invalid_tasks"}
            if payload.get("async", False):
                submitter = getattr(self.scheduler, "submit_chain_async", None)
                if not callable(submitter):
                    return {"ok": False, "error": "chain_not_supported"}
                return {"ok": True, "data": submitter(tasks)}
            runner = getattr(self.scheduler, "run_chain", None)
            if not callable(runner):
                return {"ok": False, "error": "chain_not_supported"}
            res = runner(tasks)
            return {"ok": bool(res.get("ok")), "error": None if res.get("ok") else "链路执行中断", "data": res}
        # --- 在线静态安全分析（CA）写接口 ---
        if path.startswith("/api/ca/"):
            ca_repo = self._ca_repo()
            ca_task = getattr(self.config, "tasks", {}).get("ca")
            parts = path.strip("/").split("/")
            try:
                if path == "/api/ca/params":
                    return {"ok": True, "data": ca_repo.ca_params_save(payload)}
                if path == "/api/ca/params/reset":
                    return {"ok": True, "data": ca_repo.ca_params_reset()}
                if path == "/api/ca/contingencies/defs":
                    return {"ok": True, "data": ca_repo.ca_contingency_save(payload)}
                if path == "/api/ca/contingencies/sync":
                    model_file = getattr(ca_task, "model_file", None)
                    if not model_file or not Path(model_file).is_file():
                        return {"ok": False, "error": "model_file_not_found"}
                    mt = read_model_tables(Path(model_file))
                    dts = payload.get("device_types") if isinstance(payload.get("device_types"), list) else None
                    return {
                        "ok": True,
                        "data": ca_repo.ca_contingencies_sync(mt, device_types=dts, overwrite=bool(payload.get("overwrite", False))),
                    }
                if path == "/api/ca/contingencies/seed-weather":
                    return {
                        "ok": True,
                        "data": ca_repo.ca_contingencies_seed_weather(overwrite=bool(payload.get("overwrite", False))),
                    }
                if path == "/api/ca/contingencies/bulk-toggle":
                    return {
                        "ok": True,
                        "data": {
                            "updated": ca_repo.ca_contingencies_bulk_toggle(
                                enabled=bool(payload.get("enabled", True)),
                                category=str(payload.get("category") or ""),
                                device_type=str(payload.get("device_type") or ""),
                            )
                        },
                    }
                if path == "/api/ca/contingencies/clear":
                    return {
                        "ok": True,
                        "data": {"deleted": ca_repo.ca_contingencies_clear(only_auto=bool(payload.get("only_auto", False)))},
                    }
                if len(parts) == 6 and parts[:4] == ["api", "ca", "contingencies", "defs"] and parts[5] == "delete":
                    cid = _int_path(parts[4])
                    if cid is None:
                        return {"ok": False, "error": "invalid_id"}
                    return {"ok": True, "data": {"deleted": ca_repo.ca_contingency_delete(cid), "id": cid}}
                if path == "/api/ca/logs/policy":
                    return {"ok": True, "data": ca_repo.ca_logs_policy_update(payload)}
                if path == "/api/ca/logs/purge":
                    return {
                        "ok": True,
                        "data": ca_repo.ca_logs_purge(
                            dry_run=bool(payload.get("dry_run", False)),
                            retention_days=int(payload["retention_days"]) if payload.get("retention_days") not in (None, "") else None,
                            keep_error_days=int(payload["keep_error_days"]) if payload.get("keep_error_days") not in (None, "") else None,
                            max_rows=int(payload["max_rows"]) if payload.get("max_rows") not in (None, "") else None,
                            source="operator",
                        ),
                    }
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if path == "/api/weather/current":
            try:
                saved = self._weather_repo().weather_state_save(payload)
                summary = self._weather_summary(include_presets=True, state_override=saved)
                ca_job = None
                if bool(payload.get("trigger_ca", False)) and callable(getattr(self.scheduler, "trigger_task_async", None)):
                    ca_job = self.scheduler.trigger_task_async("ca")
                return {"ok": True, "data": {**summary, "ca_job": ca_job}}
            except (ValueError, TypeError, OSError, input_store.sqlite3.Error) as exc:
                return {"ok": False, "error": str(exc)}
        if path == "/api/ui/branding":
            try:
                return {"ok": True, "data": self._save_ui_branding(payload)}
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
                err_msg = None
                if not ok:
                    st = self.scheduler.status() if callable(getattr(self.scheduler, "status", None)) else {}
                    jobs = [j for j in (st.get("jobs") or ()) if j.get("task") == task]
                    if jobs and jobs[-1].get("error_message"):
                        err_msg = str(jobs[-1]["error_message"])
                    elif callable(getattr(self.repository, "list_runs", None)):
                        recent = self.repository.list_runs(1, task)
                        if recent and recent[0].get("error_message"):
                            err_msg = str(recent[0]["error_message"])
                    err_msg = err_msg or f"{task.upper()} 计算执行失败"
                return {
                    "ok": ok,
                    "error": err_msg,
                    "data": {"task": task, "success": ok, "execution_source": "manual", "error_message": err_msg},
                }
            trigger_all = getattr(self.scheduler, "trigger_all", None)
            result = trigger_all() if callable(trigger_all) else self.scheduler.run_once()
            all_ok = bool(result) and all(result.values())
            return {
                "ok": all_ok,
                "error": None if all_ok else "部分分析任务执行失败",
                "data": {"results": result, "execution_source": "manual"},
            }
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
            if len(parts) == 5 and parts[:4] == ["api", "se", "prefilter", "rules"]:
                rid = _int_path(parts[4])
                if rid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": se_repo.se_prefilter_rule_save(payload, rule_id=rid)}
            if len(parts) == 4 and parts[:3] == ["api", "se", "weights"]:
                wid = _int_path(parts[3])
                if wid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": se_repo.se_weight_rule_save(payload, rule_id=wid)}
            if len(parts) == 4 and parts[:3] == ["api", "lf", "overrides"]:
                oid = _int_path(parts[3])
                if oid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": self._lf_repo().lf_override_save(payload, override_id=oid)}
            if len(parts) == 5 and parts[:4] == ["api", "ca", "contingencies", "defs"]:
                cid = _int_path(parts[4])
                if cid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": self._ca_repo().ca_contingency_save(payload, contingency_id=cid)}
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
            if len(parts) == 5 and parts[:4] == ["api", "se", "prefilter", "rules"]:
                rid = _int_path(parts[4])
                if rid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": se_repo.se_prefilter_rule_delete(rid), "id": rid}}
            if len(parts) == 4 and parts[:3] == ["api", "se", "weights"]:
                wid = _int_path(parts[3])
                if wid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": se_repo.se_weight_rule_delete(wid), "id": wid}}
            if len(parts) == 4 and parts[:3] == ["api", "lf", "overrides"]:
                oid = _int_path(parts[3])
                if oid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": self._lf_repo().lf_override_delete(oid), "id": oid}}
            if len(parts) == 5 and parts[:4] == ["api", "ca", "contingencies", "defs"]:
                cid = _int_path(parts[4])
                if cid is None:
                    return {"ok": False, "error": "invalid_id"}
                return {"ok": True, "data": {"deleted": self._ca_repo().ca_contingency_delete(cid), "id": cid}}
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

            def _send_bytes(
                self,
                body: bytes,
                content_type: str,
                status: int = 200,
                *,
                etag: str | None = None,
                cache_control: str = "no-store",
                extra_headers: dict[str, str] | None = None,
            ):
                if etag and self.headers.get("If-None-Match") == etag:
                    self.send_response(HTTPStatus.NOT_MODIFIED)
                    self.send_header("ETag", etag)
                    self.send_header("Cache-Control", cache_control)
                    self.end_headers()
                    return
                accept_enc = self.headers.get("Accept-Encoding") or ""
                use_gzip = ("gzip" in accept_enc.lower()) and len(body) >= 1024
                payload = gzip.compress(body, compresslevel=6) if use_gzip else body
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                if use_gzip:
                    self.send_header("Content-Encoding", "gzip")
                    self.send_header("Vary", "Accept-Encoding")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", cache_control)
                if etag:
                    self.send_header("ETag", etag)
                if extra_headers:
                    for hk, hv in extra_headers.items():
                        self.send_header(hk, hv)
                self.end_headers()
                self.wfile.write(payload)

            def _send_json(self, payload: dict[str, Any], status: int = 200):
                body = json.dumps(_sanitize_json(payload), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")
                self._send_bytes(body, "application/json; charset=utf-8", status=status, cache_control="no-store")

            def _serve_sse(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "keep-alive")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                last_ver = ""
                last_ping = time.monotonic()
                deadline = time.monotonic() + 300.0
                try:
                    while time.monotonic() < deadline:
                        info = platform_insights.compute_event_version(app)
                        if info["version"] != last_ver:
                            last_ver = info["version"]
                            chunk = f"event: update\ndata: {json.dumps(info, ensure_ascii=False)}\n\n".encode("utf-8")
                            self.wfile.write(chunk)
                            self.wfile.flush()
                            last_ping = time.monotonic()
                        elif time.monotonic() - last_ping >= 15.0:
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                            last_ping = time.monotonic()
                        time.sleep(1.5)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                    pass

            def do_GET(self):  # noqa: N802
                parsed_get = urlparse(self.path)
                if parsed_get.path == "/api/events":
                    self._serve_sse()
                    return
                if parsed_get.path == "/api/report/snapshot":
                    try:
                        html_text = platform_insights.build_snapshot_report_html(app)
                        fname = f"pas-snapshot-{time.strftime('%Y%m%d-%H%M%S')}.html"
                        self._send_bytes(
                            html_text.encode("utf-8"),
                            "text/html; charset=utf-8",
                            extra_headers={"Content-Disposition": f'attachment; filename="{fname}"'},
                        )
                    except Exception as exc:
                        self._send_json({"ok": False, "error": str(exc)}, 500)
                    return
                if parsed_get.path == "/api/se/svg":
                    svg_path = app._se_svg_path()
                    if svg_path is None:
                        self._send_json({"ok": False, "error": "svg_not_found"}, 404)
                        return
                    st = svg_path.stat()
                    etag = f'W/"{st.st_mtime_ns:x}-{st.st_size:x}"'
                    self._send_bytes(
                        svg_path.read_bytes(),
                        "image/svg+xml; charset=utf-8",
                        etag=etag,
                        cache_control="no-cache",
                    )
                    return
                if parsed_get.path == "/api/se/measurements/export":
                    query = parse_qs(parsed_get.query)
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    body = app._se_repo().se_measurements_export_csv(
                        source=query.get("source", ["all"])[0],
                        device_type=query.get("device_type", [""])[0],
                        q=query.get("q", [""])[0],
                        sort=query.get("sort", ["abs_residual"])[0],
                        direction=query.get("direction", ["desc"])[0],
                        high_residual_only=query.get("high_residual_only", ["0"])[0] in {"1", "true"},
                        run_id=rid_val,
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", 'attachment; filename="se-measurements.csv"')
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
                if parsed_get.path == "/api/lf/results/export":
                    query = parse_qs(parsed_get.query)
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    body = app._lf_repo().lf_results_export_csv(
                        kind=query.get("kind", ["branches"])[0],
                        domain=query.get("domain", ["all"])[0],
                        device_type=query.get("device_type", [""])[0],
                        only_abnormal=query.get("only_abnormal", ["0"])[0] in {"1", "true"},
                        q=query.get("q", [""])[0],
                        run_id=rid_val,
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", 'attachment; filename="lf-results.csv"')
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed_get.path == "/api/lf/logs/export":
                    query = parse_qs(parsed_get.query)
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    csv_text = app._lf_repo().lf_logs_export_csv(
                        level=query.get("level", [""])[0],
                        stage=query.get("stage", [""])[0],
                        source=query.get("source", [""])[0],
                        run_id=rid_val,
                        window=query.get("window", ["all"])[0],
                        q=query.get("q", [""])[0],
                    )
                    body = csv_text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", 'attachment; filename="lf-run-logs.csv"')
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed_get.path == "/api/ca/risks/export":
                    query = parse_qs(parsed_get.query)
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    body = app._ca_repo().ca_risks_export_csv(
                        category=query.get("category", ["all"])[0],
                        severity=query.get("severity", ["all"])[0],
                        risk_category=query.get("risk_category", ["all"])[0],
                        q=query.get("q", [""])[0],
                        run_id=rid_val,
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", 'attachment; filename="ca-risks.csv"')
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if parsed_get.path == "/api/ca/logs/export":
                    query = parse_qs(parsed_get.query)
                    rid_raw = query.get("run_id", [""])[0].strip()
                    rid_val = _int_path(rid_raw) if rid_raw else None
                    csv_text = app._ca_repo().ca_logs_export_csv(
                        level=query.get("level", [""])[0],
                        stage=query.get("stage", [""])[0],
                        source=query.get("source", [""])[0],
                        run_id=rid_val,
                        window=query.get("window", ["all"])[0],
                        q=query.get("q", [""])[0],
                    )
                    body = csv_text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header("Content-Disposition", 'attachment; filename="ca-run-logs.csv"')
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
                st = path.stat()
                etag = f'W/"{st.st_mtime_ns:x}-{st.st_size:x}"'
                ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                if ctype.startswith("text/") or ctype in {"application/javascript", "application/json", "image/svg+xml"}:
                    ctype = f"{ctype}; charset=utf-8"
                self._send_bytes(path.read_bytes(), ctype, etag=etag, cache_control="no-cache")

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
