---
tags: [redpanda, kafka, consumer, offsets, consumer-groups]
file: services/orchestrator/app/core/kafka.py
---

# 05 Consumers Consumer Groups and Offsets

> If producers start the story, consumers decide how the story gets read.

Related: [[06 Topics Partitions and Ordering]] · [[10 Orchestrator Kafka Consumer Flow]] · [[Home]]

---

## The Consumer Loop

The orchestrator consumer is the cleanest example in this repo:

```python
consumer = AIOKafkaConsumer(
    "research.created",
    bootstrap_servers=bootstrap_servers,
    group_id="orchestrator",
    auto_offset_reset="earliest",
)

async for msg in consumer:
    event = json.loads(msg.value)
    asyncio.create_task(on_event(task_id, query))
```

This is a long-running background process, not a one-off read.

## Why `group_id` Matters

The group ID tells Kafka which logical reader this consumer belongs to.

For the orchestrator:

- `group_id="orchestrator"` means all orchestrator instances share one consumer identity
- if you scale orchestrator horizontally, Kafka can distribute work across them

For SSE:

- each browser connection gets a unique group ID
- each connection keeps its own offset history

That difference is very important.

## Why `auto_offset_reset="earliest"` Matters

This setting only matters when a consumer group has no committed offset yet.

`"earliest"` means:

- start reading from the beginning of the topic
- do not skip older messages

That helps with cases like:

- orchestrator starts after some tasks were already published
- a browser connects after workflow events have already begun

## Offsets Are State

Kafka is not stateless from the consumer point of view. The offset is durable reading progress.

That is one of the big mental shifts:

- queues often feel like consume-and-disappear
- Kafka feels like read-from-a-log-with-position

The repo uses that model directly when it replays progress history for late SSE subscribers.

## Consumer Design Questions

When reading Kafka code, ask:

1. What topic is being consumed?
2. What group ID is being used?
3. Where should the consumer begin if it has no prior offset?
4. Should work be awaited inline or launched concurrently?

That checklist will explain most consumer behavior you see here.
