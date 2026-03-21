#!/usr/bin/env python3

import argparse
import csv
import json
import math
import random
import sys
import time
from pathlib import Path


FIELDNAMES = [
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
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def phase_bounds():
    # Fraction of total run used by each flight phase.
    return [
        ("startup", 0.00, 0.10),
        ("takeoff", 0.10, 0.20),
        ("climb", 0.20, 0.45),
        ("cruise", 0.45, 0.75),
        ("descent", 0.75, 0.92),
        ("landing", 0.92, 1.01),
    ]


def get_phase(progress: float) -> str:
    for name, start, end in phase_bounds():
        if start <= progress < end:
            return name
    return "landing"


def phase_progress(progress: float, phase: str) -> float:
    for name, start, end in phase_bounds():
        if name == phase:
            width = max(0.0001, end - start)
            return clamp((progress - start) / width, 0.0, 1.0)
    return 0.0


def get_targets(phase: str, p: float) -> dict:
    # Targets are intentionally simple so the behavior is easy to read and tweak.
    if phase == "startup":
        return {
            "airspeed_kts": 0 + 8 * p,
            "engine_rpm": 700 + 500 * p,
            "pitch_deg": 0.0,
            "vertical_rate_fps": 0.0,
        }
    if phase == "takeoff":
        return {
            "airspeed_kts": 80 + 60 * p,
            "engine_rpm": 2200 + 400 * p,
            "pitch_deg": 8.0 + 2.0 * p,
            "vertical_rate_fps": 18.0 + 8.0 * p,
        }
    if phase == "climb":
        return {
            "airspeed_kts": 145 + 45 * p,
            "engine_rpm": 2400 - 100 * p,
            "pitch_deg": 7.0 - 2.0 * p,
            "vertical_rate_fps": 30.0 - 6.0 * p,
        }
    if phase == "cruise":
        return {
            "airspeed_kts": 230 + 10 * p,
            "engine_rpm": 2050 + 30 * p,
            "pitch_deg": 1.0,
            "vertical_rate_fps": 0.2,
        }
    if phase == "descent":
        return {
            "airspeed_kts": 220 - 70 * p,
            "engine_rpm": 1900 - 260 * p,
            "pitch_deg": -2.0 - 2.5 * p,
            "vertical_rate_fps": -22.0 - 14.0 * p,
        }
    # landing: distinct from descent with stronger deceleration and flare-like pitch recovery.
    return {
        "airspeed_kts": 150 - 115 * p,
        "engine_rpm": 1600 - 700 * p,
        "pitch_deg": -3.5 + 4.5 * p,
        "vertical_rate_fps": -70.0 + 56.0 * p,
    }


def choose_anomaly_window(num_rows: int, rng: random.Random):
    # Keep anomaly in the second half so "normal" behavior is visible first.
    if num_rows < 30:
        return (0, 0)
    center = rng.randint(num_rows // 2, max(num_rows // 2, num_rows - 10))
    width = rng.randint(8, 20)
    start = max(0, center - width // 2)
    end = min(num_rows, start + width)
    return (start, end)


def choose_altitude_drop_window(num_rows: int, rng: random.Random):
    # Restrict altitude-drop anomalies to climb/cruise portions.
    eligible = []
    for i in range(num_rows):
        progress = i / max(1, num_rows - 1)
        if get_phase(progress) in ("climb", "cruise"):
            eligible.append(i)

    if not eligible:
        return (0, 0)

    low = eligible[0]
    high = eligible[-1] + 1
    max_width = min(18, high - low)
    if max_width < 6:
        return (0, 0)
    width = rng.randint(6, max_width)
    start = rng.randint(low, high - width)
    end = start + width
    return (start, end)


def initial_state() -> dict:
    # Mutable state that evolves over time.
    return {
        "altitude_ft": 0.0,
        "airspeed_kts": 0.0,
        "engine_rpm": 700.0,
        "engine_temp_c": 45.0,
        "vibration_g": 0.03,
        "pitch_deg": 0.0,
    }


class TelemetrySimulator:
    def __init__(
        self,
        dt: float,
        seed: int,
        anomaly: str,
        cycle_rows: int,
        anomaly_probability: float,
    ):
        self.dt = dt
        self.anomaly = anomaly
        self.cycle_rows = cycle_rows
        self.anomaly_probability = anomaly_probability
        self.rng = random.Random(seed)
        self.state = initial_state()
        self.i = 0
        self.temp_drift_offset = 0.0
        self.anomaly_window = self._sample_cycle_anomaly()

    def _sample_cycle_anomaly(self):
        window = {
            "active": False,
            "type": "none",
            "start": 0,
            "end": 0,
            "duration": 0,
            "params": {},
        }

        if self.anomaly == "none":
            return window

        if self.rng.random() >= self.anomaly_probability:
            return window

        if self.anomaly == "altitude_drop":
            start, end = choose_altitude_drop_window(self.cycle_rows, self.rng)
        else:
            start, end = choose_anomaly_window(self.cycle_rows, self.rng)

        duration = max(0, end - start)
        if duration == 0:
            return window

        params = {}
        if self.anomaly == "vibration_spike":
            params = {
                "max_extra": self.rng.uniform(0.14, 0.24),
                "osc_amp": self.rng.uniform(0.08, 0.18),
                "osc_freq": self.rng.uniform(2.0, 4.5),
                "osc_phase": self.rng.uniform(0.0, math.tau),
                "ramp_frac": self.rng.uniform(0.18, 0.30),
                "decay_frac": self.rng.uniform(0.22, 0.36),
            }
        elif self.anomaly == "temp_drift":
            params = {
                "slope_per_step": self.rng.uniform(0.35, 0.75),
                "max_offset": self.rng.uniform(18.0, 42.0),
            }
        elif self.anomaly == "temp_spike":
            params = {
                "spike_mag": self.rng.uniform(24.0, 48.0),
                "decay_rate": self.rng.uniform(0.84, 0.93),
            }
        elif self.anomaly == "altitude_drop":
            params = {
                "drop_fps": self.rng.uniform(35.0, 80.0),
                "ramp_frac": self.rng.uniform(0.10, 0.22),
                "decay_frac": self.rng.uniform(0.18, 0.34),
            }

        window.update(
            {
                "active": True,
                "type": self.anomaly,
                "start": start,
                "end": end,
                "duration": duration,
                "params": params,
            }
        )
        return window

    def _window_progress(self, cycle_i: int) -> tuple[float, int]:
        start = self.anomaly_window["start"]
        duration = max(1, self.anomaly_window["duration"])
        step_idx = max(0, cycle_i - start)
        step_idx = min(step_idx, duration - 1)
        t = step_idx / max(1, duration - 1)
        return t, step_idx

    def _envelope(self, t: float, ramp_frac: float, decay_frac: float) -> float:
        ramp = max(0.05, min(0.45, ramp_frac))
        decay = max(0.05, min(0.45, decay_frac))
        if t < ramp:
            return t / ramp
        if t > 1.0 - decay:
            return max(0.0, (1.0 - t) / decay)
        return 1.0

    def _apply_anomaly(self, cycle_i: int, phase: str) -> None:
        anomaly_type = self.anomaly_window["type"]
        params = self.anomaly_window["params"]
        t, step_idx = self._window_progress(cycle_i)

        if anomaly_type == "vibration_spike":
            envelope = self._envelope(t, params["ramp_frac"], params["decay_frac"])
            oscillation = 1.0 + params["osc_amp"] * math.sin(
                math.tau * params["osc_freq"] * t + params["osc_phase"]
            )
            extra = max(0.0, params["max_extra"] * envelope * oscillation)
            self.state["vibration_g"] += extra
        elif anomaly_type == "temp_drift":
            self.temp_drift_offset = min(
                params["max_offset"],
                self.temp_drift_offset + params["slope_per_step"],
            )
            self.state["engine_temp_c"] += self.temp_drift_offset
        elif anomaly_type == "temp_spike":
            boost = params["spike_mag"] * (params["decay_rate"] ** step_idx)
            self.state["engine_temp_c"] += boost
        elif anomaly_type == "altitude_drop":
            if phase in ("climb", "cruise"):
                envelope = self._envelope(t, params["ramp_frac"], params["decay_frac"])
                self.state["altitude_ft"] -= params["drop_fps"] * envelope * self.dt

    def _start_new_cycle(self) -> None:
        self.state = initial_state()
        self.temp_drift_offset = 0.0
        self.anomaly_window = self._sample_cycle_anomaly()

    def next_event(self, timestamp_s: float) -> dict:
        cycle_i = self.i % self.cycle_rows
        if self.i > 0 and cycle_i == 0:
            self._start_new_cycle()

        progress = cycle_i / max(1, self.cycle_rows - 1)
        phase = get_phase(progress)
        phase_p = phase_progress(progress, phase)
        targets = get_targets(phase, phase_p)

        # Smoothly move each signal toward phase-dependent targets.
        self.state["airspeed_kts"] += 0.12 * (
            targets["airspeed_kts"] - self.state["airspeed_kts"]
        )
        self.state["engine_rpm"] += 0.18 * (
            targets["engine_rpm"] - self.state["engine_rpm"]
        )
        self.state["pitch_deg"] += 0.15 * (targets["pitch_deg"] - self.state["pitch_deg"])

        # altitude-airpeed-pitch coupling:
        # climb/descent rate responds to both target rate and current pitch/airspeed.
        pitch_factor = self.state["pitch_deg"] / 10.0
        speed_factor = clamp(self.state["airspeed_kts"] / 180.0, 0.0, 1.5)
        vertical_rate_fps = targets["vertical_rate_fps"] + 5.0 * pitch_factor * speed_factor
        self.state["altitude_ft"] += vertical_rate_fps * self.dt
        self.state["altitude_ft"] = max(0.0, self.state["altitude_ft"])

        # RPM -> temperature dependency (with lag so temp reacts gradually).
        temp_target = (
            60.0 + 0.055 * self.state["engine_rpm"] + 0.0018 * self.state["altitude_ft"]
        )
        self.state["engine_temp_c"] += 0.08 * (temp_target - self.state["engine_temp_c"])

        # RPM -> vibration dependency.
        vib_target = 0.03 + 0.00011 * self.state["engine_rpm"]
        self.state["vibration_g"] += 0.20 * (vib_target - self.state["vibration_g"])

        is_anomaly = (
            self.anomaly_window["active"]
            and self.anomaly_window["start"] <= cycle_i < self.anomaly_window["end"]
        )
        anomaly_type = self.anomaly_window["type"] if is_anomaly else "none"
        if is_anomaly:
            self._apply_anomaly(cycle_i, phase)

        # Small noise keeps data from being too perfect while staying smooth.
        self.state["altitude_ft"] += self.rng.gauss(0, 4.0)
        self.state["airspeed_kts"] += self.rng.gauss(0, 0.35)
        self.state["engine_rpm"] += self.rng.gauss(0, 2.5)
        self.state["engine_temp_c"] += self.rng.gauss(0, 0.18)
        self.state["vibration_g"] += self.rng.gauss(0, 0.0012)

        # Keep values in believable ranges.
        self.state["altitude_ft"] = clamp(self.state["altitude_ft"], 0.0, 42000.0)
        self.state["airspeed_kts"] = clamp(self.state["airspeed_kts"], 0.0, 420.0)
        self.state["engine_rpm"] = clamp(self.state["engine_rpm"], 600.0, 3000.0)
        self.state["engine_temp_c"] = clamp(self.state["engine_temp_c"], 20.0, 260.0)
        self.state["vibration_g"] = clamp(self.state["vibration_g"], 0.0, 2.0)

        row = {
            "timestamp_s": round(timestamp_s, 3),
            "phase": phase,
            "altitude_ft": round(self.state["altitude_ft"], 2),
            "airspeed_kts": round(self.state["airspeed_kts"], 2),
            "engine_rpm": round(self.state["engine_rpm"], 2),
            "engine_temp_c": round(self.state["engine_temp_c"], 2),
            "vibration_g": round(self.state["vibration_g"], 4),
            "pitch_deg": round(self.state["pitch_deg"], 2),
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type,
        }
        self.i += 1
        return row


def generate_rows(
    num_rows: int,
    dt: float,
    seed: int,
    anomaly: str,
    anomaly_probability: float,
):
    simulator = TelemetrySimulator(
        dt=dt,
        seed=seed,
        anomaly=anomaly,
        cycle_rows=num_rows,
        anomaly_probability=anomaly_probability,
    )
    for i in range(num_rows):
        yield simulator.next_event(timestamp_s=i * dt)


def write_csv(output_path: Path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(output_path: Path, rows):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def stream_events(simulator: TelemetrySimulator, event_interval_ms: int, max_events: int) -> int:
    emitted = 0
    interval_s = event_interval_ms / 1000.0

    while max_events <= 0 or emitted < max_events:
        event = simulator.next_event(timestamp_s=time.time())
        print(json.dumps(event), flush=True)
        emitted += 1
        time.sleep(interval_s)

    return emitted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate phase-based synthetic flight telemetry."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic_runs/telemetry_phase2.csv"),
        help="Output path.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=240,
        help="Number of rows to generate.",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=1.0,
        help="Sampling interval in seconds.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for repeatability.",
    )
    parser.add_argument(
        "--anomaly",
        choices=["none", "vibration_spike", "temp_drift", "temp_spike", "altitude_drop"],
        default="none",
        help="Optional anomaly to inject.",
    )
    parser.add_argument(
        "--anomaly-probability",
        type=float,
        default=1.0,
        help="Probability that a cycle contains an anomaly window (0.0-1.0).",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "jsonl"],
        default="csv",
        help="Output format (default: csv).",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Emit events continuously to stdout instead of writing a file.",
    )
    parser.add_argument(
        "--event-interval-ms",
        type=int,
        default=200,
        help="Delay between streamed events in milliseconds (100-500).",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="Stop after N streamed events (0 = run forever).",
    )

    args = parser.parse_args()

    if args.rows <= 0:
        raise ValueError("--rows must be > 0")
    if args.dt <= 0:
        raise ValueError("--dt must be > 0")
    if args.event_interval_ms < 100 or args.event_interval_ms > 500:
        raise ValueError("--event-interval-ms must be between 100 and 500")
    if args.max_events < 0:
        raise ValueError("--max-events must be >= 0")
    if args.anomaly_probability < 0.0 or args.anomaly_probability > 1.0:
        raise ValueError("--anomaly-probability must be between 0.0 and 1.0")

    if args.stream:
        simulator = TelemetrySimulator(
            dt=args.dt,
            seed=args.seed,
            anomaly=args.anomaly,
            cycle_rows=args.rows,
            anomaly_probability=args.anomaly_probability,
        )
        try:
            emitted = stream_events(
                simulator=simulator,
                event_interval_ms=args.event_interval_ms,
                max_events=args.max_events,
            )
            if args.max_events > 0:
                print(f"Stream completed after {emitted} events", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nStream stopped", file=sys.stderr)
        return

    rows = list(
        generate_rows(
            num_rows=args.rows,
            dt=args.dt,
            seed=args.seed,
            anomaly=args.anomaly,
            anomaly_probability=args.anomaly_probability,
        )
    )

    if args.format == "csv":
        write_csv(output_path=args.output, rows=rows)
    else:
        write_jsonl(output_path=args.output, rows=rows)

    print(f"Wrote {args.rows} rows to {args.output} ({args.format})")


if __name__ == "__main__":
    main()
