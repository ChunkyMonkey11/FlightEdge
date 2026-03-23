# FlightEdge

FlightEdge is a telemetry-to-anomaly-detection sandbox for realtime edge ML workflows.

## Current Status (March 23, 2026)

The Kafka telemetry stream is already operational on:

- Topic: `flightedge`
- Broker: `localhost:9092`
- Message key: `flight_id` (preserves per-flight ordering)

## Next Milestone: Phase 3 (Active)

Phase 3 focuses on transforming raw telemetry streams into model-ready features.

### Objective

Build a preprocessing and feature extraction layer that converts live telemetry
data into rolling-window statistics and derived signals for anomaly detection.

### Scope

1. Build a preprocessing pipeline for incoming telemetry events.
2. Implement rolling windows over time-series telemetry.
3. Compute derived features (moving averages, rates of change, variance, z-scores).
4. Normalize or scale features where appropriate.
5. Ensure the feature pipeline runs continuously in realtime.
6. Validate model input vectors.
7. Document feature definitions and processing decisions.

### Deliverables

1. `consumer/preprocess.py` for raw telemetry transformation.
2. `consumer/feature_windows.py` for rolling feature computation.
3. Validated, model-ready feature vectors.
4. Documentation for feature definitions and flow.

## Repository Layout

```text
FlightEdge/
├── producer/       # Telemetry generation and Kafka publishing
├── consumer/       # Kafka consumption + upcoming feature pipeline
├── data/           # Schema and generated telemetry samples
├── model/          # Model training/inference/export placeholders
├── benchmarks/     # Benchmark placeholders
├── dashboard/      # UI placeholder
├── docs/           # Lightweight architecture and roadmap notes
├── docker-compose.yml
└── requirements.txt
```

## Quick Start (Realtime Stream)

1. Start Kafka:

```bash
docker compose up -d
```

2. Install Python dependency:

```bash
pip install -r requirements.txt
```

3. Start consumer:

```bash
python consumer/consumer.py \
  --kafka-bootstrap-servers localhost:9092 \
  --kafka-topic flightedge
```

4. Stream telemetry:

```bash
python producer/telemetry_generator.py \
  --mode kafka \
  --kafka-bootstrap-servers localhost:9092 \
  --kafka-topic flightedge \
  --flight-id FLIGHT-001 \
  --rows 240 \
  --event-interval-ms 200 \
  --max-events 20
```
