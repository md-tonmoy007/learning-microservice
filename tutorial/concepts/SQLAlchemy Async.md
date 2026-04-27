---
tags: [concept, sqlalchemy, async, postgresql]
---

# SQLAlchemy Async

> How async SQLAlchemy 2 works — engine, session, Mapped columns, and the get_db pattern.

Used in: [[PostgreSQL Models]] · [[LangGraph Orchestrator]]

---

## Setup — `database.py`

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(settings.postgres_url, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionFactory() as session:
        yield session
```

Three things to understand here: the engine, the sessionmaker, and `Base`.

---

## create_async_engine

```python
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:5432/db",
    echo=False,  # True logs all SQL — useful for debugging, noisy in production
)
```

The URL uses `postgresql+asyncpg://` — this tells SQLAlchemy to use the `asyncpg` driver. If you use `postgresql://` without the driver prefix, it uses the synchronous `psycopg2` and blocks the event loop.

The engine manages a **connection pool**. Create it once at startup; never create a new engine per request.

---

## async_sessionmaker

```python
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)
```

`async_sessionmaker` is a factory that creates `AsyncSession` objects. Each call to `AsyncSessionFactory()` creates a new session (with its own transaction scope).

### expire_on_commit=False

By default, SQLAlchemy expires all attributes on a model after `commit()`. This means accessing `task.id` after `await db.commit()` would trigger a new SELECT query to refresh it.

With `expire_on_commit=False`, attributes remain accessible after commit without a round-trip. This is essential for background tasks where the session may be closed before you've finished reading the object.

---

## get_db — the FastAPI dependency

```python
async def get_db():
    async with AsyncSessionFactory() as session:
        yield session
```

This is an **async generator dependency**. FastAPI calls it before your route handler:
1. Creates a session (`AsyncSessionFactory()`)
2. Yields it to the route handler
3. Closes it (and rolls back any uncommitted transaction) after the handler returns

The `async with` on the sessionmaker handles both open and close. You rarely need to call `session.close()` manually.

---

## Mapped columns — SQLAlchemy 2 ORM style

```python
from sqlalchemy.orm import Mapped, mapped_column

class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    final_report: Mapped[str | None] = mapped_column(Text)
```

- `Mapped[str]` — non-nullable string column
- `Mapped[str | None]` — nullable column (Python None maps to SQL NULL)
- `mapped_column(Text)` — SQLAlchemy column type and constraints

This is SQLAlchemy 2's "annotated" style. It gives you type safety and IDE autocomplete on model attributes.

---

## Common Async ORM Patterns

### INSERT (create)

```python
task = ResearchTask(user_query=query, status="pending")
db.add(task)
await db.commit()
await db.refresh(task)  # re-reads from DB so default values (id, created_at) are populated
return task
```

### SELECT by primary key

```python
from sqlalchemy import select

result = await db.execute(select(ResearchTask).where(ResearchTask.id == task_id))
task = result.scalar_one_or_none()  # None if not found
```

`scalar_one_or_none()` returns the first column of the first row, or None. Use `scalar_one()` if the row must exist (raises if not found).

### UPDATE

```python
task.status = "running"   # mutate the attribute
await db.commit()          # SQLAlchemy detects the change and issues UPDATE
```

SQLAlchemy's "unit of work" pattern tracks changes to loaded objects. You don't write UPDATE SQL manually.

### The `execute → scalar` pattern vs `get`

```python
# Modern way (always works)
result = await db.execute(select(ResearchTask).where(ResearchTask.id == id))
task = result.scalar_one_or_none()

# Shorthand for primary key lookup (also fine)
task = await db.get(ResearchTask, id)
```

---

## AsyncSessionFactory in Background Tasks

In background tasks (not tied to an HTTP request), use `AsyncSessionFactory` directly instead of `get_db`:

```python
async def run_workflow(task_id: str) -> None:
    async with AsyncSessionFactory() as db:
        task = await db.get(ResearchTask, task_id)
        # ... do work
        await db.commit()
    # session auto-closed here
```

See [[FastAPI Background Tasks]] for why background tasks must never use the request session.

> [!tip] When to use `echo=True`
> Set `echo=True` on the engine during development to log every SQL query. This helps you see what SQLAlchemy is actually doing — N+1 queries, missing indexes, unexpected updates. Turn it off in production (very noisy).
