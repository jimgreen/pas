PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS device (
 device_id INTEGER PRIMARY KEY, model_table TEXT NOT NULL, model_idx INTEGER NOT NULL,
 name TEXT NOT NULL, scada_dev_id INTEGER, model_json TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 UNIQUE(model_table,model_idx)
);
CREATE TABLE IF NOT EXISTS device_measurement (
 measurement_id INTEGER PRIMARY KEY, device_id INTEGER NOT NULL REFERENCES device(device_id),
 metric TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('yc','yx')), name TEXT NOT NULL,
 unit TEXT NOT NULL DEFAULT '', se_type TEXT, se_enabled INTEGER NOT NULL DEFAULT 0 CHECK(se_enabled IN (0,1)),
 weight REAL NOT NULL DEFAULT 1 CHECK(weight>0), max_age_seconds REAL NOT NULL DEFAULT 120 CHECK(max_age_seconds>0),
 origin TEXT NOT NULL, catalog_active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
 UNIQUE(device_id,kind,metric)
);
CREATE TABLE IF NOT EXISTS scada_point_mapping (
 measurement_id INTEGER PRIMARY KEY REFERENCES device_measurement(measurement_id),
 source_database TEXT NOT NULL DEFAULT 'scdfe_c.db', rtu_id INTEGER NOT NULL CHECK(rtu_id>0),
 pnt_no INTEGER NOT NULL CHECK(pnt_no>=0), enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
 scale REAL NOT NULL DEFAULT 1, offset REAL NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
 updated_at TEXT NOT NULL, UNIQUE(source_database,rtu_id,pnt_no,measurement_id)
);
CREATE TABLE IF NOT EXISTS measurement_refresh (
 refresh_id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
 total_count INTEGER NOT NULL DEFAULT 0, valid_count INTEGER NOT NULL DEFAULT 0, se_valid_count INTEGER NOT NULL DEFAULT 0,
 source_database TEXT NOT NULL, error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS measurement_value (
 measurement_id INTEGER PRIMARY KEY REFERENCES device_measurement(measurement_id),
 refresh_id INTEGER NOT NULL REFERENCES measurement_refresh(refresh_id),
 source_value REAL, value REAL, quality INTEGER, source_time_ms INTEGER,
 collected_at TEXT NOT NULL, valid INTEGER NOT NULL CHECK(valid IN (0,1)), reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS input_change_log (
 change_id INTEGER PRIMARY KEY, changed_at TEXT NOT NULL, entity TEXT NOT NULL, entity_id INTEGER,
 before_json TEXT NOT NULL, after_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_device_name ON device(name);
CREATE INDEX IF NOT EXISTS idx_measurement_device ON device_measurement(device_id);
CREATE INDEX IF NOT EXISTS idx_measurement_se ON device_measurement(se_enabled);
CREATE VIEW IF NOT EXISTS device_measurement_view AS
 SELECT m.*,d.model_table,d.model_idx,d.name AS device_name,d.scada_dev_id,d.active,
 p.source_database,p.rtu_id,p.pnt_no,p.enabled AS mapping_enabled,p.scale,p.offset,p.version AS mapping_version,
 v.value,v.source_value,v.quality,v.source_time_ms,v.collected_at,v.valid,v.reason,v.refresh_id
 FROM device_measurement m JOIN device d USING(device_id)
 LEFT JOIN scada_point_mapping p USING(measurement_id) LEFT JOIN measurement_value v USING(measurement_id);
