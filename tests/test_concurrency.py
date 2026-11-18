import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace
from urllib.request import Request, urlopen

import pytest

from pas.config import TaskConfig
from pas.db import Repository
from pas.scheduler import Scheduler
from pas.web import serve


def make_scheduler(tmp_path, runners=None):
    repo = Repository(tmp_path / "runs.db")
    repo.initialize()
    input_file = tmp_path / "input.e"
    input_file.write_text("test")
    config = SimpleNamespace(kernel_root=tmp_path, tick_seconds=.01, retry_seconds=.01,
        tasks={name: TaskConfig(name, True, 60, input_file, input_file, input_file, input_file) for name in ("se", "lf", "ca")})
    scheduler = Scheduler(config, repo, runners or {name: lambda: {} for name in config.tasks})
    scheduler.restore_schedules()
    return scheduler, repo


def test_async_parallel_execution_and_duplicate_prevention(tmp_path):
    barrier = threading.Barrier(4)
    release = threading.Event()
    def run():
        barrier.wait(timeout=3)
        assert release.wait(3)
        return {}
    scheduler, repo = make_scheduler(tmp_path, {name: run for name in ("se", "lf", "ca")})
    try:
        accepted = scheduler.trigger_all_async()["tasks"]
        barrier.wait(timeout=3)  # All three kernels have entered before any finishes.
        assert scheduler.trigger_task_async("se")["reason"] == "already_running"
        assert scheduler.trigger_task("lf") is False
        assert set(scheduler.status()["active_tasks"]) == {"se", "lf", "ca"}
        release.set()
        scheduler.shutdown()
        for name, job in accepted.items():
            finished = scheduler.get_job(job["job_id"])
            assert finished["status"] == "succeeded"
            assert repo.get_run(finished["run_id"])["task_type"] == name
        assert repo.count_runs(status="succeeded", execution_source="manual") == 3
    finally:
        release.set()
        scheduler.shutdown()
        repo.close()


def test_start_failure_releases_reserved_slot(tmp_path, monkeypatch):
    scheduler, repo = make_scheduler(tmp_path)
    original = repo.start_run
    def fail(*args):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(repo, "start_run", fail)
    assert scheduler.trigger_task("se") is False
    assert not scheduler.status()["active_tasks"]
    monkeypatch.setattr(repo, "start_run", original)
    assert scheduler.trigger_task("se") is True
    scheduler.shutdown()
    repo.close()


def test_transaction_isolation_from_other_thread_commit(tmp_path):
    _, repo = make_scheduler(tmp_path)
    sid = repo.upsert_schedule("lf", True, 60, {})
    rid = repo.start_run(sid, "lf", "t", "k", "fp")
    inserted, release, entered = threading.Event(), threading.Event(), threading.Event()
    def writer():
        with pytest.raises(RuntimeError), repo.result_transaction():
            repo.store_lf_result(rid, {})
            inserted.set()
            assert release.wait(3)
            raise RuntimeError("rollback")
    def config_writer():
        entered.set()
        repo.set_config("test", 1)
    with ThreadPoolExecutor(2) as pool:
        a=pool.submit(writer)
        assert inserted.wait(2)
        b=pool.submit(config_writer)
        assert entered.wait(2)
        time.sleep(.03)
        assert not b.done()
        release.set()
        a.result(timeout=3); b.result(timeout=3)
    assert repo.get_result("lf", rid) is None
    assert repo.get_config("test") == 1
    repo.close()


def test_schedule_persistence_validation_and_restoration(tmp_path):
    scheduler, repo = make_scheduler(tmp_path)
    scheduler.update_schedule("lf", False, 15.5)
    for invalid in (float("nan"),float("inf"),0,True,604801):
        with pytest.raises(ValueError): scheduler.update_schedule("lf", True, invalid)
    with pytest.raises(ValueError): scheduler.update_schedule("lf", "false", 20)
    scheduler.shutdown(); repo.close()
    restored, repo = make_scheduler(tmp_path)
    assert restored.config.tasks["lf"].enabled is False
    assert restored.config.tasks["lf"].period_seconds == 15.5
    assert repo.list_schedules()[1]["next_due_at"] is None
    restored.shutdown(); repo.close()


