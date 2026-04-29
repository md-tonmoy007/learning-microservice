import json

from aiokafka import AIOKafkaProducer

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
