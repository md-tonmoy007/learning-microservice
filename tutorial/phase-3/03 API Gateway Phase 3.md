---
tags: [phase-3, fastapi, kafka, sse, redis, gateway]
file: services/api-gateway/app/api/research.py
---

# 03 API Gateway Phase 3

> The gateway evolves from an HTTP proxy into a Kafka producer + SSE streamer. It publishes one event to kick off a workflow, then lets Kafka carry all further communication.

Related: [[Kafka and Redpanda]] · [[Server-Sent Events]] · [[Redis]] · [[01 Event-Driven Architecture]] · [[Home]]

---

## The Code

**New modules added:**

`services/api-gateway/app/core/kafka.py`:
```python
from aiokafka import AIOKafkaProducer
import json

_producer: AIOKafkaProducer | None = None

async def start_producer(bootstrap_servers: str) -> None:
    global _producer
    _producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
    await _producer.start()

async def stop_producer() -> None:
    if _producer:
        await _producer.stop()

async def publish_event(topic: str, event: dict) -> None:
    await _producer.send_and_wait(
        topic,
        value=json.dumps(event).encode(),
        key=event["task_id"].encode(),
    )
```

`services/api-gateway/app/core/redis_client.py`:
```python
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

**Updated lifespan** (`app/main.py`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_producer(settings.kafka_bootstrap_servers)
    await start_redis(settings.redis_url)
    yield
    await stop_producer()
    await stop_redis()
```

