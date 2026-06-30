-- ============================================================
-- MIRRA PADANG - Database Schema
-- Jalankan sekali saat setup VPS baru:
--   psql "$DATABASE_URL" -f init.sql
-- File ini idempotent (aman dijalankan ulang) berkat IF NOT EXISTS
-- dan ON CONFLICT DO NOTHING pada seed data.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Tabel Master Node
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS nodes (
    node_id SMALLINT PRIMARY KEY,
    label VARCHAR(50),
    location VARCHAR(100),
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);

-- ------------------------------------------------------------
-- 2. Tabel Sesi Pengiriman Data
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    session_id BIGSERIAL PRIMARY KEY,
    node_id SMALLINT REFERENCES nodes(node_id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    sample_count SMALLINT DEFAULT 0,
    complete BOOLEAN DEFAULT FALSE,
    battery_v NUMERIC(4,2),
    sd_ok BOOLEAN,
    fft_done BOOLEAN DEFAULT FALSE
);

-- ------------------------------------------------------------
-- 3. Hypertable: Data Mentah Vibrasi
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vibration_raw (
    time TIMESTAMPTZ NOT NULL,
    session_id BIGINT REFERENCES sessions(session_id),
    node_id SMALLINT,
    ax REAL,
    ay REAL,
    az REAL,
    gx REAL,
    gy REAL,
    gz REAL
);

SELECT create_hypertable(
    'vibration_raw',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

ALTER TABLE vibration_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'node_id, session_id'
);

SELECT add_compression_policy(
    'vibration_raw',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ------------------------------------------------------------
-- 4. Hypertable: Data Cuaca (weather_readings)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_readings (
    time TIMESTAMPTZ NOT NULL,
    gateway_id TEXT,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    rainfall DOUBLE PRECISION,
    wind_speed DOUBLE PRECISION
);

SELECT create_hypertable(
    'weather_readings',
    'time',
    if_not_exists => TRUE
);

ALTER TABLE weather_readings SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'gateway_id'
);

SELECT add_compression_policy(
    'weather_readings',
    compress_after => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ------------------------------------------------------------
-- 5. Hypertable: Hasil FFT (fft_results)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fft_results (
    time TIMESTAMPTZ NOT NULL,
    session_id BIGINT REFERENCES sessions(session_id),
    node_id SMALLINT REFERENCES nodes(node_id),
    axis TEXT NOT NULL,
    frequencies DOUBLE PRECISION[],
    magnitudes DOUBLE PRECISION[],
    dominant_hz DOUBLE PRECISION,
    peak_magnitude DOUBLE PRECISION
);

SELECT create_hypertable(
    'fft_results',
    'time',
    if_not_exists => TRUE
);

ALTER TABLE fft_results SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'node_id, session_id'
);

SELECT add_compression_policy(
    'fft_results',
    INTERVAL '7 days',
    if_not_exists => TRUE
);

-- ------------------------------------------------------------
-- 6. Seed Master Node
-- Dashboard tidak akan menampilkan apa pun apabila tabel
-- nodes kosong. ON CONFLICT DO NOTHING -> aman dijalankan ulang.
-- ------------------------------------------------------------
INSERT INTO nodes (node_id, label, location)
VALUES
    (1, 'Node 1', 'Bentang 1'),
    (2, 'Node 2', 'Bentang 2'),
    (3, 'Node 3', 'Bentang 3'),
    (4, 'Node 4', 'Bentang 4')
ON CONFLICT (node_id) DO NOTHING;

-- ============================================================
-- Selesai. Verifikasi cepat:
--   \dt
--   SELECT * FROM nodes;
-- ============================================================
