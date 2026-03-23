#!/usr/bin/env python3

import json
import sys
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError


class KafkaTelemetryProducer:
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        topic: str = "flightedge",
    ):
        self.topic = topic
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            acks="all",
            retries=5,
            key_serializer=lambda value: value.encode("utf-8"),
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def send_event(self, flight_id: str, event: dict[str, Any]) -> bool:
        try:
            future = self._producer.send(self.topic, key=flight_id, value=event)
            future.get(timeout=10)
            return True
        except KafkaError as err:
            print(f"Kafka send failed for flight_id={flight_id}: {err}", file=sys.stderr)
            return False

    def flush(self) -> None:
        self._producer.flush()

    def close(self) -> None:
        self._producer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.close()
