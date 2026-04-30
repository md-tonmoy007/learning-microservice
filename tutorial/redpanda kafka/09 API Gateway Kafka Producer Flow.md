---
tags: [redpanda, kafka, api-gateway, producer, fastapi]
file: services/api-gateway/app/api/research.py
---

# 09 API Gateway Kafka Producer Flow

> The gateway is the front door of the system, but in Phase 3 it stops being the coordinator. It becomes a publisher.

Related: [[10 Orchestrator Kafka Consumer Flow]] · [[11 SSE Redis and User Feedback]] · [[Home]]

---

## The Submission Path

The gateway's `POST /research` endpoint does three essential things:

1. generate a `task_id`
2. build a standard event with `make_event(...)`
3. publish `research.created`

The shape is simple:

```python
task_id = str(uuid4())
event = make_event(task_id, RESEARCH_CREATED, "api-gateway", {"query": request.query})
await publish_event(RESEARCH_CREATED, event)
```

## Why the Gateway Generates `task_id`

This is one of the most important architectural decisions in the repo.

The user gets a stable ID immediately, before the orchestrator has even processed the message. That means the client can:

- poll status right away
- connect to `/research/{task_id}/events` right away
- treat the workflow as already created from the user's point of view

## What Changed from the HTTP Version

Before Kafka:

- the gateway called the orchestrator directly
- the orchestrator created the task
- the gateway waited for a response

After Kafka:

- the gateway creates the task identity
- the gateway publishes an event
- the orchestrator reacts later

That is the decoupling move in concrete form.

## Why This Endpoint Feels Fast

The endpoint returns `202 Accepted` with status `"pending"` rather than trying to complete the workflow inline. That is exactly the right HTTP shape for async work submitted to an event-driven backend.
