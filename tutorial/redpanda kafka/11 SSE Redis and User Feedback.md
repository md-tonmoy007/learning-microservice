---
tags: [redpanda, kafka, sse, redis, api-gateway]
file: services/api-gateway/app/api/research.py
---

# 11 SSE Redis and User Feedback

> Kafka is the backbone, but the user experience appears through SSE and Redis.

Related: [[12 Reliability Delivery and Idempotency]] · [[05 Server-Sent Events SSE]] · [[06 Redis Status Cache]] · [[Home]]

---

## Why Kafka Alone Is Not the User Interface

Kafka moves messages between services. Browsers do not consume Kafka topics directly in this repo. The gateway acts as the bridge.

Two user-facing paths exist:

- SSE for live progress
- Redis-backed polling for fast status checks

## SSE Flow

The endpoint `/research/{task_id}/events` creates a Kafka consumer over `ALL_PROGRESS_TOPICS`, filters by `task_id`, and yields SSE frames:

```python
yield f"data: {json.dumps(event)}\\n\\n"
```

That lets the browser watch the workflow unfold in near real time.

## Why the SSE Consumer Uses a Unique Group

Each connection gets its own `group_id`, something like:

```python
group_id=f"gateway-sse-{task_id}-{uuid4().hex}"
```

That means:

- each browser connection has its own offset history
- late connections can replay earlier progress events
- one client does not advance offsets for another

## Redis Complements Kafka

Kafka is great for event history and streaming. Redis is great for the latest known state.

The orchestrator writes snapshots like:

```text
task:{task_id}:status -> {"status": "running"}
```

The gateway can read that quickly for `/status` without hitting PostgreSQL.

## Why This Split Is Good Design

Kafka answers: "what happened over time?"

Redis answers: "what is the latest state right now?"

Those are different questions, and the repo treats them differently. That is a healthy architecture choice.
