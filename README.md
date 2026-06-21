# agentic-career-search

An AI-agent-oriented backend for autonomous job discovery workflows.  
This project showcases practical agent engineering: goal-driven run orchestration, source adapters, scoring and planning policies, durable event traces, cancellation control, and production-minded verification.

## Why This Is Agentic

- **Goal-driven execution:** each run represents an explicit objective (`query + sources`) processed by a worker loop.
- **Observe -> Decide -> Act loop:** adapters observe external pages, services score and plan actions, worker persists outcomes.
- **Tool-using architecture:** source adapters are pluggable tools (`Greenhouse`, `Lever`) behind a stable interface.
- **Memory and traceability:** run and event persistence create a full decision trail for every agent step.
- **Control and safety:** cancellable runs, bounded scope, timeouts, and deterministic behavior for repeatability.

## AI Agent Skills Demonstrated

- **Orchestration design:** lifecycle state machine (`queued`, `running`, `completed`, `failed`, `cancelled`).
- **Agent infrastructure:** in-process async worker that claims, executes, and records jobs atomically.
- **Multi-tool integration:** adapter abstraction for heterogeneous external job sources.
- **Decision layer engineering:** deterministic scoring and planning services for explainable action policy.
- **Reliability engineering:** typed models, structured events, health endpoints, CI checks, and integration tests.

## Current Capabilities

- Async FastAPI API for source configs, runs, events, jobs, and health endpoints.
- Background run executor with persisted run-event sequencing.
- Public career-page ingestion from Greenhouse and Lever.
- Normalized job records with score and plan output.
- SQLite + SQLAlchemy async persistence with Alembic scaffold.
- CI with lint (`ruff`), type checks (`mypy`), and tests (`pytest`).

## API Surface

- `POST /source-configs` create source tool configs.
- `GET /source-configs` list configured sources.
- `POST /runs` queue an autonomous run.
- `GET /runs/{run_id}` inspect run state.
- `GET /runs/{run_id}/events` inspect full agent event timeline.
- `POST /runs/{run_id}/cancel` request cancellation.
- `GET /jobs` list extracted and planned job outputs.
- `GET /health/live` and `GET /health/ready`.

## Repository Layout

- `src/autoapply_agent/` application package
- `tests/` unit and integration tests
- `scripts/` local helper scripts
- `alembic/` migration scaffold
- `.github/workflows/` CI pipeline

## Local Development (uv)

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
uv run uvicorn autoapply_agent.main:app --reload
```

Open API docs at <http://127.0.0.1:8000/docs>.

## Portfolio Positioning

If you want to demonstrate AI agent engineering in interviews, this repo highlights:

- explicit agent loop design over prompt-only demos,
- robust state and observability over black-box automation,
- extensible tool adapters over one-off scripts,
- and verification discipline (lint/type/test/CI) for real-world delivery.

For full setup and operating guidance, see `QUICKSTART.md`, `CONFIGURATION.md`, `SAFETY.md`, and `ARCHITECTURE.md`.
