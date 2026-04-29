---
tags: [alembic, database, migrations, postgresql]
file: services/orchestrator/alembic/
---

# Alembic Overview

> Alembic is a database migration tool for SQLAlchemy. It tracks every schema change as a versioned script so the database structure can be evolved, rolled back, and reproduced exactly.

Related: [[Async Setup]] · [[Common Commands]] · [[Codex]] · [[PostgreSQL Models]] · [[SQLAlchemy Async]] · [[Home]]

---

## The Problem Alembic Solves

Without a migration tool, changing your database schema is manual and dangerous:

```bash
# Bad workflow — no history, no rollback
psql -U postgres -d research -c "ALTER TABLE research_tasks ADD COLUMN rating INT;"
# Later: what did this DB look like 3 weeks ago? No idea.
# New developer: what commands do I need to run? No idea.
# Production hotfix needed? No safe rollback.
```

With Alembic:
```bash
# Good workflow
uv run alembic revision --autogenerate -m "add rating column"
# → generates alembic/versions/abc123_add_rating_column.py
uv run alembic upgrade head
# → runs the migration, records it in the DB
uv run alembic downgrade -1
# → runs the undo, as if the migration never happened
```

Every schema change is a **versioned, reversible script** stored in version control alongside the code that needs it.

---

## How Alembic Tracks History

Alembic creates one table in your database the first time it runs:

```sql
CREATE TABLE alembic_version (
    version_num VARCHAR(32) PRIMARY KEY
);
```

This table holds exactly one row — the ID of the last migration that was applied. When you run `upgrade head`, Alembic reads this table, finds which migrations haven't been applied yet, runs them in order, and updates the row. When you run `downgrade -1`, it runs the undo function of the current version and updates the row.

```
alembic_version table:
┌──────────────────────────┐
│ version_num              │
├──────────────────────────┤
│ 3f8a1b2c4d5e             │  ← "we are at this migration"
└──────────────────────────┘
```

---

## The Files in This Project

```
services/orchestrator/
├── alembic.ini              ← alembic's config file (DB URL, log format)
└── alembic/
    ├── env.py               ← entry point — runs when alembic CLI is invoked
    └── versions/            ← one .py file per migration
        ├── 001_initial.py   ← first migration (creates research_tasks)
        └── 002_add_col.py   ← (example of a future migration)
```

### `alembic.ini` — the config

The config file tells Alembic where to find the migration scripts and sets log levels:

```ini
[alembic]
script_location = alembic        # where the alembic/ folder is
prepend_sys_path = .             # add current dir to sys.path (so app imports work)
sqlalchemy.url = postgresql+asyncpg://...  # fallback URL (overridden by env.py in our project)
```

`prepend_sys_path = .` is crucial — it lets `env.py` do `from app.core.config import settings` without having to be installed as a package. Without it, the import would fail.

> [!warning] We override `sqlalchemy.url` in env.py
> The URL in `alembic.ini` is a fallback. Our `env.py` reads the real URL from `settings.postgres_url` which comes from the `.env` file. The `alembic.ini` URL is what you'd need if you ran alembic directly without `env.py` overriding it — we always use the override.

### `alembic/env.py` — the entry point

Every time you run any `alembic` command, this file runs. It's responsible for:
1. Reading config
2. Connecting to the database
3. Running the migrations

See [[Async Setup]] for a deep dive into `env.py`, since ours is non-standard (we use async).

### `alembic/versions/` — the migration scripts

Each file here is one migration. They look like this:

```python
# alembic/versions/3f8a1b2c4d5e_create_research_tasks.py

revision = '3f8a1b2c4d5e'   # this migration's ID
down_revision = None          # None = this is the first migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('research_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_query', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50)),
        # ...
    )

def downgrade() -> None:
    op.drop_table('research_tasks')
```

`revision` — the unique ID of this migration (random hex string).
`down_revision` — the ID of the migration that must have run before this one. This is how Alembic knows the order. `None` means "this is the first one."
`upgrade()` — the SQL changes to apply.
`downgrade()` — the SQL to undo them.

---

## The Chain of Migrations

Migrations form a linked list via `down_revision`:

```
None ← 3f8a1b ← 7c2d3e ← a1b4f5
                                ↑
                           "head" = latest
```

`alembic upgrade head` means "apply everything up to the latest."
`alembic downgrade base` means "undo everything back to the start."
`alembic downgrade -1` means "undo the last one."
`alembic upgrade +2` means "apply the next two."

---

## `--autogenerate` — the killer feature

Instead of writing `upgrade()` and `downgrade()` by hand, Alembic can compare your SQLAlchemy models to the live database and generate the migration automatically:

```bash
uv run alembic revision --autogenerate -m "add rating column"
```

How it works:
1. Alembic connects to the DB and reads the current schema
2. Alembic reads `target_metadata = Base.metadata` from `env.py` — this is your ORM models
3. It diffs the two and generates `upgrade()` / `downgrade()` functions

**Always review the generated file before applying.** Autogenerate is very good but not perfect — it misses things like:
- Changes to `default=` values (Python-side defaults are invisible to SQL)
- Changes to stored procedures or views
- Some index changes depending on configuration

> [!tip] Autogenerate is a starting point, not a final answer
> Think of `--autogenerate` as a first draft. Always open the generated file, read `upgrade()` and `downgrade()`, and make sure they look right before running `upgrade head`.
