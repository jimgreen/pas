# Online Analysis Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python resident scheduler that periodically runs SE, LF, and CA through the reference kernels and stores run metadata, statistics, and details in SQLite.

**Architecture:** A small `pas` package separates JSON configuration, SQLite persistence, kernel adapters, scheduling, and CLI orchestration. The scheduler owns task timing and run lifecycle; adapters return serializable normalized results; the repository commits each result transaction independently while preserving failed run records.

**Tech Stack:** Python 3.10+, standard-library `sqlite3`, `dataclasses`, `threading`, `argparse`, `unittest`; reference kernel modules imported from the configured `kernel_root/src` path.

---

### Task 1: Create package and configuration model

**Files:**
- Create: `pas/__init__.py`
- Create: `pas/config.py`
- Create: `config.example.json`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing configuration tests**

```python
import json
from pathlib import Path

import pytest

from pas.config import AppConfig, ConfigError, load_config


def test_load_config_resolves_paths_and_task_defaults(tmp_path: Path):
    kernel = tmp_path / "kernel"
    model = tmp_path / "model.e"
    meas = tmp_path / "model.meas"
    para = tmp_path / "se.para"
    lf_para = tmp_path / "lf.para"
    limit = tmp_path / "limit.calmt"
    for path in (model, meas, para, lf_para, limit):
        path.write_text("x", encoding="utf-8")
    source = tmp_path / "config.json"
    source.write_text(json.dumps({
        "kernel_root": str(kernel),
        "database": str(tmp_path / "runs.db"),
        "tasks": {
            "se": {"enabled": True, "period_seconds": 5, "model_file": str(model), "measurement_file": str(meas), "parameter_file": str(para)},
            "lf": {"enabled": True, "period_seconds": 10, "model_file": str(model), "parameter_file": str(lf_para)},
            "ca": {"enabled": False, "period_seconds": 30, "model_file": str(model), "limit_file": str(limit)},
        },
    }), encoding="utf-8")

    config = load_config(source)

    assert isinstance(config, AppConfig)
    assert config.database == (tmp_path / "runs.db").resolve()
    assert config.tasks["se"].period_seconds == 5
    assert config.tasks["ca"].enabled is False


def test_enabled_task_requires_existing_input(tmp_path: Path):
    source = tmp_path / "config.json"
    source.write_text(json.dumps({
        "kernel_root": str(tmp_path / "kernel"),
        "database": str(tmp_path / "runs.db"),
        "tasks": {"se": {"enabled": True, "period_seconds": 1}},
    }), encoding="utf-8")

    with pytest.raises(ConfigError, match="model_file"):
        load_config(source)


def test_period_must_be_positive(tmp_path: Path):
    source = tmp_path / "config.json"
    source.write_text(json.dumps({"database": str(tmp_path / "runs.db"), "tasks": {"lf": {"period_seconds": 0}}}), encoding="utf-8")

    with pytest.raises(ConfigError, match="period_seconds"):
        load_config(source)
```

- [ ] **Step 2: Run the focused test to verify the expected missing-module failure**

Run: `python -m pytest tests/test_config.py -q`
Expected: FAIL because `pas.config` does not exist.

- [ ] **Step 3: Implement dataclass configuration and validation**

Implement `TaskConfig` and `AppConfig` as frozen dataclasses. `load_config(path)` reads JSON, fills disabled tasks with defaults, resolves all paths, validates positive periods and required paths for enabled tasks, creates the database parent directory, and raises `ConfigError` with the field name.

- [ ] **Step 4: Add the example configuration and rerun tests**

Run: `python -m pytest tests/test_config.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Commit**

```powershell
git add pas/__init__.py pas/config.py config.example.json tests/test_config.py
git commit -m "feat: add online analysis configuration"
```

### Task 2: Implement SQLite schema and repository

**Files:**
- Create: `pas/schema.sql`
- Create: `pas/db.py`
- Test: `tests/test_db.py`

- [ ] **Step 1: Write failing repository tests**

```python
import sqlite3
from pathlib import Path

from pas.db import Repository


