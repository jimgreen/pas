# 在线状态估计、潮流分析与静态安全评估设计

## 目标

在 `D:\codex\pas` 中建立 Python 常驻调度服务，按用户为 SE、LF、CA 分别配置的周期，直接调用
`D:\codex\elec_power_flow\hybrid_power_system_analysis\src\hybrid_power_system_analysis`
中的计算内核，并把每次运行的状态、统计结果和计算明细保存到 SQLite。

## 范围与假设

- SE 采用内核的 `ACStateEstimator`，输入为 AC 模型、量测文件和 SE 参数文件。
- LF 采用 `HybridPowerFlowCalc`，输入为混合能源系统 E 文件和 LF 参数文件。
- CA 采用 `run_hybrid_ca`，输入为模型文件和限值文件，并支持 N-1 扫描开关。
- 第一版以单进程、单调度循环为运行边界；同一任务不允许并发重入，SE/LF/CA 在同一调度周期内按顺序执行。
- 数据库只保存结果与统计，不复制或改写内核输入文件；CA 的 E 文件输出使用临时目录，数据库保存结构化风险结果。

## 架构

### 配置层

`pas.config` 读取 JSON 配置并生成不可变配置对象。配置包含内核根目录、SQLite 数据库路径，以及 SE/LF/CA 各自的输入文件、周期和启停状态。配置还包含调度循环最小 tick、失败重试间隔和 UTC 时间记录策略。

配置校验要求周期为正数，启用的任务必须具备存在的输入文件；数据库父目录自动创建。

### 调度层

`pas.scheduler` 为每个启用任务维护 `next_due`。调度器每次 tick：

1. 选出到期且未运行的任务；
2. 为任务创建 `calculation_run` 记录；
3. 顺序调用 SE、LF、CA 适配器；
4. 在成功或异常后更新运行记录和下一次触发时间。

单个任务的异常不会终止守护进程；异常文本、异常类型和耗时写入失败运行记录。服务退出通过停止事件结束 tick 循环，不删除历史数据。`run-once` 命令绕过等待，按相同顺序执行启用任务。

### 内核适配层

`pas.kernels` 将内核 `src` 目录加入导入路径，并将内核对象归一化为与数据库无关的字典：

- SE：调用 `ACStateEstimator.prepare()` 和 `run(result_mode="full")`，保存收敛、可观测性、迭代、目标函数、修正量、残差、状态向量、量测分类统计以及坏数据摘要。
- LF：调用 `_read_lf_network_from_file()`、`HybridPowerFlowCalc(..., result_mode="summary")` 和 `run()`，保存混合、AC、DC 收敛指标及节点/设备结果摘要。
- CA：调用 `run_hybrid_ca()`，从返回的 N-0/N-1 `CARisk` 列表提取风险等级、扫描数、风险计数和逐条风险。

适配器只负责调用和归一化，不负责数据库事务；内核异常向调度层抛出，由调度层统一记录。

### 数据访问层

`pas.db` 使用标准库 `sqlite3`，启动时执行幂等 schema migration。所有一次运行的结果写入一个事务；明细插入失败时整体回滚结果事务，但保留已创建的运行记录并标记失败。

## 数据库结构

- `schema_version(version, applied_at)`：迁移版本。
- `schedule(schedule_id, task_type, enabled, period_seconds, next_due_at, config_json, created_at, updated_at)`：调度配置快照。
- `calculation_run(run_id, schedule_id, task_type, status, started_at, finished_at, elapsed_seconds, return_code, input_fingerprint, kernel_root, error_type, error_message)`：一次计算主记录。
- `calculation_metric(metric_id, run_id, name, value_real, value_text, unit)`：跨任务通用指标。
- `se_result(run_id, converged, observable, iterations, objective, max_correction, residual_inf, rank, state_count, measurement_count, deficiency, prefiltered_count, pseudo_count, bad_data_count, normal_count, state_json, summary_json)`：SE 主结果。
- `se_measurement_result(result_id, run_id, measurement_idx, measurement_name, device_type, device_name, measurement_type, value, estimated_value, residual, normalized_residual, valid, source, reason)`：SE 量测明细。
- `lf_result(run_id, converged, iterations, norm_f, failure_reason, ac_converged, ac_iterations, ac_norm_f, dc_converged, dc_iterations, dc_norm_f, summary_json)`：LF 主结果。
- `lf_device_result(result_id, run_id, domain, device_type, device_key, node_from, node_to, voltage_from, voltage_to, p_from, q_from, p_to, q_to, current_from, current_to, result_json)`：LF 节点、支路、变流器等明细。
- `ca_result(run_id, risk_level, n0_risk_count, n1_scan_count, n1_risk_count, summary_json)`：CA 主结果。
- `ca_risk(risk_id, run_id, contingency, risk_source, risk_dist, risk_type, risk_value_real, risk_value_text, risk_info, created_at)`：CA N-0/N-1 风险明细。

所有结果表以 `run_id` 外键关联 `calculation_run`，并对 `task_type/status/started_at`、`run_id` 和 CA 风险等级建立索引。数值没有可靠统一单位时保存内核原值并在 `unit` 或 JSON 中标记来源。

## 错误处理与可观测性

- 输入文件缺失、配置错误在启动时拒绝运行并给出文件路径。
- 内核计算未收敛属于“已执行但失败”的运行，保存返回码、收敛标志和失败原因。
- Python 异常属于“异常失败”运行，保存异常类型和消息，并继续调度其他任务。
- 每次运行保存 UTC ISO-8601 时间和单调时钟计算出的耗时。
- 日志输出任务类型、run_id、状态、耗时和错误摘要，不输出完整状态向量或敏感输入内容。

## 测试与验收

- 配置测试：周期校验、启用任务输入文件校验和默认值。
- 数据库测试：schema 幂等初始化、主记录/结果/明细外键、失败事务行为和查询索引。
- 调度测试：到期判断、任务顺序、单任务异常隔离、停止事件和禁止重入。
- 适配器测试：使用轻量 fake kernel 对象验证 SE/LF/CA 结果归一化；不在单元测试中运行长时间 N-1 扫描。
- 冒烟验证：用内核现有小型案例执行 `run-once`，确认三类任务能创建运行记录并写入各自结果表；输入文件或依赖缺失时给出明确失败记录。

## 命令接口

- `python -m pas.cli init-db --config config.example.json`
- `python -m pas.cli run-once --config config.example.json`
- `python -m pas.cli daemon --config config.example.json`

默认配置和 SQLite schema 会随仓库提供，便于在真实案例前先完成数据库和调度验证。
