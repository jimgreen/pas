"""Scenario measurement mappings, current samples and CA constraints.

SCADA's acquisition database is always opened read-only. Operator changes and
derived samples belong to the separate devices database; limits belong to CA.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
from collections import Counter
from typing import Any

from .model_input import _cell, read_model_tables, SQLITE_SUFFIXES
from .rtdb_schema import execute_schema, schema_transaction

_refresh_lock = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@contextmanager
def connect(path, *, readonly=False):
    path = Path(path).resolve()
    if not readonly:
        path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=30) if readonly else sqlite3.connect(path, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    if not readonly:
        c.execute("PRAGMA journal_mode=WAL")
    try:
        yield c
        if not readonly:
            c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def model_records(path):
    return {name: block['rows'] for name, block in read_model_tables(Path(path)).items()}


def se_type(table, metric, kind):
    if kind != 'yc':
        return None
    # Balanced estimator: use the AB voltage and A current once, not three
    # correlated phase readings as three independent measurements.
    if table in ('ACNode', 'DCNode'):
        return 'V' if metric in ('uab', 'u') else None
    if table in ('ACGenerator', 'DCGenerator', 'ACLoad', 'DCLoad'):
        suffix = 'GEN' if table.endswith('Generator') else 'LOAD'
        return {key: f'{value}_{suffix}' for key, value in {'p':'P','q':'Q','uab':'V','u':'V','ia':'I','i':'I'}.items()}.get(metric)
    if table in ('ACBranch', 'DCBranch', 'ACZeroBranch', 'DCDCConverter'):
        side, _, quantity = metric.partition('_')
        code = {'p':'P','q':'Q','uab':'V','u':'V','ia':'I','i':'I'}.get(quantity)
        return f"{code}_{'FROM' if side == 'i' else 'TO'}" if side in ('i','j') and code else None
    if table == 'DCACConverter':
        return {'ac_p':'P_AC','ac_q':'Q_AC','ac_uab':'V_AC','ac_ia':'I_AC','dc_p':'P_DC','dc_u':'V_DC','dc_i':'I_DC'}.get(metric)
    return None


CA_FIELDS = {
    'ACNode': ('v',), 'DCNode': ('v',),
    'ACGenerator': ('p','v'), 'DCGenerator': ('p','v'),
    'ACLoad': ('p','v'), 'DCLoad': ('p','v'),
    'ACBranch': ('p','i'), 'DCBranch': ('p','i'),
    'ACBreak': ('i','v'), 'DCBreak': ('i','v'),
    'DCDCConverter': ('i_c','j_c','i_v','j_v'),
    'DCACConverter': ('i_c','j_c','i_v','j_v'),
    'ACACConverter': ('i_c','j_c','i_v','j_v'),
}
CA_ALIASES = {'ACGenerator':'ACUnit','DCGenerator':'DCUnit','ACBreak':'ACBreaker','DCBreak':'DCBreaker',
              'DCDCConverter':'DCDCConver','DCACConverter':'DCACConver','ACACConverter':'ACACConver'}


SE_SOLVER_METRICS: dict[str, dict[str, str]] = {
    "ACNode": {"uab": "V"},
    "DCNode": {"u": "V"},
    "ACGenerator": {"p": "P_GEN", "q": "Q_GEN", "uab": "V_GEN", "ia": "I_GEN"},
    "DCGenerator": {"p": "P_GEN", "u": "V_GEN", "i": "I_GEN"},
    "ACLoad": {"p": "P_LOAD", "q": "Q_LOAD", "uab": "V_LOAD", "ia": "I_LOAD"},
    "DCLoad": {"p": "P_LOAD", "u": "V_LOAD", "i": "I_LOAD"},
    "ACBranch": {
        "i_p": "P_FROM", "i_q": "Q_FROM", "i_uab": "V_FROM", "i_ia": "I_FROM",
        "j_p": "P_TO", "j_q": "Q_TO", "j_uab": "V_TO", "j_ia": "I_TO",
    },
    "DCBranch": {
        "i_p": "P_FROM", "i_u": "V_FROM", "i_i": "I_FROM",
        "j_p": "P_TO", "j_u": "V_TO", "j_i": "I_TO",
    },
    "ACZeroBranch": {
        "i_p": "P_FROM", "i_q": "Q_FROM", "i_uab": "V_FROM", "i_ia": "I_FROM",
        "j_p": "P_TO", "j_q": "Q_TO", "j_uab": "V_TO", "j_ia": "I_TO",
    },
    "DCDCConverter": {
        "i_p": "P_FROM", "i_u": "V_FROM", "i_i": "I_FROM",
        "j_p": "P_TO", "j_u": "V_TO", "j_i": "I_TO",
    },
    "DCACConverter": {
        "ac_p": "P_AC", "ac_q": "Q_AC", "ac_uab": "V_AC", "ac_ia": "I_AC",
        "dc_p": "P_DC", "dc_u": "V_DC", "dc_i": "I_DC",
    },
}

# 需要落库到 se.sqlite3 各类设备表 (se_dev_*) 的设备与量测字段定义
SE_DEVICE_RESULT_METRICS: dict[str, dict[str, str]] = {
    **SE_SOLVER_METRICS,
    "ACBreak": {"ia": "I_FROM"},
    "DCBreak": {"i": "I_FROM"},
}


def is_scdfe_d_wide_db(path: str | Path | None) -> bool:
    """判断 SQLite 文件是否为 scdfe_d 按设备分表的宽表量测库（只读探测）。"""
    if path is None:
        return False
    candidate = Path(path)
    if candidate.suffix.lower() not in SQLITE_SUFFIXES or not candidate.is_file():
        return False
    try:
        with connect(candidate, readonly=True) as connection:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if "device_measurement" in tables and "measurement_value" in tables:
                return False
            for device_table in ("ACNode", "DCNode", "ACBranch", "ACGenerator", "DCACConverter"):
                if device_table in tables:
                    columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{device_table}")')}
                    if any(col.endswith("_qual") for col in columns):
                        return True
    except (OSError, sqlite3.Error):
        return False
    return False


def _default_metric_unit(se_code: str, units: dict[str, Any]) -> str:
    prefix = se_code.split("_", 1)[0]
    if prefix == "V":
        return str(units.get("u_unit", "V"))
    if prefix == "I":
        return str(units.get("i_unit", "A"))
    if prefix == "Q":
        return {"W": "var", "kW": "kvar", "MW": "Mvar"}.get(str(units.get("p_unit", "kW")), "kvar")
    return str(units.get("p_unit", "kW"))


_CATALOG_UNIT_CACHE: dict[tuple[str, int, int], dict[tuple[str, str], str]] = {}


def _catalog_units(point_catalog_path: Path | None) -> dict[tuple[str, str], str]:
    if point_catalog_path is None:
        return {}
    p = Path(point_catalog_path)
    if not p.is_file():
        return {}
    try:
        st = p.stat()
        key = (str(p.resolve()), st.st_mtime_ns, st.st_size)
    except OSError:
        return {}
    cached = _CATALOG_UNIT_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        catalog = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    result: dict[tuple[str, str], str] = {}
    for point in catalog.get("points", ()):
        if point.get("kind") == "yc" and point.get("unit"):
            result.setdefault((str(point.get("model_table", "")), str(point.get("metric", ""))), str(point["unit"]))
    if len(_CATALOG_UNIT_CACHE) >= 8:
        _CATALOG_UNIT_CACHE.clear()
    _CATALOG_UNIT_CACHE[key] = result
    return result


def read_scdfe_d_wide_snapshot(
    path: str | Path,
    model: dict[str, list[dict]],
    *,
    point_catalog_path: Path | None = None,
) -> tuple[list[dict], dict]:
    """在单只读事务中读取 scdfe_d.sqlite3 宽表量测与有效遥信，绝不修改源库。"""
    source_path = Path(path).resolve()
    units = (model.get("Model") or model.get("PowerBase") or [{}])[0]
    catalog_unit_map = _catalog_units(point_catalog_path)
    model_names = {
        (table, int(row["idx"])): str(row["name"])
        for table, records in model.items()
        for row in records
        if "idx" in row and "name" in row
    }
    model_has_run_stat = {
        table
        for table, records in model.items()
        if records and "run_stat" in records[0]
    }
    selected: list[dict] = []
    missing_measurements: list[dict] = []
    rejected: Counter[str] = Counter()
    topology_overrides: dict[str, dict[int, dict[str, int]]] = {}
    device_meas: dict[tuple[str, int, str], dict] = {}
    measurement_lookup: dict[int, dict] = {}
    total_candidates = 0
    latest_time_ms: int | None = None
    mid = 0

    with connect(source_path, readonly=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        scada_tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        # 1. 提取有效遥信（断路器分合位置、设备运行状态），用于同步内存拓扑
        for brk_table in ("ACBreak", "DCBreak"):
            if brk_table not in scada_tables or brk_table not in model:
                continue
            cols = {row[1] for row in connection.execute(f'PRAGMA table_info("{brk_table}")')}
            if not {"idx", "position", "position_qual"} <= cols:
                continue
            notuse_expr = '"position_notuse"' if "position_notuse" in cols else "0"
            for row in connection.execute(
                f'SELECT idx, name, position, position_qual, {notuse_expr} AS pos_notuse FROM "{brk_table}" ORDER BY idx'
            ):
                dev_idx = int(row["idx"])
                if model_names.get((brk_table, dev_idx)) != str(row["name"]):
                    continue
                if row["position"] is not None and row["position_qual"] == 0 and not row["pos_notuse"]:
                    pos_val = int(row["position"])
                    if pos_val in (0, 1):
                        topology_overrides.setdefault(brk_table, {}).setdefault(dev_idx, {})["status"] = pos_val

        for table in sorted(model_has_run_stat & scada_tables):
            cols = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
            if not {"idx", "run", "run_qual"} <= cols:
                continue
            notuse_expr = '"run_notuse"' if "run_notuse" in cols else "0"
            for row in connection.execute(
                f'SELECT idx, name, run, run_qual, {notuse_expr} AS run_notuse FROM "{table}" ORDER BY idx'
            ):
                dev_idx = int(row["idx"])
                if model_names.get((table, dev_idx)) != str(row["name"]):
                    continue
                if row["run"] is not None and row["run_qual"] == 0 and not row["run_notuse"]:
                    run_val = int(row["run"])
                    if run_val in (0, 1):
                        topology_overrides.setdefault(table, {}).setdefault(dev_idx, {})["run_stat"] = run_val

        # 2. 提取所有设备表的量测值（全量快照 + 参与 SE 求解的有效集合）
        for table, metric_map in SE_DEVICE_RESULT_METRICS.items():
            if table not in scada_tables:
                continue
            cols = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
            solver_metrics = SE_SOLVER_METRICS.get(table, {})
            for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY idx'):
                dev_idx = int(row["idx"])
                dev_name = str(row["name"])
                model_match = model_names.get((table, dev_idx)) == dev_name
                for metric, se_code in metric_map.items():
                    if metric not in cols:
                        continue
                    raw_val = row[metric]
                    qual = row[f"{metric}_qual"] if f"{metric}_qual" in cols else None
                    notuse = row[f"{metric}_notuse"] if f"{metric}_notuse" in cols else 0
                    weight_raw = row[f"{metric}_weight"] if f"{metric}_weight" in cols else 1.0
                    time_ms = row[f"{metric}_time"] if f"{metric}_time" in cols else None
                    if isinstance(time_ms, (int, float)) and time_ms > 0:
                        t_int = int(time_ms)
                        if latest_time_ms is None or t_int > latest_time_ms:
                            latest_time_ms = t_int

                    target_unit = _default_metric_unit(se_code, units)
                    source_unit = catalog_unit_map.get((table, metric), target_unit)
                    eng_val: float | None = None
                    if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool) and math.isfinite(raw_val):
                        eng_val = float(raw_val) * _unit_factor(source_unit, target_unit)

                    weight = 1.0
                    if isinstance(weight_raw, (int, float)) and not isinstance(weight_raw, bool) and math.isfinite(weight_raw) and weight_raw > 0:
                        weight = float(weight_raw)

                    # 保存到设备级量测表字典（无论是否参与求解，均保留最新有效工程值）
                    is_good_sample = (
                        model_match
                        and eng_val is not None
                        and qual == 0
                        and not bool(notuse)
                    )
                    device_meas[(table, dev_idx, metric)] = {
                        "device_type": table,
                        "device_idx": dev_idx,
                        "device_name": dev_name,
                        "metric": metric,
                        "se_type": se_code,
                        "unit": target_unit,
                        "meas_value": eng_val if is_good_sample else None,
                        "raw_value": eng_val,
                        "qual": qual,
                        "notuse": int(bool(notuse)),
                        "weight": weight,
                        "source_time_ms": int(time_ms) if isinstance(time_ms, (int, float)) and time_ms > 0 else None,
                        "valid": int(is_good_sample),
                    }

                    if metric not in solver_metrics:
                        continue
                    total_candidates += 1
                    reason = None
                    if not model_match:
                        reason = "device_mismatch"
                    elif bool(notuse):
                        reason = "disabled"
                    elif eng_val is None:
                        reason = "missing_sample"
                    elif qual != 0:
                        reason = "bad_quality"
                    if reason:
                        rejected[reason] += 1
                        if model_match and reason in {"missing_sample", "bad_quality", "disabled"}:
                            missing_measurements.append(
                                {
                                    "device_type": table,
                                    "device_idx": dev_idx,
                                    "device_name": dev_name,
                                    "metric": metric,
                                    "meas_name": f"{table}.{dev_idx}.{metric}",
                                    "se_type": se_code,
                                    "unit": target_unit,
                                    "raw_value": eng_val,
                                    "qual": qual,
                                    "notuse": int(bool(notuse)),
                                    "reason": reason,
                                }
                            )
                        continue

                    mid += 1
                    meas_name = f"{table}.{dev_idx}.{metric}"
                    entry = {
                        "measurement_id": mid,
                        "meas_name": meas_name,
                        "model_table": table,
                        "model_idx": dev_idx,
                        "device_name": dev_name,
                        "metric": metric,
                        "se_type": se_code,
                        "unit": target_unit,
                        "value": eng_val,
                        "weight": weight,
                        "quality": int(qual),
                        "source_time_ms": int(time_ms) if isinstance(time_ms, (int, float)) and time_ms > 0 else None,
                    }
                    selected.append(entry)
                    measurement_lookup[mid] = entry

    metadata = {
        "source": str(source_path),
        "format": "scdfe_d_wide",
        "total": total_candidates,
        "se_candidates": total_candidates,
        "se_valid": len(selected),
        "rejected": dict(rejected),
        "latest_source_time_ms": latest_time_ms,
        "topology_overrides": topology_overrides,
        "device_meas": device_meas,
        "measurement_lookup": measurement_lookup,
        "missing_measurements": missing_measurements,
    }
    return selected, metadata


def initialize_inputs(config):
    se, ca = config.tasks['se'], config.tasks['ca']
    if se.measurement_file and se.measurement_file.suffix.lower() in SQLITE_SUFFIXES:
        # scdfe_d 宽表库为外部采集库，只读访问，禁止建表或写入
        if not is_scdfe_d_wide_db(se.measurement_file) and se.measurement_file.name.lower() != "scdfe_d.sqlite3":
            with connect(se.measurement_file) as c:
                with schema_transaction(c, se.measurement_file):
                    execute_schema(c, Path(__file__).with_name('measurement_schema.sql').read_text(encoding='utf-8'))
                    if 'catalog_active' not in {r[1] for r in c.execute('PRAGMA table_info(device_measurement)')}:
                        c.execute('ALTER TABLE device_measurement ADD COLUMN catalog_active INTEGER NOT NULL DEFAULT 1')
            catalog = getattr(se, 'point_catalog_file', None)
            if catalog and catalog.is_file():
                sync_measurements(se)
    if ca.limit_file and ca.limit_file.suffix.lower() in SQLITE_SUFFIXES:
        with connect(ca.limit_file) as c:
            with schema_transaction(c, ca.limit_file):
                execute_schema(c, Path(__file__).with_name('limit_schema.sql').read_text(encoding='utf-8'))
        seed_limits(ca)


def sync_measurements(task):
    model = model_records(task.model_file)
    catalog = json.loads(task.point_catalog_file.read_text(encoding='utf-8-sig'))
    indexed = {(table,int(row['idx'])): row for table,rows in model.items() for row in rows if 'idx' in row and 'name' in row}
    points = [p for p in catalog['points'] if p['kind'] in ('yc','yx')]
    # Verify the catalog still belongs to this model before committing anything.
    for p in points:
        row = indexed.get((p['model_table'],int(p['model_idx'])))
        if row is None or row['name'] != p['device_name']:
            raise ValueError(f"Point catalog no longer matches model: {p['model_table']}[{p['model_idx']}]")
    stamp = now()
    with _refresh_lock, connect(task.measurement_file) as c:
        c.execute('UPDATE device SET active=0')
        c.execute('UPDATE device_measurement SET catalog_active=0')
        for p in points:
            row = indexed[(p['model_table'],int(p['model_idx']))]
            c.execute('''INSERT INTO device(model_table,model_idx,name,scada_dev_id,model_json) VALUES(?,?,?,?,?)
                ON CONFLICT(model_table,model_idx) DO UPDATE SET name=excluded.name,scada_dev_id=excluded.scada_dev_id,model_json=excluded.model_json,active=1''',
                (p['model_table'],p['model_idx'],row['name'],p['dev_id'],json.dumps(row,ensure_ascii=False)))
            did = c.execute('SELECT device_id FROM device WHERE model_table=? AND model_idx=?',(p['model_table'],p['model_idx'])).fetchone()[0]
            kind = se_type(p['model_table'],p['metric'],p['kind'])
            c.execute('''INSERT INTO device_measurement(device_id,metric,kind,name,unit,se_type,se_enabled,origin,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(device_id,kind,metric) DO UPDATE SET catalog_active=1''',
                (did,p['metric'],p['kind'],p['name'],p['unit'],kind,int(kind is not None),p['seed_origin'],stamp))
            mid = c.execute('SELECT measurement_id FROM device_measurement WHERE device_id=? AND kind=? AND metric=?',(did,p['kind'],p['metric'])).fetchone()[0]
            c.execute('''INSERT INTO scada_point_mapping(measurement_id,source_database,rtu_id,pnt_no,updated_at) VALUES(?,?,?,?,?)
                         ON CONFLICT(measurement_id) DO NOTHING''',(mid,task.scada_source_file.name,p['rtu_id'],p['pnt_no'],stamp))
        c.execute("INSERT INTO input_change_log(changed_at,entity,before_json,after_json) VALUES(?,'catalog_sync','{}',?)",(stamp,json.dumps({'points':len(points)})))
    return {'points':len(points),'devices':len({(p['model_table'],p['model_idx']) for p in points})}


def refresh_measurements(task):
    with _refresh_lock, connect(task.measurement_file) as c:
        rows = [dict(r) for r in c.execute('SELECT * FROM device_measurement_view ORDER BY measurement_id')]
        stamp, instant = now(), time.time()*1000
        source = task.scada_source_file
        catalog = json.loads(task.point_catalog_file.read_text(encoding='utf-8-sig')) if task.point_catalog_file and task.point_catalog_file.is_file() else {'points':[]}
        semantics = {(p['kind'],p['rtu_id'],p['pnt_no']):p for p in catalog['points']}
        values, error = {}, ''
        try:
            with connect(source, readonly=True) as scada:
                scada.execute('BEGIN')
                for kind in ('yc','yx'):
                    for row in scada.execute(f'SELECT * FROM fes_{kind}_define'):
                        values[(kind,row['rtu_id'],row['pnt_no'])] = dict(row)
        except (OSError,sqlite3.Error) as exc:
            error = str(exc)
        batch = c.execute('INSERT INTO measurement_refresh(started_at,source_database,error) VALUES(?,?,?)',(stamp,str(source),error)).lastrowid
        samples, valid_count, se_count = [], 0, 0
        for row in rows:
            point = values.get((row['kind'],row['rtu_id'],row['pnt_no']))
            reason, value, quality, source_time, raw = '', None, None, None, None
            if not row['active'] or not row['catalog_active']: reason = 'device_inactive'
            elif not row['mapping_enabled']: reason = 'mapping_disabled'
            elif row['source_database'] != source.name: reason = 'source_mismatch'
            elif error: reason = 'source_unavailable'
            elif point is None: reason = 'point_missing'
            elif row['scada_dev_id'] is not None and point.get('dev_id') != row['scada_dev_id']: reason = 'device_mismatch'
            elif row['se_enabled'] and (spec:=semantics.get((row['kind'],row['rtu_id'],row['pnt_no']))) and (spec['metric']!=row['metric'] or spec['unit']!=row['unit']): reason = 'semantic_mismatch'
            if not reason and (spec:=semantics.get((row['kind'],row['rtu_id'],row['pnt_no']))) and point.get('name') is not None and point['name']!=spec.get('name'):
                reason='point_definition_changed'
            if point:
                raw, quality = point.get('value'), point.get('status')
                source_time = point.get('raw_time') if row['kind']=='yc' else point.get('refresh_time')
                if not reason:
                    if quality != 0: reason = 'bad_quality'
                    elif point.get('iflock'): reason = 'locked'
                    elif not source_time or source_time<=0: reason = 'no_timestamp'
                    elif source_time>instant+5000: reason = 'future_timestamp'
                    elif instant-source_time>row['max_age_seconds']*1000: reason = 'stale'
                if isinstance(raw,(float,int)) and math.isfinite(raw):
                    value = raw*row['scale']+row['offset']
                    if not math.isfinite(value): value=None;reason=reason or 'invalid_value'
                else: reason=reason or 'invalid_value';raw=None
            valid = int(not reason)
            valid_count += valid
            se_count += valid*row['se_enabled']
            samples.append((row['measurement_id'],batch,raw,value,quality,source_time,stamp,valid,reason))
            row.update(value=value,quality=quality,source_time_ms=source_time,valid=valid,reason=reason,refresh_id=batch)
        c.executemany('''INSERT OR REPLACE INTO measurement_value
            (measurement_id,refresh_id,source_value,value,quality,source_time_ms,collected_at,valid,reason) VALUES(?,?,?,?,?,?,?,?,?)''',samples)
        c.execute('UPDATE measurement_refresh SET finished_at=?,total_count=?,valid_count=?,se_valid_count=? WHERE refresh_id=?',
                  (now(),len(rows),valid_count,se_count,batch))
        return {'refresh_id':batch,'total':len(rows),'valid':valid_count,'se_valid':se_count,'source_error':error,'rows':rows}


def _unit_factor(unit, target):
    groups = ({'mV':.001,'V':1,'kV':1000},{'W':.001,'kW':1,'MW':1000},
              {'var':.001,'kvar':1,'Mvar':1000},{'mA':.001,'A':1,'kA':1000})
    for group in groups:
        if unit in group and target in group:
            return group[unit]/group[target]
    raise ValueError(f'Unsupported measurement unit conversion: {unit} -> {target}')


def read_scada_snapshot(path, model, *, point_catalog_path: Path | None = None):
    """Read the collector's latest completed batch without writing to SCADA."""
    if is_scdfe_d_wide_db(path):
        return read_scdfe_d_wide_snapshot(path, model, point_catalog_path=point_catalog_path)
    with connect(path, readonly=True) as connection:
        connection.execute("BEGIN")
        refresh = connection.execute(
            "SELECT refresh_id, finished_at, total_count FROM measurement_refresh "
            "WHERE finished_at IS NOT NULL ORDER BY refresh_id DESC LIMIT 1"
        ).fetchone()
        if refresh is None:
            raise ValueError(f"SCADA 量测库没有完成的采集批次：{path}")
        rows = connection.execute(
            """SELECT m.measurement_id, m.metric, m.kind, m.unit, m.se_type, m.weight,
                      m.max_age_seconds, m.notuse, d.model_table, d.model_idx, d.name AS device_name,
                      d.active, s.enabled AS mapping_enabled, v.value, v.quality, v.source_time_ms,
                      v.valid, v.reason, v.refresh_id
               FROM device_measurement m JOIN device d USING (device_id)
               LEFT JOIN scada_point_mapping s USING (measurement_id)
               LEFT JOIN measurement_value v USING (measurement_id)
               WHERE m.catalog_active=1 AND m.se_enabled=1 ORDER BY m.measurement_id"""
        ).fetchall()
    model_names = {(table, str(row["idx"])): str(row["name"])
                   for table, records in model.items() for row in records if "idx" in row and "name" in row}
    instant_ms = time.time() * 1000
    selected, rejected = [], Counter()
    for row in rows:
        reason = None
        if not row["active"] or not row["mapping_enabled"] or row["notuse"]:
            reason = "disabled"
        elif row["kind"] != "yc" or not row["se_type"] or row["metric"].endswith("_readback"):
            reason = "unsupported_quantity"
        elif model_names.get((row["model_table"], str(row["model_idx"]))) != row["device_name"]:
            reason = "device_mismatch"
        elif row["refresh_id"] != refresh["refresh_id"]:
            reason = "missing_sample"
        elif not row["valid"] or row["quality"] != 0:
            reason = row["reason"] or "bad_quality"
        elif not isinstance(row["value"], (float, int)) or not math.isfinite(row["value"]):
            reason = "invalid_value"
        elif not row["source_time_ms"] or row["source_time_ms"] <= 0:
            reason = "no_timestamp"
        elif row["source_time_ms"] > instant_ms + 5000:
            reason = "future_timestamp"
        elif instant_ms - row["source_time_ms"] > row["max_age_seconds"] * 1000:
            reason = "stale"
        if reason:
            rejected[reason] += 1
        else:
            selected.append(dict(row))
    return selected, {
        "source": str(path), "format": "scdfe_d_sqlite", "refresh_id": refresh["refresh_id"],
        "collected_at": refresh["finished_at"], "total": refresh["total_count"],
        "se_candidates": len(rows), "se_valid": len(selected), "rejected": dict(rejected),
    }


