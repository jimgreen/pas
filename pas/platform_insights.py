"""PAS 全平台深度洞察、断面 Diff、单设备 360° 档案、数据源体检与报告导出。"""

from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import input_store


def _parse_iso_seconds_ago(ts: Any) -> int | None:
    """将 ISO 时间字符串换算为距今秒数；解析失败返回 None。"""
    if not ts:
        return None
    text = str(ts).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0, int((now - dt.astimezone(timezone.utc)).total_seconds()))
    except (ValueError, TypeError):
        return None


def _human_size(size: int) -> str:
    val = float(max(0, size))
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024.0 or unit == "GB":
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= 1024.0
    return f"{size} B"


def _file_probe(label: str, key: str, path: str | Path | None, mode: str) -> dict[str, Any]:
    if not path:
        return {
            "key": key,
            "label": label,
            "path": "",
            "exists": False,
            "size_bytes": 0,
            "size_text": "—",
            "mtime": None,
            "mode": mode,
            "status": "missing",
        }
    p = Path(path)
    try:
        st = p.stat()
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
        writable = os.access(p, os.W_OK) if mode == "rw" else True
        return {
            "key": key,
            "label": label,
            "path": str(p),
            "exists": True,
            "size_bytes": int(st.st_size),
            "size_text": _human_size(int(st.st_size)),
            "mtime": mtime,
            "age_seconds": _parse_iso_seconds_ago(mtime),
            "mode": mode,
            "status": "ok" if writable else "readonly_warn",
        }
    except OSError:
        return {
            "key": key,
            "label": label,
            "path": str(p),
            "exists": False,
            "size_bytes": 0,
            "size_text": "—",
            "mtime": None,
            "age_seconds": None,
            "mode": mode,
            "status": "missing",
        }


def build_datasource_health(app: Any) -> dict[str, Any]:
    """汇总全部 PAS 自管库与外部只读源库的实际命中路径、大小、更新时间与健康状态。"""
    items: list[dict[str, Any]] = []
    control = getattr(app.repository, "control", None)
    control_path = getattr(app.config, "database", None) or getattr(control, "path", None)
    items.append(_file_probe("PAS 控制与调度库", "pas_db", control_path, "rw"))

    dbs = getattr(app.config, "databases", None) or {}
    repos = getattr(app.repository, "repositories", None) or {}
    for mod, title in (("se", "状态估计结果库 (SE)"), ("lf", "潮流分析结果库 (LF)"), ("ca", "静态安全结果库 (CA)")):
        p = dbs.get(mod) or (getattr(repos.get(mod), "path", None) if mod in repos else None)
        items.append(_file_probe(title, f"{mod}_db", p, "rw"))

    se_task = getattr(app.config, "tasks", {}).get("se")
    ca_task = getattr(app.config, "tasks", {}).get("ca")
    items.append(_file_probe("电网模型库 (devices)", "model_file", getattr(se_task, "model_file", None), "ro"))
    items.append(_file_probe("实时宽表量测库 (scdfe_d)", "measurement_file", getattr(se_task, "measurement_file", None), "ro"))
    items.append(_file_probe("前置采集库 (scdfe_c)", "scada_source_file", getattr(se_task, "scada_source_file", None), "ro"))
    items.append(_file_probe("点表映射文件", "point_catalog_file", getattr(se_task, "point_catalog_file", None), "ro"))
    items.append(_file_probe("安全限值库 (CA limits)", "limit_file", getattr(ca_task, "limit_file", None), "rw"))

    ok_cnt = sum(1 for x in items if x["status"] == "ok")
    return {
        "total": len(items),
        "ok_count": ok_cnt,
        "missing_count": sum(1 for x in items if x["status"] == "missing"),
        "items": items,
    }


