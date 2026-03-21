#!/usr/bin/env python3

import argparse
from typing import Iterable

from telemetry_generator import TelemetrySimulator, generate_rows


RANGES = {
    "altitude_ft": (0.0, 42000.0),
    "airspeed_kts": (0.0, 420.0),
    "engine_rpm": (600.0, 3000.0),
    "engine_temp_c": (20.0, 260.0),
    "vibration_g": (0.0, 2.0),
}

ALL_ANOMALIES = ["none", "vibration_spike", "temp_drift", "temp_spike", "altitude_drop"]


def _generate(rows: int, dt: float, seed: int, anomaly: str, anomaly_probability: float):
    return list(
        generate_rows(
            num_rows=rows,
            dt=dt,
            seed=seed,
            anomaly=anomaly,
            anomaly_probability=anomaly_probability,
        )
    )


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _anomaly_indices(rows: Iterable[dict]) -> list[int]:
    return [i for i, row in enumerate(rows) if row["is_anomaly"]]


def validate_metadata(rows: int, dt: float, seed: int) -> None:
    normal = _generate(rows, dt, seed, anomaly="none", anomaly_probability=1.0)
    _assert(
        all((row["is_anomaly"] is False and row["anomaly_type"] == "none") for row in normal),
        "Metadata failed: normal run must emit is_anomaly=false and anomaly_type='none'.",
    )

    anom = _generate(rows, dt, seed, anomaly="temp_drift", anomaly_probability=1.0)
    _assert(any(row["is_anomaly"] for row in anom), "Metadata failed: expected anomaly rows.")
    _assert(
        all((row["anomaly_type"] == "temp_drift") for row in anom if row["is_anomaly"]),
        "Metadata failed: anomaly_type mismatch on anomaly rows.",
    )


def validate_temp_spike(rows: int, dt: float, seed: int, min_spike_delta: float) -> None:
    baseline = _generate(rows, dt, seed, anomaly="none", anomaly_probability=1.0)
    spike = _generate(rows, dt, seed, anomaly="temp_spike", anomaly_probability=1.0)
    idxs = _anomaly_indices(spike)
    _assert(idxs, "Temp spike failed: no anomaly rows present.")

    deltas = [spike[i]["engine_temp_c"] - baseline[i]["engine_temp_c"] for i in idxs]
    max_delta = max(deltas)
    _assert(
        max_delta >= min_spike_delta,
        f"Temp spike failed: max delta {max_delta:.2f}C < {min_spike_delta:.2f}C.",
    )

    # Temporal structure check:
    # 1) rapid onset within first steps, and
    # 2) cooling trend after peak.
    onset_jump = deltas[min(2, len(deltas) - 1)] - deltas[0]
    _assert(
        onset_jump >= 8.0,
        "Temp spike failed: onset is not sufficiently sharp.",
    )

    peak_i = max(range(len(deltas)), key=lambda i: deltas[i])
    post_peak_drop = deltas[peak_i] - deltas[-1]
    _assert(
        post_peak_drop >= 6.0,
        "Temp spike failed: expected cooling trend after peak.",
    )


def validate_altitude_drop(rows: int, dt: float, seed: int, min_drop_ft: float) -> None:
    baseline = _generate(rows, dt, seed, anomaly="none", anomaly_probability=1.0)
    drop = _generate(rows, dt, seed, anomaly="altitude_drop", anomaly_probability=1.0)
    idxs = _anomaly_indices(drop)
    _assert(idxs, "Altitude drop failed: no anomaly rows present.")

    phases = {drop[i]["phase"] for i in idxs}
    _assert(
        phases.issubset({"climb", "cruise"}),
        f"Altitude drop failed: anomaly phases not restricted to climb/cruise: {sorted(phases)}",
    )

    # Distinguishable drop against baseline trajectory.
    delta_alt = [drop[i]["altitude_ft"] - baseline[i]["altitude_ft"] for i in idxs]
    worst_drop = min(delta_alt)
    _assert(
        worst_drop <= -min_drop_ft,
        f"Altitude drop failed: min baseline-relative drop {worst_drop:.2f}ft "
        f"is not <= -{min_drop_ft:.2f}ft.",
    )

    # Ensure at least one local descent during anomaly rows.
    has_descent = False
    for i in idxs:
        if i > 0 and drop[i]["altitude_ft"] < drop[i - 1]["altitude_ft"]:
            has_descent = True
            break
    _assert(has_descent, "Altitude drop failed: no negative altitude step detected.")


def validate_realism(rows: int, dt: float, seed: int) -> None:
    for anomaly in ALL_ANOMALIES:
        series = _generate(rows, dt, seed, anomaly=anomaly, anomaly_probability=1.0)
        for row in series:
            for key, (low, high) in RANGES.items():
                value = row[key]
                _assert(
                    low <= value <= high,
                    f"Realism failed: {key} out of range for {anomaly}: {value}",
                )


def validate_frequency(cycle_rows: int, dt: float, seed: int) -> None:
    cycles = 200
    tolerance = 0.08
    for p in (0.0, 0.5, 1.0):
        sim = TelemetrySimulator(
            dt=dt,
            seed=seed,
            anomaly="temp_spike",
            cycle_rows=cycle_rows,
            anomaly_probability=p,
        )
        anomalous_cycles = 0
        for c in range(cycles):
            any_anomaly = False
            for i in range(cycle_rows):
                row = sim.next_event(timestamp_s=float(c * cycle_rows + i))
                any_anomaly = any_anomaly or row["is_anomaly"]
            if any_anomaly:
                anomalous_cycles += 1
        observed = anomalous_cycles / cycles
        _assert(
            abs(observed - p) <= tolerance,
            f"Frequency failed: p={p:.2f}, observed={observed:.3f}, tolerance={tolerance:.2f}",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate anomaly behavior realism and metadata contract."
    )
    parser.add_argument("--rows", type=int, default=240, help="Rows for single-run checks.")
    parser.add_argument("--dt", type=float, default=1.0, help="Sampling interval in seconds.")
    parser.add_argument("--seed", type=int, default=42, help="Validation seed.")
    parser.add_argument(
        "--min-temp-spike-delta-c",
        type=float,
        default=15.0,
        help="Minimum baseline-relative engine temp spike delta required.",
    )
    parser.add_argument(
        "--min-altitude-drop-ft",
        type=float,
        default=120.0,
        help="Minimum baseline-relative altitude drop required during anomaly window.",
    )
    args = parser.parse_args()

    validate_metadata(args.rows, args.dt, args.seed)
    validate_temp_spike(args.rows, args.dt, args.seed, args.min_temp_spike_delta_c)
    validate_altitude_drop(args.rows, args.dt, args.seed, args.min_altitude_drop_ft)
    validate_realism(args.rows, args.dt, args.seed)
    validate_frequency(cycle_rows=max(80, args.rows), dt=args.dt, seed=args.seed)

    print("Validation passed:")
    print("- temp spike behavior")
    print("- altitude drop behavior")
    print("- realism bounds")
    print("- metadata contract")
    print("- anomaly frequency checks")


if __name__ == "__main__":
    main()
