---
tags: [concept, sse, streaming, fastapi, http]
---

# Server-Sent Events

> SSE is a browser-standard HTTP mechanism for a server to push a stream of events to a client over a single long-lived connection.

Used in: [[03 API Gateway Phase 3]] · [[05 Server-Sent Events SSE]]

---

## The Problem SSE Solves

A normal HTTP request has one response. Once the server sends it, the connection closes. For progress updates ("the planner finished", "search returned 12 results"), you need either:

1. **Polling** — client asks every N seconds "are you done yet?" — wastes requests, adds latency
2. **WebSocket** — full bidirectional streaming — both client and server can send messages at any time
3. **SSE** — server streams events to the client over one HTTP connection, one direction only

For research progress updates, SSE is the right fit: the server has things to say, the client just listens.

---

## How SSE Works

SSE is a plain HTTP response with `Content-Type: text/event-stream`. The connection stays open. The server writes lines in a simple text format:

```
data: {"task_id": "abc", "event": "research.planned"}\n\n
data: {"task_id": "abc", "event": "research.search.completed"}\n\n
data: {"task_id": "abc", "event": "research.completed"}\n\n
```

Rules:
- Each event is prefixed with `data: `
- Events end with **two newlines** (`\n\n`) — one empty line signals "this event is done"
- The server can also send `: comment` lines (keepalive pings that clients ignore)
- The browser's `EventSource` API handles reconnection automatically

---

## SSE vs WebSocket

| Concern | SSE | WebSocket |
|---------|-----|-----------|
| Direction | Server → client only | Bidirectional |
| Protocol | Plain HTTP/1.1 | Upgraded connection (ws://) |
| Browser support | Native `EventSource` API | `WebSocket` API |
| Reconnection | Automatic | Manual |
| Proxy/firewall | Works everywhere HTTP works | Sometimes blocked |
| Use case | Notifications, feeds, progress | Chat, games, real-time editing |

For workflow progress (server pushes, client reads), SSE is simpler than WebSocket. You don't need the extra complexity of bidirectional communication.

---

## FastAPI Implementation — StreamingResponse

FastAPI's `StreamingResponse` takes an async generator and streams its output to the client:

```python
from fastapi.responses import StreamingResponse

@router.get("/{task_id}/events")
async def stream_events(task_id: str):
    async def generator():
        yield "data: {\"event\": \"started\"}\n\n"
        await asyncio.sleep(1)
        yield "data: {\"event\": \"done\"}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
```

The generator runs while the client is connected. Each `yield` immediately flushes one chunk to the client. When the generator returns (or the client disconnects), the response ends.

### Detecting Disconnection

FastAPI gives you access to the `Request` object so you can check if the client disconnected:

```python
async def stream_events(task_id: str, request: Request):
    async def generator():
        while True:
            if await request.is_disconnected():
                break
            yield "data: keepalive\n\n"
```

Without this check, the generator keeps running and consuming resources even after the browser tab closes.

---

## The Keepalive Pattern

SSE connections time out if no data is sent for a while (proxies, load balancers, and browsers have different timeouts — commonly 30–60 seconds). Send a comment line as a keepalive:

```python
try:
    event = await asyncio.wait_for(queue.get(), timeout=30)
    yield f"data: {json.dumps(event)}\n\n"
except asyncio.TimeoutError:
    yield ": keepalive\n\n"  # comment line — client ignores it
```

The `:` prefix marks it as an SSE comment. The client's `EventSource` does not fire an `onmessage` event for comment lines.

---

## Browser Usage

```javascript
const source = new EventSource('/research/abc-123/events');

source.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.event);  // "research.planned", etc.
    if (data.event === 'research.completed') {
        source.close();
    }
};

source.onerror = () => {
    // EventSource automatically reconnects on error
};
```

The browser's `EventSource` automatically reconnects if the connection drops. It also sends the `Last-Event-ID` header so the server can resume from where it left off (if you implement event IDs — we don't in Phase 3).

> [!tip]
> `EventSource` only supports GET requests and cannot send a body. That's fine for our use case — the `task_id` is in the URL path.
