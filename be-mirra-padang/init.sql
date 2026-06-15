-- Tabel Master Node
CREATE TABLE nodes (
    node_id SMALLINT PRIMARY KEY,
    label VARCHAR(50),
    location VARCHAR(100),
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE
);

-- Tabel Sesi Pengiriman Data
CREATE TABLE sessions (
    session_id BIGSERIAL PRIMARY KEY,
    node_id SMALLINT REFERENCES nodes(node_id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    sample_count SMALLINT DEFAULT 0,
    complete BOOLEAN DEFAULT FALSE,
    battery_v NUMERIC(4,2),
    sd_ok BOOLEAN,
    fft_done BOOLEAN DEFAULT FALSE
);

-- Hypertable untuk Data Mentah Vibrasi
CREATE TABLE vibration_raw (
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

-- Mengubah vibration_raw menjadi Hypertable TimescaleDB (partisi per 1 hari)
SELECT create_hypertable('vibration_raw', 'time', chunk_time_interval => INTERVAL '1 day');

-- Setup Compression (Opsional tapi disarankan sesuai spesifikasi)
ALTER TABLE vibration_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'node_id, session_id'
);
SELECT add_compression_policy('vibration_raw', INTERVAL '7 days');
