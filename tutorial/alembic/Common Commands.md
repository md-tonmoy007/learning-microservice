---
tags: [alembic, commands, reference]
file: services/orchestrator/alembic/
---

# Alembic Common Commands

> Every alembic command you'll use on this project, with what it does and when to use it.

Related: [[Alembic Overview]] · [[Async Setup]] · [[Codex]] · [[Home]]

---

> [!note] Always run from inside the orchestrator directory
> Alembic reads `alembic.ini` from the current directory. All commands below assume you are in `services/orchestrator/`.
> ```bash
> cd services/orchestrator
> ```
> Or via Docker:
> ```bash
> docker compose exec orchestrator <command>
> ```

---

## Setting Up — First Time

### Apply all migrations to a fresh database

```bash
uv run alembic upgrade head
```

Run this once after `docker compose up` brings postgres up. It reads every file in `alembic/versions/`, runs them in order from oldest to newest, and updates `alembic_version` to the latest revision ID.

If the `research_tasks` table already exists (e.g. you ran this before), Alembic skips migrations that are already recorded in `alembic_version`. It never applies the same migration twice.

---

## Day-to-Day Development

### 1. You changed a model — generate a migration

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

**Example:**
```bash
uv run alembic revision --autogenerate -m "add rating column to research_tasks"
```

This:
1. Connects to the live DB and reads its current schema
2. Reads `Base.metadata` (your ORM models) from `env.py`
3. Diffs the two
4. Writes a new file to `alembic/versions/` with `upgrade()` and `downgrade()` pre-filled

**Always open the generated file and read it** before the next step. Verify the `upgrade()` function matches what you intended.

### 2. Apply the new migration

```bash
uv run alembic upgrade head
```

Runs all unapplied migrations up to `head`. If you just generated one, this applies exactly that one.

### 3. Roll back the last migration

```bash
uv run alembic downgrade -1
```

Runs the `downgrade()` function of the current migration and moves `alembic_version` back to the previous revision. Use this when:
- The migration had a bug
- You want to redo the `--autogenerate` with different model changes
- You need to test that `downgrade()` actually works

### 4. Revert everything to a blank slate

```bash
uv run alembic downgrade base
```

Runs every `downgrade()` from newest to oldest. This drops all your tables. Useful for testing migrations from scratch.

---

## Inspecting State

### Check current migration version

```bash
uv run alembic current
```

Prints the revision ID in `alembic_version` and whether it matches `head`. Example output:
```
3f8a1b2c4d5e (head)
```

If nothing is applied yet:
```
(no current revision)
```

### See all migrations and which is current

```bash
uv run alembic history --verbose
```

Prints the full chain of migrations with dates and descriptions. The one with `(head)` is the latest. The one marked with `->` is the current one applied.

```
Rev: a1b4f5 (head)
Parent: 7c2d3e
Path: alembic/versions/a1b4f5_add_rating.py
  add rating column to research_tasks
  create_date: 2024-01-15 10:30:00

Rev: 7c2d3e
Parent: 3f8a1b
  add error_message column
  ...

Rev: 3f8a1b
Parent: <base>
  create research_tasks
  ...
```

### Preview what SQL a migration will run (without executing)

```bash
uv run alembic upgrade head --sql
```

Prints the raw SQL to stdout. Does not connect to or modify the DB. Use this to review exactly what Alembic will execute, or to hand the SQL to a DBA.

---

## Targeting a Specific Migration

### Upgrade to a specific revision

```bash
uv run alembic upgrade 7c2d3e
```

Applies all migrations up to and including `7c2d3e`. Stops there even if newer ones exist.

### Downgrade to a specific revision

```bash
uv run alembic downgrade 3f8a1b
```

Rolls back until `alembic_version` equals `3f8a1b`. Runs `downgrade()` for every migration between current and target.

### Upgrade N steps forward

```bash
uv run alembic upgrade +2
```

Applies the next 2 unapplied migrations from current position.

### Downgrade N steps back

```bash
uv run alembic downgrade -2
```

Rolls back the last 2 applied migrations.

---

## Handling Mistakes

### "I applied a migration but the SQL was wrong"

```bash
uv run alembic downgrade -1          # undo it
# edit the generated migration file
uv run alembic upgrade head          # re-apply the fixed version
```

Only do this before the migration has been shared with anyone or applied to any non-local DB. Once it's in git and on another machine, create a new corrective migration instead.

### "I deleted a migration file but it's still in alembic_version"

```bash
uv run alembic stamp <revision_id>   # tell alembic "we are at this revision" without running anything
```

`stamp` updates `alembic_version` without executing any migration code. Use it to reset Alembic's pointer when the actual DB state is correct but the tracking is wrong.

### "I want to mark the DB as fully migrated without running anything"

```bash
uv run alembic stamp head
```

Sets `alembic_version` to `head` without executing any migration code. Use this when you created the DB tables manually (e.g. from a dump) and just need Alembic to acknowledge the state.

### "I created a migration by accident and haven't applied it"

Just delete the file from `alembic/versions/`. Since it was never applied, `alembic_version` doesn't reference it and nothing breaks.

---

## Docker Compose Workflow

### Run migrations inside the running container

```bash
docker compose exec orchestrator uv run alembic upgrade head
```

### Run migrations as a one-off container (DB must be running)

```bash
docker compose run --rm orchestrator uv run alembic upgrade head
```

### Check current migration in the container

```bash
docker compose exec orchestrator uv run alembic current
```

### Generate a migration (model file must already be edited)

```bash
docker compose exec orchestrator uv run alembic revision --autogenerate -m "your message"
```

> [!warning] After generating inside Docker, copy the file out
> The generated file lives inside the container. Either commit it from inside, or copy it out:
> ```bash
> docker compose cp orchestrator:/app/alembic/versions/ ./services/orchestrator/alembic/
> ```
> Running locally (`cd services/orchestrator && uv run alembic revision ...`) is simpler for development — the file lands directly in your working tree.