def _row_run_id(row: dict[str, Any] | None) -> int | None:
    if not row:
        return None
    val = row.get("run_id") if row.get("run_id") is not None else row.get("id")
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def compute_event_version(app: Any) -> dict[str, Any]:
    """低开销生成当前全平台运行版本号，供 SSE 推送变更检测。"""
    se_id = lf_id = ca_id = 0
    try:
        r_se = app._se_repo().list_runs(1, "se")
        se_id = _row_run_id(r_se[0]) or 0 if r_se else 0
    except Exception:
        pass
    try:
        r_lf = app._lf_repo().list_runs(1, "lf")
        lf_id = _row_run_id(r_lf[0]) or 0 if r_lf else 0
    except Exception:
        pass
    try:
        r_ca = app._ca_repo().list_runs(1, "ca")
        ca_id = _row_run_id(r_ca[0]) or 0 if r_ca else 0
    except Exception:
        pass
    sched = app.scheduler.status() if callable(getattr(app.scheduler, "status", None)) else {}
    active = sorted(str(x) for x in (sched.get("active_tasks") or ()))
    token = f"{se_id}:{lf_id}:{ca_id}:{','.join(active)}"
    return {
        "version": token,
        "se_run_id": se_id,
        "lf_run_id": lf_id,
        "ca_run_id": ca_id,
        "active_tasks": active,
    }


def enrich_pipeline_status(app: Any, data: dict[str, Any]) -> dict[str, Any]:
    """为 /api/pipeline/status 叠加基态滞后（Stale）、最新失败排障提示与链路耗时分解。"""
    se_repo = app._se_repo()
    lf_repo = app._lf_repo()
    ca_repo = app._ca_repo()

    se_latest_ok = (data.get("se") or {}).get("latest")
    lf_latest_ok = (data.get("lf") or {}).get("latest")
    ca_latest_ok = (data.get("ca") or {}).get("latest")

    # 检查各模块最近一次（含失败）运行，用于识别“最新一轮失败、正在沿用旧基态”
    def _latest_any(repo: Any, task: str) -> dict[str, Any] | None:
        try:
            rows = repo.list_runs(1, task)
            return rows[0] if rows else None
        except Exception:
            return None

    se_any = _latest_any(se_repo, "se")
    lf_any = _latest_any(lf_repo, "lf")
    ca_any = _latest_any(ca_repo, "ca")

    se_ok_id = _row_run_id(se_latest_ok)
    se_any_id = _row_run_id(se_any)
    lf_any_id = _row_run_id(lf_any)
    ca_any_id = _row_run_id(ca_any)
    se_last_failed = bool(se_any and se_any.get("status") == "failed")
    se_stale = bool(se_last_failed or (se_any_id and se_ok_id and se_any_id > se_ok_id))
    se_age_s = _parse_iso_seconds_ago((se_latest_ok or {}).get("timestamp") or (se_latest_ok or {}).get("created_at") or (se_latest_ok or {}).get("calc_time"))
    lf_age_s = _parse_iso_seconds_ago((lf_latest_ok or {}).get("timestamp") or (lf_latest_ok or {}).get("created_at") or (lf_latest_ok or {}).get("calc_time"))
    ca_age_s = _parse_iso_seconds_ago((ca_latest_ok or {}).get("timestamp") or (ca_latest_ok or {}).get("created_at") or (ca_latest_ok or {}).get("calc_time"))

    se_err_msg = str((se_any or {}).get("error_message") or "")
    se_quality_issue = any(k in se_err_msg for k in ("bad_quality", "missing_sample", "无有效", "量测"))

    # 链路端到端耗时分解
    se_s = float((se_latest_ok or {}).get("elapsed_seconds") or 0.0)
    lf_s = float((lf_latest_ok or {}).get("elapsed_seconds") or 0.0)
    ca_s = float((ca_latest_ok or {}).get("elapsed_seconds") or 0.0)

    data["diagnostics"] = {
        "se_stale": se_stale,
        "se_age_seconds": se_age_s,
        "lf_age_seconds": lf_age_s,
        "ca_age_seconds": ca_age_s,
        "se_latest_attempt": {
            "id": se_any_id,
            "status": (se_any or {}).get("status"),
            "error_message": se_err_msg[:260],
            "quality_issue": se_quality_issue,
        } if se_any else None,
        "lf_latest_attempt": {
            "id": lf_any_id,
            "status": (lf_any or {}).get("status"),
            "error_message": str((lf_any or {}).get("error_message") or "")[:260],
        } if lf_any else None,
        "ca_latest_attempt": {
            "id": ca_any_id,
            "status": (ca_any or {}).get("status"),
            "error_message": str((ca_any or {}).get("error_message") or "")[:260],
        } if ca_any else None,
        "timing": {
            "se_seconds": round(se_s, 3),
            "lf_seconds": round(lf_s, 3),
            "ca_seconds": round(ca_s, 3),
            "total_seconds": round(se_s + lf_s + ca_s, 3),
        },
    }
    return data


