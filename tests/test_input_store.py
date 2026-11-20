import json
from pathlib import Path
import sqlite3
import time
from types import SimpleNamespace

import pytest

from pas.config import TaskConfig
from pas.input_store import (initialize_inputs,connect,sync_measurements,refresh_measurements,
                            measurement_input,update_measurement,save_limit,read_limits,browse_inputs,seed_limits)


def environment(tmp_path):
    model=tmp_path/'model.sqlite3'
    tables={'Model':[{'name':'test','p_base':100,'u_unit':'V','p_unit':'kW','i_unit':'A'}],
            'ACNode':[{'idx':1,'name':'母线','vbase':380}],
            'ACGenerator':[{'idx':1,'name':'机组','node':1,'p_min':0,'p_max':10,'v_min':.9,'v_max':1.1}]}
    with sqlite3.connect(model) as c:
        c.execute('CREATE TABLE rtdb_schema_tables(table_name,ordinal)')
        c.execute('CREATE TABLE rtdb_schema_columns(table_name,ordinal,eng_name)')
        for i,(table,rows) in enumerate(tables.items()):
            fields=list(rows[0]);c.execute('INSERT INTO rtdb_schema_tables VALUES(?,?)',(table,i))
            c.executemany('INSERT INTO rtdb_schema_columns VALUES(?,?,?)',[(table,j,f) for j,f in enumerate(fields)])
            c.execute(f'CREATE TABLE rtdb_data_{table}(_pos INTEGER PRIMARY KEY,'+','.join(f'c{j}' for j in range(len(fields)))+')')
            c.executemany(f'INSERT INTO rtdb_data_{table} VALUES('+','.join('?' for _ in range(len(fields)+1))+')',[(n,*r.values()) for n,r in enumerate(rows)])
    catalog=tmp_path/'point_catalog.json'
    points=[dict(model_table='ACGenerator',model_idx=1,device_name='机组',dev_id=11,kind='yc',metric=metric,
        unit='kW',rtu_id=1,pnt_no=i,name=metric,seed_origin='template') for i,metric in enumerate(('p','p_set_readback'),1)]
    catalog.write_text(json.dumps({'points':points}),encoding='utf-8')
    source=tmp_path/'scdfe_c.sqlite3'
    with sqlite3.connect(source) as c:
        c.execute('CREATE TABLE fes_yc_define(rtu_id,pnt_no,value,status,raw_time,refresh_time,iflock,dev_id)')
        c.execute('CREATE TABLE fes_yx_define(rtu_id,pnt_no,value,status,refresh_time,iflock,dev_id)')
        c.executemany('INSERT INTO fes_yc_define VALUES(?,?,?,?,?,?,?,?)',[(1,i,3.,0,time.time()*1000,time.time()*1000,0,11) for i in (1,2)])
    se=TaskConfig('se',model_file=model,measurement_file=tmp_path/'devices.sqlite3',scada_source_file=source,point_catalog_file=catalog)
    ca=TaskConfig('ca',model_file=model,limit_file=tmp_path/'ca.sqlite3')
    config=SimpleNamespace(tasks={'se':se,'ca':ca})
    initialize_inputs(config)
    return config


def test_sync_maps_actual_points_and_preserves_operator_settings(tmp_path):
    cfg=environment(tmp_path);task=cfg.tasks['se']
    update_measurement(task,'measurement',1,{'version':1,'weight':4,'max_age_seconds':60})
    sync_measurements(task)
    with connect(task.measurement_file,readonly=True) as c:
        assert c.execute('SELECT count(*) FROM device_measurement').fetchone()[0]==2
        assert c.execute('SELECT weight,version FROM device_measurement WHERE measurement_id=1').fetchone()[:]==(4,2)
        assert c.execute('SELECT se_enabled FROM device_measurement WHERE measurement_id=2').fetchone()[0]==0
    with pytest.raises(ValueError,match='记录已更新'):
        update_measurement(task,'measurement',1,{'version':1,'weight':2})
    with pytest.raises(ValueError,match='不参与'):
        update_measurement(task,'measurement',2,{'version':1,'se_enabled':1})


@pytest.mark.parametrize('field,value,reason',[('status',128,'bad_quality'),('raw_time',0,'no_timestamp'),
    ('raw_time',1,'stale'),('raw_time',9999999999999,'future_timestamp'),('iflock',1,'locked'),('dev_id',99,'device_mismatch')])
