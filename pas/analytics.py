"""Validated result queries and UTC time-window aggregation."""
from datetime import datetime, timedelta, timezone


DETAILS = {
    "se": ("se_measurement_result", "result_id", (
        "measurement_name", "device_name", "measurement_type", "value", "estimated_value",
        "residual", "normalized_residual", "valid", "reason", "source", "measurement_idx", "device_type")),
    "lf": ("lf_device_result", "result_id", (
        "device_key", "domain", "device_type", "voltage_from", "voltage_to", "p_from", "q_from",
        "p_to", "q_to", "current_from", "current_to", "node_from", "node_to")),
    "ca": ("ca_risk", "risk_id", (
        "risk_source", "contingency", "risk_type", "risk_value_real", "risk_info", "risk_dist",
        "risk_value_text", "created_at")),
}
VIEWS = {
    "se": {"invalid": "valid = 0", "valid": "valid = 1"},
    "lf": {name: f"domain = '{name}'" for name in ("ac", "dc", "dcac", "acac")},
    "ca": {"n0": "contingency = 'N-0'", "n1": "contingency = 'N-1'"},
}


def detail_query(task, run_id, search="", sort="", direction="asc", view="all"):
    if task not in DETAILS or direction not in ("asc", "desc"):
        raise ValueError("invalid task or sort direction")
    table, key, columns = DETAILS[task]
    if view != "all" and view not in VIEWS[task]:
        raise ValueError("invalid result filter")
    if sort == "abs_residual" and task == "se":
        expression = "ABS(residual)"
    elif not sort or sort in columns:
        expression = f"[{sort or key}]"
    else:
        raise ValueError("invalid sort column")
    predicate, params = "run_id = ?", [int(run_id)]
    if view != "all":
        predicate += " AND " + VIEWS[task][view]
    if search:
        predicate += " AND (" + " OR ".join(f"CAST([{col}] AS TEXT) LIKE ?" for col in columns) + ")"
        params.extend([f"%{search}%"] * len(columns))
    # Stable ordering and missing values last in either direction.
    order = f"{expression} IS NULL, {expression} {direction}, {key} ASC"
    return table, columns, predicate, params, order


def hour_window(limit, end_at=None):
    hours = max(1, min(int(limit), 168))
    end = datetime.fromisoformat(end_at.replace("Z", "+00:00")) if end_at else datetime.now(timezone.utc)
    if end.tzinfo is None:
        raise ValueError("end_at must include a timezone")
    end = end.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start = end - timedelta(hours=hours)
    return start, end


def merge_trends(series, start, end):
    buckets = {(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H"): {}
               for i in range(int((end-start).total_seconds() // 3600))}
    for rows in series:
        for row in rows:
            for name, values in row["tasks"].items():
                target = buckets[row["bucket"]].setdefault(name, {
                    "runs": 0, "succeeded": 0, "failed": 0, "running": 0,
                    "elapsed_count": 0, "elapsed_sum": 0.0})
                for field in target:
                    target[field] += values[field]
    return [{"bucket": bucket, "tasks": {name: {**item, "avg_elapsed_seconds":
             item["elapsed_sum"] / item["elapsed_count"] if item["elapsed_count"] else None}
             for name, item in tasks.items()}} for bucket, tasks in buckets.items()]
