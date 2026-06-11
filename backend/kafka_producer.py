import json
import logging

import config

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    try:
        from kafka import KafkaProducer
        _producer = KafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        logger.info("Kafka producer connected to %s", config.KAFKA_BOOTSTRAP_SERVERS)
    except Exception as exc:
        logger.warning("Kafka producer unavailable: %s — continuing without streaming", exc)
        _producer = None
    return _producer


def publish_decision(decision_payload: dict) -> None:
    if not config.KAFKA_ENABLED:
        return
    producer = _get_producer()
    if producer is None:
        return
    try:
        producer.send(config.KAFKA_TOPIC, value=decision_payload)
        producer.flush(timeout=2)
    except Exception as exc:
        logger.warning("Failed to publish to Kafka: %s", exc)
