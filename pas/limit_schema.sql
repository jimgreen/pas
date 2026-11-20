CREATE TABLE IF NOT EXISTS ca_limit (
 limit_id INTEGER PRIMARY KEY, model_table TEXT NOT NULL, model_idx INTEGER NOT NULL, device_name TEXT NOT NULL,
 field TEXT NOT NULL, lower_value REAL, upper_value REAL, unit TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)), source TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
 CHECK(lower_value IS NOT NULL OR upper_value IS NOT NULL),
 CHECK(lower_value IS NULL OR upper_value IS NULL OR lower_value<=upper_value),
 UNIQUE(model_table,model_idx,field)
);
CREATE TABLE IF NOT EXISTS ca_limit_change_log (
 change_id INTEGER PRIMARY KEY, changed_at TEXT NOT NULL, limit_id INTEGER,
 before_json TEXT NOT NULL, after_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ca_limit_device ON ca_limit(model_table,model_idx);
