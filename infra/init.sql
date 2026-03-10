CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS telemetry (
    time            TIMESTAMPTZ     NOT NULL,
    apid            INTEGER         NOT NULL,
    data_field      BYTEA           NOT NULL,
    fecf            BIGINT          NOT NULL,
    rssi            SMALLINT,
    temperature     REAL
);

SELECT create_hypertable(
    'telemetry', 'time',
    if_not_exists => TRUE
);

SELECT add_retention_policy('telemetry', INTERVAL '30 days', if_not_exists => TRUE);
