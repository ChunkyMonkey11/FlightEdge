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

Wire Python telemetry generation into Kafka publishing.

## Next Work Item (Before/After Push)

Set up and wire the telemetry generator to a producer/consumer pipeline:
- producer publishes generated telemetry events to Kafka topic `flightdata`
- consumer reads events from `flightdata` and logs/validates end-to-end flow
