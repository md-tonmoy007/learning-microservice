---
tags: [phase-1, fastapi, httpx, gateway]
file: services/api-gateway/app/api/research.py
---

# API Gateway

> The public face of the system. Accepts research requests from users and delegates all real work to the orchestrator.

Related: [[LangGraph Orchestrator]] · [[FastAPI Background Tasks]] · [[Home]]

---

## The Code

**Entry point:** `services/api-gateway/app/main.py`
**Routes:** `services/api-gateway/app/api/research.py`
**Config:** `services/api-gateway/app/core/config.py`
**Schemas:** `services/api-gateway/app/schemas/research.py`

---

## Walkthrough

### What the gateway does

The api-gateway is a **thin proxy**. It has zero business logic. Its only job is:
1. Accept HTTP requests from users
2. Forward them to the orchestrator via httpx
3. Return whatever the orchestrator says

In Phase 1 this is a synchronous proxy over HTTP. In Phase 3, the gateway will stop proxying and instead publish a Kafka event and stream SSE to the user. Understanding why the gateway is thin now makes it obvious why we need Kafka later.

### Why not put the logic in the gateway?

The gateway is the only service exposed to the internet. Keeping it thin means:
- Less attack surface
- Simpler to scale independently
- Can swap out the backend (orchestrator) without touching the public API

### The three routes

```python
POST /research          → forwards to POST /internal/research on orchestrator
GET  /research/{id}     → forwards to GET  /internal/research/{id}
GET  /research/{id}/status → forwards to GET /internal/research/{id}/status
```

The gateway just relays — it reads the JSON body, calls orchestrator, and returns the response JSON.

### httpx — async HTTP client

`httpx` is the async HTTP client for Python. It mirrors the `requests` API but is fully async:

```python
async with httpx.AsyncClient() as client:
    resp = await client.post(url, json={"query": "..."}, timeout=10.0)
    resp.raise_for_status()  # raises HTTPStatusError if 4xx/5xx
```

We use `async with` because AsyncClient holds a connection pool. The context manager ensures it's properly closed after the request.

### Error handling — two httpx exception types

```python
except httpx.HTTPStatusError as e:
    # Server responded with 4xx or 5xx
    # e.response.status_code gives you the code
    # e.response.text gives you the body
    raise HTTPException(status_code=502, detail=e.response.text)

except httpx.RequestError as e:
    # Network error — DNS failure, connection refused, timeout
    raise HTTPException(status_code=503, detail=str(e))
```

**502 Bad Gateway** = orchestrator responded with an error.
**503 Service Unavailable** = couldn't reach orchestrator at all.

### pydantic-settings for config

`app/core/config.py` uses `pydantic-settings` to read env vars:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    orchestrator_url: str = "http://orchestrator:8001"

settings = Settings()
```

When running in Docker, `ORCHESTRATOR_URL` is set in `docker-compose.yml`. When running locally, `.env` is read. The field name is the env var name (case-insensitive).

---

## Workflow

```
User: POST /research {"query": "..."}
  → api/research.py: submit_research()
    → httpx.AsyncClient.post(orchestrator_url/internal/research)
      → orchestrator creates task, returns {"task_id": "abc-123", "status": "pending"}
  → returns 202 Accepted with task_id

User: GET /research/abc-123/status
  → api/research.py: get_research_status()
    → httpx.AsyncClient.get(orchestrator_url/internal/research/abc-123/status)
  → returns {"task_id": "abc-123", "status": "running"}

User: GET /research/abc-123
  → api/research.py: get_research()
    → httpx.AsyncClient.get(orchestrator_url/internal/research/abc-123)
  → returns full task with final_report when status = "completed"
```

> [!tip] Why 202 Accepted?
> HTTP 200 means "here is your answer." HTTP 202 means "I've accepted your request and will process it — come back for the result." Research takes time, so 202 is semantically correct here.

> [!note] Phase 3 change
> In Phase 3, `submit_research` will publish to Kafka instead of calling the orchestrator directly. The user will get a `task_id` back immediately, and a separate SSE endpoint will stream live progress events.
