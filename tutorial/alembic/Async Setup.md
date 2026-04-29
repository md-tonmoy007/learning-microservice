---
tags: [alembic, async, asyncpg, sqlalchemy]
file: services/orchestrator/alembic/env.py
---

# Alembic Async Setup

> Standard Alembic is synchronous. Our project uses asyncpg (async PostgreSQL driver). This note explains the exact changes needed to make them work together.

Related: [[Alembic Overview]] · [[Common Commands]] · [[SQLAlchemy Async]] · [[Home]]

---

## The Problem

Standard Alembic ships with a synchronous `env.py` that calls `engine.connect()` — a blocking call. `asyncpg` does not support synchronous connections at all. If you try to use the standard `env.py` with `asyncpg` in the connection URL, you get:

```
sqlalchemy.exc.InvalidRequestError: The asyncio extension requires an async driver to be used.
```

The fix has two parts:
1. Use `create_async_engine` to get an async connection
2. Use `connection.run_sync(...)` to run Alembic's synchronous migration code inside that async connection

---

## The Full `env.py` — annotated

```python
# services/orchestrator/alembic/env.py

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.models import research  # noqa: F401

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata
```

### Line by line — the imports and setup

**`from alembic import context`** — `context` is Alembic's runtime object. It knows whether you're running in offline or online mode, holds the connection, and exposes `run_migrations()`.

**`from sqlalchemy import pool`** — we need `pool.NullPool` specifically (explained below).

**`from app.core.config import settings`** — reads `POSTGRES_URL` from `.env`. This overrides whatever URL is in `alembic.ini`. Always prefer this — `alembic.ini` has a hardcoded local URL that breaks in Docker.

**`from app.core.database import Base`** — `Base` is `DeclarativeBase`. Its `.metadata` attribute contains the table definitions of every model that inherits from it.

**`from app.models import research  # noqa: F401`** — this import has no runtime use. Its only purpose is to execute `models/research.py`, which causes `ResearchTask` to register itself onto `Base.metadata`. Without this import, `Base.metadata` is empty and autogenerate generates nothing.

> [!warning] Every new model file needs its own import here
> When you add `models/user.py` in Phase 2, you must add `from app.models import user  # noqa: F401` to `env.py` or autogenerate will not see the new model.

**`target_metadata = Base.metadata`** — tells Alembic what the schema *should* look like (from your ORM models). Alembic diffs this against the live DB schema to produce `--autogenerate` migrations.

---

### The offline function — `run_migrations_offline()`

```python
def run_migrations_offline() -> None:
    context.configure(
        url=settings.postgres_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
```

"Offline mode" means Alembic generates SQL **without connecting to the database**. You call it with:

```bash
alembic upgrade head --sql
```

This prints the SQL statements to stdout instead of executing them. Useful for:
- Reviewing what a migration will actually do
- Generating SQL to hand off to a DBA
- CI pipelines that can't reach the DB

`literal_binds=True` makes parameters embedded directly in the SQL string (e.g., `'pending'` instead of `$1`) so the output is copy-paste-runnable.

---

### The sync helper — `do_run_migrations()`

```python
def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

This is a plain synchronous function. It takes a `connection` (a synchronous-compat connection from `run_sync`) and runs the actual migrations.

We separate this into its own function because `connection.run_sync()` requires a callable — it will call `do_run_migrations(connection)` in the right context.

---

### The async entry point — `run_migrations_online()`

```python
async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.postgres_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()
```

This is the important one. Step by step:

**`create_async_engine(settings.postgres_url, poolclass=pool.NullPool)`**

Creates an async SQLAlchemy engine. `NullPool` is critical here — it means every `connect()` call creates a brand-new connection and closes it when done, with no pooling. For Alembic (which runs once and exits), pooling is wasteful and can cause connections to hang open. Without `NullPool`, Alembic sometimes fails to close the connection cleanly before the process exits.

**`async with connectable.connect() as connection:`**

Opens a single async connection. The `async with` guarantees it's closed when the block exits, even on error.

**`await connection.run_sync(do_run_migrations)`**

This is the bridge between async and sync. `run_sync` takes a synchronous function and runs it on the event loop in a way that the sync function can call sync SQLAlchemy operations (like `context.run_migrations()`) while the surrounding code is async. It's roughly equivalent to running the sync function in a thread executor, but integrated with SQLAlchemy's async machinery.

**`await connectable.dispose()`**

Explicitly disposes the engine to release all resources. With `NullPool` this is mostly a no-op, but it's good practice.

---

### The dispatcher — the `if` at the bottom

```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

When Alembic CLI runs `env.py`, it sets up `context` first. `context.is_offline_mode()` returns `True` only when you passed `--sql`. Otherwise it's `False` and we run online.

`asyncio.run(run_migrations_online())` starts an event loop, runs our async function to completion, and closes the loop. This is the standard way to run a top-level async function from synchronous code (like a CLI entry point).

---

## Why `NullPool` is non-negotiable

Regular connection pools keep connections open for reuse:

```
Pool: [conn1, conn2, conn3]  ← stays alive between operations
```

When `asyncio.run()` completes, the event loop closes. Any open async connections that were pooled become invalid. SQLAlchemy then logs errors trying to clean them up, and sometimes the process hangs waiting for the pool to drain. `NullPool` bypasses this entirely:

```
NullPool: connect() → use → close() → gone
```

One connection, used once, closed immediately. Perfect for a CLI tool that runs and exits.

---

## Anatomy of a Generated Migration File

When you run `alembic revision --autogenerate -m "create research_tasks"`, Alembic writes something like this to `alembic/versions/`:

```python
"""create research_tasks

Revision ID: 3f8a1b2c4d5e
Revises: 
Create Date: 2024-01-01 12:00:00.000000
"""
from typing import Annotated
from alembic import op
import sqlalchemy as sa

revision: str = '3f8a1b2c4d5e'
down_revision: str | None = None   # None = first migration
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table('research_tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('research_plan', sa.Text(), nullable=True),
        sa.Column('final_report', sa.Text(), nullable=True),
        sa.Column('iteration_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('research_tasks')
```

`op` is Alembic's operations object. Common operations:
- `op.create_table(...)` / `op.drop_table(...)`
- `op.add_column(table, Column(...))` / `op.drop_column(table, column_name)`
- `op.alter_column(table, column, ...)` — change type, nullable, default
- `op.create_index(...)` / `op.drop_index(...)`
- `op.execute("raw SQL")` — for anything op doesn't cover

> [!tip] `downgrade()` must undo `upgrade()` exactly
> If `upgrade()` adds a column, `downgrade()` must drop it. If `upgrade()` creates a table, `downgrade()` must drop it. Alembic does not verify this — you have to think about it yourself.
