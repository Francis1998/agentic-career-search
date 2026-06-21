# ARCHITECTURE

## Components

- **API Layer** (`autoapply_agent.api`): FastAPI routes for health, source config, run lifecycle, and jobs listing.
- **Worker** (`autoapply_agent.services.worker`): in-process async polling loop that claims queued runs.
- **Adapters** (`autoapply_agent.adapters`): Greenhouse and Lever HTTP parsers.
- **Domain Services** (`autoapply_agent.services.scoring`, `planning`): deterministic score and plan generation.
- **Persistence** (`autoapply_agent.db`): SQLAlchemy async models/session with SQLite.

## Run Lifecycle

1. Client creates run (`POST /runs`) -> run status `queued`, event `run.created`.
2. Worker claims queued run -> status `running`, event `run.started`.
3. Worker resolves source configs, fetches jobs per source, scores/plans each job.
4. Worker persists source and summary events.
5. Run reaches terminal state: `completed`, `cancelled`, or `failed`.

## Persistence Model

- `Run`: lifecycle state and user query.
- `RunEvent`: ordered event stream for observability.
- `SourceConfig`: source adapter configuration.
- `Job`: normalized job snapshot tied to run.

## Migrations

- Alembic scaffold included under `alembic/` and `alembic.ini`.
- Runtime creates tables for local simplicity; migrations are ready for incremental schema control.
