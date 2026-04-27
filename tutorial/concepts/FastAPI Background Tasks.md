---
tags: [concept, fastapi, background-tasks, async]
---

# FastAPI Background Tasks

> How BackgroundTasks works, why it needs its own DB session, and when to use it vs a task queue.

Used in: [[LangGraph Orchestrator]]

---

## What BackgroundTasks Does

FastAPI's `BackgroundTasks` runs a function **after the HTTP response is sent**, in the same process and event loop.

```python
from fastapi import BackgroundTasks

@router.post("")
async def create_research(request: ..., background_tasks: BackgroundTasks):
    task = await create_task(db, request.query)
    background_tasks.add_task(run_workflow, task.id, request.query)
    return {"task_id": task.id}  # ← response sent here
    # run_workflow() starts AFTER this return
```

The user gets the `task_id` response immediately. The workflow runs concurrently in the same event loop.

---

## The DB Session Lifecycle Problem

This is the most common gotcha with BackgroundTasks and databases.

### What happens to the DB session

FastAPI's `get_db` dependency creates a session that lives **for the duration of the HTTP request**:

```python
async def get_db():
    async with AsyncSessionFactory() as session:
        yield session
    # ← session closes here, after the request handler returns
```

When your route handler returns and sends the response, the session closes. But `BackgroundTasks` run **after** the response. If the background task tries to use the request's session, it gets a `SessionClosed` error.

### The wrong way (broken)

```python
# DO NOT DO THIS
background_tasks.add_task(run_workflow, task.id, request.query, db)
# db is the request session — it will be closed when run_workflow runs
```

### The right way

The background task creates its own session using `AsyncSessionFactory` directly:

```python
# services/research.py
async def run_workflow(task_id: str, query: str) -> None:
    async with AsyncSessionFactory() as db:  # fresh session
        task = await get_task(db, task_id)
        # ... do work
        await db.commit()
```

And the route handler does **not** pass `db`:
```python
background_tasks.add_task(run_workflow, task.id, request.query)
# no db arg — run_workflow creates its own
```

---

## Comparison: BackgroundTasks vs Celery vs Kafka

| Feature                  | BackgroundTasks           | Celery                    | Kafka task                |
|-------------------------|--------------------------|---------------------------|---------------------------|
| Setup                   | Zero — built into FastAPI | Redis/RabbitMQ broker      | Kafka + consumer          |
| Persistence             | No — lost on crash       | Yes (broker stores tasks)  | Yes (log-based)           |
| Retry on failure        | No                       | Yes (built-in)             | Yes (re-consume)          |
| Scaling                 | Same process only        | Multiple workers           | Multiple consumer replicas|
| Learning complexity     | Low                      | Medium                     | High                      |
| Phase in this project   | Phase 1                  | Not used                   | Phase 3                   |

### When BackgroundTasks is enough

- Tasks are fast enough to complete before the process restarts
- Failure is acceptable (learning project)
- You want zero additional infrastructure

### When to move to Kafka (Phase 3)

- Task progress needs to be streamed to the user in real time
- Tasks need to survive service restarts
- Multiple services need to react to the same event

---

## The Event Loop Implication

FastAPI runs in a single async event loop (per worker). BackgroundTasks run as coroutines in that same loop. This means:

- LangGraph's `ainvoke` (which is fully async) works perfectly — it yields control to the loop between LLM calls
- A blocking call in a background task (e.g., `time.sleep`) would freeze the whole server
- If you need CPU-intensive work, use `asyncio.to_thread()` or a separate process

> [!warning] Not fault-tolerant
> If the orchestrator crashes mid-workflow, the background task is lost. The `research_tasks` row stays at `status="running"` forever. Phase 3's Kafka approach solves this because the `research.created` event can be re-consumed.
