---
tags: [redpanda, kafka, local-dev, docker]
---

# 03 Redpanda for Local Development

> Redpanda gives us Kafka-compatible behavior without the setup weight that usually comes with local Kafka.

Related: [[08 Redpanda in docker-compose]] · [[Kafka and Redpanda]] · [[Home]]

---

## Why This Repo Uses Redpanda

Kafka is powerful, but local setup can feel heavier than the lesson you are actually trying to learn. Redpanda keeps the developer experience small:

- single container
- Kafka-compatible protocol
- fast startup
- no separate ZooKeeper

That makes it ideal for a teaching repo where the goal is understanding event-driven patterns, not babysitting infrastructure.

## Important Idea

The Python client code does not care that the broker is Redpanda instead of Kafka.

Code like this works the same way:

```python
producer = AIOKafkaProducer(bootstrap_servers="redpanda:9092")
consumer = AIOKafkaConsumer(
    "research.created",
    bootstrap_servers="redpanda:9092",
    group_id="orchestrator",
)
```

That is the practical win: we learn Kafka patterns locally and carry the same application behavior into production later.

## Why This Matters for Learning

Redpanda reduces the amount of "ops noise" between you and the architecture:

- you can focus on topics, groups, keys, and offsets
- you can inspect the event flow with fewer moving parts
- docker-compose stays easy to understand

## Repo Context

In this project, Redpanda is introduced in Phase 3 exactly when the architecture becomes asynchronous. That timing is intentional:

- Phase 1 teaches the workflow
- Phase 2 teaches service decomposition with gRPC
- Phase 3 teaches event-driven coordination with Redpanda and Redis

Redpanda is the enabling infrastructure for that third shift.
