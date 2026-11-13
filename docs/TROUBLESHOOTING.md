# Troubleshooting

Common issues when running `agentic-career-search`.

## Setup and startup

| Issue | Likely cause | Fix |
|---|---|---|
| `No module named autoapply_agent` | Dependencies not installed or venv inactive | Run `uv sync --extra dev --frozen` and activate `.venv` |
| Port already in use | Another process on `:8000` | Start with `--port 8001` or stop the conflicting process |
| `/health/ready` returns 503 | Database URL unreachable | Verify `DATABASE_URL` path permissions and connectivity |

## Runs and worker behavior

| Issue | Likely cause | Fix |
|---|---|---|
| Run stays `queued` | Worker disabled | Set `ENABLE_WORKER=true` and restart API |
| Run completes with zero jobs | Source URL invalid or adapter mismatch | Confirm `source_type` and public board URL |
| Run stuck in `running` | Slow upstream source | Lower `HTTP_TIMEOUT_SECONDS` or cancel via `POST /runs/{id}/cancel` |
| Duplicate jobs skipped | Same URL already persisted for run | Expected behavior via `uq_jobs_run_url` constraint |

## MCP server

| Issue | Likely cause | Fix |
|---|---|---|
| `error: database file not found` on start | Relative SQLite path resolved against the MCP host's working directory | Pass an absolute `--database-url` (four slashes) or launch with `uv --directory /abs/path/agentic-career-search run career-search-mcp` |
| Tools return "The job database could not be read" | Database file without the app schema | Start the API once against it, or apply the Alembic migrations |
| Host lists no tools | Host not restarted, or server failed to start | Restart the host and read its MCP log (server diagnostics go to STDERR; try `--log-level INFO`) |

More in the [MCP Server Guide](guides/MCP_SERVER_GUIDE.md#troubleshooting).

## LLM enrichment

| Issue | Likely cause | Fix |
|---|---|---|
| No `agent.llm_enrichment` events | Enrichment disabled | Set `LLM_ENABLE_ENRICHMENT=true` |
| Enrichment silently absent | Missing provider API key | Set the key for active `LLM_PROVIDER` |
| Provider timeouts | Network latency or slow model | Increase `LLM_TIMEOUT_SECONDS` |
| Wrong provider selected | Misconfigured env | Use `gemini`, `kimi`, `claude`, or `gpt` |
| Enrichment absent with `claude-fable-5-2` | Organization or workspace without 30-day data retention (HTTP 400) | Enable 30-day retention or use `claude-opus-5-5` |
| Kimi enrichment stops on a `kimi-k2.*` model | K2 models are retiring by the end of December 2026 (closed to new users on 2026-10-31) | Set `KIMI_MODEL=kimi-k3.1-pro` |

Provider key mapping:

- `gemini` → `GEMINI_API_KEY`
- `kimi` → `KIMI_API_KEY`
- `claude` → `CLAUDE_API_KEY`
- `gpt` → `OPENAI_API_KEY`

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

## See also

- [QUICKSTART.md](../QUICKSTART.md)
- [CONFIGURATION.md](../CONFIGURATION.md)
- [API Reference](./API.md)
