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

当前示例配置使用场景工作目录。配置字段 `workspace_root`、`runtime`、`scenario` 分别为 `D:/codex/workspace`、`realtime`、`qinling`，推导出 `D:/codex/workspace/realtime/qinling`。场景名按实际目录拼写为 `qinling`。

| 用途 | 相对工作目录的路径 |
| --- | --- |
| 模型输入（只读） | `sqldb/model/devices.sqlite3` |
| SE 计算结果 | `sqldb/pas/se.sqlite3` |
| LF 计算结果 | `sqldb/pas/lf.sqlite3` |
| CA 计算结果 | `sqldb/pas/ca.sqlite3` |
| PAS 参数、日志 | `sqldb/pas/pas.sqlite3` |

工作目录模式统一推导模型和四个数据库路径，优先于旧 `database`、`databases`、任务 `model_file` 字段。不配置工作目录参数时保持旧路径配置方式。旧库不会自动迁移或删除；新场景库从新的运行记录开始。

CLI 和 Web 均支持参数覆盖（命令行优先于 JSON）：

```powershell
python -m pas.webapp --config D:/codex/pas/config.example.json --workspace-root D:/codex/workspace --runtime realtime --scenario qinling --host 127.0.0.1 --port 8091
python -m pas.cli init-db --config config.example.json --workspace-root D:/codex/workspace --runtime realtime --scenario qinling
```

运行态和场景名必须为单个目录名，不允许路径穿越、绝对路径或 Windows 保留名称。不同运行态/场景分别保存结果与调度覆盖参数。辅助输入的相对路径按工作目录解析；默认 SE 量测为 `meas/measurements.meas`，SE/LF 参数为 `config/se.para`、`config/lf.para`，CA 限值为 `config/ca.calmt`，也可显式配置绝对路径。当前示例保留内核的 SE/LF 算法参数文件。

`devices.sqlite3` 使用 RTDB 内嵌结构（`rtdb_schema_tables`、`rtdb_schema_columns`、`rtdb_data_*`）。每次调用在单个只读事务中读取全部声明表与列，包含 WAL 中已提交的数据，生成临时 E 模型交给内核；不读取旁边同名旧 E 模型，也不修改模型库。快照随调用释放，结果摘要保存源路径、SHA-256、表数和行数。SQLite 输入每次重新读取，暂不使用 E 文件模板缓存，防止模型更新后复用旧模板。非法结构、NULL、非有限数值或内核无法表示的字符串会明确失败。

SE 使用支持 AC/DC/混合模型的 `HybridStateEstimator`。SQLite 模式会核对量测/限值中的设备名，拒绝混用其他场景的输入。当前实际模型库只有设备表，尚缺匹配的 SE 量测和 CA 限值，因此示例配置暂时关闭 SE/CA 周期调度，LF 每 60 秒自动执行。补齐两个场景文件后，可在对应页面启用周期调度或人工执行；缺少文件时人工执行会记录失败原因，不伪造计算结果。

`/workspace.html` 是独立工作目录页面，分目录参数、模型输入、结果数据库展示当前有效配置；`GET /api/config` 的 `workspace` 字段返回这些参数。

周期执行由 `daemon` 调度器负责，任务按各自 `period_seconds` 到期提交，不同任务可并行执行，同一任务避免重复执行，并将下一次执行时间写入 `schedule.next_due_at`。Web/API 的人工触发使用同一套内核、事务和回写流程，即使任务的周期开关为关闭，也可以单独执行；每条 `calculation_run.execution_source` 标记为 `schedule` 或 `manual`，便于界面和日志区分来源。对应接口为 `POST /api/actions/trigger`（传入 `{"task":"se"}`）或兼容接口 `POST /api/actions/run-once`。

Web 人工执行优先使用 `POST /api/actions/submit`，接口立即返回任务编号，前端通过 `/api/jobs/{job_id}` 轮询状态；同一任务已有等待或运行任务时会拒绝重复提交。`POST /api/schedules/{se|lf|ca}` 可在线保存周期和启用状态，配置写入 PAS 控制库的 `pas_config.schedule_overrides`，服务重启会恢复。调度器使用有界线程池并行执行不同任务、合并错过的周期 tick，并在退出时等待已接受任务完成。

总览的“运行趋势”支持 6/24/48/168 小时窗口、执行/成功/失败次数及平均耗时切换、分页统计明细与窗口 CSV 导出。`GET /api/metrics/trend?limit=24` 按 UTC 自然小时聚合完整窗口，包含尚未结束的当前小时，空小时补齐；平均耗时只按有耗时的记录计算。执行控制页提供“重试失败任务”，仅当该任务最近一次运行失败才重试；`POST /api/actions/retry-failed` 可传 `{"task":"lf"}` 限定任务，已恢复成功的旧失败记录不会重跑。

