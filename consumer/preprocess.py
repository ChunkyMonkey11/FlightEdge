"""Raw telemetry preprocessing entrypoint for Phase 3 feature engineering.

This module is intentionally lightweight right now and defines shared constants
and validation helpers so the rolling feature pipeline can build on a stable
input contract.
"""

from typing import Any

REQUIRED_FIELDS = (
    "flight_id",
    "timestamp_s",
    "phase",
    "altitude_ft",
    "airspeed_kts",
    "engine_rpm",
    "engine_temp_c",
    "vibration_g",
    "pitch_deg",
    "is_anomaly",
    "anomaly_type",
)

NUMERIC_FIELDS = (
    "timestamp_s",
    "altitude_ft",
    "airspeed_kts",
    "engine_rpm",
    "engine_temp_c",
    "vibration_g",
    "pitch_deg",
)


def validate_required_fields(event: dict[str, Any]) -> list[str]:
    """Return a list of missing required telemetry keys."""
    return [field for field in REQUIRED_FIELDS if field not in event]


def coerce_numeric_fields(event: dict[str, Any]) -> dict[str, Any]:
    """Coerce known numeric fields to float where possible."""
    normalized = dict(event)
    for field in NUMERIC_FIELDS:
        value = normalized.get(field)
        if value is None:
            continue
        normalized[field] = float(value)
    return normalized