@contextmanager
def measurement_input(
    task,
    model=None,
    *,
    scada_snapshot=False,
    bad_policies: list[dict] | None = None,
    prefilter_rules: list[dict] | None = None,
    pseudo_meas_defines: list[dict] | None = None,
    pseudo_stat_defines: list[dict] | None = None,
):
    if not scada_snapshot and task.measurement_file.suffix.lower() not in SQLITE_SUFFIXES:
        yield task.measurement_file, {'source':str(task.measurement_file),'format':'file'}
        return
    model = model if model is not None else model_records(task.model_file)
    units_raw = (model.get('Model') or model.get('PowerBase') or [{}])[0]
    units = {
        'u_unit': str(units_raw.get('u_unit') or 'V'),
        'i_unit': str(units_raw.get('i_unit') or 'A'),
        'p_unit': str(units_raw.get('p_unit') or 'kW'),
    }
    wide_mode = is_scdfe_d_wide_db(task.measurement_file)
    active_pseudos = [
        p for p in (pseudo_meas_defines or ())
        if int(p.get("meas_useflag", 1)) and str(p.get("device_type") or "") in SE_SOLVER_METRICS
    ]
    if scada_snapshot or wide_mode:
        selected, metadata = read_scada_snapshot(
            task.measurement_file,
            model,
            point_catalog_path=getattr(task, "point_catalog_file", None),
        )
        if not selected and not active_pseudos:
            reasons = ", ".join(f"{reason}={count}" for reason, count in sorted(metadata["rejected"].items()))
            batch_tag = f"批次 #{metadata['refresh_id']}，" if "refresh_id" in metadata else ""
            raise ValueError(
                f"无有效 SE 实时量测：{metadata['source']} {batch_tag}"
                f"候选 {metadata['se_candidates']}，有效 0（{reasons or '无候选点'}）"
            )
    else:
        batch = refresh_measurements(task)
        selected = [r for r in batch['rows'] if r['valid'] and r['se_enabled'] and r['se_type']]
        if not selected and not active_pseudos:
            raise ValueError(f"无有效 SE 实时量测：已采集 {batch['total']} 个点，请检查质量、时间及点关联；不使用给定回读代替实测。")
        metadata = {k:v for k,v in batch.items() if k!='rows'}
        metadata.update(source=str(task.measurement_file), format='scada_sqlite')

    # 1. 合并人工伪状态覆盖（仅影响内存临时模型，绝不修改外部源库）
    model_idx_by_name = {
        table: {str(row.get("name", row.get("idx", ""))): int(row["idx"]) for row in rows if "idx" in row}
        for table, rows in model.items()
    }
    pseudo_stat_applied = 0
    if pseudo_stat_defines:
        topo_overrides = metadata.setdefault("topology_overrides", {})
        for pstat in pseudo_stat_defines:
            if not int(pstat.get("stat_useflag", 1)):
                continue
            d_type = str(pstat.get("device_type") or "")
            d_name = str(pstat.get("dev_name") or pstat.get("device_name") or "")
            metric = str(pstat.get("metric") or "status")
            d_idx = pstat.get("device_idx")
            if d_idx is None:
                d_idx = model_idx_by_name.get(d_type, {}).get(d_name)
            if d_type and d_idx is not None and pstat.get("stat_value") is not None:
                val = 1 if int(float(pstat["stat_value"])) != 0 else 0
                topo_overrides.setdefault(d_type, {}).setdefault(int(d_idx), {})[metric] = val
                pseudo_stat_applied += 1

    # 2. 构建坏量测屏蔽查找表（enabled=1 的 suppress / replace_pseudo 策略）
    suppress_map: dict[tuple[str, str, str], dict] = {}
    for pol in bad_policies or ():
        if not int(pol.get("enabled", 1)):
            continue
        suppress_map[(str(pol.get("device_type") or ""), str(pol.get("device_name") or ""), str(pol.get("metric") or ""))] = pol

    active_rules = [r for r in (prefilter_rules or ()) if int(r.get("enabled", 1))]
    use_status_col = bool(suppress_map or active_rules or active_pseudos)
    header = (
        '<Measurement>\n@ idx name dev_type dev_name meas_type weight valid value status\n'
        if use_status_col
        else '<Measurement>\n@ idx name dev_type dev_name meas_type weight valid value\n'
    )
    parts = [header]
    lookup: dict[int, dict] = {}
    max_mid = 0
    policy_suppressed_count = 0
    rule_prefiltered_count = 0

    from .se_prefilter import evaluate_prefilter_rule

    for row in selected:
        mid = int(row['measurement_id'])
        if mid > max_mid:
            max_mid = mid
        prefix = row['se_type'].split('_')[0]
        target = units['u_unit'] if prefix=='V' else units['i_unit'] if prefix=='I' else units['p_unit']
        if prefix=='Q': target={'W':'var','kW':'kvar','MW':'Mvar'}[target]
        value = row['value']*_unit_factor(row['unit'],target)
        mname = row.get('meas_name') or f"m{mid}"
        pol = suppress_map.get((str(row['model_table']), str(row['device_name']), str(row.get('metric') or '')))
        rule_hit = None
        if pol is None and active_rules:
            rule_hit = evaluate_prefilter_rule(
                active_rules,
                device_type=str(row['model_table']),
                device_name=str(row['device_name']),
                metric=str(row.get('metric') or ''),
                value=float(value),
            )
        excluded = (pol is not None) or (rule_hit is not None)
        valid_flag = 0 if excluded else 1
        status_flag = 1 if excluded else 0  # 0=NORMAL, 1=INVALID
        if pol is not None:
            policy_suppressed_count += 1
        elif rule_hit is not None:
            rule_prefiltered_count += 1
        cols = (mid, mname, row['model_table'], row['device_name'], row['se_type'], row['weight'], valid_flag, value)
        if use_status_col:
            cols = (*cols, status_flag)
        parts.append('# ' + ' '.join(_cell(v) for v in cols) + '\n')
        lookup[mid] = {
            "measurement_id": mid,
            "meas_name": mname,
            "model_table": str(row["model_table"]),
            "model_idx": row.get("model_idx"),
            "device_name": str(row["device_name"]),
            "metric": str(row.get("metric") or ""),
            "se_type": str(row["se_type"]),
            "unit": target,
            "value": float(value),
            "weight": float(row["weight"]),
            "source_time_ms": row.get("source_time_ms"),
            "policy_suppressed": bool(pol is not None),
            "policy_id": pol.get("id") if pol is not None else None,
            "policy_reason": str(pol.get("reason") or pol.get("action") or "") if pol is not None else "",
            "rule_prefiltered": bool(rule_hit is not None),
            "prefilter_rule_id": rule_hit.get("rule_id") if rule_hit is not None else None,
            "prefilter_min_value": rule_hit.get("min_value") if rule_hit is not None else None,
            "prefilter_max_value": rule_hit.get("max_value") if rule_hit is not None else None,
            "prefilter_reason": str(rule_hit.get("reason") or "") if rule_hit is not None else "",
        }

    # 3. 注入人工启用的伪量测（status=2 对应内核 MEAS_STATUS_PSEUDO）
    user_pseudo_injected = 0
    for pdef in active_pseudos:
        d_type = str(pdef["device_type"])
        metric = str(pdef.get("metric") or "")
        se_code = str(pdef.get("se_type") or SE_SOLVER_METRICS.get(d_type, {}).get(metric, ""))
        d_name = str(pdef.get("dev_name") or pdef.get("device_name") or "")
        if not se_code or not d_name:
            continue
        if d_name not in model_idx_by_name.get(d_type, {}):
            continue
        max_mid += 1
        prefix = se_code.split('_')[0]
        target = units['u_unit'] if prefix=='V' else units['i_unit'] if prefix=='I' else units['p_unit']
        if prefix=='Q': target={'W':'var','kW':'kvar','MW':'Mvar'}[target]
        src_unit = str(pdef.get("unit") or target)
        value = float(pdef["meas_value"]) * _unit_factor(src_unit, target)
        weight = float(pdef.get("meas_weight") or 1e-4)
        mname = str(pdef.get("meas_name") or f"pseudo.{d_type}.{d_name}.{metric}")
        parts.append('# ' + ' '.join(_cell(v) for v in (max_mid, mname, d_type, d_name, se_code, weight, 1, value, 2)) + '\n')
        d_idx = pdef.get("device_idx")
        if d_idx is None:
            d_idx = model_idx_by_name.get(d_type, {}).get(d_name)
        lookup[max_mid] = {
            "measurement_id": max_mid,
            "meas_name": mname,
            "model_table": d_type,
            "model_idx": d_idx,
            "device_name": d_name,
            "metric": metric,
            "se_type": se_code,
            "unit": target,
            "value": float(value),
            "weight": weight,
            "is_user_pseudo": True,
            "pseudo_define_id": int(pdef["id"]),
            "pseudo_note": str(pdef.get("note") or pdef.get("source_mode") or "user_defined"),
        }
        user_pseudo_injected += 1

    if not selected and user_pseudo_injected == 0:
        raise ValueError("无有效 SE 实时量测且已启用的伪量测均未匹配当前模型设备，已终止计算。")

    parts.append('</Measurement>\n')
    text=''.join(parts)
    metadata["snapshot_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    metadata["_measurement_lookup"] = lookup
    metadata["policy_suppressed_count"] = policy_suppressed_count
    metadata["rule_prefiltered_count"] = rule_prefiltered_count
    metadata["user_pseudo_injected"] = user_pseudo_injected
    metadata["pseudo_stat_applied"] = pseudo_stat_applied
    with tempfile.TemporaryDirectory(prefix='pas_meas_') as directory:
        path=Path(directory)/'measurements.meas';path.write_text(text,encoding='utf-8')
        yield path,metadata


def seed_limits(task):
    model=model_records(task.model_file)
    units_raw=(model.get('Model') or model.get('PowerBase') or [{}])[0]
    units={'u_unit':str(units_raw.get('u_unit') or 'V'),'i_unit':str(units_raw.get('i_unit') or 'A'),'p_unit':str(units_raw.get('p_unit') or 'kW')}
    nodes={side:{r['idx']:r for r in model.get(side+'Node',[])} for side in ('AC','DC')}
    candidates=[]
    for table,fields in CA_FIELDS.items():
        for row in model.get(table,[]):
            for field in fields:
                key=field.replace('_c','_i')
                lower,upper=row.get(key+'_min'),row.get(key+'_max')
                if lower is None and upper is None or (lower or 0)==0 and (upper or 0)==0:
                    continue
                unit=units['u_unit'] if field.endswith('v') else 'kW' if field=='p' else 'A'
                factor=1.
                if field.endswith('v'):
                    side='DC' if table.startswith('DC') else 'AC'
                    node_key='node'
                    if table=='DCDCConverter': node_key=field[0]+'_node';side='DC'
                    elif table=='DCACConverter': node_key='dc_node' if field[0]=='i' else 'ac_node';side='DC' if field[0]=='i' else 'AC'
                    elif table=='ACACConverter': node_key=field[0]+'_node';side='AC'
                    node=row if table in ('ACNode','DCNode') else nodes[side].get(row.get(node_key),{})
                    factor=node.get('vbase',0)
                    if not factor or not all(0<float(v)<3 for v in (lower,upper) if v is not None): continue
                elif field=='p': factor=_unit_factor(units['p_unit'],'kW')
                else: factor=_unit_factor(units['i_unit'],'A')
                lower=None if lower is None else float(lower)*factor
                upper=None if upper is None else float(upper)*factor
                if lower is not None and upper is not None and lower>upper: continue
                candidates.append((table,row['idx'],row['name'],field,lower,upper,unit,
                    f"model:{table}[{row['idx']}].{key}_min/{key}_max; multiplier={factor}",now()))
    with connect(task.limit_file) as c:
        before=c.total_changes
        c.executemany('''INSERT INTO ca_limit(model_table,model_idx,device_name,field,lower_value,upper_value,unit,source,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(model_table,model_idx,field) DO NOTHING''',candidates)
        return {'inserted':c.total_changes-before,'candidates':len(candidates)}


def read_limits(task, model=None):
    with connect(task.limit_file,readonly=True) as c:
        rows=[dict(r) for r in c.execute('SELECT * FROM ca_limit WHERE enabled=1 ORDER BY limit_id')]
    if not rows: raise ValueError('CA 限值表没有启用的限值')
    model=model if model is not None else model_records(task.model_file)
    index={(t,int(r['idx'])):r for t,rr in model.items() for r in rr if 'idx' in r}
    constraints={}
    for row in rows:
        device=index.get((row['model_table'],row['model_idx']))
        if not device or device['name']!=row['device_name']: raise ValueError(f"CA limit {row['limit_id']} no longer matches model")
        field=row['field']
        if field not in CA_FIELDS.get(row['model_table'],()): raise ValueError('Unsupported CA constraint field')
        table=CA_ALIASES.get(row['model_table'],row['model_table'])
        values=constraints.setdefault(table,{}).setdefault(row['device_name'],{})
        units=(model.get('Model') or model.get('PowerBase'))[0]
        target=units['u_unit'] if field.endswith('v') else 'kW' if field=='p' else 'A'
        factor=_unit_factor(row['unit'],target)
        for side,column in (('min','lower_value'),('max','upper_value')):
            if row[column] is not None:
                if not math.isfinite(row[column]): raise ValueError('Non-finite CA limit')
                values[field+'_'+side]=row[column]*factor
    return constraints, {'source':str(task.limit_file),'count':len(rows),'snapshot_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}


def browse_inputs(config, kind, *, q='', page=0, size=8, view='all'):
    if kind not in ('measurements','limits'): raise ValueError('Unknown input collection')
    size=max(1,min(100,int(size)));page=max(0,int(page));q=str(q)[:200]
    task=config.tasks['se' if kind=='measurements' else 'ca']
    path=task.measurement_file if kind=='measurements' else task.limit_file
    if kind == 'measurements' and is_scdfe_d_wide_db(path):
        model = model_records(task.model_file)
        selected, metadata = read_scdfe_d_wide_snapshot(
            path,
            model,
            point_catalog_path=getattr(task, 'point_catalog_file', None),
        )
        rows = []
        for idx, ((table, dev_idx, metric), item) in enumerate(sorted(metadata['device_meas'].items()), 1):
            se_enabled = int(metric in SE_SOLVER_METRICS.get(table, {}))
            rows.append({
                'measurement_id': idx,
                'model_table': table,
                'model_idx': dev_idx,
                'device_name': item['device_name'],
                'metric': metric,
                'name': f'{table}.{dev_idx}.{metric}',
                'unit': item['unit'],
                'se_type': item['se_type'],
                'se_enabled': se_enabled,
                'weight': item['weight'],
                'value': item['meas_value'],
                'quality': item['qual'],
                'source_time_ms': item['source_time_ms'],
                'valid': item['valid'],
                'reason': '' if item['valid'] else ('disabled' if item['notuse'] else ('bad_quality' if item['qual'] != 0 else 'missing_sample')),
            })
        stats = {
            'total': len(rows),
            'valid': sum(bool(r['valid']) for r in rows),
            'se_enabled': sum(r['se_enabled'] for r in rows),
            'se_valid': len(selected),
        }
        if view == 'se':
            rows = [r for r in rows if r['se_enabled']]
        elif view == 'invalid':
            rows = [r for r in rows if not r['valid']]
        elif view == 'valid':
            rows = [r for r in rows if r['valid']]
        elif view != 'all':
            raise ValueError('Unknown measurement filter')
        if q:
            rows = [r for r in rows if q.casefold() in ' '.join(str(r.get(k, '')) for k in ('model_table', 'model_idx', 'device_name', 'metric', 'name')).casefold()]
        return {'rows': rows[page*size:(page+1)*size], 'total': len(rows), 'stats': stats, 'path': str(path)}
    with connect(path,readonly=True) as c:
        if kind=='measurements':
            rows=[dict(r) for r in c.execute('SELECT * FROM device_measurement_view ORDER BY measurement_id')]
            instant=time.time()*1000
            for row in rows:
                if row['valid'] and (not row['source_time_ms'] or instant-row['source_time_ms']>row['max_age_seconds']*1000):
                    row['valid']=0;row['reason']='stale'
                if not row['mapping_enabled'] or not row['active'] or not row['catalog_active']:
                    row['valid']=0;row['reason']='mapping_disabled' if not row['mapping_enabled'] else 'device_inactive'
            stats={'total':len(rows),'valid':sum(bool(r['valid']) for r in rows),
                   'se_enabled':sum(r['se_enabled'] for r in rows),'se_valid':sum(bool(r['valid']) and r['se_enabled'] for r in rows)}
            if view=='se': rows=[r for r in rows if r['se_enabled']]
            elif view=='invalid': rows=[r for r in rows if not r['valid']]
            elif view=='valid': rows=[r for r in rows if r['valid']]
            elif view!='all': raise ValueError('Unknown measurement filter')
        else:
            rows=[dict(r) for r in c.execute('SELECT * FROM ca_limit ORDER BY limit_id')]
            stats={'total':len(rows),'enabled':sum(r['enabled'] for r in rows)}
            if view=='enabled': rows=[r for r in rows if r['enabled']]
            elif view=='disabled': rows=[r for r in rows if not r['enabled']]
            elif view!='all': raise ValueError('Unknown limit filter')
        if q:
            rows=[r for r in rows if q.casefold() in ' '.join(str(r.get(k,'')) for k in ('model_table','model_idx','device_name','metric','name','field','rtu_id','pnt_no')).casefold()]
        total=len(rows)
        return {'rows':rows[page*size:(page+1)*size],'total':total,'stats':stats,'path':str(path)}


def _numeric(value, name, *, integer=False, minimum=None, maximum=None):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if integer and int(value)!=value: raise ValueError(f'{name} must be an integer')
    if minimum is not None and value<minimum or maximum is not None and value>maximum:
        raise ValueError(f'{name} outside allowed range')
    return int(value) if integer else float(value)


def update_measurement(task, entity, identity, payload):
    allowed={'measurement':{'weight','max_age_seconds','se_enabled'},'mapping':{'rtu_id','pnt_no','enabled','scale','offset'}}
    if entity not in allowed or set(payload)-allowed[entity]-{'version'}: raise ValueError('Unknown measurement fields')
    with _refresh_lock,connect(task.measurement_file) as c:
        c.execute('BEGIN IMMEDIATE')
        table='device_measurement' if entity=='measurement' else 'scada_point_mapping'
        original=c.execute(f'SELECT * FROM {table} WHERE measurement_id=?',(identity,)).fetchone()
        if original is None: raise ValueError('Measurement not found')
        original=dict(original)
        if payload.get('version')!=original['version']: raise ValueError('记录已更新，请刷新后再保存')
        updated={**original,**{k:v for k,v in payload.items() if k!='version'}}
        for flag in ('se_enabled','enabled'):
            if flag in updated: updated[flag]=_numeric(updated[flag],flag,integer=True,minimum=0,maximum=1)
        if entity=='measurement':
            updated['weight']=_numeric(updated['weight'],'weight',minimum=1e-12,maximum=1e12)
            updated['max_age_seconds']=_numeric(updated['max_age_seconds'],'max_age_seconds',minimum=1,maximum=86400)
            if updated['se_enabled'] and not updated['se_type']: raise ValueError('该量测类型不参与 SE，给定值回读不能替代实测')
        else:
            updated['rtu_id']=_numeric(updated['rtu_id'],'rtu_id',integer=True,minimum=1)
            updated['pnt_no']=_numeric(updated['pnt_no'],'pnt_no',integer=True,minimum=0)
            for field in ('scale','offset'): updated[field]=_numeric(updated[field],field)
            if updated['scale']==0: raise ValueError('scale cannot be zero')
            device=c.execute('SELECT m.kind,d.scada_dev_id FROM device_measurement m JOIN device d USING(device_id) WHERE measurement_id=?',(identity,)).fetchone()
            with connect(task.scada_source_file,readonly=True) as scada:
                point=scada.execute(f"SELECT dev_id FROM fes_{device['kind']}_define WHERE rtu_id=? AND pnt_no=?",(updated['rtu_id'],updated['pnt_no'])).fetchone()
            if not point or point['dev_id']!=device['scada_dev_id']: raise ValueError('SCADA 点不存在或不属于此设备')
            if task.point_catalog_file and task.point_catalog_file.is_file():
                catalog=json.loads(task.point_catalog_file.read_text(encoding='utf-8-sig'))
                source=next((p for p in catalog['points'] if (p['kind'],p['rtu_id'],p['pnt_no'])==(device['kind'],updated['rtu_id'],updated['pnt_no'])),None)
                definition=c.execute('SELECT metric,unit FROM device_measurement WHERE measurement_id=?',(identity,)).fetchone()
                if source and (source['metric']!=definition['metric'] or source['unit']!=definition['unit']):
                    raise ValueError('SCADA 点量测类型或单位不匹配，不能用给定回读替代实测')
        fields=sorted(allowed[entity])
        c.execute(f"UPDATE {table} SET "+','.join(f'{f}=?' for f in fields)+',version=version+1,updated_at=? WHERE measurement_id=?',
                  [updated[f] for f in fields]+[now(),identity])
        # Any edit invalidates the previously collected value until resampled.
        c.execute("UPDATE measurement_value SET valid=0,reason='configuration_changed' WHERE measurement_id=?",(identity,))
        c.execute('INSERT INTO input_change_log(changed_at,entity,entity_id,before_json,after_json) VALUES(?,?,?,?,?)',
                  (now(),entity,identity,json.dumps(original,ensure_ascii=False),json.dumps(updated,ensure_ascii=False)))
    return {'measurement_id':identity,'version':original['version']+1}


def limit_options(task):
    model=model_records(task.model_file)
    return [{'model_table':t,'model_idx':r['idx'],'device_name':r['name'],'fields':fields}
            for t,fields in CA_FIELDS.items() for r in model.get(t,[])]


def save_limit(task, payload):
    allowed={'limit_id','version','model_table','model_idx','field','lower_value','upper_value','unit','enabled'}
    if set(payload)-allowed: raise ValueError('Unknown limit fields')
    identity=payload.get('limit_id')
    with connect(task.limit_file) as c:
        c.execute('BEGIN IMMEDIATE')
        original=c.execute('SELECT * FROM ca_limit WHERE limit_id=?',(identity,)).fetchone() if identity else None
        if identity and original is None: raise ValueError('Limit not found')
        original=dict(original) if original else {}
        if original and payload.get('version')!=original['version']: raise ValueError('记录已更新，请刷新后再保存')
        row={**original,**payload}
        table,idx,field=row.get('model_table'),row.get('model_idx'),row.get('field')
        if field not in CA_FIELDS.get(table,()): raise ValueError('Unsupported device/limit field')
        idx=_numeric(idx,'model_idx',integer=True,minimum=0)
        devices=limit_options(task)
        device=next((d for d in devices if d['model_table']==table and d['model_idx']==idx),None)
        if not device: raise ValueError('Model device not found')
        lower,upper=row.get('lower_value'),row.get('upper_value')
        if lower is None and upper is None: raise ValueError('至少填写一个限值')
        if lower is not None: lower=_numeric(lower,'lower_value')
        if upper is not None: upper=_numeric(upper,'upper_value')
        if lower is not None and upper is not None and lower>upper: raise ValueError('下限不能大于上限')
        unit=row.get('unit','')
        _unit_factor(unit,'V' if field.endswith('v') else 'kW' if field=='p' else 'A')
        enabled=_numeric(row.get('enabled',1),'enabled',integer=True,minimum=0,maximum=1)
        values=(table,idx,device['device_name'],field,lower,upper,unit,enabled,'operator',now())
        if original:
            c.execute('''UPDATE ca_limit SET model_table=?,model_idx=?,device_name=?,field=?,lower_value=?,upper_value=?,unit=?,enabled=?,source=?,updated_at=?,version=version+1 WHERE limit_id=?''',(*values,identity))
        else:
            identity=c.execute('''INSERT INTO ca_limit(model_table,model_idx,device_name,field,lower_value,upper_value,unit,enabled,source,updated_at)
                                  VALUES(?,?,?,?,?,?,?,?,?,?)''',values).lastrowid
        saved=dict(c.execute('SELECT * FROM ca_limit WHERE limit_id=?',(identity,)).fetchone())
        c.execute('INSERT INTO ca_limit_change_log(changed_at,limit_id,before_json,after_json) VALUES(?,?,?,?)',
                  (now(),identity,json.dumps(original,ensure_ascii=False),json.dumps(saved,ensure_ascii=False)))
        return saved
