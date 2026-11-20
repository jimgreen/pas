import json
from pathlib import Path
import sqlite3

import pytest

from pas.config import ConfigError, load_config
from pas.model_input import kernel_model, read_sqlite_model


def make_model(path):
    connection = sqlite3.connect(path)
    connection.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE rtdb_schema_tables(table_name TEXT, ordinal INTEGER);
        CREATE TABLE rtdb_schema_columns(table_name TEXT,ordinal INTEGER,eng_name TEXT);
        INSERT INTO rtdb_schema_tables VALUES('ACNode',0);
        INSERT INTO rtdb_schema_columns VALUES('ACNode',0,'idx'),('ACNode',1,'name'),('ACNode',2,'voltage');
        CREATE TABLE rtdb_data_ACNode(_pos INTEGER PRIMARY KEY,c0 INTEGER,c1 TEXT,c2 REAL);
        INSERT INTO rtdb_data_ACNode VALUES(1,1,'母线1',380);
    ''')
    return connection


def test_workspace_parameters_determine_model_and_isolated_outputs(tmp_path):
    source = tmp_path / "config.json"
    source.write_text(json.dumps({"kernel_root": str(tmp_path), "workspace_root": str(tmp_path / 'workspace'),
                                 "runtime": "realtime", "scenario": "qinling",
                                 "database": "old.db", "databases": {"lf": "old-lf.db"}}))
    config = load_config(source)
    work = tmp_path / "workspace/realtime/qinling"
    assert config.workspace_directory == work
    assert config.database == work / "sqldb/pas/pas.sqlite3"
    assert all(config.databases[t] == work / f"sqldb/pas/{t}.sqlite3" for t in ('se','lf','ca'))
    assert all(task.model_file == work / "sqldb/model/devices.sqlite3" for task in config.tasks.values())
    assert config.tasks['se'].measurement_file == work / "meas/measurements.meas"
    other = load_config(source, runtime="study", scenario="other")
    assert other.workspace_directory == tmp_path / "workspace/study/other"
    assert not set(other.databases.values()) & set(config.databases.values())
    # Loading configuration alone must not create or migrate databases.
    assert not work.exists()


@pytest.mark.parametrize('component', ['../escape', 'a/b', r'a\b', 'D:', '', '.', 'qinling.', 'NUL'])
def test_workspace_rejects_path_components(tmp_path, component):
    source = tmp_path / 'config.json'
    source.write_text(json.dumps({'kernel_root': str(tmp_path), 'workspace_root': str(tmp_path),
                                 'runtime': 'realtime', 'scenario': component}))
    with pytest.raises(ConfigError, match='directory name'):
        load_config(source)


def test_sqlite_snapshot_sees_committed_wal_and_never_writes_model(tmp_path):
    path = tmp_path / 'devices.sqlite3'
    writer = make_model(path)
    writer.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    disk_before = path.read_bytes()
    writer.execute('UPDATE rtdb_data_ACNode SET c2=400')
    writer.commit()
    assert path.read_bytes() == disk_before  # Changed value is only in WAL.
    with kernel_model(path) as first:
        assert '# 1 母线1 400.0' in first.path.read_text(encoding='utf-8')
        first_digest = first.metadata['snapshot_sha256']
        assert first.metadata['row_count'] == 1
        snapshot_path = first.path
        writer.execute('UPDATE rtdb_data_ACNode SET c2=420')
        writer.commit()
        assert '420' not in snapshot_path.read_text(encoding='utf-8')
    assert not snapshot_path.exists()
    with kernel_model(path) as second:
        assert '# 1 母线1 420.0' in second.path.read_text(encoding='utf-8')
        assert second.metadata['snapshot_sha256'] != first_digest
    assert path.read_bytes() == disk_before
    writer.close()


def test_bad_embedded_schema_is_rejected_without_fallback(tmp_path):
    path = tmp_path / 'devices.sqlite3'
    writer = make_model(path)
    writer.execute("UPDATE rtdb_schema_tables SET table_name='ACNode; DROP TABLE x'")
    writer.commit()
    with pytest.raises(ValueError, match='Invalid model'):
        read_sqlite_model(path)
    writer.close()


def test_snapshot_rejects_null_instead_of_inventing_defaults(tmp_path):
    path = tmp_path / 'devices.sqlite3'
    writer = make_model(path)
    writer.execute('UPDATE rtdb_data_ACNode SET c2=NULL')
    writer.commit()
    with pytest.raises(ValueError, match='NULL'):
        read_sqlite_model(path)
    writer.close()


def test_snapshot_keeps_one_transaction_during_concurrent_commit(tmp_path, monkeypatch):
    from pas import model_input
    path = tmp_path / 'devices.sqlite3'
    writer = make_model(path)
    writer.execute("INSERT INTO rtdb_data_ACNode VALUES(2,2,'母线2',380)")
    writer.commit()
    original = model_input._cell
    changed = False
    def cell(value):
        nonlocal changed
        if not changed:
            writer.execute('UPDATE rtdb_data_ACNode SET c2=999')
            writer.commit()
            changed = True
        return original(value)
    monkeypatch.setattr(model_input, '_cell', cell)
    text, _, count = read_sqlite_model(path)
    assert count == 2 and text.count('380.0') == 2 and '999' not in text
    assert read_sqlite_model(path)[0].count('999.0') == 2
    writer.close()


def test_missing_physical_column_is_not_read_as_sqlite_string_literal(tmp_path):
    path = tmp_path / 'devices.sqlite3'
    writer = make_model(path)
    writer.execute('ALTER TABLE rtdb_data_ACNode RENAME COLUMN c2 TO wrong')
    writer.commit()
    with pytest.raises(ValueError, match='Physical columns'):
        read_sqlite_model(path)
    writer.close()


def test_web_exposes_effective_workspace_parameters(tmp_path):
    from tests.test_web import make_app
    app, _ = make_app(tmp_path)
    app.config.workspace_root = tmp_path
    app.config.workspace_directory = tmp_path / 'realtime/qinling'
    app.config.runtime, app.config.scenario = 'realtime', 'qinling'
    response = app.api_get('/api/config')['data']['workspace']
    assert response['scenario'] == 'qinling'
    assert response['workspace_directory'] == str(tmp_path / 'realtime/qinling')
    app.repository.close()