def test_schema_is_idempotent_and_stores_run_result(tmp_path: Path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    repo.initialize()
    schedule_id = repo.upsert_schedule("lf", True, 10, {"model_file": "m.e"})
    run_id = repo.start_run(schedule_id, "lf", "2026-11-17T00:00:00+00:00", "kernel", "fingerprint")
    repo.finish_run(run_id, "succeeded", "2026-11-17T00:00:01+00:00", 1.0, 0)
    repo.store_lf_result(run_id, {"converged": True, "iterations": 2, "norm_f": 1e-9, "summary": {"nodes": 3}})

    with sqlite3.connect(tmp_path / "runs.db") as conn:
        assert conn.execute("select count(*) from schema_version").fetchone()[0] == 1
        assert conn.execute("select status from calculation_run where run_id = ?", (run_id,)).fetchone()[0] == "succeeded"
        assert conn.execute("select converged from lf_result where run_id = ?", (run_id,)).fetchone()[0] == 1


def test_failed_result_transaction_does_not_leave_partial_rows(tmp_path: Path):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    schedule_id = repo.upsert_schedule("ca", True, 10, {})
    run_id = repo.start_run(schedule_id, "ca", "t", "kernel", "fp")

    try:
        with repo.result_transaction():
            repo.store_ca_result(run_id, {"risk_level": "高", "n0_risk_count": 1, "n1_scan_count": 0, "n1_risk_count": 0, "risks": []})
            raise RuntimeError("rollback")
    except RuntimeError:
        pass

    with sqlite3.connect(tmp_path / "runs.db") as conn:
        assert conn.execute("select count(*) from ca_result").fetchone()[0] == 0
        assert conn.execute("select count(*) from calculation_run").fetchone()[0] == 1
```

- [ ] **Step 2: Run tests and verify the missing repository failure**

Run: `python -m pytest tests/test_db.py -q`
Expected: FAIL because `pas.db` does not exist.

- [ ] **Step 3: Write the schema and repository methods**

Create the tables from the approved design with foreign keys and indexes. `Repository.initialize()` enables foreign keys and applies schema version 1. Implement schedule upsert, run start/finish, metric insertion, result transaction context manager, and `store_se_result`, `store_lf_result`, `store_ca_result` methods. Serialize summary and detail payloads with compact JSON.

- [ ] **Step 4: Run the database tests**

Run: `python -m pytest tests/test_db.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add pas/schema.sql pas/db.py tests/test_db.py
git commit -m "feat: add SQLite result repository"
```

### Task 3: Add kernel adapters

**Files:**
- Create: `pas/kernels.py`
- Test: `tests/test_kernels.py`

- [ ] **Step 1: Write failing adapter normalization tests**

```python
from types import SimpleNamespace

from pas.kernels import normalize_ca, normalize_lf, normalize_se


def test_normalize_se_keeps_statistics_and_state():
    value = SimpleNamespace(statistics=SimpleNamespace(converged=True, observable=True, iterations=3, objective=2.0, max_correction=0.1, residual_inf=0.01, rank=4, state_count=4, measurement_count=6, deficiency=0, prefiltered_measurement_count=1, pseudo_measurement_count=2, bad_data_count=0, normal_measurement_count=3), normal_measurements=[])
    result = normalize_se(value, SimpleNamespace(x=[1.0, 2.0]))
    assert result["converged"] is True
    assert result["state"] == [1.0, 2.0]
    assert result["statistics"]["measurement_count"] == 6


def test_normalize_lf_and_ca_return_serializable_summaries():
    lf = normalize_lf(SimpleNamespace(converged=True, iterations=2, normF=1e-8, failure_reason="", lf_result=None))
    ca = normalize_ca([SimpleNamespace(risk_source="BASE", risk_dist="Bus", risk_type="Voltage", risk_value=0.9, risk_info="low")], [])[0]
    assert lf["converged"] is True
    assert ca["n0_risk_count"] == 1
    assert ca["risks"][0]["risk_type"] == "Voltage"
```

- [ ] **Step 2: Run tests and verify they fail before implementation**

Run: `python -m pytest tests/test_kernels.py -q`
Expected: FAIL because `pas.kernels` does not exist.

- [ ] **Step 3: Implement adapter imports and normalization**

Add `kernel_root/src` to `sys.path` once per process. Implement `run_se`, `run_lf`, and `run_ca` plus pure `normalize_se`, `normalize_lf`, and `normalize_ca` helpers. Keep all NumPy objects converted to Python scalars/lists; preserve measurement and risk rows as dictionaries. CA uses a temporary output directory and `scan_n1` from config.

- [ ] **Step 4: Run focused adapter tests**

Run: `python -m pytest tests/test_kernels.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add pas/kernels.py tests/test_kernels.py
git commit -m "feat: adapt state estimation flow and security kernels"
```

### Task 4: Implement scheduler and run lifecycle

**Files:**
- Create: `pas/scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing scheduler tests**

```python
import threading
from types import SimpleNamespace

from pas.scheduler import Scheduler


def test_run_once_executes_enabled_tasks_in_order_and_isolates_failure():
    calls = []

    def run(task):
        calls.append(task)
        if task == "lf":
            raise ValueError("bad lf")
        return {"ok": True}

    scheduler = Scheduler(SimpleNamespace(tasks={"se": SimpleNamespace(enabled=True), "lf": SimpleNamespace(enabled=True), "ca": SimpleNamespace(enabled=True)}), repository=FakeRepository(), runners={name: (lambda name=name: run(name)) for name in ("se", "lf", "ca")})
    scheduler.run_once()

    assert calls == ["se", "lf", "ca"]
    assert scheduler.repository.statuses == ["succeeded", "failed"]


def test_stop_event_ends_daemon_loop():
    event = threading.Event()
    event.set()
    scheduler = Scheduler(SimpleNamespace(tasks={}), repository=FakeRepository(), runners={})
    scheduler.run_daemon(stop_event=event)


class FakeRepository:
    statuses = []
    def upsert_schedule(self, *args): return 1
    def start_run(self, *args): return len(self.statuses) + 1
    def finish_run(self, run_id, status, *args): self.statuses.append(status)
    def result_transaction(self): return NullContext()
    def store_result(self, *args): pass


class NullContext:
    def __enter__(self): return self
    def __exit__(self, *args): return False
```

- [ ] **Step 2: Run scheduler tests and verify missing implementation**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: FAIL because `pas.scheduler` does not exist.

- [ ] **Step 3: Implement task execution and timing**

Implement `Scheduler.run_once()` in fixed `se`, `lf`, `ca` order and `run_daemon(stop_event)` with a monotonic tick. Each task gets one run record, runner exceptions become failed runs, result writes occur in `result_transaction()`, and a task's failure does not prevent later tasks. Track active task names to prevent re-entry. Use UTC timestamps and `time.perf_counter()` for elapsed seconds.

- [ ] **Step 4: Run scheduler tests**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Commit**

```powershell
git add pas/scheduler.py tests/test_scheduler.py
git commit -m "feat: schedule periodic analysis runs"
```

### Task 5: Add CLI, example configuration, and integration checks

**Files:**
- Create: `pas/cli.py`
- Create: `tests/test_cli.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing CLI test**

```python
from pas.cli import main


def test_init_db_command_creates_database(tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"database": "runs.db", "tasks": {}}', encoding="utf-8")
    assert main(["init-db", "--config", str(config)]) == 0
    assert (tmp_path / "runs.db").exists()
```

- [ ] **Step 2: Run it to verify the missing CLI failure**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL because `pas.cli` does not exist.

- [ ] **Step 3: Implement CLI and documentation**

Implement `init-db`, `run-once`, and `daemon` subcommands. `run-once` loads config, initializes the repository, constructs adapters, runs enabled tasks, prints one-line statuses, and exits nonzero only if at least one task failed. `daemon` handles `KeyboardInterrupt` and stop events. Update README with setup, configuration, commands, database query examples, and a note that the reference kernel dependencies must be installed in the Python environment.

- [ ] **Step 4: Run the full test suite and compile check**

Run: `python -m pytest -q` and `python -m compileall pas`
Expected: all tests pass and compileall exits 0.

- [ ] **Step 5: Run the real kernel smoke command**

Run: `python -m pas.cli run-once --config config.example.json`
Expected: SQLite contains one `calculation_run` per enabled task; each result table has a row or a failure run with an explanatory error. CA N-1 can be disabled in the example to keep the smoke run bounded.

- [ ] **Step 6: Commit**

```powershell
git add pas/cli.py tests/test_cli.py README.md config.example.json
git commit -m "feat: add online analysis service CLI"
```

### Task 6: Final verification and handoff

**Files:**
- Modify only files needed to fix verification failures.

- [ ] **Step 1: Inspect repository state and diff**

Run: `git status --short --branch` and `git diff HEAD~5 --stat`.

- [ ] **Step 2: Run all targeted checks again**

Run: `python -m pytest -q` and `python -m compileall pas`.

- [ ] **Step 3: Confirm schema and run queries**

Run a read-only SQLite query that reports task type, status, elapsed seconds, and result row counts.

- [ ] **Step 4: Commit any narrowly scoped fixes**

```powershell
git add pas tests README.md config.example.json
git commit -m "fix: complete online analysis verification"
```
