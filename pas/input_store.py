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


def initialize_inputs(config):
    se, ca = config.tasks['se'], config.tasks['ca']
    if se.measurement_file and se.measurement_file.suffix.lower() in SQLITE_SUFFIXES:
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


@contextmanager
def measurement_input(task, model=None):
    if task.measurement_file.suffix.lower() not in SQLITE_SUFFIXES:
        yield task.measurement_file, {'source':str(task.measurement_file),'format':'file'}
        return
    batch = refresh_measurements(task)
    model = model if model is not None else model_records(task.model_file)
    units = (model.get('Model') or model.get('PowerBase'))[0]
    selected = [r for r in batch['rows'] if r['valid'] and r['se_enabled'] and r['se_type']]
    if not selected:
        raise ValueError(f"无有效 SE 实时量测：已采集 {batch['total']} 个点，请检查质量、时间及点关联；不使用给定回读代替实测。")
    parts = ['<Measurement>\n@ idx name dev_type dev_name meas_type weight valid value\n']
    for row in selected:
        prefix = row['se_type'].split('_')[0]
        target = units['u_unit'] if prefix=='V' else units['i_unit'] if prefix=='I' else units['p_unit']
        if prefix=='Q': target={'W':'var','kW':'kvar','MW':'Mvar'}[target]
        value = row['value']*_unit_factor(row['unit'],target)
        parts.append('# ' + ' '.join(_cell(v) for v in (row['measurement_id'],f"m{row['measurement_id']}",row['model_table'],row['device_name'],row['se_type'],row['weight'],1,value))+'\n')
    parts.append('</Measurement>\n')
    text=''.join(parts)
    metadata={k:v for k,v in batch.items() if k!='rows'}
    metadata.update(source=str(task.measurement_file),format='scada_sqlite',snapshot_sha256=hashlib.sha256(text.encode()).hexdigest())
    with tempfile.TemporaryDirectory(prefix='pas_meas_') as directory:
        path=Path(directory)/'measurements.meas';path.write_text(text,encoding='utf-8')
        yield path,metadata


def seed_limits(task):
    model=model_records(task.model_file)
    units=(model.get('Model') or model.get('PowerBase'))[0]
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
