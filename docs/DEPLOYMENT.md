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
- Apply migrations with:

```bash
uv run alembic upgrade head
```

## Operational notes

- The in-process worker polls queued runs; for higher throughput, run a dedicated worker process pattern in future releases.
- Cancellation is cooperative: active runs finish the current source step before stopping.
- LLM provider failures degrade to deterministic-only output; runs still complete.

## See also

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [SAFETY.md](../SAFETY.md)
- [API Reference](./API.md)
