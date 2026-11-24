"""状态估计（SE）运行日志存储、检索、导出与定期自动删除模块。"""

from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

LOG_LEVEL_ORDER: dict[str, int] = {
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "ERROR": 40,
}

VALID_LOG_LEVELS = tuple(LOG_LEVEL_ORDER.keys())

VALID_LOG_STAGES = (
    "trigger",
    "input_load",
    "policy_apply",
    "pseudo_inject",
    "solve",
    "bad_detect",
    "persist",
    "param_change",
    "pseudo_change",
    "bad_change",
    "cleanup",
    "error",
)

DEFAULT_LOG_POLICY: dict[str, Any] = {
    "id": 1,
    "enabled": 1,
    "retention_days": 30,
    "keep_error_days": 90,
    "max_rows": 50000,
    "cleanup_interval_hours": 6.0,
    "min_level": "INFO",
    "last_cleanup_at": "",
    "last_deleted_count": 0,
}


def utc_now() -> str:
    """返回标准 UTC ISO-8601 毫秒时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _parse_iso(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    text = str(stamp).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ensure_se_log_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    """确保 se_log_policy 单行默认策略存在并返回当前配置。"""
    row = conn.execute("SELECT * FROM se_log_policy WHERE id = 1").fetchone()
    if row is not None:
        return dict(row)
    now_str = utc_now()
    conn.execute(
        """INSERT OR IGNORE INTO se_log_policy(
               id, enabled, retention_days, keep_error_days, max_rows,
               cleanup_interval_hours, min_level, last_cleanup_at,
               last_deleted_count, updated_at
           ) VALUES (1, ?, ?, ?, ?, ?, ?, '', 0, ?)""",
        (
            DEFAULT_LOG_POLICY["enabled"],
            DEFAULT_LOG_POLICY["retention_days"],
            DEFAULT_LOG_POLICY["keep_error_days"],
            DEFAULT_LOG_POLICY["max_rows"],
            DEFAULT_LOG_POLICY["cleanup_interval_hours"],
            DEFAULT_LOG_POLICY["min_level"],
            now_str,
        ),
    )
    created = conn.execute("SELECT * FROM se_log_policy WHERE id = 1").fetchone()
    return dict(created) if created is not None else {**DEFAULT_LOG_POLICY, "updated_at": now_str}


def update_se_log_policy(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    """校验并更新 SE 日志存储与定期清理策略。"""
    current = ensure_se_log_policy(conn)
    allowed = {"enabled", "retention_days", "keep_error_days", "max_rows", "cleanup_interval_hours", "min_level"}
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"不支持的日志策略字段: {', '.join(sorted(unknown))}")

    updated = dict(current)
    if "enabled" in payload:
        raw = payload["enabled"]
        if isinstance(raw, bool):
            updated["enabled"] = int(raw)
        elif raw in (0, 1, "0", "1"):
            updated["enabled"] = int(raw)
        else:
            raise ValueError("enabled 必须为布尔值或 0/1")

    for int_field, (lo, hi) in {
        "retention_days": (1, 3650),
        "keep_error_days": (1, 3650),
        "max_rows": (100, 2_000_000),
    }.items():
        if int_field in payload:
            raw = payload[int_field]
            if isinstance(raw, bool) or raw is None:
                raise ValueError(f"{int_field} 必须为整数")
            try:
                val = int(float(raw))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{int_field} 必须为整数") from exc
            if not lo <= val <= hi:
                raise ValueError(f"{int_field} 超出允许范围 [{lo}, {hi}]")
            updated[int_field] = val

    if updated["keep_error_days"] < updated["retention_days"]:
        updated["keep_error_days"] = updated["retention_days"]

    if "cleanup_interval_hours" in payload:
        raw = payload["cleanup_interval_hours"]
        if isinstance(raw, bool) or raw is None:
            raise ValueError("cleanup_interval_hours 必须为数值")
        try:
            hours = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("cleanup_interval_hours 必须为数值") from exc
        if not math.isfinite(hours) or not 0.1 <= hours <= 720.0:
            raise ValueError("cleanup_interval_hours 超出允许范围 [0.1, 720]")
        updated["cleanup_interval_hours"] = hours

    if "min_level" in payload:
        lvl = str(payload["min_level"] or "").upper()
        if lvl not in LOG_LEVEL_ORDER:
            raise ValueError(f"min_level 必须为 {', '.join(VALID_LOG_LEVELS)} 之一")
        updated["min_level"] = lvl

    updated["updated_at"] = utc_now()
    conn.execute(
        """UPDATE se_log_policy
           SET enabled=?, retention_days=?, keep_error_days=?, max_rows=?,
               cleanup_interval_hours=?, min_level=?, updated_at=?
           WHERE id=1""",
        (
            updated["enabled"],
            updated["retention_days"],
            updated["keep_error_days"],
            updated["max_rows"],
            updated["cleanup_interval_hours"],
            updated["min_level"],
            updated["updated_at"],
        ),
    )
    return updated


def record_se_log(
    conn: sqlite3.Connection,
    *,
    level: str,
    stage: str,
    message: str,
    run_id: int | None = None,
    source: str = "system",
    elapsed_ms: float | None = None,
    detail: dict[str, Any] | None = None,
    calc_time: str | None = None,
    respect_min_level: bool = True,
) -> int | None:
    """写入一条结构化状态估计运行日志；若低于策略 min_level 则跳过。"""
    lvl = str(level or "INFO").upper()
    if lvl not in LOG_LEVEL_ORDER:
        lvl = "INFO"
    stg = str(stage or "system").strip() or "system"
    if respect_min_level and stg != "cleanup":
        policy = ensure_se_log_policy(conn)
        min_lvl = str(policy.get("min_level") or "INFO").upper()
        if LOG_LEVEL_ORDER.get(lvl, 20) < LOG_LEVEL_ORDER.get(min_lvl, 20):
            return None
    stamp = str(calc_time or utc_now())
    detail_text = json.dumps(detail or {}, ensure_ascii=False, default=str)
    cur = conn.execute(
        """INSERT INTO se_run_log(run_id, calc_time, level, stage, source, elapsed_ms, message, detail_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            int(run_id) if run_id is not None else None,
            stamp,
            lvl,
            stg,
            str(source or "system"),
            float(elapsed_ms) if isinstance(elapsed_ms, (int, float)) and math.isfinite(elapsed_ms) else None,
            str(message or ""),
            detail_text,
        ),
    )
    return int(cur.lastrowid)


