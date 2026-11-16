PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schedule (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL UNIQUE CHECK (task_type IN ('se', 'lf', 'ca')),
    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
    period_seconds REAL NOT NULL CHECK (period_seconds > 0),
    next_due_at TEXT,
    config_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calculation_run (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL REFERENCES schedule(schedule_id),
    task_type TEXT NOT NULL CHECK (task_type IN ('se', 'lf', 'ca')),
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    elapsed_seconds REAL,
    return_code INTEGER,
    input_fingerprint TEXT,
    kernel_root TEXT,
    error_type TEXT,
    error_message TEXT
);
CREATE TABLE IF NOT EXISTS calculation_metric (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value_real REAL,
    value_text TEXT,
    unit TEXT
);
CREATE TABLE IF NOT EXISTS se_result (
    run_id INTEGER PRIMARY KEY REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    converged INTEGER NOT NULL,
    observable INTEGER NOT NULL,
    iterations INTEGER NOT NULL,
    objective REAL NOT NULL,
    max_correction REAL NOT NULL,
    residual_inf REAL NOT NULL,
    rank INTEGER NOT NULL,
    state_count INTEGER NOT NULL,
    measurement_count INTEGER NOT NULL,
    deficiency INTEGER NOT NULL,
    prefiltered_count INTEGER NOT NULL,
    pseudo_count INTEGER NOT NULL,
    bad_data_count INTEGER NOT NULL,
    normal_count INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS se_measurement_result (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    measurement_idx INTEGER NOT NULL,
    measurement_name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_name TEXT NOT NULL,
    measurement_type TEXT NOT NULL,
    value REAL,
    estimated_value REAL,
    residual REAL,
    normalized_residual REAL,
    valid INTEGER NOT NULL,
    source TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lf_result (
    run_id INTEGER PRIMARY KEY REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    converged INTEGER NOT NULL,
    iterations INTEGER NOT NULL,
    norm_f REAL NOT NULL,
    failure_reason TEXT NOT NULL,
    ac_converged INTEGER,
    ac_iterations INTEGER,
    ac_norm_f REAL,
    dc_converged INTEGER,
    dc_iterations INTEGER,
    dc_norm_f REAL,
    summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lf_device_result (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    device_type TEXT NOT NULL,
    device_key TEXT NOT NULL,
    node_from INTEGER,
    node_to INTEGER,
    voltage_from REAL,
    voltage_to REAL,
    p_from REAL,
    q_from REAL,
    p_to REAL,
    q_to REAL,
    current_from REAL,
    current_to REAL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ca_result (
    run_id INTEGER PRIMARY KEY REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    risk_level TEXT NOT NULL,
    n0_risk_count INTEGER NOT NULL,
    n1_scan_count INTEGER NOT NULL,
    n1_risk_count INTEGER NOT NULL,
    summary_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ca_risk (
    risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES calculation_run(run_id) ON DELETE CASCADE,
    contingency TEXT NOT NULL,
    risk_source TEXT NOT NULL,
    risk_dist TEXT NOT NULL,
    risk_type TEXT NOT NULL,
    risk_value_real REAL,
    risk_value_text TEXT,
    risk_info TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_calculation_run_type_status_time ON calculation_run(task_type, status, started_at);
CREATE INDEX IF NOT EXISTS idx_calculation_metric_run ON calculation_metric(run_id);
CREATE INDEX IF NOT EXISTS idx_ca_risk_run_level ON ca_risk(run_id, risk_type);
