"""Rolling-window feature primitives for realtime telemetry streams.

Phase 3 implementation should expand this module with concrete moving-window
statistics used to build model-ready feature vectors.
"""

from collections import deque
from statistics import mean


class RollingWindow:
    """Simple fixed-size numeric window used by higher-level feature builders."""

    def __init__(self, size: int) -> None:
        if size <= 1:
            raise ValueError("RollingWindow size must be > 1")
        self.size = size
        self.values: deque[float] = deque(maxlen=size)

    def push(self, value: float) -> None:
        self.values.append(float(value))

    def is_ready(self) -> bool:
        return len(self.values) == self.size

    def avg(self) -> float | None:
        if not self.values:
            return None
        return mean(self.values)