def test_bad_or_stale_scada_data_never_enters_se(tmp_path,field,value,reason):
    cfg=environment(tmp_path);task=cfg.tasks['se']
    with sqlite3.connect(task.scada_source_file) as c:c.execute(f'UPDATE fes_yc_define SET {field}=? WHERE pnt_no=1',(value,))
    batch=refresh_measurements(task)
    assert batch['rows'][0]['reason']==reason and batch['se_valid']==0
    with pytest.raises(ValueError,match='无有效 SE'):
        with measurement_input(task): pass


def test_export_uses_engineering_value_and_unit_conversion_without_source_writes(tmp_path):
    cfg=environment(tmp_path);task=cfg.tasks['se']
    before=task.scada_source_file.read_bytes()
    with connect(task.measurement_file) as c:c.execute("UPDATE device_measurement SET unit='MW' WHERE measurement_id=1")
    catalog=json.loads(task.point_catalog_file.read_text(encoding='utf-8'))
    catalog['points'][0]['unit']='MW';task.point_catalog_file.write_text(json.dumps(catalog),encoding='utf-8')
    with measurement_input(task) as (path,meta):
        text=path.read_text(encoding='utf-8')
        assert 'P_GEN 1.0 1 3000.0' in text
        assert meta['se_valid']==1 and 'p_set_readback' not in text
    assert not path.exists()
    assert task.scada_source_file.read_bytes()==before


def test_mapping_edit_invalidates_sample_and_checks_device_identity(tmp_path):
    cfg=environment(tmp_path);task=cfg.tasks['se']
    refresh_measurements(task)
    with pytest.raises(ValueError,match='SCADA 点'):
        update_measurement(task,'mapping',1,{'version':1,'pnt_no':500})
    with pytest.raises(ValueError,match='给定回读'):
        update_measurement(task,'mapping',1,{'version':1,'pnt_no':2})
    update_measurement(task,'mapping',1,{'version':1,'scale':2})
    assert browse_inputs(cfg,'measurements')['rows'][0]['reason']=='configuration_changed'
    assert refresh_measurements(task)['rows'][0]['value']==6.


def test_removed_catalog_point_becomes_ineligible(tmp_path):
    cfg=environment(tmp_path);task=cfg.tasks['se']
    catalog=json.loads(task.point_catalog_file.read_text(encoding='utf-8'))
    catalog['points']=catalog['points'][1:]
    task.point_catalog_file.write_text(json.dumps(catalog),encoding='utf-8')
    sync_measurements(task)
    assert refresh_measurements(task)['rows'][0]['reason']=='device_inactive'


def test_sparse_limits_preserve_null_and_operator_edits(tmp_path):
    cfg=environment(tmp_path);task=cfg.tasks['ca']
    data=browse_inputs(cfg,'limits')
    assert data['stats']=={'total':2,'enabled':2}
    row=next(r for r in data['rows'] if r['field']=='v')
    assert (row['lower_value'],row['upper_value'])==(342.,418.00000000000006)
    save_limit(task,{'limit_id':row['limit_id'],'version':1,'lower_value':None,'upper_value':400})
    seed_limits(task)
    limits,meta=read_limits(task)
    assert limits['ACUnit']['机组']['v_max']==400 and 'v_min' not in limits['ACUnit']['机组']
    with pytest.raises(ValueError,match='下限'):
        save_limit(task,{'limit_id':row['limit_id'],'version':2,'lower_value':500,'upper_value':400})
    assert meta['count']==2


def test_input_api_rejects_unknown_fields_and_reports_effective_rows(tmp_path):
    from tests.test_web import make_app
    cfg=environment(tmp_path);app,_=make_app(tmp_path)
    app.config.tasks.update(cfg.tasks)
    assert app.api_post('/api/inputs/refresh',{})['data']['se_valid']==1
    assert app.api_get('/api/inputs/measurements?view=se&size=1')['data']['total']==1
    assert not app.api_post('/api/inputs/measurement/1',{'version':1,'sql':'bad'})['ok']
    assert app.api_post('/api/inputs/limits',{'model_table':'ACNode','model_idx':1,'field':'v','lower_value':350,'unit':'V'})['ok']
    assert app.api_get('/api/inputs/limits')['data']['total']==3
    app.repository.close()
