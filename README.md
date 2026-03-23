# FlightEdge

FlightEdge is an edge-ML sandbox for telemetry anomaly detection workflows.

The repository currently focuses on model experimentation, inference benchmarking, and dashboard work.

---

# Project Structure

```text
flightedge/
│
├── README.md
├── requirements.txt
│
├── model/
│   ├── train.py
│   ├── infer.py
│   ├── export_onnx.py
│   ├── quantize.py
│   └── artifacts/
│
├── benchmarks/
│   ├── benchmark_fp32.py
│   ├── benchmark_quantized.py
│   └── results/
│
├── dashboard/
│   ├── app.py
│   └── components/
│
├── data/
│   ├── synthetic_runs/
│   └── telemetry_schema.json
│
└── docs/
    ├── architecture.md
    ├── telemetry_schema.md
    ├── roadmap.md
    └── plans/
```

---

# Kafka/Docker Progress Log

## Done So Far

1. Created [`docker-compose.yml`](/Users/revant/FlightEdge/docker-compose.yml) with a single Kafka service:
   - image: `apache/kafka:latest`
   - container name: `kafka`
   - port mapping: `9092:9092`
   - KRaft-related environment variables configured

2. Started Kafka container:

```bash
docker compose up -d
```

3. Verified running containers:

```bash
docker ps
```

4. Created topic `flightdata`:

```bash
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --topic flightdata \
  --partitions 1 \
  --replication-factor 1
```

5. Verified topic exists:

```bash
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

6. Ran manual Kafka messaging test successfully:
   - started console producer on topic `flightdata`
   - started console consumer on topic `flightdata` with `--from-beginning`
   - sent test messages and confirmed they were received

## Next Step

Begin Phase 2 follow-up work: route consumed telemetry into persistence and/or downstream processing.

## Next Work Item (Before/After Push)

Build on the validated stream:
- add consumer-side persistence target (file/DB) for replayable records
- connect consumer output to feature windows and anomaly pipeline


Notes:
1. Ill allow codex to decide this
2. We will use kafka topic name flightedge, and port number 9092 for our consumer and producer
3.flight_id is fine so each flight stays ordered in a partition

4.yeah we can add a publish mode path. 
clarification: is this adding an argument for argparse? 

## Phase 2 Milestone Validation (March 23, 2026)

- Milestone status: Complete for core realtime pipeline objective.
- Topic and broker used: `flightedge` on `localhost:9092`.
- Keying strategy: `flight_id` used as Kafka message key to preserve per-flight ordering.

Validated commands:

```bash
python consumer/consumer.py \
  --kafka-bootstrap-servers localhost:9092 \
  --kafka-topic flightedge
```

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

Validation result:
- Produced `20` events and consumed `20` events end-to-end in realtime.

Current limitation (expected for this milestone):
- Consumer is terminal-print only; persistence and downstream processing are not yet implemented.

---

# Kafka Realtime Runbook (`flightedge`)

## 1) Start Kafka

```bash
docker compose up -d
```

## 2) Create topic (safe if already exists)

```bash
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --if-not-exists \
  --topic flightedge \
  --partitions 1 \
  --replication-factor 1
```

## 3) Verify topic list

```bash
docker exec -it kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

## 4) Install Python dependency

```bash
pip install -r requirements.txt
```

## 5) Start consumer (terminal 1)

```bash
python consumer/consumer.py \
  --kafka-bootstrap-servers localhost:9092 \
  --kafka-topic flightedge
```

## 6) Stream producer (terminal 2)

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

## Optional: stream and write file at the same time

```bash
python producer/telemetry_generator.py \
  --mode both \
  --kafka-bootstrap-servers localhost:9092 \
  --kafka-topic flightedge \
  --flight-id FLIGHT-001 \
  --max-events 50 \
  --output data/synthetic_runs/telemetry_phase2.csv \
  --format csv
```
