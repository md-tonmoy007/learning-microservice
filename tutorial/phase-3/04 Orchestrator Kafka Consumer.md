---
tags: [phase-3, kafka, orchestrator, langgraph, asyncio]
file: services/orchestrator/app/services/research.py
---

# 04 Orchestrator Kafka Consumer

> The orchestrator switches from receiving HTTP requests to consuming Kafka events. It also publishes progress events after each LangGraph node and writes status to Redis.

Related: [[Kafka and Redpanda]] · [[Redis]] · [[01 Event-Driven Architecture]] · [[LangGraph Phase 2]] · [[Home]]

---

## The Code

**Kafka module** (`app/core/kafka.py`):
```python
async def run_research_consumer(bootstrap_servers: str, on_event) -> None:
    consumer = AIOKafkaConsumer(
        "research.created",
        bootstrap_servers=bootstrap_servers,
        group_id="orchestrator",
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = json.loads(msg.value)
            task_id = event.get("task_id")
            query = event.get("payload", {}).get("query", "")
            asyncio.create_task(on_event(task_id, query))  # don't await — fire and forget
    finally:
        await consumer.stop()
```

**Updated lifespan** (`app/main.py`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer(settings.kafka_bootstrap_servers)
    await start_redis(settings.redis_url)
    consumer_task = asyncio.create_task(
        run_research_consumer(settings.kafka_bootstrap_servers, run_workflow)
    )
    yield
    consumer_task.cancel()
    await asyncio.gather(consumer_task, return_exceptions=True)
    await stop_producer()
    await stop_redis()
    await engine.dispose()
```

**Updated `run_workflow`** (`app/services/research.py`):
```python
_NODE_TOPIC: dict[str, str] = {
    "plan_research":    RESEARCH_PLANNED,
    "search_web":       RESEARCH_SEARCHED,
    "summarize_results": RESEARCH_SUMMARIZED,
    "critique_answer":  RESEARCH_CRITIQUED,
}

async def run_workflow(task_id: str, query: str) -> None:
    async with AsyncSessionFactory() as db:
        task = ResearchTask(id=task_id, user_query=query, status="running")
        db.add(task)
        try:
            await db.commit()
            await db.refresh(task)
        except Exception:
            await db.rollback()
            task = await get_task(db, task_id)
            task.status = "running"
            await db.commit()

        await _set_redis_status(task_id, "running")

        initial_state: ResearchState = { "task_id": task_id, "user_query": query, ... }
        current_state = dict(initial_state)

        try:
            async for output in research_graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in output.items():
                    current_state.update(node_output)
                    topic = _NODE_TOPIC.get(node_name)
                    if topic:
                        event = make_event(task_id, topic, "orchestrator",
                                          {"status": node_output.get("status", node_name)})
                        await publish_event(topic, event)
                        await _set_redis_status(task_id, node_output.get("status", node_name))

            task.status = current_state.get("status", "completed")
            task.final_report = current_state.get("final_report", "")
            task.iteration_count = current_state.get("iteration_count", 0)
            await db.commit()

            await _set_redis_status(task_id, "completed")
            await publish_event(RESEARCH_COMPLETED,
                make_event(task_id, RESEARCH_COMPLETED, "orchestrator"))

        except Exception as exc:
            task.status = "failed"
            task.error_message = str(exc)
            await db.commit()
            await _set_redis_status(task_id, "failed")
            await publish_event(RESEARCH_FAILED,
                make_event(task_id, RESEARCH_FAILED, "orchestrator", {"error": str(exc)}))
```

---

## Walkthrough

### From HTTP server to Kafka consumer

In Phase 2, the orchestrator was triggered by an HTTP POST:
```
gateway → HTTP POST /internal/research → orchestrator
```

In Phase 3, that endpoint is removed. The orchestrator is now triggered by a Kafka message:
```
[research.created topic] → orchestrator consumer → run_workflow()
```

The orchestrator still runs an HTTP server (for `GET /internal/research/{id}` detail queries), but it no longer accepts research submissions via HTTP.

### The consumer as a background task

```python
consumer_task = asyncio.create_task(
    run_research_consumer(settings.kafka_bootstrap_servers, run_workflow)
)
```

`run_research_consumer` is an infinite `async for` loop. It can't be `await`ed at startup (that would block the app from starting). Instead, it's wrapped in `asyncio.create_task()` which schedules it to run concurrently on the event loop.

When the app shuts down:
```python
consumer_task.cancel()
await asyncio.gather(consumer_task, return_exceptions=True)
```

`cancel()` injects a `CancelledError` into the task at its next `await`. `asyncio.gather(..., return_exceptions=True)` waits for the task to finish and absorbs the `CancelledError` (instead of propagating it). The `finally: await consumer.stop()` in `run_research_consumer` fires during cancellation, cleanly closing the Kafka consumer.

### `asyncio.create_task` inside the consumer — fire and forget

```python
async for msg in consumer:
    event = json.loads(msg.value)
    asyncio.create_task(on_event(task_id, query))  # ← not awaited
```

The consumer loop calls `asyncio.create_task(run_workflow(...))` instead of `await run_workflow(...)`. If we `await`ed it, the consumer would be blocked processing one workflow at a time and couldn't pick up the next `research.created` message until the workflow finished (potentially 30–120 seconds).

By using `create_task`, the workflow runs concurrently. The consumer loop immediately moves on to the next Kafka message, so multiple workflows can run in parallel.

### `ainvoke` → `astream` — what changes and why

**Phase 2:**
```python
final_state = await research_graph.ainvoke(initial_state)
# returns only when the entire workflow is done
```

**Phase 3:**
```python
async for output in research_graph.astream(initial_state, stream_mode="updates"):
    for node_name, node_output in output.items():
        # called once per node completion
        current_state.update(node_output)
        await publish_event(...)
```

`astream(stream_mode="updates")` yields a dict after each node completes. The dict contains only the fields that node changed — e.g., after `plan_research` runs, you get `{"research_plan": [...], "report_sections": [...], "status": "planned"}`.

We maintain `current_state` by merging each update in. By the end of the stream, `current_state` equals what `ainvoke` would have returned — but we got to inspect intermediate steps along the way.

### The `_NODE_TOPIC` mapping

```python
_NODE_TOPIC: dict[str, str] = {
    "plan_research":    RESEARCH_PLANNED,
    "search_web":       RESEARCH_SEARCHED,
    "summarize_results": RESEARCH_SUMMARIZED,
    "critique_answer":  RESEARCH_CRITIQUED,
}
```

This maps each LangGraph node name (the string passed to `graph.add_node()`) to the Kafka topic to publish after that node finishes. `generate_report` is not in this dict — it publishes `RESEARCH_COMPLETED` separately (handled after the `async for` loop ends).

This keeps the node functions (`app/graph/nodes.py`) unchanged. Nodes are still pure functions that take state and return a partial dict. The Kafka publishing logic lives entirely in `run_workflow`.

### task_id comes from the gateway — what changes in DB insert

In Phase 2, `run_workflow` received a `task_id` that already existed in the database (created by the orchestrator's HTTP endpoint). In Phase 3, `run_workflow` receives a `task_id` from the Kafka event that has never been inserted:

```python
task = ResearchTask(id=task_id, user_query=query, status="running")
db.add(task)
try:
    await db.commit()
except Exception:
    # Duplicate delivery — task already exists
    await db.rollback()
    task = await get_task(db, task_id)
    task.status = "running"
    await db.commit()
```

The try/except handles **duplicate delivery**: if the consumer crashes after committing the Kafka offset but before finishing the workflow, Kafka may redeliver the message. The second delivery would try to INSERT a task that already exists and hit a unique constraint. The except block catches this and updates the existing row instead.

---

## Workflow

```
App startup:
  lifespan()
    → start_producer("redpanda:9092")    → one AIOKafkaProducer for sending events
    → start_redis("redis://redis:6379")  → one Redis connection pool for status writes
    → asyncio.create_task(run_research_consumer(...))  → starts the infinite consumer loop

Consumer loop running (background):
  AIOKafkaConsumer("research.created", group_id="orchestrator", offset="earliest")
  async for msg in consumer:
    event = json.loads(msg.value)  → {"task_id": "abc", "event": "research.created", "payload": {"query": "..."}}
    asyncio.create_task(run_workflow("abc", "..."))  → fires off, consumer moves to next message

run_workflow("abc", "What is quantum computing?") [concurrently]:
  INSERT research_tasks (id="abc", query="...", status="running")
  Redis SET task:abc:status = '{"status": "running"}'

  astream(initial_state):
    ← plan_research node finishes → {"research_plan": [...], "status": "planned"}
      publish research.planned → {"task_id": "abc", "event": "research.planned", ...}
      Redis SET task:abc:status = '{"status": "planned"}'

    ← search_web node finishes → {"search_results": [...], "status": "searched"}
      publish research.search.completed
      Redis SET task:abc:status = '{"status": "searched"}'

    ← summarize_results node finishes
      publish research.summary.completed
    ← critique_answer node finishes
      publish research.critique.completed
    ← (loop?) → search_web again → ...
    ← generate_report node finishes

  publish research.completed
  Redis SET task:abc:status = '{"status": "completed"}'
  UPDATE research_tasks: final_report=..., status="completed", iteration_count=...
```

> [!tip]
> The `run_research_consumer` function takes `on_event` as a parameter (dependency injection). In tests, you can pass a mock function instead of `run_workflow` to verify that the consumer calls it correctly without running the full workflow.

> [!note]
> The `generate_report` node is not in `_NODE_TOPIC`. That's because `RESEARCH_COMPLETED` is published after the `astream` loop ends (not mid-loop). This way `completed` is published only after the final report has been saved to the database — the browser sees `completed` and immediately fetches the report from `GET /research/{id}`.