def build_device_profile(app: Any, device_name: str) -> dict[str, Any]:
    """跨 SE / LF / CA / 限值库聚合单台设备的 360° 全景档案。"""
    name = (device_name or "").strip()
    if not name:
        raise ValueError("device name is required")

    se_repo = app._se_repo()
    lf_repo = app._lf_repo()
    ca_repo = app._ca_repo()

    # 1. SE 最新断面该设备量测与估计值
    se_meas: list[dict[str, Any]] = []
    se_run_id: int | None = None
    se_device_type = ""
    try:
        se_data = se_repo.se_measurements_browse(q=name, limit=80, offset=0)
        se_run_id = se_data.get("run_id")
        for row in se_data.get("rows") or ():
            if str(row.get("device_name") or "").strip() == name:
                se_meas.append(row)
                if not se_device_type and row.get("device_type"):
                    se_device_type = str(row["device_type"])
        if not se_meas:
            # 模糊包含兜底
            se_meas = list((se_data.get("rows") or ())[:20])
            if se_meas and not se_device_type:
                se_device_type = str(se_meas[0].get("device_type") or "")
    except Exception:
        pass

    # 2. LF 最新断面该设备的母线与支路潮流
    lf_buses: list[dict[str, Any]] = []
    lf_branches: list[dict[str, Any]] = []
    lf_run_id: int | None = None
    try:
        b_res = lf_repo.lf_results_browse(kind="buses", q=name, limit=20, offset=0)
        lf_run_id = b_res.get("run_id")
        lf_buses = [r for r in (b_res.get("rows") or ()) if str(r.get("device_name") or "").strip() == name]
        if not lf_buses:
            lf_buses = list((b_res.get("rows") or ())[:5])
    except Exception:
        pass
    try:
        br_res = lf_repo.lf_results_browse(kind="branches", q=name, limit=20, offset=0)
        lf_run_id = lf_run_id or br_res.get("run_id")
        lf_branches = [r for r in (br_res.get("rows") or ()) if str(r.get("device_name") or "").strip() == name]
        if not lf_branches:
            lf_branches = list((br_res.get("rows") or ())[:5])
        if not se_device_type:
            if lf_buses:
                se_device_type = str(lf_buses[0].get("device_type") or "")
            elif lf_branches:
                se_device_type = str(lf_branches[0].get("device_type") or "")
    except Exception:
        pass

    # 3. CA 最新断面涉及该设备的安全风险与相关故障
    ca_risks: list[dict[str, Any]] = []
    ca_run_id: int | None = None
    try:
        r_res = ca_repo.ca_risks_browse(q=name, limit=40, offset=0)
        ca_run_id = r_res.get("run_id")
        ca_risks = [
            r for r in (r_res.get("rows") or ())
            if str(r.get("device_name") or "").strip() == name or name in str(r.get("contingency_name") or "")
        ]
    except Exception:
        pass

    # 4. 安全限值配置
    limits: list[dict[str, Any]] = []
    try:
        lim_res = input_store.browse_inputs(app.config, "limits", q=name, page=0, size=20, view="all")
        limits = [r for r in (lim_res.get("rows") or ()) if str(r.get("device_name") or "").strip() == name]
    except Exception:
        pass

    return {
        "device_name": name,
        "device_type": se_device_type,
        "run_ids": {"se": se_run_id, "lf": lf_run_id, "ca": ca_run_id},
        "se_measurements": se_meas[:30],
        "lf_buses": lf_buses[:10],
        "lf_branches": lf_branches[:10],
        "ca_risks": ca_risks[:30],
        "limits": limits[:15],
        "links": {
            "se_flow": f"/se-flow.html?device={name}",
            "lf_flow": f"/lf-flow.html?device={name}",
            "ca_graph": f"/ca-risks.html?tab=graph&device={name}",
            "se_measurements": f"/se-measurements.html?q={name}",
        },
    }


def _num_diff(a: Any, b: Any, digits: int = 4) -> float | None:
    if a is None or b is None:
        return None
    try:
        return round(float(b) - float(a), digits)
    except (TypeError, ValueError):
        return None


