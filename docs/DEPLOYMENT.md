# Deployment Guide

Production-minded deployment notes for `agentic-career-search`.

## Prerequisites

- Python 3.11+
- `uv` (recommended) or another PEP 517 installer
- Outbound HTTPS access to configured career page sources
- Optional: LLM provider API keys when enrichment is enabled

## Local / single-node deployment

```bash
git clone https://github.com/Francis1998/agentic-career-search.git
cd agentic-career-search
uv venv
source .venv/bin/activate
uv sync --extra dev --frozen
cp .env.example .env
uv run uvicorn autoapply_agent.main:app --host 0.0.0.0 --port 8000
```

Health checks:

```bash
curl -s http://127.0.0.1:8000/health/live
curl -s http://127.0.0.1:8000/health/ready
```

## Environment configuration

See [CONFIGURATION.md](../CONFIGURATION.md) for the full variable reference.

Minimum production settings:

```env
ENVIRONMENT=prod
DATABASE_URL=sqlite+aiosqlite:///./data/autoapply_agent.db
ENABLE_WORKER=true
ENABLE_SCHEDULER=true
HTTP_TIMEOUT_SECONDS=12.0
MAX_JOBS_PER_SOURCE=50
```

Optional LLM enrichment:

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=gpt   # gemini | kimi | claude | gpt
OPENAI_API_KEY=your_key_here
```

## Database and migrations

- Runtime bootstraps tables via SQLAlchemy `create_all` for local simplicity.
- Alembic scaffold lives under `alembic/` for incremental schema control.
- Alembic reads `sqlalchemy.url` from `alembic.ini` (default `sqlite:///./autoapply_agent.db`),
  not `DATABASE_URL`: point it at the database to migrate, using the sync driver
  (`sqlite:///…` for `sqlite+aiosqlite:///…`).
- Apply migrations with:

```bash
uv run alembic upgrade head
```

### Upgrading an existing database

A database created by the app's startup `create_all` has no `alembic_version` table, so
`upgrade head` would try to recreate its tables (`table source_configs already exists`).
Stamp the initial revision once, then upgrade:

```bash
uv run alembic current             # no revision listed: the schema was created by the app
uv run alembic stamp 87de9ef55524  # record the initial schema as applied
uv run alembic upgrade head        # job ordering indexes (c41f2a7d9e60), tracker tables (d3a9f1c4b7e2), pay columns (e5b8c2a7f913)
```

The app's startup `create_all` adds missing tables but never adds columns to an existing
table: a database created before `e5b8c2a7f913` fails on `/jobs` (`no such column:
jobs.salary_min_annual`) until it is upgraded. Jobs captured before the upgrade get pay
when discovery captures them again (no backfill).

## Operational notes

- The in-process worker polls queued runs; for higher throughput, run a dedicated worker process pattern in future releases.
- Cancellation is cooperative: active runs finish the current source step before stopping.
- The in-process scheduler (`ENABLE_SCHEDULER`, `SCHEDULER_TICK_SECONDS`) queues the runs of due
  [run schedules](guides/RUN_SCHEDULES_GUIDE.md). Each fire is claimed exactly once, so it is safe
  in every replica; fires missed while the service is down become one run when it restarts.
- LLM provider failures degrade to deterministic-only output; runs still complete.

## See also

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [SAFETY.md](../SAFETY.md)
- [API Reference](./API.md)
