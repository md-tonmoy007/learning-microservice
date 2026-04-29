---
tags: [phase-1, logging, shared]
file: shared/logging.py
---

# Shared Logging

> A single JSON logger factory used by every service. Keeps log format consistent so Loki can parse them in Phase 4.

Related: [[Project Structure]] · [[LangGraph Orchestrator]] · [[API Gateway]] · [[Home]]

---

## The Code

```python
# shared/logging.py

class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": record.name,
            "message": record.getMessage(),
        }
        for extra in ("task_id", "event"):
            if hasattr(record, extra):
                payload[extra] = getattr(record, extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def get_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(service_name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
```

---

## Walkthrough

### Why structured JSON logs?

Plain text logs look like this:
```
2024-01-01 12:00:00 INFO Starting research task abc-123
```

JSON logs look like this:
```json
{"timestamp": "2024-01-01T12:00:00Z", "level": "INFO", "service": "orchestrator", "task_id": "abc-123", "message": "Starting research task"}
```

The JSON format is machine-readable. In Phase 4, Loki will ingest these and let you filter by `task_id`, `service`, or `level` without regex. Elasticsearch, Datadog, and every major log aggregation tool work the same way.

### `get_logger(service_name)` — the factory

Call this once per service, usually at module top level:

```python
from shared.logging import get_logger

logger = get_logger("orchestrator")

# later:
logger.info("Research task started", extra={"task_id": task_id})
logger.error("LLM call failed", extra={"task_id": task_id, "event": "llm_error"})
```

The `service_name` becomes the `"service"` field in every log line. Use the service folder name: `"api-gateway"`, `"orchestrator"`.

### The `if not logger.handlers` guard

Python's `logging.getLogger(name)` returns the same logger object every time you call it with the same name. Without the guard, calling `get_logger("orchestrator")` twice would add a second handler, causing every message to print twice. The guard makes `get_logger` safe to call multiple times.

### The `extra` fields pattern

Standard Python logging passes extra context via the `extra=` keyword:

```python
logger.info("Task created", extra={"task_id": "abc-123", "event": "task_created"})
```

The formatter checks for `task_id` and `event` fields:
```python
for extra in ("task_id", "event"):
    if hasattr(record, extra):
        payload[extra] = getattr(record, extra)
```

Only these two extras are promoted to top-level JSON fields. To add more (e.g., `user_id`), extend the tuple in the formatter.

### `logger.propagate = False`

By default, Python loggers propagate messages up to the root logger. The root logger might have its own handler (e.g., uvicorn's) that prints in a different format. Setting `propagate = False` keeps our JSON formatter as the sole handler and prevents duplicate output with different formats.

### `sys.stdout` not `sys.stderr`

We write to stdout, not stderr, because:
- Docker captures stdout for log aggregation
- `stderr` is conventionally for process errors, not application logs
- Loki/Fluentd pipelines typically tail stdout

---

## Workflow

```python
# In any service file:
from shared.logging import get_logger
logger = get_logger("orchestrator")

# Basic log
logger.info("Starting workflow")
# → {"timestamp": "...", "level": "INFO", "service": "orchestrator", "message": "Starting workflow"}

# Log with task context
logger.info("Plan created", extra={"task_id": "abc-123", "event": "plan_created"})
# → {"timestamp": "...", "level": "INFO", "service": "orchestrator", "task_id": "abc-123", "event": "plan_created", "message": "Plan created"}

# Log an exception
try:
    await research_graph.ainvoke(state)
except Exception:
    logger.exception("Workflow failed", extra={"task_id": task_id})
# → includes "exception": "<traceback>" in the JSON
```

> [!tip] Use `logger.exception()` inside `except` blocks
> `logger.exception()` is like `logger.error()` but automatically captures the current exception info and adds it as `"exception"` in the JSON. No need to pass `exc_info=True` manually.

> [!note] Phase 4 change
> In Phase 4, the formatter will also add an OpenTelemetry `trace_id` field so logs can be correlated with distributed traces in Grafana.
