# agentic-career-search

A Python-first FastAPI service for queueing deterministic job-search runs, scraping public careers pages (Greenhouse and Lever), scoring listings, and storing run lifecycle events.

## Highlights

- Async FastAPI API with run lifecycle endpoints.
- In-process async worker loop for queued runs.
- Public-page adapters for Greenhouse and Lever (no login automation).
- SQLite + SQLAlchemy async models and Alembic-ready migration scaffold.
- Deterministic scoring and planning services.
- Pytest unit + integration coverage for run lifecycle.

## Repository Layout

- `src/autoapply_agent/`: application package
- `tests/`: unit and integration tests
- `scripts/`: local helper scripts
- `alembic/`: migration scaffold
- `.github/workflows/`: CI pipeline

## Local Development (uv)

1. Create environment and install dependencies:

   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

2. Start API server:

   ```bash
   uv run uvicorn autoapply_agent.main:app --reload
   ```

3. Open API docs:

   - <http://127.0.0.1:8000/docs>

See `QUICKSTART.md` for copy/paste flow and `CONFIGURATION.md` for settings.
