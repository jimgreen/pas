"""Register PAS SQL tables for direct, read-only access from RTDB."""

import hashlib
import json
import math
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS rtdb_schema_database (
    version INTEGER PRIMARY KEY CHECK(version=1), eng_name TEXT NOT NULL, chn_name TEXT NOT NULL,
    storage_format TEXT NOT NULL DEFAULT 'native' CHECK(storage_format='native')
);
CREATE TABLE IF NOT EXISTS rtdb_schema_tables (
    table_name TEXT PRIMARY KEY, chn_name TEXT NOT NULL, ordinal INTEGER NOT NULL,
    fingerprint TEXT NOT NULL, indexes_json TEXT
);
CREATE TABLE IF NOT EXISTS rtdb_schema_columns (
    table_name TEXT NOT NULL REFERENCES rtdb_schema_tables(table_name) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL, eng_name TEXT NOT NULL, chn_name TEXT NOT NULL, data_type TEXT NOT NULL,
    primary_key INTEGER NOT NULL CHECK(primary_key IN (0,1)),
    disp_type TEXT NOT NULL, disp_menu TEXT NOT NULL,
    has_default INTEGER NOT NULL CHECK(has_default IN (0,1)), default_json TEXT,
    PRIMARY KEY(table_name, ordinal), UNIQUE(table_name, eng_name)
);
"""


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def execute_schema(connection, script):
    """Apply a schema script without executescript's implicit commit."""
    statement = ""
    start = 0
    for match in re.finditer(";", script):
        end = match.end()
        statement += script[start:end]
        start = end
        if sqlite3.complete_statement(statement):
            connection.execute(statement)
            statement = ""
    tail = statement + script[start:]
    if tail.strip():
        connection.execute(tail)


@contextmanager
def schema_transaction(connection, path):
    """Commit PAS DDL and RTDB definitions together."""
    if connection.in_transaction:
        raise RuntimeError("PAS schema transaction requires an idle connection")
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield
        sync_embedded_schema(connection, path)
        connection.commit()
    except BaseException:
        connection.rollback()
        raise


def _literal_default(sql, kind):
    if sql is None:
        return None
    text = sql.strip()
    while text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    if re.fullmatch(r"'(?:[^']|'')*'", text):
        value = text[1:-1].replace("''", "'")
        return value if kind == "str" else None
    if kind == "int" and re.fullmatch(r"[+-]?\d+", text):
        value = int(text)
        return value if -(2**63) <= value < 2**63 else None
    if kind == "int" and text.upper() in {"TRUE", "FALSE"}:
        return int(text.upper() == "TRUE")
    if kind == "float" and re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text):
        value = float(text)
        return value if math.isfinite(value) else None
    return None  # Dynamic defaults remain on the native PAS table.


