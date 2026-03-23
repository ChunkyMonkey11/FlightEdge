#!/usr/bin/env python3
"""Kafka CLI consumer for inspecting live FlightEdge telemetry events."""

import argparse
import json
from datetime import datetime, timezone

from kafka import KafkaConsumer


def build_consumer(
    bootstrap_servers: str,
    topic: str,
    group_id: str,
    from_beginning: bool,
) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers.split(","),
        group_id=group_id,
        auto_offset_reset="earliest" if from_beginning else "latest",
        enable_auto_commit=True,
        key_deserializer=lambda key: key.decode("utf-8") if key else "",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Consume flight telemetry from Kafka and print realtime events."
    )
    parser.add_argument(
        "--kafka-bootstrap-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers (comma-separated).",
    )
    parser.add_argument(
        "--kafka-topic",
        default="flightedge",
        help="Kafka topic name for telemetry events.",
    )
    parser.add_argument(
        "--group-id",
        default="flightedge-cli-consumer",
        help="Kafka consumer group id.",
    )
    parser.add_argument(
        "--from-beginning",
        action="store_true",
        help="Consume from earliest available offset.",
    )
    args = parser.parse_args()

    consumer = build_consumer(
        bootstrap_servers=args.kafka_bootstrap_servers,
        topic=args.kafka_topic,
        group_id=args.group_id,
        from_beginning=args.from_beginning,
    )

    print(
        f"Listening on topic '{args.kafka_topic}' via {args.kafka_bootstrap_servers}. "
        "Press Ctrl+C to stop."
    )

    try:
        for message in consumer:
            consumed_at = datetime.now(timezone.utc).isoformat()
            payload = json.dumps(message.value, sort_keys=True)
            print(
                f"[{consumed_at}] key={message.key} "
                f"partition={message.partition} offset={message.offset} value={payload}",
                flush=True,
            )
    except KeyboardInterrupt:
        print("\nConsumer stopped")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
