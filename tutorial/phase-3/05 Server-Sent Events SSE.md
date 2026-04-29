---
tags: [phase-3, sse, streaming, fastapi, kafka]
file: services/api-gateway/app/api/research.py
---

# 05 Server-Sent Events SSE

> The `GET /research/{task_id}/events` endpoint creates a persistent HTTP connection that pushes live workflow progress to the browser as Kafka events arrive.

Related: [[Server-Sent Events]] · [[Kafka and Redpanda]] · [[03 API Gateway Phase 3]] · [[Home]]

---

## The Code

```python
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
```

---

## Walkthrough

### What `StreamingResponse` does

`StreamingResponse(generator(), media_type="text/event-stream")` tells FastAPI:
- Send HTTP headers immediately (`200 OK`, `Content-Type: text/event-stream`)
- Keep the connection open
- Each time `generator()` yields a string, write that string to the socket immediately (no buffering)
- Close the connection when `generator()` returns

The browser receives a never-ending HTTP response body where each chunk is a formatted SSE event. The browser's `EventSource` API reads each chunk and fires `onmessage` for each event.

### The SSE text format

```
data: {"task_id": "abc", "event": "research.planned", ...}\n\n
data: {"task_id": "abc", "event": "research.search.completed", ...}\n\n
```

Two newlines (`\n\n`) mark the end of one event. The `data:` prefix is required by the SSE spec. Everything after `data:` and before `\n\n` is the event payload. The browser parses this and puts the content after `data: ` into `event.data`.

### The Kafka consumer lifecycle inside a generator

```python
async def generator():
    consumer = AIOKafkaConsumer(...)
    await consumer.start()      # ← TCP connection to Redpanda, subscribe to topics
    try:
        async for msg in consumer:
            ...
            yield f"data: ...\n\n"   # ← pushed to browser immediately
    finally:
        await consumer.stop()   # ← called even if exception or disconnect
```

**`consumer.start()`** — opens a TCP connection to Redpanda and fetches topic metadata (partition assignments). This happens once per SSE connection, not once globally.

**`consumer.stop()`** — in the `finally` block so it always runs, even if:
- The browser disconnects (causing the `async for` to break)
- An exception is thrown inside the loop
- The workflow ends normally (break on `completed`/`failed`)

A leaked consumer (one that's started but never stopped) holds a TCP connection to Redpanda and a consumer group registration. Over time, leaked consumers exhaust connection limits.

### Why the generator runs inside the response

When FastAPI calls `StreamingResponse(generator(), ...)`, the generator object is created but not yet run. FastAPI starts iterating it when the first response chunk is requested. The entire generator body runs inside the HTTP request's asyncio context — meaning `await request.is_disconnected()` works correctly.

### Disconnect detection

```python
if await request.is_disconnected():
    break
```

This checks whether the client closed the connection (browser tab closed, navigation, etc.). Without it, the generator would keep consuming Kafka messages for a task nobody is watching. The check happens on every Kafka message, so the latency between disconnect and cleanup is at most one Kafka poll interval (default 1 second).

### The termination condition

```python
if event["event"] in (RESEARCH_COMPLETED, RESEARCH_FAILED):
    break
```

When the orchestrator publishes `research.completed` or `research.failed`, the SSE stream ends. The generator returns, `consumer.stop()` is called in `finally`, and the HTTP connection closes. The browser's `EventSource` sees the connection close and may try to reconnect — the browser should check the last received event and close `EventSource` itself when it sees `completed`:

```javascript
source.onmessage = (e) => {
    const event = JSON.parse(e.data);
    if (event.event === 'research.completed') {
        source.close();
    }
};
```

### Filtering messages by task_id

```python
if event["task_id"] == task_id:
    yield f"data: {json.dumps(event)}\n\n"
```

The consumer subscribes to `ALL_PROGRESS_TOPICS`, which carry events from every research task running on the system. Without the filter, a user watching task `abc` would also receive events for task `xyz` if both are running simultaneously.

The filter is cheap (dictionary key lookup) and correct. A more sophisticated approach would be to use Kafka topic-per-task (e.g., `research.abc-123.planned`) but that creates a proliferation of topics and is not how Kafka is typically used.

---

## The Full SSE Flow — Example

```
Browser                         api-gateway                      Kafka
───────                         ───────────                      ─────
GET /research/abc/events  ──►   StreamingResponse starts
                                AIOKafkaConsumer starts
                                (group_id="gateway-sse-abc-<random>")
                                (offset=earliest, topics=[research.planned,...])

                                ← polls Kafka, no messages yet for "abc"

                                ← msg: research.planned (task_id="abc") arrives
◄── data: {"event":"research.planned",...} ──  yield "data: ...\n\n"

                                ← msg: research.search.completed (task_id="abc")
◄── data: {"event":"research.search.completed",...}

                                ← msg: research.summary.completed
◄── data: {"event":"research.summary.completed",...}

                                ← msg: research.critique.completed
◄── data: {"event":"research.critique.completed",...}

                                ← msg: research.completed
◄── data: {"event":"research.completed",...}
                                break (completed event received)
                                finally: consumer.stop()
Connection closed ──────────────────────────────────────────────────────
```

---

## What If the User Connects Late?

```
T=0  POST /research → task_id="abc"
T=1  research.planned published
T=3  research.search.completed published
T=10 User opens /research/abc/events  (connecting AFTER events were published)
     → consumer starts with auto_offset_reset="earliest"
     → reads research.planned from T=1      ← replayed
     → reads research.search.completed      ← replayed
T=15 research.completed arrives
     → SSE ends
```

`auto_offset_reset="earliest"` combined with a unique per-connection consumer group guarantees all historical events are replayed. A user connecting after the workflow finishes will receive a rapid burst of all events up to `completed`, then the stream closes.

> [!warning]
> Kafka retains messages for a configurable time period (default 7 days for most clusters, Redpanda defaults to 24 hours). If a user connects more than 24 hours after a task completed, historical events may be gone. For this learning project that's acceptable — tasks complete in minutes, not days.

> [!note]
> The SSE consumer subscribes to all progress topics in a single `AIOKafkaConsumer` call using `*ALL_PROGRESS_TOPICS`. This is more efficient than creating one consumer per topic, because Kafka consumers can subscribe to multiple topics in one connection.