**Updated routes** (`app/api/research.py`):
```python
@router.post("", response_model=ResearchResponse, status_code=202)
async def submit_research(request: ResearchRequest):
    task_id = str(uuid4())
    event = make_event(task_id, RESEARCH_CREATED, "api-gateway", {"query": request.query})
    await publish_event(RESEARCH_CREATED, event)
    return ResearchResponse(
        task_id=task_id,
        status="pending",
        message=f"Research queued. Stream progress at /research/{task_id}/events",
    )


@router.get("/{task_id}/events")
async def stream_events(task_id: str, request: Request):
    async def generator():
        consumer = AIOKafkaConsumer(
            *ALL_PROGRESS_TOPICS,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=f"gateway-sse-{task_id}-{uuid4().hex}",
            auto_offset_reset="earliest",
        )
        await consumer.start()
        try:
            async for msg in consumer:
                if await request.is_disconnected():
                    break
                event = json.loads(msg.value)
                if event["task_id"] == task_id:
                    yield f"data: {json.dumps(event)}\n\n"
                    if event["event"] in (RESEARCH_COMPLETED, RESEARCH_FAILED):
                        break
        finally:
            await consumer.stop()
    return StreamingResponse(generator(), media_type="text/event-stream")


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

### What changed from Phase 2

**Phase 2 `POST /research`:**
```python
async def submit_research(request: ResearchRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(orchestrator_url, json={"query": request.query})
        resp.raise_for_status()
    return resp.json()
```

**Phase 3 `POST /research`:**
```python
async def submit_research(request: ResearchRequest):
    task_id = str(uuid4())
    event = make_event(task_id, RESEARCH_CREATED, "api-gateway", {"query": request.query})
    await publish_event(RESEARCH_CREATED, event)
    return ResearchResponse(task_id=task_id, status="pending", ...)
```

In Phase 2, the gateway blocked on an HTTP call and returned whatever the orchestrator said. In Phase 3, the gateway generates a UUID, publishes one Kafka message, and returns immediately — no HTTP call, no waiting.

### The producer singleton pattern

`_producer` is a module-level variable. There is one `AIOKafkaProducer` for the entire lifetime of the gateway process. It's initialized in `lifespan()` and stopped on shutdown.

Why not create a new producer per request? Producers maintain a TCP connection pool to the Kafka brokers and have internal batching buffers. Creating one per request is expensive and creates connection churn. A singleton is the correct pattern.

```python
# lifespan runs once at startup
await start_producer(settings.kafka_bootstrap_servers)
# every request calls this
await publish_event(RESEARCH_CREATED, event)  # reuses the singleton
```

### The SSE consumer — one per connection

Unlike the producer (one for the whole process), the SSE endpoint creates a **new Kafka consumer for each SSE connection**.

```python
group_id=f"gateway-sse-{task_id}-{uuid4().hex}"
```

The group ID is unique per connection (task_id + random hex). This is intentional:

1. **Independent reads** — each SSE connection reads from the beginning (`"earliest"`) and gets all events for that task. If two browsers connect to the same task's SSE stream, they both get all events independently.
2. **No group state collision** — if a unique group_id weren't used, two SSE connections would share a consumer group. Kafka would split the partitions between them, and each connection would only see some of the events.

The cost: each SSE connection consumes a Kafka connection and a TCP socket. For a small learning project with a handful of concurrent users, this is fine.

### `auto_offset_reset="earliest"` — why it matters for SSE

```python
consumer = AIOKafkaConsumer(
    *ALL_PROGRESS_TOPICS,
    auto_offset_reset="earliest",  # ← critical
    ...
)
```

A user might connect to the SSE endpoint after the workflow has already started. For example:

```
T=0   POST /research → task_id = "abc-123"
T=1   orchestrator publishes research.planned
T=2   orchestrator publishes research.search.completed
T=5   User opens the SSE stream at /research/abc-123/events
T=5   SSE consumer starts with auto_offset_reset="earliest"
      → reads research.planned from T=1  ← would be missed with "latest"
      → reads research.search.completed from T=2  ← would be missed with "latest"
T=8   orchestrator publishes research.completed
      → SSE consumer reads it → stream ends
```

With `"latest"`, the consumer starts at the current end of the topic and misses everything published before it connected. With `"earliest"`, it starts from the very beginning and replays all events.

### Filter by task_id — why it's necessary

The SSE consumer subscribes to topics that carry events from *all* research tasks, not just the current one. If two research tasks are running simultaneously, the consumer will receive events for both.

```python
if event["task_id"] == task_id:
    yield f"data: {json.dumps(event)}\n\n"
```

This filter ensures the SSE stream only forwards events that belong to the requested task.

### `GET /research/{id}/status` now reads Redis

Phase 2:
```python
# calls orchestrator over HTTP → orchestrator queries PostgreSQL
resp = await httpx.get(orchestrator_url + "/internal/research/{id}/status")
```

Phase 3:
```python
# reads directly from Redis — sub-millisecond, no network hop to orchestrator
raw = await redis.get(f"task:{task_id}:status")
```

The key `task:{task_id}:status` is written by the orchestrator at every status change. The gateway reads it directly, skipping the orchestrator entirely.

### `GET /research/{id}` still proxies to orchestrator

Status is cached in Redis. But the full task detail (final report, error message, timestamps) still lives in PostgreSQL. The `GET /research/{id}` endpoint still proxies to the orchestrator's DB query — Redis only caches the current status string.

---

## Workflow

```
Startup:
  lifespan() → start_producer("redpanda:9092") → TCP connection pool to Redpanda
             → start_redis("redis://redis:6379") → connection pool to Redis

POST /research {"query": "What is quantum computing?"}
  → task_id = uuid4() = "abc-123"
  → make_event("abc-123", "research.created", "api-gateway", {"query": "..."})
  → publish_event("research.created", event)
     → send_and_wait(topic="research.created", value=b'...json...', key=b"abc-123")
  → return 202 {"task_id": "abc-123", "status": "pending"}

GET /research/abc-123/events    (browser opens SSE stream)
  → new AIOKafkaConsumer(group_id="gateway-sse-abc-123-<random>", offset="earliest")
  → async for msg in consumer:
       if msg.task_id == "abc-123":
          yield "data: {event}\n\n"    → pushed to browser immediately
       if event == "completed": break
  → consumer.stop()

GET /research/abc-123/status
  → redis.get("task:abc-123:status")  → '{"status": "searched"}'
  → return {"task_id": "abc-123", "status": "searched"}
```

> [!tip]
> The producer is started in `lifespan()` before the app begins accepting requests. If `start_producer()` failed (Redpanda isn't running), the gateway would fail to start entirely — which is the correct behavior. A gateway that can't publish to Kafka can't do its job.

> [!warning]
> The SSE generator creates a Kafka consumer inside a closure. If the HTTP response is closed before `consumer.stop()` is called (e.g., an exception), the `finally` block ensures cleanup. Never skip the `finally: await consumer.stop()` — leaked consumers hold open TCP connections and waste Redpanda resources.
