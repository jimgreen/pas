"""Read RTDB's embedded SQLite model as one consistent, read-only snapshot.

The reference kernels accept E files. Materialize every declared table/column
without changing the source database or substituting a different model file.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
import sqlite3
import tempfile


SQLITE_SUFFIXES = {".sqlite3", ".sqlite", ".db"}


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid model table/column name: {value!r}")
    return value


def _cell(value):
    if value is None:
        raise ValueError("NULL model values cannot be represented by the calculation kernel")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite model value")
    text = str(value)
    if any(c in text for c in "\r\n\x00'"):
        raise ValueError("Model values containing quotes or line breaks are unsupported by the kernel")
    return f"'{text}'" if not text or any(c.isspace() for c in text) else text


def read_model_tables(path: Path) -> dict[str, dict]:
    """Read declared RTDB fields and values from a single read-only transaction."""
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        tables = connection.execute("SELECT table_name FROM rtdb_schema_tables ORDER BY ordinal,table_name").fetchall()
        if not tables:
            raise ValueError("SQLite model has no embedded RTDB tables")
        result = {}
        for (name,) in tables:
            name = _identifier(name)
            columns = connection.execute("SELECT ordinal,eng_name FROM rtdb_schema_columns WHERE table_name=? ORDER BY ordinal", (name,)).fetchall()
            if not columns or [item[0] for item in columns] != list(range(len(columns))):
                raise ValueError(f"Invalid embedded columns for {name}")
            fields = [_identifier(item[1]) for item in columns]
            physical = {item[1] for item in connection.execute(f'PRAGMA table_info("rtdb_data_{name}")')}
            if not {"_pos", *(f"c{i}" for i in range(len(columns)))} <= physical:
                raise ValueError(f"Physical columns do not match embedded schema for {name}")
            selected = ",".join(f'"c{i}"' for i in range(len(columns)))
            result[name] = {"fields": fields, "rows": [dict(zip(fields, row)) for row in
                connection.execute(f'SELECT {selected} FROM "rtdb_data_{name}" ORDER BY "_pos"')]}
        if not any(name in result for name in ("ACNode", "DCNode", "Node")):
            raise ValueError("SQLite model contains no AC/DC node table")
        return result
    except sqlite3.Error as exc:
        raise ValueError(f"Cannot read embedded RTDB SQLite model {path}: {exc}") from exc
    finally:
        connection.rollback()
        connection.close()


def apply_topology_overrides(
    tables: dict[str, dict],
    topology_overrides: dict[str, dict[int, dict[str, int]]] | None,
) -> tuple[dict[str, dict], int]:
    """将实时遥信（断路器位置、设备运行状态）覆盖到内存模型副本，不修改源模型库。"""
    if not topology_overrides:
        return tables, 0
    updated: dict[str, dict] = {}
    applied = 0
    for name, block in tables.items():
        table_overrides = topology_overrides.get(name)
        if not table_overrides:
            updated[name] = block
            continue
        fields = set(block["fields"])
        new_rows = []
        for row in block["rows"]:
            row_idx = row.get("idx")
            patch = table_overrides.get(int(row_idx)) if row_idx is not None else None
            if not patch:
                new_rows.append(row)
                continue
            cloned = dict(row)
            changed = False
            for key, value in patch.items():
                if key in fields and cloned.get(key) != value:
                    cloned[key] = value
                    changed = True
            if changed:
                applied += 1
            new_rows.append(cloned)
        updated[name] = {"fields": block["fields"], "rows": new_rows}
    return updated, applied


def render_model_text(tables: dict[str, dict]) -> tuple[str, int, int]:
    """将模型表字典渲染为内核可读取的 E 文件文本。"""
    parts, count = [], 0
    for name, block in tables.items():
        fields = block["fields"]
        parts.extend([f"<{name}>\n", "@ " + " ".join(fields) + "\n"])
        for row in block["rows"]:
            parts.append("# " + " ".join(_cell(row[field]) for field in fields) + "\n")
            count += 1
        parts.append(f"</{name}>\n\n")
    return "".join(parts), len(tables), count


def read_sqlite_model(
    path: Path,
    *,
    topology_overrides: dict[str, dict[int, dict[str, int]]] | None = None,
) -> tuple[str, int, int]:
    tables = read_model_tables(path)
    tables, _ = apply_topology_overrides(tables, topology_overrides)
    return render_model_text(tables)


@dataclass(frozen=True)
class ModelInput:
    path: Path
    metadata: dict
    tables: dict[str, dict] | None = None


@contextmanager
def kernel_model(path, *, topology_overrides: dict[str, dict[int, dict[str, int]]] | None = None):
    source = Path(path).resolve()
    if source.suffix.lower() not in SQLITE_SUFFIXES:
        yield ModelInput(source, {"source": str(source), "format": "file"})
        return
    raw_tables = read_model_tables(source)
    patched_tables, applied = apply_topology_overrides(raw_tables, topology_overrides)
    text, table_count, row_count = render_model_text(patched_tables)
    metadata = {
        "source": str(source),
        "format": "rtdb_sqlite",
        "snapshot_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "table_count": table_count,
        "row_count": row_count,
        "topology_overrides_applied": applied,
    }
    with tempfile.TemporaryDirectory(prefix="pas_model_") as directory:
        target = Path(directory) / "model.e"
        target.write_text(text, encoding="utf-8")
        yield ModelInput(target, metadata, patched_tables)


def validate_references(model_file, auxiliary_file, *, measurements=False):
    """Reject foreign scenario names instead of silently ignoring all inputs."""
    from efile_read import EBook
    model = EBook(model_file).data
    names = {table: {str(row.get("name", row.get("idx", ""))) for row in block.data}
             for table, block in model.items()}
    for aliases in (("ACUnit", "ACGenerator"), ("DCUnit", "DCGenerator"),
                    ("ACBreaker", "ACBreak"), ("DCBreaker", "DCBreak"),
                    ("DCDCConver", "DCDCConverter"), ("DCACConver", "DCACConverter"),
                    ("ACACConver", "ACACConverter")):
        combined = set().union(*(names.get(alias, set()) for alias in aliases))
        for alias in aliases:
            names[alias] = combined
    auxiliary = EBook(auxiliary_file).data
    missing = []
    count = 0
    for table, block in auxiliary.items():
        for row in block.data:
            if measurements:
                if str(row.get("valid", "1")) == "0":
                    continue
                kind = str(row.get("dev_type", row.get("device_type", "")))
                name = str(row.get("dev_name", row.get("device_name", "")))
            else:
                kind, name = table, str(row.get("name", row.get("idx", "")))
            count += 1
            if name not in names.get(kind, set()):
                missing.append(f"{kind}.{name}")
    if not count:
        raise ValueError(f"No {'valid measurements' if measurements else 'constraints'} in {auxiliary_file}")
    if missing:
        raise ValueError(f"Inputs do not match the model ({len(missing)} unknown devices): " + ", ".join(missing[:5]))