def build_snapshot_diff(
    app: Any,
    module: str,
    run_a: int | None = None,
    run_b: int | None = None,
) -> dict[str, Any]:
    """对 SE / LF / CA 任意两次历史运行断面做 A/B 差异对比（默认自动对比最新两期有效断面）。"""
    mod = (module or "lf").lower().strip()
    if mod not in {"se", "lf", "ca"}:
        raise ValueError("module must be one of se, lf, ca")

    if mod == "lf":
        repo = app._lf_repo()
        hist = repo.lf_history_stats(limit=40)
        avail = [{"run_id": int(r["run_id"]), "timestamp": r.get("timestamp"), "label": f"LF #{r['run_id']} ({r.get('loss_rate', 0):.2f}%)"} for r in reversed(hist) if r.get("run_id")]
        if not avail:
            return {"module": "lf", "available_runs": [], "run_a": None, "run_b": None, "kpis": [], "changes": []}
        id_b = run_b or avail[0]["run_id"]
        id_a = run_a or (avail[1]["run_id"] if len(avail) > 1 else avail[0]["run_id"])
        by_id = {int(r["run_id"]): r for r in hist if r.get("run_id")}
        sa, sb = by_id.get(id_a) or {}, by_id.get(id_b) or {}
        kpis = [
            {"label": "总发电有功 (kW)", "a": sa.get("total_gen_p"), "b": sb.get("total_gen_p"), "delta": _num_diff(sa.get("total_gen_p"), sb.get("total_gen_p"), 2)},
            {"label": "总负荷有功 (kW)", "a": sa.get("total_load_p"), "b": sb.get("total_load_p"), "delta": _num_diff(sa.get("total_load_p"), sb.get("total_load_p"), 2)},
            {"label": "全网网损率 (%)", "a": sa.get("loss_rate"), "b": sb.get("loss_rate"), "delta": _num_diff(sa.get("loss_rate"), sb.get("loss_rate"), 3)},
            {"label": "最大设备负载率 (%)", "a": sa.get("max_loading_pct"), "b": sb.get("max_loading_pct"), "delta": _num_diff(sa.get("max_loading_pct"), sb.get("max_loading_pct"), 2)},
            {"label": "最低母线电压 (pu)", "a": sa.get("min_v_pu"), "b": sb.get("min_v_pu"), "delta": _num_diff(sa.get("min_v_pu"), sb.get("min_v_pu"), 4)},
            {"label": "电压越限设备数", "a": sa.get("v_violation_count"), "b": sb.get("v_violation_count"), "delta": _num_diff(sa.get("v_violation_count"), sb.get("v_violation_count"), 0)},
        ]
        # 比较母线电压与支路负载率 Top 变化
        ba = {r["device_name"]: r for r in (repo.lf_results_browse(kind="buses", run_id=id_a, limit=500).get("rows") or ())}
        bb = {r["device_name"]: r for r in (repo.lf_results_browse(kind="buses", run_id=id_b, limit=500).get("rows") or ())}
        changes = []
        for dev in set(ba) | set(bb):
            va = (ba.get(dev) or {}).get("v_pu")
            vb = (bb.get(dev) or {}).get("v_pu")
            dv = _num_diff(va, vb, 4)
            if dv is not None:
                changes.append({"device": dev, "metric": "电压 (pu)", "a": va, "b": vb, "delta": dv, "abs_delta": abs(dv)})
        bra = {r["device_name"]: r for r in (repo.lf_results_browse(kind="branches", run_id=id_a, limit=500).get("rows") or ())}
        brb = {r["device_name"]: r for r in (repo.lf_results_browse(kind="branches", run_id=id_b, limit=500).get("rows") or ())}
        for dev in set(bra) | set(brb):
            la = (bra.get(dev) or {}).get("loading_pct")
            lb = (brb.get(dev) or {}).get("loading_pct")
            dl = _num_diff(la, lb, 2)
            if dl is not None:
                changes.append({"device": dev, "metric": "负载率 (%)", "a": la, "b": lb, "delta": dl, "abs_delta": abs(dl)})
        changes.sort(key=lambda x: (-x["abs_delta"], x["device"]))
        return {"module": "lf", "available_runs": avail[:25], "run_a": id_a, "run_b": id_b, "kpis": kpis, "changes": changes[:25]}

    if mod == "ca":
        repo = app._ca_repo()
        hist = repo.ca_history_stats(limit=40)
        avail = [{"run_id": int(r["run_id"]), "timestamp": r.get("timestamp"), "label": f"CA #{r['run_id']} ({r.get('security_score', 0):.1f}分)"} for r in reversed(hist) if r.get("run_id")]
        if not avail:
            return {"module": "ca", "available_runs": [], "run_a": None, "run_b": None, "kpis": [], "changes": []}
        id_b = run_b or avail[0]["run_id"]
        id_a = run_a or (avail[1]["run_id"] if len(avail) > 1 else avail[0]["run_id"])
        by_id = {int(r["run_id"]): r for r in hist if r.get("run_id")}
        sa, sb = by_id.get(id_a) or {}, by_id.get(id_b) or {}
        kpis = [
            {"label": "安全健康评分", "a": sa.get("security_score"), "b": sb.get("security_score"), "delta": _num_diff(sa.get("security_score"), sb.get("security_score"), 1)},
            {"label": "总风险数", "a": sa.get("total_risk_count"), "b": sb.get("total_risk_count"), "delta": _num_diff(sa.get("total_risk_count"), sb.get("total_risk_count"), 0)},
            {"label": "严重风险数", "a": sa.get("critical_count"), "b": sb.get("critical_count"), "delta": _num_diff(sa.get("critical_count"), sb.get("critical_count"), 0)},
            {"label": "高风险数", "a": sa.get("high_count"), "b": sb.get("high_count"), "delta": _num_diff(sa.get("high_count"), sb.get("high_count"), 0)},
            {"label": "最大失电负荷 (kW)", "a": sa.get("max_load_loss_kw"), "b": sb.get("max_load_loss_kw"), "delta": _num_diff(sa.get("max_load_loss_kw"), sb.get("max_load_loss_kw"), 2)},
            {"label": "N-1 收敛场景数", "a": sa.get("n1_converged"), "b": sb.get("n1_converged"), "delta": _num_diff(sa.get("n1_converged"), sb.get("n1_converged"), 0)},
        ]
        ra = {(r.get("contingency_name"), r.get("device_name"), r.get("risk_category")): r for r in (repo.ca_risks_browse(run_id=id_a, limit=500).get("rows") or ())}
        rb = {(r.get("contingency_name"), r.get("device_name"), r.get("risk_category")): r for r in (repo.ca_risks_browse(run_id=id_b, limit=500).get("rows") or ())}
        changes = []
        for k in set(rb) - set(ra):
            r = rb[k]
            changes.append({"device": f"{r.get('device_name')} [{r.get('contingency_name')}]", "metric": "新增风险", "a": "无", "b": r.get("severity"), "delta": "+1", "abs_delta": 100})
        for k in set(ra) - set(rb):
            r = ra[k]
            changes.append({"device": f"{r.get('device_name')} [{r.get('contingency_name')}]", "metric": "已消除风险", "a": r.get("severity"), "b": "无", "delta": "-1", "abs_delta": 90})
        for k in set(ra) & set(rb):
            va, vb = ra[k].get("violation_pct"), rb[k].get("violation_pct")
            dv = _num_diff(va, vb, 2)
            if dv and abs(dv) > 0:
                changes.append({"device": f"{rb[k].get('device_name')} [{rb[k].get('contingency_name')}]", "metric": "越限幅度 (%)", "a": va, "b": vb, "delta": dv, "abs_delta": abs(dv)})
        changes.sort(key=lambda x: (-x["abs_delta"], x["device"]))
        return {"module": "ca", "available_runs": avail[:25], "run_a": id_a, "run_b": id_b, "kpis": kpis, "changes": changes[:25]}

    # SE Diff
    repo = app._se_repo()
    hist = repo.se_history_stats(limit=40)
    avail = [{"run_id": int(r["run_id"]), "timestamp": r.get("timestamp"), "label": f"SE #{r['run_id']} ({(r.get('pass_rate') or 0)*100:.1f}%)"} for r in reversed(hist) if r.get("run_id")]
    if not avail:
        return {"module": "se", "available_runs": [], "run_a": None, "run_b": None, "kpis": [], "changes": []}
    id_b = run_b or avail[0]["run_id"]
    id_a = run_a or (avail[1]["run_id"] if len(avail) > 1 else avail[0]["run_id"])
    by_id = {int(r["run_id"]): r for r in hist if r.get("run_id")}
    sa, sb = by_id.get(id_a) or {}, by_id.get(id_b) or {}
    kpis = [
        {"label": "量测合格率 (%)", "a": round((sa.get("pass_rate") or 0) * 100, 2), "b": round((sb.get("pass_rate") or 0) * 100, 2), "delta": _num_diff((sa.get("pass_rate") or 0) * 100, (sb.get("pass_rate") or 0) * 100, 2)},
        {"label": "有效量测数", "a": sa.get("meas_count"), "b": sb.get("meas_count"), "delta": _num_diff(sa.get("meas_count"), sb.get("meas_count"), 0)},
        {"label": "坏数据数", "a": sa.get("bad_data_count"), "b": sb.get("bad_data_count"), "delta": _num_diff(sa.get("bad_data_count"), sb.get("bad_data_count"), 0)},
        {"label": "总残差", "a": sa.get("total_residual"), "b": sb.get("total_residual"), "delta": _num_diff(sa.get("total_residual"), sb.get("total_residual"), 3)},
        {"label": "迭代次数", "a": sa.get("iterations"), "b": sb.get("iterations"), "delta": _num_diff(sa.get("iterations"), sb.get("iterations"), 0)},
    ]
    ma = {(r.get("device_name"), r.get("meas_type")): r for r in (repo.se_measurements_browse(run_id=id_a, limit=400).get("rows") or ())}
    mb = {(r.get("device_name"), r.get("meas_type")): r for r in (repo.se_measurements_browse(run_id=id_b, limit=400).get("rows") or ())}
    changes = []
    for k in set(ma) & set(mb):
        ea, eb = ma[k].get("est_value"), mb[k].get("est_value")
        de = _num_diff(ea, eb, 4)
        if de is not None:
            changes.append({"device": str(k[0]), "metric": str(k[1]), "a": ea, "b": eb, "delta": de, "abs_delta": abs(de)})
    changes.sort(key=lambda x: (-x["abs_delta"], x["device"]))
    return {"module": "se", "available_runs": avail[:25], "run_a": id_a, "run_b": id_b, "kpis": kpis, "changes": changes[:25]}


