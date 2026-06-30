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
| `LLM_ENABLE_ENRICHMENT` | `false` | Enable provider-based LLM decision enrichment |
| `LLM_PROVIDER` | `gemini` | Active LLM provider: `gemini`, `kimi`, `claude`, `gpt` |
| `LLM_TIMEOUT_SECONDS` | `12.0` | LLM API timeout in seconds |
| `GEMINI_API_KEY` | _empty_ | Gemini API key |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model |
| `KIMI_API_KEY` | _empty_ | Kimi (Moonshot) API key |
| `KIMI_MODEL` | `kimi-k2` | Kimi model |
| `KIMI_BASE_URL` | `https://api.moonshot.cn/v1` | Kimi base URL |
| `CLAUDE_API_KEY` | _empty_ | Anthropic Claude API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model |
| `OPENAI_API_KEY` | _empty_ | GPT / OpenAI-compatible API key |
| `OPENAI_MODEL` | `gpt-5.5` | GPT model name |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL |

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

### LLM enrichment enabled (Gemini example)

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### LLM enrichment enabled (Kimi example)

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=kimi
KIMI_API_KEY=your_key_here
KIMI_MODEL=kimi-k2
KIMI_BASE_URL=https://api.moonshot.cn/v1
```

### LLM enrichment enabled (Claude example)

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=claude
CLAUDE_API_KEY=your_key_here
CLAUDE_MODEL=claude-sonnet-4-6
```

### LLM enrichment enabled (GPT example)

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=gpt
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://api.openai.com/v1
```

## Notes

- SQLite is local-development friendly and deterministic for this project scope.
- For production-like deployments, use a managed DB and external worker process.
- `DATABASE_URL` can point to a file path for easy portability.
- Keep `HTTP_USER_AGENT` explicit and consistent across environments for easier request attribution.
- When LLM enrichment is enabled, provider failures degrade gracefully to deterministic-only output.
