import json

from pas.cli import main


def test_init_db_command_creates_database(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"kernel_root": str(tmp_path), "database": "runs.db", "tasks": {}}), encoding="utf-8")
    assert main(["init-db", "--config", str(config)]) == 0
    assert (tmp_path / "runs.db").exists()
