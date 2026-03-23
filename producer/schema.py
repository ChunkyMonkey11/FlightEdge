"""Helpers for working with the telemetry JSON schema definition."""

import json
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path("data/telemetry_schema.json")


def load_telemetry_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    """Load the telemetry schema JSON into a Python dictionary."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
