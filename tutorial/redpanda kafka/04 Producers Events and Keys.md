---
tags: [redpanda, kafka, producer, event-design]
file: services/api-gateway/app/core/kafka.py
---

# 04 Producers Events and Keys

> Producers are where distributed workflows begin. A good producer does more than send bytes. It establishes event shape, routing, and ordering.

Related: [[05 Consumers Consumer Groups and Offsets]] · [[07 Event Design and Shared Contracts]] · [[Home]]

---

## Producer Basics

In this repo, both the gateway and orchestrator use the same producer pattern:

```python
await _producer.send_and_wait(
    topic,
    value=json.dumps(event).encode(),
    key=event["task_id"].encode(),
)
```

Three details matter here.

## `value` is bytes

Kafka messages are transported as bytes. We serialize the event dict to JSON first:

```python
json.dumps(event).encode()
```

That keeps the event easy to log and inspect.

## `send_and_wait` is intentional

`send_and_wait` waits for broker acknowledgement before returning. In this repo, that is the right default because research tasks are important workflow triggers, not best-effort telemetry.

If the gateway published `research.created` with fire-and-forget semantics and then crashed, task creation could silently disappear.

## `key=task_id` preserves task ordering

This repo uses `task_id` as the Kafka key. That means all events for the same research task land in the same partition.

That gives us ordering for one workflow:

```text
research.created
research.planned
research.search.completed
research.summary.completed
research.completed
```

Without the key, task events could be spread across partitions and ordering would become harder to reason about.

## Producer Responsibilities

A producer should answer four questions clearly:

1. Which topic is this event for?
2. What schema does the event follow?
3. What key should determine ordering and partition placement?
4. How strong should delivery guarantees be?

This repo keeps those answers simple and consistent, which is exactly what you want in a learning system.
