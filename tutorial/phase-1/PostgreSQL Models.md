---
tags: [phase-1, sqlalchemy, alembic, postgresql, database]
file: services/orchestrator/app/models/research.py
---

# PostgreSQL Models

> How the orchestrator persists research tasks to PostgreSQL using SQLAlchemy 2 async ORM and Alembic migrations.

Related: [[LangGraph Orchestrator]] · [[SQLAlchemy Async]] · [[Home]]

---

## The Code

**Model:** `services/orchestrator/app/models/research.py`
**Database setup:** `services/orchestrator/app/core/database.py`
**Migrations:** `services/orchestrator/alembic/`

---

## Walkthrough

### The ResearchTask model

```python
class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                     default=lambda: str(uuid.uuid4()))
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    research_plan: Mapped[str | None] = mapped_column(Text)
    final_report: Mapped[str | None] = mapped_column(Text)
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                  default=lambda: datetime.now(UTC),
                                                  onupdate=lambda: datetime.now(UTC))
```

### `Mapped[T]` — SQLAlchemy 2 style

SQLAlchemy 2 uses `Mapped[T]` with `mapped_column()` for ORM columns. This is the modern way — don't use the old `Column(String)` style.

```python
# Old (SQLAlchemy 1.x style — avoid)
id = Column(String(36), primary_key=True)

# New (SQLAlchemy 2 style — use this)
id: Mapped[str] = mapped_column(String(36), primary_key=True)
```

The `Mapped[str]` tells type checkers that `task.id` is always a `str`. `Mapped[str | None]` means it can be None (matches `nullable=True`).

### Why UUID as string, not UUID column type?

Using `String(36)` with `str(uuid.uuid4())` works across all databases without a UUID column type. It's slightly less efficient than a native UUID type, but simpler for learning.

### `default` vs `server_default`

```python
# default= runs in Python before INSERT
default=lambda: datetime.now(UTC)

# server_default= would run on the DB side (SQL expression)
# server_default=func.now()
```

Python-side defaults are simpler and testable. Server-side defaults are harder to unit test. For learning, Python defaults are fine.

### `onupdate` for updated_at

```python
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    onupdate=lambda: datetime.now(UTC),
)
```

`onupdate` fires when SQLAlchemy executes an UPDATE statement on this row. It does **not** fire automatically if you update the DB directly with raw SQL.

### The status lifecycle

```
pending → running → completed
                  ↘ failed
```

The `status` column is a simple string. In Phase 3, we'll also publish these transitions as Kafka events.

---

## Alembic — Managing Schema Changes

### What Alembic does

Alembic is a database migration tool. Instead of running `CREATE TABLE` manually, you write migration scripts that Alembic can apply and roll back. This tracks which schema version the database is at.

### Workflow: model change → migration → apply

```bash
# 1. Edit your model (add/remove/change a column)

# 2. Alembic detects the diff between your models and the live DB
uv run alembic revision --autogenerate -m "add error_message column"

# 3. Review the generated file in alembic/versions/
# Make sure the upgrade() and downgrade() functions look right

# 4. Apply the migration
uv run alembic upgrade head

# 5. Roll back if needed
uv run alembic downgrade -1
```

### The async env.py

Standard Alembic assumes a synchronous SQLAlchemy connection. Since we use `asyncpg`, the `alembic/env.py` has special handling:

```python
async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.postgres_url, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

asyncio.run(run_migrations_online())
```

`connection.run_sync(do_run_migrations)` runs the synchronous Alembic migration code inside the async connection. `pool.NullPool` prevents Alembic from keeping connections open after it's done.

### The model import in env.py

```python
from app.models import research  # noqa: F401
```

This import makes Alembic aware of the `ResearchTask` model. Without it, `--autogenerate` sees no models and generates an empty migration. Add a line like this for every new model file you create.

> [!tip] First migration
> Run this once after the DB is up:
> ```bash
> docker compose exec orchestrator uv run alembic upgrade head
> ```
> This creates the `research_tasks` table. After that, use `--autogenerate` for all further changes.

> [!warning] Never edit generated migration files after applying
> Once a migration is applied to any database, treat it as immutable. Create a new migration instead. Editing an applied migration causes the `alembic_version` table to go out of sync.
