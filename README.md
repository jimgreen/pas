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

`run-once` 按 SE、LF、CA 顺序执行所有启用任务；单个任务失败会保存失败运行记录并继续后续任务。`daemon` 按各任务周期持续运行，按 Ctrl+C 停止。

## 数据库

SQLite schema 在服务启动时幂等创建。常用查询示例：

`database` 是 PAS 控制数据库，保存 `pas_config` 参数表和 `pas_log` 日志表；`databases.se`、`databases.lf`、`databases.ca` 分别是 SE、LF、CA 的结果数据库。未显式配置 `databases` 时，服务会从 `database` 自动派生三个带任务后缀的路径。Web 的“系统设置”页面会展示四个数据库路径、调度参数和 PAS 日志；运行总览与运行历史会跨三个结果库聚合。

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
