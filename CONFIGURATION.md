# CONFIGURATION

Configuration is environment-variable driven via `pydantic-settings`.

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Agentic Career Search` | Service display name |
| `DATABASE_URL` | `sqlite+aiosqlite:///./autoapply_agent.db` | SQLAlchemy async DB URL |
| `WORKER_POLL_INTERVAL_SECONDS` | `0.5` | Queue polling interval |
| `HTTP_TIMEOUT_SECONDS` | `12.0` | Adapter HTTP timeout |
| `MAX_JOBS_PER_SOURCE` | `50` | Per-source job cap |
| `HTTP_USER_AGENT` | `agentic-career-search/0.2` | Outbound HTTP user agent |
| `ENABLE_WORKER` | `true` | Start in-process worker on boot |

## Recommended Profiles

### Local dev

```env
DATABASE_URL=sqlite+aiosqlite:///./autoapply_agent.db
WORKER_POLL_INTERVAL_SECONDS=0.5
HTTP_TIMEOUT_SECONDS=12.0
MAX_JOBS_PER_SOURCE=50
ENABLE_WORKER=true
```

### CI and deterministic tests

```env
WORKER_POLL_INTERVAL_SECONDS=0.05
HTTP_TIMEOUT_SECONDS=0.5
MAX_JOBS_PER_SOURCE=5
ENABLE_WORKER=true
```

## Notes

- SQLite is local-development friendly and deterministic for this project scope.
- For production-like deployments, use a managed DB and external worker process.
- `DATABASE_URL` can point to a file path for easy portability.
- Keep `HTTP_USER_AGENT` explicit and consistent across environments for easier request attribution.
