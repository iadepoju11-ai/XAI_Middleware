"""
Demo consumer — prints credit decision events from the Kafka topic.
Run standalone: python kafka_consumer.py
Only used for demonstration; not part of the main application.
"""
import json
import logging

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def consume():
    if not config.KAFKA_ENABLED:
        logger.info("KAFKA_ENABLED=false — consumer not started.")
        return
    try:
        from kafka import KafkaConsumer
    except ImportError:
        logger.error("kafka-python not installed.")
        return

    consumer = KafkaConsumer(
        config.KAFKA_TOPIC,
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="compliance-monitor-demo",
    )
    logger.info("Listening on topic: %s", config.KAFKA_TOPIC)
    for message in consumer:
        logger.info("Decision received: %s", message.value)


if __name__ == "__main__":
    consume()
