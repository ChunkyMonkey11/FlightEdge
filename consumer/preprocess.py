"""Raw telemetry preprocessing entrypoint for Phase 3 feature engineering.

This module is intentionally lightweight right now and defines shared constants
and validation helpers so the rolling feature pipeline can build on a stable
input contract.
"""

import math
from typing import Any, Optional

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


def clamp(value: float, low: float, high: float) -> float:
    """Clamp numeric value within inclusive [low, high] bounds."""
    return max(low, min(value, high))


def sanitize_values(event: dict[str, Any]) -> dict[str, Any]:
    """Clamp physically unrealistic telemetry values to safe bounds."""
    sanitized = dict(event)

    sanitized["altitude_ft"] = max(0.0, sanitized["altitude_ft"])
    sanitized["airspeed_kts"] = max(0.0, sanitized["airspeed_kts"])
    sanitized["engine_rpm"] = max(0.0, sanitized["engine_rpm"])
    sanitized["vibration_g"] = max(0.0, sanitized["vibration_g"])

    sanitized["engine_temp_c"] = clamp(sanitized["engine_temp_c"], 0.0, 1200.0)
    sanitized["pitch_deg"] = clamp(sanitized["pitch_deg"], -90.0, 90.0)

    return sanitized


def validate_event(event: dict[str, Any]) -> bool:
    """Final safety check for nulls, NaNs, and expected numeric bounds."""
    for field in REQUIRED_FIELDS:
        if field not in event or event[field] is None:
            return False

    for field in NUMERIC_FIELDS:
        value = event[field]
        if not isinstance(value, (int, float)):
            return False
        if not math.isfinite(float(value)):
            return False

    if event["altitude_ft"] < 0:
        return False
    if event["airspeed_kts"] < 0:
        return False
    if event["engine_rpm"] < 0:
        return False
    if event["vibration_g"] < 0:
        return False
    if not (0 <= event["engine_temp_c"] <= 1200):
        return False
    if not (-90 <= event["pitch_deg"] <= 90):
        return False

    return True


def preprocess_event(raw_event: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Run validate -> coerce -> sanitize -> final-validate. Return None if dropped."""
    missing_fields = validate_required_fields(raw_event)
    if missing_fields:
        return None

    try:
        event = coerce_numeric_fields(raw_event)
    except (TypeError, ValueError):
        return None

    event = sanitize_values(event)
    if not validate_event(event):
        return None

    return event