def build_snapshot_report_html(app: Any) -> str:
    """生成自包含、打印友好的 PAS 全链路综合分析快照报告（单文件 HTML）。"""
    pipe = enrich_pipeline_status(app, app._build_pipeline_overview())
    ds = build_datasource_health(app)
    ws = pipe.get("workspace") or {}
    se = (pipe.get("se") or {}).get("latest") or {}
    lf = (pipe.get("lf") or {}).get("latest") or {}
    ca = (pipe.get("ca") or {}).get("latest") or {}
    alerts = pipe.get("alerts") or []
    recent = pipe.get("recent_runs") or []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    e = lambda v: html.escape(str(v if v is not None else "—"))

    alert_rows = "".join(
        f"<tr><td>{e(a.get('module'))}</td><td>{e(a.get('severity'))}</td><td>{e(a.get('target'))}</td><td>{e(a.get('detail'))}</td></tr>"
        for a in alerts[:25]
    ) or "<tr><td colspan='4'>当前无跨模块重点告警</td></tr>"

    run_rows = "".join(
        f"<tr><td>{e(r.get('module'))}</td><td>#{e(r.get('run_id'))}</td><td>{e(r.get('source'))}</td><td>{e(r.get('summary'))}</td><td>{e(r.get('elapsed_seconds'))} s</td></tr>"
        for r in recent[:15]
    ) or "<tr><td colspan='5'>暂无运行记录</td></tr>"

    ds_rows = "".join(
        f"<tr><td>{e(x['label'])}</td><td>{e(x['mode'])}</td><td>{e(x['status'])}</td><td>{e(x['size_text'])}</td><td style='font-family:monospace;font-size:11px'>{e(x['path'])}</td></tr>"
        for x in ds["items"]
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>PAS 在线分析综合快照报告 - {e(ws.get('scenario') or 'default')}</title>
<style>
  body {{ font-family: "Segoe UI", "Microsoft YaHei", sans-serif; color: #0f172a; background: #f8fafc; margin: 0; padding: 24px; line-height: 1.5; }}
  .wrap {{ max-width: 1080px; margin: 0 auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 24px 28px; }}
  h1 {{ margin: 0 0 4px; font-size: 20px; }}
  .meta {{ color: #64748b; font-size: 12px; margin-bottom: 18px; display: flex; justify-content: space-between; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }}
  .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }}
  .card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; background: #f8fafc; }}
  .card h2 {{ margin: 0 0 8px; font-size: 14px; color: #1e293b; }}
  .kv {{ display: flex; justify-content: space-between; font-size: 12.5px; padding: 3px 0; border-bottom: 1px dashed #e2e8f0; }}
  .kv:last-child {{ border-bottom: 0; }}
  h3 {{ margin: 18px 0 8px; font-size: 14px; color: #0f172a; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 6px 8px; text-align: left; }}
  th {{ background: #f1f5f9; color: #334155; }}
  @media print {{ body {{ background: #fff; padding: 0; }} .wrap {{ border: 0; padding: 0; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>PAS 在线分析平台 · SE → LF → CA 综合断面快照报告</h1>
  <div class="meta">
    <span>场景：{e(ws.get('runtime'))} / {e(ws.get('scenario'))}</span>
    <span>生成时间：{e(now_str)}</span>
  </div>
  <div class="cards">
    <div class="card">
      <h2>1. 状态估计 SE (#{e(se.get('run_id'))})</h2>
      <div class="kv"><span>收敛状态</span><strong>{'收敛' if se.get('converged') else '未收敛'}</strong></div>
      <div class="kv"><span>量测合格率</span><strong>{round((se.get('pass_rate') or 0)*100, 2)}%</strong></div>
      <div class="kv"><span>有效量测 / 坏数据</span><strong>{e(se.get('meas_count'))} / {e(se.get('bad_data_count'))}</strong></div>
      <div class="kv"><span>总残差 / 耗时</span><strong>{e(se.get('total_residual'))} / {e(se.get('elapsed_seconds'))}s</strong></div>
    </div>
    <div class="card">
      <h2>2. 潮流分析 LF (#{e(lf.get('run_id'))})</h2>
      <div class="kv"><span>基态溯源 SE</span><strong>SE #{e(lf.get('source_se_run_id'))}</strong></div>
      <div class="kv"><span>总发电 / 总负荷</span><strong>{e(lf.get('total_gen_p'))} / {e(lf.get('total_load_p'))} kW</strong></div>
      <div class="kv"><span>全网网损率</span><strong>{e(lf.get('loss_rate'))}% ({e(lf.get('total_loss_p'))} kW)</strong></div>
      <div class="kv"><span>最大负载 / 电压越限</span><strong>{e(lf.get('max_loading_pct'))}% / {e(lf.get('v_violation_count'))}</strong></div>
    </div>
    <div class="card">
      <h2>3. 静态安全 CA (#{e(ca.get('run_id'))})</h2>
      <div class="kv"><span>安全等级 / 评分</span><strong>{e(ca.get('security_level'))} / {e(ca.get('security_score'))}</strong></div>
      <div class="kv"><span>基态溯源 LF</span><strong>LF #{e(ca.get('source_lf_run_id'))}</strong></div>
      <div class="kv"><span>N-1 扫描 / 风险</span><strong>{e(ca.get('n1_total'))} / {e(ca.get('n1_risk_count'))}</strong></div>
      <div class="kv"><span>最严重预想故障</span><strong>{e(ca.get('worst_contingency'))}</strong></div>
    </div>
  </div>
  <h3>跨模块重点告警（Top 25）</h3>
  <table><thead><tr><th>模块</th><th>等级</th><th>对象</th><th>详情</th></tr></thead><tbody>{alert_rows}</tbody></table>
  <h3>三模块近期运行记录</h3>
  <table><thead><tr><th>模块</th><th>运行号</th><th>来源</th><th>摘要</th><th>耗时</th></tr></thead><tbody>{run_rows}</tbody></table>
  <h3>数据源健康检查（{ds['ok_count']} / {ds['total']} 正常）</h3>
  <table><thead><tr><th>数据源</th><th>模式</th><th>状态</th><th>大小</th><th>路径</th></tr></thead><tbody>{ds_rows}</tbody></table>
</div>
</body>
</html>"""