def test_daemon_coalesces_busy_ticks_and_can_restart(tmp_path):
    entered, release, stop = threading.Event(), threading.Event(), threading.Event()
    def runner():
        entered.set(); release.wait(3); return {}
    scheduler, repo = make_scheduler(tmp_path, {"se":runner})
    scheduler.config.tasks["se"] = replace(scheduler.config.tasks["se"],period_seconds=.02)
    scheduler.config.tasks["lf"] = replace(scheduler.config.tasks["lf"],enabled=False)
    scheduler.config.tasks["ca"] = replace(scheduler.config.tasks["ca"],enabled=False)
    thread = threading.Thread(target=scheduler.run_daemon,args=(stop,));thread.start()
    try:
        assert entered.wait(2)
        time.sleep(.09)
        stop.set();thread.join(2)
        assert not thread.is_alive()
        assert repo.count_runs() == 1
        assert len(scheduler._jobs) == 1
        assert repo.list_schedules()[-1]["next_due_at"] is None
    finally:
        stop.set(); release.set(); thread.join(3); scheduler.shutdown(); repo.close()


def test_http_accepts_job_before_completion_and_preserves_sync_api(tmp_path):
    release=threading.Event()
    scheduler, repo=make_scheduler(tmp_path,{"se":lambda: (release.wait(3) and {})})
    server=serve(scheduler.config,repo,scheduler,tmp_path,port=0)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        request=Request(base+"/api/actions/submit",json.dumps({"task":"se"}).encode(),{"Content-Type":"application/json"})
        with urlopen(request,timeout=2) as response:
            assert response.status == 202
            job=json.load(response)["data"]
        assert job["accepted"]
        assert server.app.api_post("/api/actions/trigger",{"task":"invalid"})["error"] == "invalid_task"
        assert server.app.api_post("/api/actions/submit",[])["error"] == "payload_must_be_object"
        assert server.app.api_post("/api/schedules/se",{"enabled":True,"period_seconds":None})["ok"] is False
        release.set(); scheduler.shutdown()
        assert server.app.api_get("/api/jobs/"+job["job_id"])["data"]["status"] == "succeeded"
    finally:
        release.set();server.shutdown();thread.join();server.app.close();server.server_close();repo.close()


def test_same_second_dbdef_snapshots_and_paginated_details(tmp_path):
    scheduler, repo=make_scheduler(tmp_path)
    ids=[]
    for power in (2.5,8.5):
        rid=repo.start_run(2,"lf","2026-11-18T00:00:00+00:00","k","fp")
        ids.append(rid)
        result={"devices":[{"device_key":f"line{i}","device_type":"branch","p_from":power} for i in range(1100)]}
        with repo.result_transaction():
            repo.store_lf_result(rid,result)
            repo.store_dbdef_result("lf",rid,result,"2026-11-18T00:00:00+00:00")
    for rid,power in zip(ids,(2.5,8.5)):
        rows=repo.browse_dbdef_table("lf",rid,"pas_lf_result",500)["rows"]
        assert any(row["calc_value"] == power for row in rows)
        page=repo.browse_details("lf",rid,8,1096)
        assert page["meta"]["total"]==1100
        assert len(page["rows"])==4
        assert page["rows"][-1]["p_from"]==power
        compact=repo.get_result("lf",rid,compact=True)
        assert compact["detail_count"]==1100
        assert "details" not in compact and "dbdef" not in compact
        assert repo.browse_details("lf",rid,8,0,"line1099")["meta"]["total"]==1
    scheduler.shutdown();repo.close()
