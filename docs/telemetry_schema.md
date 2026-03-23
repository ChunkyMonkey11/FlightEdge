# Telemetry Schema Notes

Source of truth for telemetry fields is:

- `data/telemetry_schema.json`

The stream includes core flight dynamics (altitude, airspeed, pitch), engine
signals (rpm, temperature, vibration), and labels (`is_anomaly`,
`anomaly_type`) used for supervised experiments.
