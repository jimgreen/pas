# PAS 在线分析服务

本项目按配置周期调用指定计算内核，执行在线状态估计（SE）、在线潮流分析（LF）和在线静态安全评估（CA），并将运行记录、统计结果和明细写入 SQLite。PAS 控制参数和后台日志也独立持久化，Web 界面提供按功能拆分的多页面展示与操作。

## 运行环境

需要 Python 3.10 或更高版本，以及参考内核所需的 NumPy、SciPy 等依赖。当前迁移后的参考内核目录为
`D:/codex/hybrid_power_kernel_acceptance_d1603be`，服务会从它的 `src` 目录加载内核模块。

配置中的 `kernel_root` 可以继续保留迁移前的路径：服务会在常见候选目录中发现包含 `secore`、`lfcore`、`cacore` 的新内核，并将旧根目录下的 `data/...` 输入路径自动重定位到新根目录。也可以通过环境变量 `PAS_KERNEL_ROOT` 显式指定内核目录。服务不会自动恢复或修改内核工作区。

先复制并修改 `config.example.json`，按实际输入文件设置任务周期。启用任务的模型、量测、参数或限值文件必须存在。

## 命令

```powershell
python -m pas.cli init-db --config config.example.json
python -m pas.cli run-once --config config.example.json
python -m pas.cli daemon --config config.example.json
```

`run-once` 按 SE、LF、CA 顺序人工触发所有已配置执行器；即使某任务的周期调度关闭，也可以执行该任务。单个任务失败会保存失败运行记录并继续后续任务。`daemon` 按各任务周期持续运行，按 Ctrl+C 停止。

## 数据库

SQLite schema 在服务启动时幂等创建。常用查询示例：

`database` 是 PAS 控制数据库，保存 `pas_config` 参数表和 `pas_log` 日志表；`databases.se`、`databases.lf`、`databases.ca` 分别是 SE、LF、CA 的结果数据库。未显式配置 `databases` 时，服务会从 `database` 自动派生三个带任务后缀的路径。Web 的“系统设置”页面会展示四个数据库路径、调度参数和 PAS 日志；运行总览与运行历史会跨三个结果库聚合。

当前示例配置将 `pas.db`、`se.db`、`lf.db`、`ca.db` 四个 SQLite 文件统一放在 `D:/codex/sqldb/realtime/pas`，可按部署环境修改为其他绝对路径。

周期执行由 `daemon` 调度器负责，任务按各自 `period_seconds` 顺序执行并将下一次执行时间写入 `schedule.next_due_at`。Web/API 的人工触发使用同一套内核、事务和回写流程，即使任务的周期开关为关闭，也可以单独执行；每条 `calculation_run.execution_source` 标记为 `schedule` 或 `manual`，便于界面和日志区分来源。对应接口为 `POST /api/actions/trigger`（传入 `{"task":"se"}`）或兼容接口 `POST /api/actions/run-once`。

Web 人工执行优先使用 `POST /api/actions/submit`，接口立即返回任务编号，前端通过 `/api/jobs/{job_id}` 轮询状态；同一任务已有等待或运行任务时会拒绝重复提交。`POST /api/schedules/{se|lf|ca}` 可在线保存周期和启用状态，配置写入 `pas.db` 的 `pas_config.schedule_overrides`，服务重启会恢复。调度器使用有界线程池并行执行不同任务、合并错过的周期 tick，并在退出时等待已接受任务完成。

Web 页面按功能分层：总览展示三类任务状态和服务状态；运行历史支持任务/状态筛选与分页；SE、LF、CA 页面分别提供功能概览、运行记录、结构化结果明细和执行控制标签；系统设置提供数据库、调度控制和 PAS 日志标签。页面通过 `/api/status`、`/api/runs`、`/api/runs/{task}/{run_id}`、`/api/config` 和 `/api/logs` 与后台实时联动。

用户提供的 42 个 PAS `dbdef` 定义已生成到 `pas/dbdef_catalog.json` 和 `pas/dbdef_schema.sql`，并在四个数据库初始化时幂等建表。SE、LF、CA 的一次成功计算会在各自结果库中同时写入通用结果表和对应的 `pas_se_*`、`pas_lf_*`、`pas_ra_*` 原始表；`pas_dbdef_run` 保存运行编号与 dbdef 记录时间的关联，Web 结果详情会展示本次实际写入的表和行数。LF 使用内核 `result_mode="full"` 回写 AC/DC 设备端值、节点和功率/电流明细。

每次 dbdef 回写还保存 `pas_dbdef_snapshot` 运行快照，因此相同秒内的人工或周期计算不会互相覆盖；结果浏览接口支持明细分页、关键词筛选和紧凑摘要（`/api/results/{task}/{run_id}?compact=1`），不必一次传输完整设备/风险数组。SQLite 连接启用 WAL，并对共享连接、结果事务和批量 dbdef 写入加锁。

```sql
-- 在对应的 SE/LF/CA 结果库中执行
select task_type, status, started_at, elapsed_seconds
from calculation_run
order by run_id desc;

select r.run_id, r.task_type, r.status,
       (select count(*) from se_measurement_result s where s.run_id = r.run_id) as se_rows,
       (select count(*) from lf_device_result l where l.run_id = r.run_id) as lf_rows,
       (select count(*) from ca_risk c where c.run_id = r.run_id) as ca_risks
from calculation_run r
order by r.run_id desc;
```
