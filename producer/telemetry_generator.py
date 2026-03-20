#!/usr/bin/env python3

import argparse
import csv
import json
import random
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
        ("descent", 0.75, 1.01),
    ]


def get_phase(progress: float) -> str:
    for name, start, end in phase_bounds():
        if start <= progress < end:
            return name
    return "descent"


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
    # descent
    return {
        "airspeed_kts": 220 - 60 * p,
        "engine_rpm": 1900 - 250 * p,
        "pitch_deg": -2.0 - 2.5 * p,
        "vertical_rate_fps": -18.0 - 12.0 * p,
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
    def __init__(self, dt: float, seed: int, anomaly: str, cycle_rows: int):
        self.dt = dt
        self.anomaly = anomaly
        self.cycle_rows = cycle_rows
        self.rng = random.Random(seed)
        self.state = initial_state()
        self.i = 0
        self.temp_drift_offset = 0.0
        self.anomaly_start, self.anomaly_end = choose_anomaly_window(cycle_rows, self.rng)

    def _start_new_cycle(self) -> None:
        self.state = initial_state()
        self.temp_drift_offset = 0.0
        self.anomaly_start, self.anomaly_end = choose_anomaly_window(
            self.cycle_rows, self.rng
        )

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

        # Optional anomaly injection.
        if self.anomaly != "none" and self.anomaly_start <= cycle_i < self.anomaly_end:
            if self.anomaly == "vibration_spike":
                self.state["vibration_g"] += 0.18 + 0.05 * self.rng.random()
            elif self.anomaly == "temp_drift":
                self.temp_drift_offset += 0.6
                self.state["engine_temp_c"] += self.temp_drift_offset

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
        }
        self.i += 1
        return row


def generate_rows(num_rows: int, dt: float, seed: int, anomaly: str):
    simulator = TelemetrySimulator(dt=dt, seed=seed, anomaly=anomaly, cycle_rows=num_rows)
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
        choices=["none", "vibration_spike", "temp_drift"],
        default="none",
        help="Optional anomaly to inject.",
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

    if args.stream:
        simulator = TelemetrySimulator(
            dt=args.dt,
            seed=args.seed,
            anomaly=args.anomaly,
            cycle_rows=args.rows,
        )
        try:
            emitted = stream_events(
                simulator=simulator,
                event_interval_ms=args.event_interval_ms,
                max_events=args.max_events,
            )
            if args.max_events > 0:
                print(f"Stream completed after {emitted} events")
        except KeyboardInterrupt:
            print("\nStream stopped")
        return

    rows = list(
        generate_rows(
            num_rows=args.rows,
            dt=args.dt,
            seed=args.seed,
            anomaly=args.anomaly,
        )
    )

    if args.format == "csv":
        write_csv(output_path=args.output, rows=rows)
    else:
        write_jsonl(output_path=args.output, rows=rows)

    print(f"Wrote {args.rows} rows to {args.output} ({args.format})")


if __name__ == "__main__":
    main()
