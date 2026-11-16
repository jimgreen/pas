# PAS 在线分析服务

本项目按配置周期调用指定计算内核，执行在线状态估计（SE）、在线潮流分析（LF）和在线静态安全评估（CA），并将运行记录、统计结果和明细写入 SQLite。

## 运行环境

需要 Python 3.10 或更高版本，以及参考内核所需的 NumPy、SciPy 等依赖。`kernel_root` 指向
`D:/codex/elec_power_flow/hybrid_power_system_analysis`，服务会从它的 `src` 目录加载内核模块。

冒烟运行前请确认参考内核工作区仍包含 `src/hybrid_power_system_analysis/secore`、`lfcore`、`cacore` 和对应的 `data` 输入文件；服务不会自动恢复或修改内核工作区。

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

```sql
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
