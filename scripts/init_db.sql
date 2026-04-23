-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create hypertable for tank measurements (time-series data)
CREATE TABLE IF NOT EXISTS tank_measurements (
    time TIMESTAMPTZ NOT NULL,
    tank_id INTEGER NOT NULL,
    volume_m3 REAL NOT NULL,
    level_percent REAL NOT NULL,
    temperature_celsius REAL,
    pressure_atm REAL
);

SELECT create_hypertable('tank_measurements', 'time');

-- Create continuous aggregate for 24-hour statistics
CREATE MATERIALIZED VIEW IF NOT EXISTS tank_stats_24h
WITH (timescaledb.continuous) AS
SELECT
    tank_id,
    time_bucket('1 hour', time) AS bucket,
    AVG(volume_m3) AS avg_volume,
    MAX(volume_m3) AS max_volume,
    MIN(volume_m3) AS min_volume,
    AVG(temperature_celsius) AS avg_temperature
FROM tank_measurements
GROUP BY tank_id, bucket;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_tank_measurements_tank_id ON tank_measurements (tank_id, time DESC);

-- Audit log table (will be used by application)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INTEGER,
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on audit_log for faster filtering
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log (entity_type, entity_id);
