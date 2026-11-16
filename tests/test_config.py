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
    assert config.databases["se"] == (tmp_path / "runs.se.db").resolve()
    assert config.databases["lf"] == (tmp_path / "runs.lf.db").resolve()
    assert config.databases["ca"] == (tmp_path / "runs.ca.db").resolve()
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
    source.write_text(json.dumps({"kernel_root": str(tmp_path / "kernel"), "database": str(tmp_path / "runs.db"), "tasks": {"lf": {"period_seconds": 0}}}), encoding="utf-8")

    with pytest.raises(ConfigError, match="period_seconds"):
        load_config(source)


def test_load_config_relocates_stale_kernel_root_and_input_paths(tmp_path: Path):
    stale_root = tmp_path / "old_kernel"
    migrated_root = tmp_path / "hybrid_power_kernel_acceptance_d1603be"
    package = migrated_root / "src" / "hybrid_power_system_analysis"
    (package / "secore").mkdir(parents=True)
    (package / "lfcore").mkdir()
    (package / "cacore").mkdir()
    (package / "secore" / "ac_se.py").write_text("", encoding="utf-8")
    (package / "lfcore" / "hybrid_lf.py").write_text("", encoding="utf-8")
    (package / "cacore" / "hybrid_ca.py").write_text("", encoding="utf-8")
    for relative in (
        "data/model/ac/ieee14.e",
        "data/meas/ac/ieee14.meas",
        "data/se/se.para",
        "data/model/hybrid/qinling.e",
        "data/lf/lf.para",
        "data/ca/qinling.calmt",
    ):
        target = migrated_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("x", encoding="utf-8")
    source = tmp_path / "config.json"
    source.write_text(json.dumps({
        "kernel_root": str(stale_root),
        "database": str(tmp_path / "runs.db"),
        "tasks": {
            "se": {"enabled": True, "period_seconds": 5, "model_file": str(stale_root / "data/model/ac/ieee14.e"), "measurement_file": str(stale_root / "data/meas/ac/ieee14.meas"), "parameter_file": str(stale_root / "data/se/se.para")},
            "lf": {"enabled": True, "period_seconds": 10, "model_file": str(stale_root / "data/model/hybrid/qinling.e"), "parameter_file": str(stale_root / "data/lf/lf.para")},
            "ca": {"enabled": True, "period_seconds": 30, "model_file": str(stale_root / "data/model/hybrid/qinling.e"), "limit_file": str(stale_root / "data/ca/qinling.calmt"), "scan_n1": False},
        },
    }), encoding="utf-8")

    config = load_config(source)

    assert config.kernel_root == migrated_root.resolve()
    assert config.tasks["se"].model_file == (migrated_root / "data/model/ac/ieee14.e").resolve()


def test_explicit_result_databases_are_distinct(tmp_path: Path):
    source = tmp_path / "config.json"
    paths = {name: tmp_path / f"{name}.sqlite" for name in ("se", "lf", "ca")}
    source.write_text(json.dumps({
        "kernel_root": str(tmp_path),
        "database": str(tmp_path / "control.sqlite"),
        "databases": {name: str(path) for name, path in paths.items()},
        "tasks": {},
    }), encoding="utf-8")

    config = load_config(source)

    assert config.databases == {name: path.resolve() for name, path in paths.items()}
    assert len(set(config.databases.values())) == 3
