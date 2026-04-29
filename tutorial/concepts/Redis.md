---
tags: [concept, redis, caching, key-value]
---

# Redis

> Redis is an in-memory key-value store used for fast data access — sub-millisecond reads that would take 5–20ms against PostgreSQL.

Used in: [[03 API Gateway Phase 3]] · [[04 Orchestrator Kafka Consumer]] · [[06 Redis Status Cache]]

---

## What Redis Is

Redis stores data in RAM, not on disk (though it can persist to disk for durability). Because there's no disk I/O, reads and writes are extremely fast — typically under 1 millisecond.

The simplest mental model: Redis is a Python `dict` that lives on the network and survives process restarts.

```
SET  task:abc-123:status  '{"status": "planned"}'
GET  task:abc-123:status   → '{"status": "planned"}'
```

---

## Why Redis Instead of PostgreSQL for Status

Both Redis and PostgreSQL can store task status. The difference is latency:

| Operation | PostgreSQL | Redis |
|-----------|-----------|-------|
| GET status | 5–20ms (connection pool + query parse + index lookup + network) | <1ms (direct memory read + network) |
| SET status | 5–20ms | <1ms |

For status polling (the user asks "is it done yet?" every few seconds), that difference matters. At 10 requests/second, PostgreSQL handles it fine. At 1,000 requests/second (many users), every millisecond of database time adds up.

Redis also keeps the PostgreSQL connection pool free for writes that actually need it (persisting final reports, creating task records).

> [!note]
> In Phase 3, Redis stores only `task:id:status` — transient status. The authoritative task record (with the full report, error messages, timestamps) lives in PostgreSQL. Redis is the fast cache; PostgreSQL is the source of truth.

---

## The redis-py Asyncio API

```python
import redis.asyncio as redis

# Connect
client = redis.from_url("redis://redis:6379", decode_responses=True)

# Write a value
await client.set("task:abc-123:status", '{"status": "planned"}')

# Read a value (returns None if key doesn't exist)
raw = await client.get("task:abc-123:status")

# Write with expiry (key auto-deletes after 24 hours)
await client.set("task:abc-123:status", '{"status": "done"}', ex=86400)

# Close
await client.aclose()
```

`decode_responses=True` means Redis returns Python `str` instead of `bytes` — you don't have to call `.decode()` on every value.

---

## Key Design

Redis keys are just strings. A common convention is `{namespace}:{id}:{field}`:

```
task:abc-123:status     → current status string
task:abc-123:result     → (future) cached final report
session:xyz-789         → (future) auth session
rate-limit:ip:1.2.3.4   → (future) rate limiter counter
```

Colons are just a convention — Redis treats the entire string as the key. But namespacing with colons lets Redis clients like RedisInsight show keys in a tree view.

---

## Redis as a Singleton in FastAPI

We initialize one `redis.asyncio.Redis` connection pool at startup and share it across the entire app:

```python
# app/core/redis_client.py
_redis: redis.Redis | None = None

async def start_redis(url: str) -> None:
    global _redis
    _redis = redis.from_url(url, decode_responses=True)

def get_redis() -> redis.Redis:
    return _redis
```

`redis.from_url()` creates a connection pool (not just one connection). Multiple concurrent requests can use it simultaneously — the pool handles multiplexing internally.

---

## When NOT to Use Redis

Redis stores data in RAM. If a Redis container restarts without persistence configured, all data is lost.

For this project that's acceptable — status is recoverable by reading PostgreSQL. But never store data in Redis that has no other source of truth (like the final research report). Always write to PostgreSQL first, then cache in Redis.

> [!warning]
> Redis is a cache, not a database. Always have a source of truth elsewhere. In this project that's PostgreSQL. If Redis dies, the orchestrator writes to PostgreSQL and the API can fall back to a DB query.