def _definition(connection, table):
    columns = []
    for _, name, declared, _, default, pk in connection.execute(f"PRAGMA table_info({_quote(table)})"):
        if not _IDENTIFIER.fullmatch(name):
            raise ValueError(f"Invalid RTDB column name {table}.{name}")
        declared = declared.upper()
        if "INT" in declared or declared in {"BOOL", "BOOLEAN"}:
            kind, display = "int", "整数"
        elif any(part in declared for part in ("REAL", "FLOAT", "DOUB", "NUMERIC", "DECIMAL")):
            kind, display = "float", "浮点"
        elif any(part in declared for part in ("CHAR", "CLOB", "TEXT")):
            kind, display = "str", "文本"
        elif declared == "BLOB":
            kind, display = "blob", "二进制"
        else:
            raise ValueError(f"Unsupported RTDB column type {table}.{name}: {declared}")
        column = dict(eng_name=name, chn_name=name, data_type=kind, primary_key=bool(pk),
                      disp_type=display, disp_menu="")
        value = _literal_default(default, kind)
        if value is not None:
            column["default_value"] = value
        columns.append(column)
    if not any(column["primary_key"] for column in columns):
        raise ValueError(f"PAS table {table} needs a primary key for RTDB")
    # RTDB reads the original SQLite table and uses its existing indexes.
    mapping = dict(head=dict(eng_name=table, chn_name=table), columns=columns, indexes=[])
    fingerprint = hashlib.sha256(json.dumps(mapping, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return columns, fingerprint


def _write_definition(connection, table, columns, fingerprint, ordinal):
    connection.execute(
        "INSERT INTO rtdb_schema_tables(table_name, chn_name, ordinal, fingerprint, indexes_json) "
        "VALUES (?, ?, ?, ?, '[]') ON CONFLICT(table_name) DO UPDATE SET "
        "chn_name=excluded.chn_name, ordinal=excluded.ordinal, fingerprint=excluded.fingerprint, "
        "indexes_json=excluded.indexes_json", (table, table, ordinal, fingerprint)
    )
    connection.execute("DELETE FROM rtdb_schema_columns WHERE table_name=?", (table,))
    connection.executemany(
        "INSERT INTO rtdb_schema_columns(table_name, ordinal, eng_name, chn_name, data_type, "
        "primary_key, disp_type, disp_menu, has_default, default_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(table, i, col["eng_name"], col["chn_name"], col["data_type"], int(col["primary_key"]),
          col["disp_type"], col["disp_menu"], int("default_value" in col),
          json.dumps(col["default_value"], ensure_ascii=False) if "default_value" in col else None)
         for i, col in enumerate(columns)],
    )


def sync_embedded_schema(connection, path):
    """Synchronize definitions for a PAS database within the caller's transaction."""
    if not connection.in_transaction:
        raise RuntimeError("RTDB schema sync requires an active transaction")
    tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    if "rtdb_schema_database" in tables:
        fields = {row[1] for row in connection.execute("PRAGMA table_info(rtdb_schema_database)")}
        marker = (connection.execute("SELECT storage_format FROM rtdb_schema_database WHERE version=1").fetchone()
                  if "storage_format" in fields else None)
        if marker is None or marker[0] != "native":
            raise ValueError(f"{path} is an RTDB-managed database, not a PAS database")
    elif any(table.startswith("rtdb_") for table in tables):
        raise ValueError(f"{path} has existing RTDB tables without a native storage marker")

    tables = [table for table in tables if not table.startswith(("sqlite_", "rtdb_"))]
    execute_schema(connection, _SCHEMA)
    if "indexes_json" not in {row[1] for row in connection.execute("PRAGMA table_info(rtdb_schema_tables)")}:
        connection.execute("ALTER TABLE rtdb_schema_tables ADD COLUMN indexes_json TEXT")
    stem = Path(path).stem
    database_name = stem if _IDENTIFIER.fullmatch(stem) else "pas"
    connection.execute(
        "INSERT INTO rtdb_schema_database(version, eng_name, chn_name, storage_format) VALUES (1, ?, ?, 'native') "
        "ON CONFLICT(version) DO UPDATE SET eng_name=excluded.eng_name, chn_name=excluded.chn_name "
        "WHERE eng_name<>excluded.eng_name OR chn_name<>excluded.chn_name", (database_name, stem)
    )
    registered = {row[0]: (row[1], row[2]) for row in connection.execute(
        "SELECT table_name,fingerprint,ordinal FROM rtdb_schema_tables"
    )}
    for table in registered.keys() - set(tables):
        connection.execute("DELETE FROM rtdb_schema_columns WHERE table_name=?", (table,))
        connection.execute("DELETE FROM rtdb_schema_tables WHERE table_name=?", (table,))
    for ordinal, table in enumerate(tables):
        if not _IDENTIFIER.fullmatch(table):
            raise ValueError(f"Invalid RTDB table name {table}")
        columns, fingerprint = _definition(connection, table)
        stored, old_ordinal = registered.get(table, (None, None))
        if stored != fingerprint:
            _write_definition(connection, table, columns, fingerprint, ordinal)
        elif ordinal != old_ordinal:
            connection.execute("UPDATE rtdb_schema_tables SET ordinal=? WHERE table_name=?", (ordinal, table))
    return len(tables)
