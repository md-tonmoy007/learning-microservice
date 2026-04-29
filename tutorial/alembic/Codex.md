---
tags: [alembic, reference, cheatsheet]
file: services/orchestrator/alembic/
---

# Alembic Codex

> One-page quick reference. Every concept, file, command, and gotcha you need to work with Alembic on this project.

Related: [[Alembic Overview]] · [[Async Setup]] · [[Common Commands]] · [[Home]]

---

## Key Files

| File | Purpose |
|------|---------|
| `alembic.ini` | Config: script location, log levels, fallback DB URL |
| `alembic/env.py` | Runs on every alembic CLI call. Connects to DB, runs migrations |
| `alembic/versions/*.py` | One file per migration. Each has `upgrade()` and `downgrade()` |
| `alembic_version` table | Single-row table in your DB tracking which migration is current |

---

## Essential Commands

```bash
# cd services/orchestrator first

uv run alembic upgrade head          # apply all unapplied migrations
uv run alembic downgrade -1          # undo the last migration
uv run alembic revision --autogenerate -m "message"  # generate migration from model diff
uv run alembic current               # show which migration is applied
uv run alembic history --verbose     # show full migration chain
uv run alembic upgrade head --sql    # preview SQL without executing
uv run alembic stamp head            # mark DB as current without running anything
```

---

## Migration File Anatomy

```python
revision = 'abc123'        # this migration's unique ID
down_revision = 'def456'   # previous migration's ID (None if first)

def upgrade() -> None:
    op.create_table(...)           # or add_column, alter_column, etc.

def downgrade() -> None:
    op.drop_table(...)             # must exactly undo upgrade()
```

---

## `op` Operations

```python
# Tables
op.create_table('name', sa.Column(...), ...)
op.drop_table('name')
op.rename_table('old', 'new')

# Columns
op.add_column('table', sa.Column('col', sa.String()))
op.drop_column('table', 'col')
op.alter_column('table', 'col', nullable=False, new_column_name='new_col')

# Indexes
op.create_index('idx_name', 'table', ['col1', 'col2'])
op.drop_index('idx_name', 'table')

# Raw SQL (escape hatch)
op.execute("UPDATE research_tasks SET status='pending' WHERE status IS NULL")
```

---

## `env.py` Concepts

| Concept | What it is |
|---------|-----------|
| `target_metadata = Base.metadata` | What your models say the schema should be. Used by `--autogenerate` to diff against live DB |
| `from app.models import research  # noqa: F401` | Forces model to register on `Base.metadata`. Required for every model file. |
| `pool.NullPool` | No connection pooling. Mandatory for async Alembic — prevents hanging connections on exit |
| `connection.run_sync(do_run_migrations)` | Runs sync Alembic migration code inside an async connection |
| `asyncio.run(run_migrations_online())` | Starts the event loop to run the async entry point from the sync CLI |
| `context.is_offline_mode()` | True when `--sql` flag is passed. Generates SQL without a real DB connection |

---

## Targeting Revisions

```
head          = latest migration
base          = before any migration (empty DB)
+N / -N       = N steps forward / backward from current
<revision_id> = a specific migration by its ID (can use first 4+ chars)
```

```bash
alembic upgrade head      # apply everything
alembic upgrade +1        # apply one
alembic downgrade -1      # undo one
alembic downgrade base    # undo everything
alembic upgrade abc1      # apply up to migration starting with abc1
```

---

## How `--autogenerate` Works

```
1. Connect to live DB → read actual schema
2. Read Base.metadata → read ORM model schema
3. Diff the two
4. Write upgrade() / downgrade() to alembic/versions/<id>_<message>.py
```

**What it detects:**
- New tables, dropped tables
- Added/removed columns
- Column type changes
- New/dropped indexes and unique constraints
- Primary key changes

**What it misses:**
- Python-side `default=` changes (invisible to SQL)
- `onupdate=` changes
- Stored procedures, views, triggers
- Data migrations (moving data between columns)

---

## The Migration Chain

```
None ← revision_1 ← revision_2 ← revision_3
                                        ↑ head
```

`down_revision` links each migration to its parent. Running `upgrade head` walks this chain forward. Running `downgrade base` walks it backward.

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Ran `--autogenerate`, migration is empty | You forgot `from app.models import X  # noqa: F401` in `env.py` |
| `ModuleNotFoundError` when running alembic | `alembic.ini` needs `prepend_sys_path = .` and you must run from `services/orchestrator/` |
| `asyncio + asyncpg` connection error | Missing `poolclass=pool.NullPool` in `create_async_engine` inside `env.py` |
| Applied wrong migration, want to redo | `downgrade -1`, fix the file, `upgrade head` (only before sharing with others) |
| DB schema is right but `alembic current` shows wrong version | `alembic stamp <correct_revision_id>` to fix the pointer |
| Generated migration but it wasn't applied | Just delete the file — it's safe as long as you haven't run `upgrade` |
| Edited an applied migration file | Never do this. Create a new corrective migration instead |

---

## This Project's `env.py` Flow

```
alembic upgrade head
  ↓
env.py runs
  ↓
asyncio.run(run_migrations_online())
  ↓
create_async_engine(settings.postgres_url, poolclass=NullPool)
  ↓
async with engine.connect() as connection:
    await connection.run_sync(do_run_migrations)
  ↓
do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    context.run_migrations()
  ↓
Alembic walks alembic/versions/ chain
Runs upgrade() for each unapplied migration
Updates alembic_version table
  ↓
await engine.dispose()
```

---

## First Time Setup Checklist

```bash
# 1. Make sure postgres is running
docker compose up postgres -d

# 2. Apply all migrations
cd services/orchestrator
uv run alembic upgrade head

# 3. Verify
uv run alembic current
# should print: <revision_id> (head)
```

## Adding a New Column — Full Workflow

```bash
# 1. Edit the model
# services/orchestrator/app/models/research.py
# → add the column

# 2. Generate migration
cd services/orchestrator
uv run alembic revision --autogenerate -m "add new_column to research_tasks"

# 3. Review the generated file in alembic/versions/
# Make sure upgrade() and downgrade() look correct

# 4. Apply
uv run alembic upgrade head

# 5. Verify
uv run alembic current
```
