# Persistence Mode Reference

## JSON Runtime Store (DB-off mode)

When `GIRAFFE_DB_MODE=off` (the default), all agent state is held in the **in-process JSON runtime store**.

- Buyer workspaces: `data/b_workspaces/<id>.json`
- Supplier workspaces: `data/m_workspaces/<id>.json`
- Message drafts: `data/message_drafts/<id>.json`
- OpenClaw conversation bindings: `data/openclaw_bindings/<id>.json`
- Upstream inquiry store: `data/upstream/<project_id>/`

State is written to local JSON files under `data/`. The directory is created on first write. Files are not shared between processes; concurrent workers on different machines will not see each other's state.

This is suitable for:
- Local development and demo
- Single-process CI validation
- Proof-of-concept walkthroughs

It is **not** suitable for multi-user or multi-process production deployment.

## SQLite (DB-on mode)

When `GIRAFFE_DB_MODE=on` and `GIRAFFE_DB_URL=sqlite:///./path/to/db.db`, the agent writes to a local SQLite file through the SQLAlchemy ORM layer.

Schema is created by `python build_schema.py` (idempotent; uses `CREATE TABLE IF NOT EXISTS`).

SQLite DB-on mode:
- Persists state across process restarts
- Supports the full ORM model layer (25+ tables)
- Passes `PRAGMA integrity_check` and `PRAGMA foreign_key_check`
- Can be inspected with any SQLite browser

SQLite DB-on is **not** suitable for concurrent multi-writer production use due to SQLite's write-lock model.

## DB-off vs DB-on: which to use

| Use case | Recommended mode |
|---|---|
| Local demo / walkthrough | `GIRAFFE_DB_MODE=off` |
| CI validation | `GIRAFFE_DB_MODE=off` then `DB_MODE=on` (both run in CI) |
| Single-developer staging | `GIRAFFE_DB_MODE=on` with SQLite |
| Integration testing with DB verifier | `GIRAFFE_DB_MODE=on` with SQLite |
| Production (future) | `GIRAFFE_DB_MODE=on` with PostgreSQL |

## Recommended mode for MVP demo

Use `GIRAFFE_DB_MODE=off` for demos. It requires no database setup, starts instantly, and exercises all interface contracts identically to DB-on mode. The E2E scripts (`run_bm_e2e_mvp.py`, `run_role_switching_mvp.py`, etc.) default to DB-off.

## What remains before PostgreSQL production deployment

SQLite DB-on mode validates the ORM layer but is not a production deployment. Before moving to PostgreSQL:

1. Set `GIRAFFE_DB_URL=postgresql+asyncpg://user:pass@host/db`
2. Run `alembic upgrade head` to apply migrations (not `build_schema.py`)
3. Verify `alembic/versions/` contains all required migration steps
4. Configure connection pooling (SQLAlchemy `pool_size`, `max_overflow`)
5. Add a database health-check probe to the `/health` endpoint
6. Configure row-level access controls if multiple tenants share a database
7. Encrypt credentials at rest; never pass `GIRAFFE_DB_URL` as a plain-text env var in production

The JSON runtime store and SQLite layers are **not** equivalent to a production PostgreSQL deployment. They exist to let developers run and validate the full agent logic without infrastructure dependencies.