Web 采用独立 HTML 页面：`/overview.html` 总览、`/analysis/se.html` 状态估计、`/analysis/lf.html` 潮流分析、`/analysis/ca.html` 静态安全、`/runs.html` 运行历史、`/settings.html` 系统设置；根路径 `/` 兼容打开总览。每个页面共享样式和 API 客户端，但拥有独立 URL、页面状态和加载生命周期，页面之间使用真实链接切换，不再把所有功能放在同一个 HTML 文档中。总览展示三类任务状态和服务状态；运行历史支持任务/状态筛选与分页；SE、LF、CA 页面分别提供功能概览、运行记录、结构化结果明细和执行控制标签；系统设置提供数据库健康检查、调度控制和 PAS 日志标签。Web 进程启动后会自动恢复周期调度，仍可在界面或 `/api/actions/daemon/{start|stop}` 手动控制。页面通过 `/api/status`、`/api/health`、`/api/runs`、`/api/runs/{task}/{run_id}`、`/api/config` 和 `/api/logs` 与后台实时联动。

用户提供的 42 个 PAS `dbdef` 定义已生成到 `pas/dbdef_catalog.json` 和 `pas/dbdef_schema.sql`，并在四个数据库初始化时幂等建表。SE、LF、CA 的一次成功计算会在各自结果库中同时写入通用结果表和对应的 `pas_se_*`、`pas_lf_*`、`pas_ra_*` 原始表；`pas_dbdef_run` 保存运行编号与 dbdef 记录时间的关联，Web 结果详情会展示本次实际写入的表和行数。LF 使用内核 `result_mode="full"` 回写 AC/DC 设备端值、节点和功率/电流明细。

每次 dbdef 回写还保存 `pas_dbdef_snapshot` 运行快照，因此相同秒内的人工或周期计算不会互相覆盖；结果浏览接口支持明细分页、关键词筛选和紧凑摘要（`/api/results/{task}/{run_id}?compact=1`），不必一次传输完整设备/风险数组。SQLite 连接启用 WAL，并对共享连接、结果事务和批量 dbdef 写入加锁。

## 结果分析与操作

- “结果摘要”分为计算结果、性能分项、运行信息；“诊断统计”展示 SE 有效/无效量测及残差、LF 设备分类及电压范围、CA 场景与风险类型统计。统计依据已回写的记录，跨设备电压范围不能直接视为越限结论。
- “计算明细”支持关键词、分类、字段排序及升降序。SE 支持残差绝对值排序；LF 按 AC/DC/DCAC/ACAC 域筛选；CA 按 N-0/N-1 场景筛选。长字段可点击或通过键盘查看完整值，行与字段组分别分页，小屏诊断表保留分类列。
- “本页导出”导出当前页全部字段；“筛选导出”导出当前筛选与排序下的全部匹配记录，最多 100,000 行，超过时需缩小筛选范围。CSV 使用 UTF-8 BOM，字符串做公式转义，数值负号保持不变。
- 对应接口为 `GET /api/results/{task}/{run_id}/diagnostics`、`GET /api/results/{task}/{run_id}/details?view=all&sort=&direction=asc&q=&limit=50&offset=0` 和 `GET /api/export/{task}/{run_id}?view=all&sort=&direction=asc&q=`。`view` 可选 `all`，或 SE 的 `valid/invalid`、LF 的 `ac/dc/dcac/acac`、CA 的 `n0/n1`；`sort` 为明细字段名，SE 另支持 `abs_residual`。

## 效率优化与验证

结果摘要、明细分页、诊断和趋势采用有界查询缓存，最多 64 项，每项不超过 64 KiB 序列化字符；本连接写入或其他 SQLite 连接提交后失效。事务中不缓存，返回结果与缓存隔离。导出通过独立只读连接和一致性快照每批读取 500 行。页面隐藏时暂停状态轮询，空闲时每 6 秒刷新，执行期间每 2 秒刷新。

`GET /api/health` 返回 PAS、SE、LF、CA 数据库的 SQLite `quick_check`、任务输入文件就绪状态、最近一次运行和周期调度状态。数据库页将这些信息按数据库和任务分组展示，便于重启后快速确认数据和输入是否可用。运行历史查询使用任务/状态/来源及时间复合索引，指标明细按运行编号索引。

LF 对不超过 16 MiB 的独立 `.e` 模型缓存一个未求解模板，每次执行深拷贝给求解器；缓存按绝对路径、文件内容 SHA-256 和加载函数识别，输入变更后重新解析。每次仍读取参数并完整求解，不复用上次求解状态；其他格式保持重新加载。性能分项记录模型读取/复制、求解、结果整理、模板命中情况及内核/写库耗时，旧历史记录没有的分项不会补造。

复现交替顺序的基准：

```powershell
D:\anaconda3\python.exe scripts/benchmark_lf_model_cache.py --config config.example.json --pairs 10
D:\anaconda3\python.exe -m pytest tests -q --import-mode=importlib
```

2026-11-18 本机秦岭 95 设备算例，10 对交替运行的归一化结果完全一致（排除耗时元数据）；预热后的 LF 调用中位耗时由 26.88 ms 降至 19.87 ms，减少约 26%，模型读取部分由 9.47 ms 降至 2.22 ms。这是适配层加载、求解和整理的合计，不含写库，也不代表其他模型或求解器本身具有同等加速。原始证据保存在本机 `output/optimization_round3/lf-cache-benchmark.json`；验证产物不提交 Git。

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
