---
tags: [redpanda, kafka, orchestrator, consumer, langgraph]
file: services/orchestrator/app/services/research.py
---

# 10 Orchestrator Kafka Consumer Flow

> The orchestrator is where Kafka events become workflow execution.

Related: [[11 SSE Redis and User Feedback]] · [[04 Orchestrator Kafka Consumer]] · [[Home]]

---

## Where Consumption Starts

The orchestrator creates a background task during app startup that runs the Kafka consumer loop.

That loop listens for `research.created` and launches:

```python
asyncio.create_task(on_event(task_id, query))
```

This is important because the consumer itself must keep reading. It should not block on one long LangGraph run.

## `run_workflow` as the Event Handler

Once the event is received, `run_workflow(task_id, query)` becomes the bridge between Kafka and LangGraph:

1. persist or reload the task record
2. set Redis status to `"running"`
3. stream LangGraph node updates with `astream(...)`
4. publish a Kafka progress event after each node
5. save the final report and publish `research.completed`

## Why `astream(...)` Matters

Earlier versions could have used `ainvoke(...)` and waited for one final state. Phase 3 switches to `astream(stream_mode="updates")` so the orchestrator can publish progress after each node finishes.

That is the direct link between LangGraph internals and user-visible progress streaming.

## Duplicate Delivery Awareness

The code also handles the case where a task row already exists. That is a first step toward idempotency:

- insert if new
- reload and continue if already present

This matters because messaging systems can redeliver.

## The Big Picture

The orchestrator is not just a consumer. It is a translator:

- Kafka event in
- workflow state machine runs
- Kafka progress events out

That translation layer is the heart of Phase 3.
