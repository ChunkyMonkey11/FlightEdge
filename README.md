# FlightEdge

A real-time edge telemetry anomaly detection pipeline designed to simulate machine learning systems running on constrained hardware such as NVIDIA Jetson or Thor.

FlightEdge focuses on the engineering challenges that arise when models must operate locally on streaming data rather than in cloud environments.

---

# Overview

FlightEdge is a systems-focused machine learning project that simulates how real-time telemetry from aircraft sensors might be processed on edge hardware.

Instead of training a model and stopping there, this project focuses on the full pipeline:

- generating streaming telemetry
- transporting events through a message broker
- transforming telemetry into features
- running anomaly detection in real time
- benchmarking inference latency
- experimenting with model optimization techniques such as quantization

The system simulates aircraft telemetry data flowing through a streaming architecture and evaluates how efficiently an anomaly detection model can operate under conditions similar to embedded deployment.

This project is intended to build intuition for real-world ML systems where:

- compute resources are limited  
- latency requirements are strict  
- data arrives continuously rather than in batches  

---

# Motivation

Most machine learning tutorials stop at training a model inside a notebook.

Real systems are harder.

Production ML systems must solve problems like:

- ingesting streaming data
- managing real-time pipelines
- performing inference under hardware constraints
- monitoring system latency
- optimizing models for deployment

FlightEdge focuses on the **engineering layer around ML**, which is often the hardest part of building practical systems.

---

# Project Goals

FlightEdge aims to replicate a simplified version of real edge ML workflows.

Core objectives:

1. Generate simulated aircraft telemetry in real time  
2. Stream telemetry through Kafka topics  
3. Consume and preprocess telemetry streams  
4. Convert raw telemetry into rolling feature windows  
5. Run anomaly detection models on the stream  
6. Surface anomalies through logs and dashboards  
7. Measure inference latency and throughput  
8. Compare baseline and optimized inference paths  

This project is designed as preparation for work involving:

- edge AI systems  
- streaming data pipelines  
- telemetry processing  
- embedded ML deployment  

---

# System Architecture

```text
Telemetry Generator
        ↓
Kafka Producer
        ↓
Kafka Topic
        ↓
Consumer / Preprocessing Service
        ↓
Feature Windowing
        ↓
Anomaly Detection Model
        ↓
Alerts / Logs / Dashboard
        ↓
Benchmarking & Optimization

flightedge/
│
├── README.md
├── docker-compose.yml
├── requirements.txt
│
├── producer/
│   ├── telemetry_generator.py
│   ├── schema.py
│   └── producer.py
│
├── consumer/
│   ├── consumer.py
│   ├── preprocess.py
│   ├── feature_windows.py
│   └── alerts.py
│
├── model/
│   ├── train.py
│   ├── infer.py
│   ├── export_onnx.py
│   ├── quantize.py
│   └── artifacts/
│
├── dashboard/
│   ├── app.py
│   └── components/
│
├── benchmarks/
│   ├── benchmark_fp32.py
│   ├── benchmark_quantized.py
│   └── results/
│
├── data/
│   ├── synthetic_runs/
│   └── telemetry_schema.json
│
└── docs/
    ├── architecture.md
    ├── telemetry_schema.md
    └── roadmap.md


---

# Telemetry Generator Examples

Generate normal telemetry (no anomalies):

```bash
python3 producer/telemetry_generator.py \
  --rows 240 \
  --seed 42 \
  --anomaly none \
  --format csv \
  --output data/synthetic_runs/telemetry_normal.csv
```

Generate a reproducible temp spike run:

```bash
python3 producer/telemetry_generator.py \
  --rows 240 \
  --seed 42 \
  --anomaly temp_spike \
  --anomaly-probability 1.0 \
  --format jsonl \
  --output data/synthetic_runs/telemetry_temp_spike.jsonl
```

Generate altitude drop anomalies during climb/cruise:

```bash
python3 producer/telemetry_generator.py \
  --rows 240 \
  --seed 42 \
  --anomaly altitude_drop \
  --anomaly-probability 1.0 \
  --format csv \
  --output data/synthetic_runs/telemetry_altitude_drop.csv
```

Notes:
- Set `--anomaly-probability 0.0` for fully normal runs even when anomaly type is set.
- Same `--seed` + same args produces identical anomaly timing and shape.

---

# Anomaly Validation Checks

Run the built-in validation suite:

```bash
python3 producer/validate_anomalies.py --rows 240 --seed 42
```

This checks:
- temp spike shape (sharp increase with decay)
- altitude drop behavior (unexpected descent in climb/cruise)
- realism bounds for all key sensors
- anomaly metadata contract (`is_anomaly`, `anomaly_type`)
- anomaly probability frequency behavior

