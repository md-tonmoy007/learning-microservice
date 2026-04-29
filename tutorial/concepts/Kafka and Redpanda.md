---
tags: [concept, kafka, redpanda, messaging, event-driven]
---

# Kafka and Redpanda

> Kafka is a distributed commit log that lets services communicate by publishing and consuming events, without knowing anything about each other.

Used in: [[01 Event-Driven Architecture]] · [[02 Redpanda and Kafka Events]] · [[03 API Gateway Phase 3]] · [[04 Orchestrator Kafka Consumer]]

---

## The Core Idea

In a normal HTTP call, Service A calls Service B directly. A has to know B's address, wait for B to respond, and fail if B is down.

In Kafka, Service A publishes a message to a **topic**. Service B (and C and D) read from that topic on their own schedule. A and B never talk to each other — they only talk to Kafka.

```
Phase 2 (HTTP):
  api-gateway  ───HTTP POST──►  orchestrator
  (tightly coupled — gateway blocks waiting for orchestrator)

Phase 3 (Kafka):
  api-gateway  ──publish──►  [research.created]  ◄──consume──  orchestrator
  (decoupled — gateway returns immediately, orchestrator picks up when ready)
```

---

## Core Vocabulary

**Topic** — a named channel. `research.created`, `research.planned`, etc. Think of it as a named queue, but one that persists messages and lets multiple consumers read the same message independently.

**Producer** — a service that writes (publishes) messages to a topic.

**Consumer** — a service that reads (consumes) messages from a topic.

**Consumer Group** — a named group of consumers. Kafka tracks how far each group has read (the "offset"). If you have one consumer group `orchestrator`, it reads `research.created` and Kafka remembers which messages it has already processed. A second consumer group `audit-logger` can read the same `research.created` topic from the beginning without affecting the orchestrator's position.

**Offset** — the position of a consumer within a topic's message log. Kafka stores this per consumer group. `auto_offset_reset="earliest"` means: if this consumer group has never read this topic before, start from the very first message ever published.

**Partition** — a topic can be split into multiple partitions for parallelism. For this project, one partition per topic is sufficient. The `key` on a message (we use `task_id`) determines which partition it lands on — messages with the same key always go to the same partition, which guarantees ordering per task.

---

## The aiokafka API

### Producer

```python
from aiokafka import AIOKafkaProducer
import json

producer = AIOKafkaProducer(bootstrap_servers="redpanda:9092")
await producer.start()

# Publish a message
await producer.send_and_wait(
    topic="research.created",
    value=json.dumps(event).encode(),  # Kafka messages are bytes
    key=event["task_id"].encode(),      # used to determine partition
)

await producer.stop()
```

`send_and_wait` blocks until Kafka acknowledges the message. `send` (without `_and_wait`) fires and returns a future — the message may not be delivered if the process crashes. For reliability, prefer `send_and_wait`.

### Consumer

```python
from aiokafka import AIOKafkaConsumer

consumer = AIOKafkaConsumer(
    "research.created",               # one or more topic names
    bootstrap_servers="redpanda:9092",
    group_id="orchestrator",          # consumer group name
    auto_offset_reset="earliest",     # start from beginning if no saved offset
)
await consumer.start()

async for msg in consumer:
    event = json.loads(msg.value)
    print(event["task_id"])

await consumer.stop()
```

The `async for` loop blocks until a message arrives. It never returns — it runs forever. This is why we run the consumer in a background `asyncio.Task`.

---

## Why Redpanda Instead of Kafka

Kafka requires a JVM, ZooKeeper (or complex KRaft configuration), and careful JVM tuning. For a local development environment, it's too heavy.

Redpanda is a Kafka-compatible broker written in C++. It:
- Ships as a single Docker image with no dependencies
- Uses the same Kafka wire protocol — `aiokafka` connects to it identically
- Starts in under a second
- Needs no ZooKeeper

The code you write against Redpanda is 100% portable to real Kafka. When this project goes to production (Phase 6), changing `bootstrap_servers` from `redpanda:9092` to `kafka-cluster:9092` is the only code change needed.

---

## Message Ordering and the `key` Parameter

When you publish with a key, Kafka routes all messages with the same key to the same partition. This means all events for a given `task_id` arrive at the consumer in the order they were published.

```python
await producer.send_and_wait(
    topic,
    value=json.dumps(event).encode(),
    key=event["task_id"].encode(),  # ← guarantees ordering per task
)
```

If you publish without a key, messages go to partitions round-robin and ordering is not guaranteed across partitions.

---

## Consumer Groups — Why Each Service Has Its Own

A consumer group represents one independent reader of a topic. Kafka tracks that group's read position separately.

```
Topic: research.created
Messages: [task-1, task-2, task-3]

Consumer group "orchestrator":  read position = 3 (all consumed)
Consumer group "audit-logger":  read position = 1 (2 remaining)
```

If two services shared the same consumer group, Kafka would split the partitions between them — each service would only see half the messages. That's the load-balancing use case (scaling one service horizontally). For our architecture, each service is an independent subscriber and needs its own group.

---

## The Offset Reset Question

`auto_offset_reset` controls what happens when a consumer group reads a topic for the first time:

| Value | Meaning |
|-------|---------|
| `"earliest"` | Start from the very first message ever published |
| `"latest"` | Skip all existing messages, only read new ones |

The orchestrator uses `"earliest"` for `research.created` so it can process tasks that were published before it started (e.g., after a restart).

SSE consumers (per-browser-connection) also use `"earliest"` so a user connecting after the workflow started still sees all past events.

> [!tip]
> Once a consumer group has read messages and committed its offset, `auto_offset_reset` no longer matters — Kafka uses the saved offset. The setting only applies to the very first read by a new group.
