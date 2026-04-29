---
tags: [phase-3, redis, caching, status, fastapi]
file: services/orchestrator/app/core/redis_client.py
---

# 06 Redis Status Cache

> The orchestrator writes task status to Redis after every workflow step. The api-gateway reads it directly — no HTTP round-trip to the orchestrator, no database query.

Related: [[Redis]] · [[01 Event-Driven Architecture]] · [[04 Orchestrator Kafka Consumer]] · [[Home]]

---

## The Code

**Redis client module** (same pattern in both services):
```python
# services/orchestrator/app/core/redis_client.py
# services/api-gateway/app/core/redis_client.py
import redis.asyncio as redis_lib

_redis: redis_lib.Redis | None = None

async def start_redis(redis_url: str) -> None:
    global _redis
    _redis = redis_lib.from_url(redis_url, decode_responses=True)

async def stop_redis() -> None:
    if _redis:
        await _redis.aclose()

def get_redis() -> redis_lib.Redis:
    return _redis
```

**Orchestrator writes status** (in `services/research.py`):
```python
async def _set_redis_status(task_id: str, status: str) -> None:
    redis = get_redis()
    await redis.set(f"task:{task_id}:status", json.dumps({"status": status}))
```

Called at every stage:
```python
await _set_redis_status(task_id, "running")    # before workflow starts
await _set_redis_status(task_id, "planned")    # after plan_research
await _set_redis_status(task_id, "searched")   # after search_web
await _set_redis_status(task_id, "summarized") # after summarize_results
await _set_redis_status(task_id, "critiqued")  # after critique_answer
await _set_redis_status(task_id, "completed")  # after generate_report
await _set_redis_status(task_id, "failed")     # on any exception
```

**api-gateway reads status**:
```python
@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_research_status(task_id: str):
    redis = get_redis()
    raw = await redis.get(f"task:{task_id}:status")
    if raw is None:
        raise HTTPException(status_code=404, detail="Task not found")
    data = json.loads(raw)
    return TaskStatusResponse(task_id=task_id, status=data["status"])
```

---

## Walkthrough

### The key structure

```
task:{task_id}:status  →  '{"status": "searched"}'
```

The value is JSON even though it currently only has one field. This is intentional: later we might add `updated_at`, `iteration_count`, or `progress_percentage` without changing the key or the code that reads it.

```python
# Future evolution — same key, richer value
await redis.set(
    f"task:{task_id}:status",
    json.dumps({
        "status": "searched",
        "updated_at": "2026-04-29T10:31:00Z",
        "iteration": 1,
    })
)
```

### The singleton pattern — why it works

Both the orchestrator and the api-gateway have their own `redis_client.py` with the same code. They each maintain their own connection pool to the same Redis server:

```
orchestrator → connection pool → Redis server ← connection pool ← api-gateway
```

Redis is single-threaded and serializes all commands. When the orchestrator writes `SET task:abc:status "planned"`, the api-gateway's next `GET task:abc:status` will see the new value. There's no cache invalidation to manage — every write to Redis is immediately visible to all readers.

### `decode_responses=True` — why we need it

Redis stores and returns bytes by default. `decode_responses=True` makes the client automatically decode bytes to Python strings using UTF-8:

```python
# Without decode_responses=True:
raw = await redis.get("task:abc:status")
# raw is b'{"status": "searched"}' (bytes)
data = json.loads(raw.decode())  # manual decode needed

# With decode_responses=True:
raw = await redis.get("task:abc:status")
# raw is '{"status": "searched"}' (str) — no decode needed
data = json.loads(raw)
```

Since all our values are JSON strings, `decode_responses=True` eliminates boilerplate `.decode()` calls everywhere.

### Why `None` means "not found" (not "pending")

When the api-gateway receives `GET /research/{id}/status` and Redis returns `None`, it means Redis has no record for that key. This has two possible causes:

1. The task genuinely doesn't exist — wrong `task_id`
2. The task exists but the orchestrator hasn't started yet — race condition between publishing `research.created` and the orchestrator consuming it and writing to Redis

The api-gateway returns 404 in both cases. From the user's perspective: if you get a 404 immediately after submitting, retry in a moment. This is a common pattern in eventually consistent systems.

An alternative: the api-gateway could pre-write `'{"status": "pending"}'` to Redis before publishing the Kafka event:
```python
task_id = str(uuid4())
await redis.set(f"task:{task_id}:status", json.dumps({"status": "pending"}))
await publish_event(RESEARCH_CREATED, event)
```

This would eliminate the race condition. It's not done in Phase 3 to keep the gateway's role minimal (publish and return). Phase 4 could add this.

### Redis vs PostgreSQL — when to use which

| Scenario | Use |
|----------|-----|
| Current status of a running task | Redis — fast, sub-millisecond |
| Full task detail with final report | PostgreSQL — authoritative, durable |
| Task history / audit log | PostgreSQL — persistent, queryable |
| Rate limiting, session data | Redis — fast writes, optional TTL |

The rule of thumb: Redis for hot, frequently-read data that's okay to lose on a crash. PostgreSQL for data that must survive crashes and is queried in complex ways.

### Cleanup — where does Redis data go?

Currently, `task:{id}:status` keys are never deleted. They live in Redis until Redis restarts (data is lost on container restart without persistence configured) or until a TTL expires.

For Phase 3, this is acceptable. In production, you'd add a TTL:
```python
await redis.set(f"task:{task_id}:status", json.dumps(...), ex=86400)  # expire after 24 hours
```

This prevents Redis from filling up with stale task status from months ago.

---

## The Write Path

```
run_workflow() [orchestrator]:
  Task starts
    → redis.set("task:abc:status", '{"status": "running"}')

  plan_research node finishes
    → redis.set("task:abc:status", '{"status": "planned"}')

  search_web node finishes
    → redis.set("task:abc:status", '{"status": "searched"}')

  summarize_results node finishes
    → redis.set("task:abc:status", '{"status": "summarized"}')

  critique_answer node finishes
    → redis.set("task:abc:status", '{"status": "critiqued"}')

  generate_report node finishes
    → (no immediate write — report is saved to DB first)
  
  DB commit succeeds
    → redis.set("task:abc:status", '{"status": "completed"}')
```

---

## The Read Path

```
Browser: GET /research/abc/status

api-gateway:
  redis = get_redis()               ← module-level singleton
  raw = await redis.get("task:abc:status")   ← sub-millisecond
  data = json.loads(raw)            ← parse JSON
  return {"task_id": "abc", "status": "searched"}
```

Total time: ~1ms (Redis network round-trip). Compare to Phase 2: ~15ms (HTTP to orchestrator + SQLAlchemy query + PostgreSQL index lookup + return).

> [!tip]
> Redis is sometimes called a "sidecar cache" — it lives alongside PostgreSQL, holds a hot subset of the data, and takes the read load off the database. When Redis is available, reads hit Redis. If Redis goes down, you can fall back to PostgreSQL (not implemented in Phase 3, but easy to add: wrap the Redis read in try/except and fall back to a DB query).
