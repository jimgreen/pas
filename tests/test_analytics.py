import csv
import io
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from pas.db import Repository, RepositoryHub
from pas.model_cache import ModelCache


def repo_run(tmp_path, task="se"):
    repo = Repository(tmp_path / (task+".db")); repo.initialize()
    sid = repo.upsert_schedule(task, True, 60, {})
    rid = repo.start_run(sid, task, "2026-11-18T03:01:00+00:00", "k", "fp")
    return repo, rid


def test_complete_hour_counts_timezone_and_empty_hours(tmp_path):
    repo,rid=repo_run(tmp_path)
    with repo.result_transaction():
        repo._connection().executemany("INSERT INTO calculation_run(schedule_id,task_type,status,started_at,elapsed_seconds) VALUES (1,'se','succeeded',?,?)",[("2026-11-18T16:10:00+13:00",2.)]*1000)
        repo._connection().execute("INSERT INTO calculation_run(schedule_id,task_type,status,started_at,elapsed_seconds) VALUES (1,'se','failed','2026-11-18T03:30:00Z',4.)")
    trend=repo.trend(3,"2026-11-18T03:50:00+00:00")
    assert len(trend)==3 and trend[0]["tasks"]=={}
    item=trend[-1]["tasks"]["se"]
    assert item["runs"]==1002 and item["running"]==1
    assert item["elapsed_count"]==1001
    assert item["avg_elapsed_seconds"]==pytest.approx(2004/1001)
    assert repo.trend(1,"2026-11-18T03:50:00Z")[-1]==trend[-1]
    assert repo.trend(1,"2026-11-18T04:50:00Z")[0]["tasks"]=={}
    repo.close()


def test_hub_averages_use_completed_count(tmp_path):
    a,rid=repo_run(tmp_path)
    a.finish_run(rid,"succeeded","t",4,0)
    other=Repository(tmp_path/"extra.db");other.initialize()
    sid=other.upsert_schedule("se",True,60,{})
    other.start_run(sid,"se","2026-11-18T03:00:00Z","k","f")
    rid=other.start_run(sid,"se","2026-11-18T03:00:00Z","k","f")
    other.finish_run(rid,"succeeded","t",2,0)
    hub=RepositoryHub({"a":a,"b":other})
    item=hub.trend(1,"2026-11-18T03:59:00Z")[0]["tasks"]["se"]
    assert item["avg_elapsed_seconds"]==3 and item["runs"]==3
    hub.close()


def test_detail_sort_filter_cache_invalidation_and_export(tmp_path):
    repo,rid=repo_run(tmp_path)
    with repo.result_transaction():
        repo.store_se_result(rid,{"measurements":[{"name":"=SUM(A1)","residual":-3.,"value":-5.,"valid":False},{"name":"m2","residual":2.,"valid":True},{"name":"m3","residual":None,"valid":False}]})
    page=repo.browse_details("se",rid,sort="abs_residual",direction="desc")
    assert [r["measurement_name"] for r in page["rows"]]==["=SUM(A1)","m2","m3"]
    assert repo.browse_details("se",rid,view="invalid")["meta"]["total"]==2
    trace=[];repo._connection().set_trace_callback(trace.append)
    repo.browse_details("se",rid,sort="abs_residual",direction="desc")
    assert not any("FROM se_measurement_result" in sql for sql in trace)
    page["rows"][0]["residual"]=1000
    assert repo.browse_details("se",rid,sort="abs_residual",direction="desc")["rows"][0]["residual"]==-3.
    # Writes through a different SQLite connection invalidate all cached results.
    with sqlite3.connect(repo.path) as conn:
        conn.execute("UPDATE se_measurement_result SET residual=-6 WHERE measurement_name='m2'")
    assert repo.browse_details("se",rid,sort="abs_residual",direction="desc")["rows"][0]["measurement_name"]=="m2"
    blob=b"".join(repo.export_details("se",rid,view="invalid"))
    rows=list(csv.DictReader(io.StringIO(blob.decode("utf-8-sig"))))
    assert len(rows)==2 and rows[0]["measurement_name"].startswith("'=")
    assert rows[0]["value"]=="-5.0"
    assert repo.diagnostics("se",rid)["metrics"]["invalid"]==2
    for options in ({"sort":"residual; DROP TABLE calculation_run"},{"direction":"bad"},{"view":"bad"}):
        with pytest.raises(ValueError):repo.browse_details("se",rid,**options)
    repo.close()


def test_cache_does_not_publish_rolled_back_results(tmp_path):
    repo,rid=repo_run(tmp_path,"lf")
    assert repo.get_result("lf",rid,True) is None
    with pytest.raises(RuntimeError):
        with repo.result_transaction():
            repo.store_lf_result(rid,{})
            assert repo.get_result("lf",rid,True) is not None
            raise RuntimeError("rollback")
    assert repo.get_result("lf",rid,True) is None
    repo.close()


def test_empty_diagnostics_keep_counts_zero_and_values_missing(tmp_path):
    repo, rid = repo_run(tmp_path)
    metrics = repo.diagnostics("se", rid)["metrics"]
    assert metrics["valid"] == metrics["invalid"] == metrics["total"] == 0
    assert metrics["max_abs_residual"] is None
    assert repo.diagnostics("lf", rid) is None
    repo.close()


def test_model_template_never_reuses_solved_state_or_stale_file(tmp_path):
    path=tmp_path/"m.e";path.write_text("one")
    calls=[]
    def loader(path):
        calls.append(1);return {"value":path.read_text(),"state":[0]}
    cache=ModelCache()
    first,hit=cache.load(path,loader);assert not hit
    first["state"][0]=99
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:cache.load(path,loader),range(2)))
    assert all(hit and model["state"]==[0] for model,hit in results)
    assert results[0][0] is not results[1][0]
    stamp=path.stat();path.write_text("two");os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    second,hit=cache.load(path,loader)
    assert not hit and second["value"]=="two" and len(calls)==2


def test_retry_only_latest_failure_and_duplicate_guard(tmp_path):
    from tests.test_concurrency import make_scheduler
    scheduler,repo=make_scheduler(tmp_path)
    sid=repo.upsert_schedule("lf",True,60,{})
    rid=repo.start_run(sid,"lf","2026-11-18T00:00:00Z","k","f")
    repo.finish_run(rid,"failed","t",1,1)
    assert scheduler.retry_failed_async("lf")["accepted"]
    scheduler.shutdown()
    assert repo.list_runs(1,"lf")[0]["status"]=="succeeded"
    assert scheduler.retry_failed_async("lf")["tasks"]["lf"]["reason"]=="no_failed_run"
    repo.close()