def _build_log_where(
    *,
    level: str = "",
    stage: str = "",
    source: str = "",
    run_id: int | None = None,
    date_from: str = "",
    date_to: str = "",
    q: str = "",
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if level and level.upper() in LOG_LEVEL_ORDER:
        clauses.append("level = ?")
        params.append(level.upper())
    if stage and stage != "all":
        clauses.append("stage = ?")
        params.append(stage)
    if source and source != "all":
        clauses.append("source = ?")
        params.append(source)
    if run_id is not None:
        clauses.append("run_id = ?")
        params.append(int(run_id))
    if date_from:
        clauses.append("calc_time >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("calc_time <= ?")
        params.append(date_to)
    if q and q.strip():
        like = f"%{q.strip()}%"
        clauses.append("(message LIKE ? OR detail_json LIKE ? OR stage LIKE ? OR CAST(COALESCE(run_id,'') AS TEXT) LIKE ?)")
        params.extend([like, like, like, like])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def list_se_logs(
    conn: sqlite3.Connection,
    *,
    level: str = "",
    stage: str = "",
    source: str = "",
    run_id: int | None = None,
    date_from: str = "",
    date_to: str = "",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """分页检索 SE 运行日志明细。"""
    where, params = _build_log_where(
        level=level,
        stage=stage,
        source=source,
        run_id=run_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    total = int(conn.execute(f"SELECT COUNT(*) FROM se_run_log {where}", params).fetchone()[0] or 0)
    rows_raw = conn.execute(
        f"""SELECT log_id, run_id, calc_time, level, stage, source, elapsed_ms, message, detail_json
            FROM se_run_log {where}
            ORDER BY calc_time DESC, log_id DESC
            LIMIT ? OFFSET ?""",
        [*params, int(limit), int(offset)],
    ).fetchall()
    rows: list[dict[str, Any]] = []
    for item in rows_raw:
        rec = dict(item)
        try:
            rec["detail"] = json.loads(rec.get("detail_json") or "{}")
        except json.JSONDecodeError:
            rec["detail"] = {}
        rows.append(rec)
    return {
        "rows": rows,
        "total": total,
        "limit": int(limit),
        "offset": int(offset),
    }


def se_log_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    """统计日志总量、近 24h 错误与告警数、各级别与阶段分布及策略信息。"""
    policy = ensure_se_log_policy(conn)
    total = int(conn.execute("SELECT COUNT(*) FROM se_run_log").fetchone()[0] or 0)
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="milliseconds")
    recent_24h = int(conn.execute("SELECT COUNT(*) FROM se_run_log WHERE calc_time >= ?", (cutoff_24h,)).fetchone()[0] or 0)
    errors_24h = int(
        conn.execute(
            "SELECT COUNT(*) FROM se_run_log WHERE calc_time >= ? AND level = 'ERROR'",
            (cutoff_24h,),
        ).fetchone()[0]
        or 0
    )
    warns_24h = int(
        conn.execute(
            "SELECT COUNT(*) FROM se_run_log WHERE calc_time >= ? AND level = 'WARN'",
            (cutoff_24h,),
        ).fetchone()[0]
        or 0
    )
    by_level = {
        row["level"]: int(row["cnt"])
        for row in conn.execute("SELECT level, COUNT(*) AS cnt FROM se_run_log GROUP BY level")
    }
    by_stage = [
        {"stage": row["stage"], "count": int(row["cnt"]), "avg_ms": row["avg_ms"]}
        for row in conn.execute(
            """SELECT stage, COUNT(*) AS cnt, AVG(elapsed_ms) AS avg_ms
               FROM se_run_log GROUP BY stage ORDER BY cnt DESC"""
        )
    ]
    oldest = conn.execute("SELECT MIN(calc_time) FROM se_run_log").fetchone()[0] or ""
    newest = conn.execute("SELECT MAX(calc_time) FROM se_run_log").fetchone()[0] or ""
    preview = preview_purge_se_logs(conn)
    return {
        "total": total,
        "recent_24h": recent_24h,
        "errors_24h": errors_24h,
        "warns_24h": warns_24h,
        "by_level": by_level,
        "by_stage": by_stage,
        "oldest_at": oldest,
        "newest_at": newest,
        "policy": policy,
        "pending_purge": preview,
    }


def _select_purge_ids(
    conn: sqlite3.Connection,
    *,
    retention_days: int,
    keep_error_days: int,
    max_rows: int,
    now_dt: datetime | None = None,
) -> tuple[list[int], int, int]:
    """计算按时间超限与行数超限应删除的 log_id 集合。"""
    ref_now = now_dt or datetime.now(timezone.utc)
    normal_cutoff = (ref_now - timedelta(days=int(retention_days))).isoformat(timespec="milliseconds")
    error_cutoff = (ref_now - timedelta(days=int(keep_error_days))).isoformat(timespec="milliseconds")

    expired_rows = conn.execute(
        """SELECT log_id FROM se_run_log
           WHERE (level != 'ERROR' AND calc_time < ?)
              OR (level = 'ERROR' AND calc_time < ?)""",
        (normal_cutoff, error_cutoff),
    ).fetchall()
    expired_ids = [int(r[0]) for r in expired_rows]
    expired_set = set(expired_ids)

    total_rows = int(conn.execute("SELECT COUNT(*) FROM se_run_log").fetchone()[0] or 0)
    remaining = total_rows - len(expired_ids)
    overflow_ids: list[int] = []
    if remaining > int(max_rows):
        need_trim = remaining - int(max_rows)
        # 优先裁剪最旧的非 ERROR 日志，不足时再裁剪最旧的 ERROR 日志
        candidates = conn.execute(
            """SELECT log_id FROM se_run_log
               ORDER BY CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END ASC,
                        calc_time ASC, log_id ASC"""
        ).fetchall()
        for row in candidates:
            lid = int(row[0])
            if lid in expired_set:
                continue
            overflow_ids.append(lid)
            if len(overflow_ids) >= need_trim:
                break
    return [*expired_ids, *overflow_ids], len(expired_ids), len(overflow_ids)


def preview_purge_se_logs(
    conn: sqlite3.Connection,
    *,
    retention_days: int | None = None,
    keep_error_days: int | None = None,
    max_rows: int | None = None,
    now_dt: datetime | None = None,
) -> dict[str, Any]:
    """预估当前策略或指定阈值下将被删除的日志条数（不执行删除）。"""
    policy = ensure_se_log_policy(conn)
    r_days = int(policy["retention_days"] if retention_days is None else retention_days)
    e_days = int(policy["keep_error_days"] if keep_error_days is None else keep_error_days)
    m_rows = int(policy["max_rows"] if max_rows is None else max_rows)
    if not 0 <= r_days <= 3650 or not 0 <= e_days <= 3650 or not 0 <= m_rows <= 2_000_000:
        raise ValueError("清理参数超出有效范围")
    ids, expired_count, overflow_count = _select_purge_ids(
        conn,
        retention_days=r_days,
        keep_error_days=e_days,
        max_rows=m_rows,
        now_dt=now_dt,
    )
    return {
        "total_to_delete": len(ids),
        "expired_count": expired_count,
        "overflow_count": overflow_count,
        "retention_days": r_days,
        "keep_error_days": e_days,
        "max_rows": m_rows,
    }


def purge_se_logs(
    conn: sqlite3.Connection,
    *,
    retention_days: int | None = None,
    keep_error_days: int | None = None,
    max_rows: int | None = None,
    source: str = "system",
    now_dt: datetime | None = None,
) -> dict[str, Any]:
    """执行 SE 运行日志清理，更新清理策略记录并追加 cleanup 审计日志。"""
    policy = ensure_se_log_policy(conn)
    r_days = int(policy["retention_days"] if retention_days is None else retention_days)
    e_days = int(policy["keep_error_days"] if keep_error_days is None else keep_error_days)
    m_rows = int(policy["max_rows"] if max_rows is None else max_rows)
    if not 0 <= r_days <= 3650 or not 0 <= e_days <= 3650 or not 0 <= m_rows <= 2_000_000:
        raise ValueError("清理参数超出有效范围")

    ids, expired_count, overflow_count = _select_purge_ids(
        conn,
        retention_days=r_days,
        keep_error_days=e_days,
        max_rows=m_rows,
        now_dt=now_dt,
    )
    deleted = 0
    # 分批删除避免超出 SQLite 绑定变量上限
    for i in range(0, len(ids), 500):
        chunk = ids[i : i + 500]
        placeholders = ",".join("?" for _ in chunk)
        cur = conn.execute(f"DELETE FROM se_run_log WHERE log_id IN ({placeholders})", chunk)
        deleted += max(0, cur.rowcount)

    now_str = (now_dt or datetime.now(timezone.utc)).isoformat(timespec="milliseconds")
    conn.execute(
        "UPDATE se_log_policy SET last_cleanup_at=?, last_deleted_count=?, updated_at=? WHERE id=1",
        (now_str, deleted, now_str),
    )
    if deleted > 0 or source == "operator":
        record_se_log(
            conn,
            level="INFO",
            stage="cleanup",
            source=source,
            message=f"日志清理完成：删除 {deleted} 条（过期 {expired_count}，超限裁剪 {overflow_count}）",
            detail={
                "deleted": deleted,
                "expired_count": expired_count,
                "overflow_count": overflow_count,
                "retention_days": r_days,
                "keep_error_days": e_days,
                "max_rows": m_rows,
            },
            calc_time=now_str,
            respect_min_level=False,
        )
    return {
        "deleted": deleted,
        "expired_count": expired_count,
        "overflow_count": overflow_count,
        "cleaned_at": now_str,
        "retention_days": r_days,
        "keep_error_days": e_days,
        "max_rows": m_rows,
    }


def maybe_auto_purge_se_logs(conn: sqlite3.Connection, *, now_dt: datetime | None = None) -> dict[str, Any] | None:
    """按 se_log_policy.cleanup_interval_hours 判断是否到期，到期则自动执行定期清理。"""
    policy = ensure_se_log_policy(conn)
    if not int(policy.get("enabled", 1)):
        return None
    ref_now = now_dt or datetime.now(timezone.utc)
    last_dt = _parse_iso(policy.get("last_cleanup_at"))
    interval = timedelta(hours=float(policy.get("cleanup_interval_hours") or 6.0))
    if last_dt is not None and (ref_now - last_dt) < interval:
        return None
    return purge_se_logs(conn, source="schedule", now_dt=ref_now)


def export_se_logs_csv(
    conn: sqlite3.Connection,
    *,
    level: str = "",
    stage: str = "",
    source: str = "",
    run_id: int | None = None,
    date_from: str = "",
    date_to: str = "",
    q: str = "",
    limit: int = 5000,
) -> str:
    """将符合条件的 SE 运行日志导出为 UTF-8 BOM CSV 文本。"""
    data = list_se_logs(
        conn,
        level=level,
        stage=stage,
        source=source,
        run_id=run_id,
        date_from=date_from,
        date_to=date_to,
        q=q,
        limit=min(max(1, int(limit)), 20000),
        offset=0,
    )
    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf)
    writer.writerow(["log_id", "run_id", "calc_time", "level", "stage", "source", "elapsed_ms", "message", "detail_json"])
    for row in data["rows"]:
        writer.writerow(
            [
                row["log_id"],
                "" if row["run_id"] is None else row["run_id"],
                row["calc_time"],
                row["level"],
                row["stage"],
                row["source"],
                "" if row["elapsed_ms"] is None else round(float(row["elapsed_ms"]), 3),
                row["message"],
                row["detail_json"],
            ]
        )
    return buf.getvalue()
