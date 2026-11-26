import sqlite3
from contextlib import closing

import pytest

from pas.rtdb_schema import schema_transaction, sync_embedded_schema


def _columns(connection, table):
    return connection.execute(
        'SELECT eng_name, data_type, "primary_key" FROM rtdb_schema_columns '
        'WHERE table_name = ? ORDER BY ordinal', (table,),
    ).fetchall()


def _tables(connection):
    return {row[0] for row in connection.execute('SELECT table_name FROM rtdb_schema_tables')}


def test_schema_changes_update_definitions_and_preserve_existing_rows(tmp_path):
    path = tmp_path / 'analysis.db'
    with closing(sqlite3.connect(path)) as connection:
        with schema_transaction(connection, path):
            connection.execute('CREATE TABLE reading (id INTEGER PRIMARY KEY, value REAL)')
            connection.execute('INSERT INTO reading VALUES (42, 5.5)')
            connection.execute('CREATE TABLE retired (id INTEGER PRIMARY KEY)')

        assert _tables(connection) == {'reading', 'retired'}
        before = connection.execute(
            "SELECT fingerprint FROM rtdb_schema_tables WHERE table_name = 'reading'"
        ).fetchone()[0]
        assert _columns(connection, 'reading') == [('id', 'int', 1), ('value', 'float', 0)]

        with schema_transaction(connection, path):
            connection.execute("ALTER TABLE reading ADD COLUMN label TEXT DEFAULT 'normal'")
            connection.execute('ALTER TABLE reading RENAME COLUMN value TO measured')
            connection.execute('ALTER TABLE retired RENAME TO replacement')

        assert _tables(connection) == {'reading', 'replacement'}
        assert _columns(connection, 'retired') == []
        assert _columns(connection, 'reading') == [
            ('id', 'int', 1), ('measured', 'float', 0), ('label', 'str', 0),
        ]
        assert connection.execute('SELECT * FROM reading').fetchall() == [(42, 5.5, 'normal')]
        after = connection.execute(
            "SELECT fingerprint FROM rtdb_schema_tables WHERE table_name = 'reading'"
        ).fetchone()[0]
        assert before != after
        with schema_transaction(connection, path):
            connection.execute('DROP TABLE replacement')

        assert _tables(connection) == {'reading'}
        assert _columns(connection, 'replacement') == []
        with schema_transaction(connection, path):
            connection.execute('ALTER TABLE reading DROP COLUMN label')

        assert _columns(connection, 'reading') == [('id', 'int', 1), ('measured', 'float', 0)]
        assert connection.execute('SELECT * FROM reading').fetchall() == [(42, 5.5)]


def test_schema_and_catalog_roll_back_together(tmp_path):
    path = tmp_path / 'analysis.db'
    with closing(sqlite3.connect(path)) as connection:
        with schema_transaction(connection, path):
            connection.execute('CREATE TABLE reading (id INTEGER PRIMARY KEY, value REAL)')
        original = _columns(connection, 'reading')

        with pytest.raises(RuntimeError, match='abort migration'):
            with schema_transaction(connection, path):
                connection.execute('ALTER TABLE reading ADD COLUMN unpublished TEXT')
                connection.execute('CREATE TABLE unpublished (id INTEGER PRIMARY KEY)')
                sync_embedded_schema(connection, path)
                assert _tables(connection) == {'reading', 'unpublished'}
                assert _columns(connection, 'reading')[-1][0] == 'unpublished'
                raise RuntimeError('abort migration')

    with closing(sqlite3.connect(path)) as observer:
        assert _tables(observer) == {'reading'}
        assert _columns(observer, 'reading') == original
        assert [r[1] for r in observer.execute('PRAGMA table_info(reading)')] == ['id', 'value']
        assert observer.execute(
            "SELECT name FROM sqlite_schema WHERE name IN ('unpublished', 'rtdb_data_unpublished')"
        ).fetchall() == []


def test_registry_is_idempotent_and_uses_original_tables(tmp_path):
    path = tmp_path / 'analysis.db'
    with closing(sqlite3.connect(path)) as connection:
        with schema_transaction(connection, path):
            connection.execute("CREATE TABLE reading (id INTEGER PRIMARY KEY, label TEXT DEFAULT 'normal')")
            connection.execute('INSERT INTO reading(id) VALUES (42)')
        assert connection.execute('SELECT storage_format FROM rtdb_schema_database').fetchone() == ('native',)
        assert connection.execute("SELECT has_default, default_json FROM rtdb_schema_columns WHERE eng_name='label'").fetchone() == (1, '"normal"')
        writes = connection.total_changes
        with schema_transaction(connection, path):
            pass
        assert connection.total_changes == writes
        assert connection.execute("SELECT name FROM sqlite_master WHERE name GLOB 'rtdb_data_*'").fetchall() == []
        with connection:
            connection.execute("UPDATE reading SET label='updated' WHERE id=42")
        assert connection.execute('SELECT * FROM reading').fetchall() == [(42, 'updated')]


def test_unkeyed_table_rolls_back_without_publishing_partial_schema(tmp_path):
    path = tmp_path / 'analysis.db'
    with closing(sqlite3.connect(path)) as connection:
        with pytest.raises(ValueError, match='needs a primary key'):
            with schema_transaction(connection, path):
                connection.execute('CREATE TABLE invalid (value REAL)')
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
