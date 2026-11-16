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
    source.write_text(json.dumps({"kernel_root": str(tmp_path / "kernel"), "database": str(tmp_path / "runs.db"), "tasks": {"lf": {"period_seconds": 0}}}), encoding="utf-8")

    with pytest.raises(ConfigError, match="period_seconds"):
        load_config(source)
