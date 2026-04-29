import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None


async def start_producer(bootstrap_servers: str) -> None:
    global _producer
    _producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
    await _producer.start()


async def stop_producer() -> None:
    if _producer:
        await _producer.stop()


async def publish_event(topic: str, event: dict) -> None:
    await _producer.send_and_wait(
        topic,
        value=json.dumps(event).encode(),
        key=event["task_id"].encode(),
    )


async def run_research_consumer(bootstrap_servers: str, on_event) -> None:
    """Long-running consumer that triggers on_event(task_id, query) for each research.created message."""
    consumer = AIOKafkaConsumer(
        "research.created",
        bootstrap_servers=bootstrap_servers,
        group_id="orchestrator",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    logger.info("Orchestrator Kafka consumer started")
    try:
        async for msg in consumer:
            event = json.loads(msg.value)
            task_id = event.get("task_id")
            query = event.get("payload", {}).get("query", "")
            logger.info("Received research.created for task %s", task_id)
            asyncio.create_task(on_event(task_id, query))
    finally:
        await consumer.stop()
