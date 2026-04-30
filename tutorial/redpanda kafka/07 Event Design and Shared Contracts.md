---
tags: [redpanda, kafka, events, contracts, shared]
file: shared/kafka_events.py
---

# 07 Event Design and Shared Contracts

> A messaging system gets brittle fast if every service invents its own event names and payload shapes.

Related: [[08 Redpanda in docker-compose]] · [[02 Redpanda and Kafka Events]] · [[Home]]

---

## The Shared Contract File

This repo centralizes event names and the event factory in [`shared/kafka_events.py`](/d:/learning-microservice/shared/kafka_events.py:1).

That file defines:

- topic constants like `RESEARCH_CREATED`
- `ALL_PROGRESS_TOPICS`
- `make_event(...)`

This is a small design choice with a big payoff.

## Why Shared Constants Matter

If one service publishes `research.create` and another consumes `research.created`, nothing explodes loudly. The system just quietly fails to connect.

Shared constants reduce that risk. Topic naming becomes one source of truth instead of string duplication spread across the repo.

## The Standard Event Shape

All events follow this shape:

```json
{
  "task_id": "abc-123",
  "event": "research.created",
  "service": "api-gateway",
  "timestamp": "2026-04-30T10:00:00+00:00",
  "payload": {}
}
```

Each field earns its place:

- `task_id`: ties the message to one workflow
- `event`: repeats the event name for easier logging and debugging
- `service`: tells you who published it
- `timestamp`: gives you ordering clues and debugging context
- `payload`: carries event-specific data without changing the outer shape

## Why This Event Shape Works Well

It is stable enough for all services to understand and flexible enough to evolve. The envelope stays the same while `payload` changes by event type.

That balance is ideal for a teaching repo because the structure is easy to memorize and easy to inspect in logs.

## Design Principle

In distributed systems, consistency of message design matters more than cleverness. This repo makes the contract boring on purpose, and that is good engineering.
