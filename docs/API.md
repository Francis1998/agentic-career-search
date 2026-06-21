# API Reference

FastAPI routes exposed by `agentic-career-search`.

Base URL (local default): `http://127.0.0.1:8000`

Interactive docs: `http://127.0.0.1:8000/docs`

## Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe (DB connectivity) |

## Source configs

| Method | Path | Description |
|---|---|---|
| `POST` | `/source-configs` | Create a source adapter config |
| `GET` | `/source-configs` | List source configs |
| `GET` | `/source-configs/{source_config_id}` | Fetch one source config |
| `PATCH` | `/source-configs/{source_config_id}` | Update source config fields |

Supported `source_type` values: `greenhouse`, `lever`.

## Runs

| Method | Path | Description |
|---|---|---|
| `POST` | `/runs` | Enqueue an autonomous run |
| `GET` | `/runs/{run_id}` | Inspect run lifecycle state |
| `GET` | `/runs/{run_id}/events` | Read ordered run event timeline |
| `POST` | `/runs/{run_id}/cancel` | Request run cancellation |

Run statuses: `queued`, `running`, `completed`, `failed`, `cancel_requested`, `cancelled`.

## Jobs

| Method | Path | Description |
|---|---|---|
| `GET` | `/jobs` | List normalized jobs (optional `run_id` query filter) |

Job payloads include deterministic `agent_decision` traces and optional `llm_enrichment` when provider enrichment is enabled.

## Example flow

```bash
curl -X POST "http://127.0.0.1:8000/source-configs" \
  -H "content-type: application/json" \
  -d '{"name":"demo","source_type":"greenhouse","base_url":"https://boards.greenhouse.io/embed/job_board?for=example"}'

RUN_ID=$(curl -s -X POST "http://127.0.0.1:8000/runs" \
  -H "content-type: application/json" \
  -d '{"query":"python backend"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s "http://127.0.0.1:8000/runs/$RUN_ID/events"
curl -s "http://127.0.0.1:8000/jobs?run_id=$RUN_ID"
```
