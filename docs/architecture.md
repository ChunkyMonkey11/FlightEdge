# Architecture (Current)

FlightEdge currently runs a synthetic telemetry pipeline with:

1. `producer/telemetry_generator.py` generating phase-based aircraft telemetry.
2. `producer/producer.py` publishing events to Kafka topic `flightedge`.
3. `consumer/consumer.py` consuming and printing events in realtime.

Phase 3 adds the missing preprocessing and feature extraction layer between
consumption and model inference.
