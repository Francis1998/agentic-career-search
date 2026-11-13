# API Reference

FastAPI routes exposed by `agentic-career-search`.

Base URL (local default): `http://127.0.0.1:8000`

Interactive docs: `http://127.0.0.1:8000/docs`

Integer ids (`source_config_id`, `job_id` and the items of `source_config_ids`) must be
between `1` and `2^63-1` (`9223372036854775807`), and `offset` between `0` and `2^63-1`:
the range of a SQLite `INTEGER`. Other values return `422` with the standard FastAPI
validation body instead of reaching the database.

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

`POST /runs/{run_id}/cancel` cancels a `queued` run immediately (`cancelled`) and moves a
`running` run to `cancel_requested` until the worker stops it (`cancelled`). A run that
has already finished keeps its final status and gets a `run.cancel_ignored` event; this
includes a run that finishes while the cancel request waits for the worker's database
write (on SQLite, a cancel sent while the last source is being ingested). Such a run
used to be switched from `completed` to `cancel_requested`, which it never left.

With LLM enrichment enabled the worker commits before each provider call, so a cancel
sent while a call is in flight is accepted at once; the job being enriched is still
stored and no further provider call is made. Such a cancel used to wait for the whole
source on SQLite and fail with a 500 (`database is locked`).

## Jobs

| Method | Path | Description |
|---|---|---|
| `GET` | `/jobs` | Search jobs with filters, `sort`, `dedupe` and `limit`/`offset`; total matches in the `X-Total-Count` header |
| `GET` | `/jobs/{job_id}` | Fetch one job (`404 {"detail": "job not found"}` when missing) |
| `GET` | `/jobs/export` | Stream every match as `format=csv` (default, OWASP CSV-injection safe) or `format=jsonl` |
| `GET` | `/jobs/feed.atom` | Atom 1.0 feed of the newest distinct matches (stable entry ids) |
| `POST` | `/jobs/match` | Rank jobs against resume text: `match_score`, `matched_skills`, `missing_skills`, `explanation`; `?format=csv` |

Shared filters: `q` (each term in title/company/location), `company`, `location`, `remote`, `min_score`, `source_config_id`, `run_id`, `created_after` (ISO-8601), `hours_old`. `/jobs` and `/jobs/export` also take `sort=newest|score` and `dedupe=true|false`; the feed is always deduplicated. Without parameters `GET /jobs` still returns the 50 newest jobs. Semantics, recipes and security notes: [Job Search, Export & Atom Feed Guide](guides/JOB_SEARCH_EXPORT_GUIDE.md).

Job payloads include deterministic `agent_decision` traces and optional `llm_enrichment` when provider enrichment is enabled.

`POST /jobs/match` takes a JSON body (`Content-Type: application/json`, at most 1 MiB):
`resume_text` (required, 1–50,000 characters, plain text), the shared filters above,
`dedupe` (default `true`), `sort=match|blend`, `limit` (1–500, default 20), `min_match`
and `include_extra_skills`. Skills are extracted deterministically from the resume and from
each job's title and description-like `raw` fields with a curated alias-aware lexicon;
`match_score` is the share of the posting's skills found on the resume and
`blend_score = 0.7 * match_score + 0.3 * score`. The response carries `resume_sha256`,
`resume_skills`, `implied_skills`, `total` (also `X-Total-Count`) and the ranked jobs (every
`GET /jobs` field plus `rank`, `match_score`, `blend_score`, `matched_skills`,
`missing_skills`, `extra_skills`, `explanation`). Errors: `413` for a body over 1 MiB, `415`
for a non-JSON body, `422` for invalid fields (inputs are never echoed). The resume is never
stored or logged (only its SHA-256 digest is logged). Details:
[Resume-to-Job Match Guide](guides/RESUME_JOB_MATCH_GUIDE.md).

## MCP (stdio)

The same data is available read-only to AI assistants through the Model Context Protocol:
`career-search-mcp` (or `python -m autoapply_agent.mcp`) speaks newline-delimited JSON-RPC
2.0 on stdio, protocol `2026-07-28` plus the `2025-11-25` / `2025-06-18` `initialize`
handshake.

| Tool | HTTP equivalent |
|---|---|
| `search_jobs` | `GET /jobs` (same filters, `sort`, `dedupe`, `limit` ≤ 50 / `offset`, total in the result) |
| `get_job` | `GET /jobs/{job_id}`, with the decision trace unpacked |
| `explain_job_score` | — (score breakdown recomputed by the deterministic scorer) |
| `list_runs` | — (runs newest first, with job counts) |
| `get_run` | `GET /runs/{run_id}` + the most recent `GET /runs/{run_id}/events` |
| `list_sources` | `GET /source-configs`, with job counts |
| `match_resume_to_jobs` | `POST /jobs/match` (same ranking; `limit` ≤ 50) |

There are no MCP tools for the routes that change state (`POST /source-configs`, `PATCH`,
`POST /runs`, `POST /runs/{run_id}/cancel`); `POST /jobs/match` only reads. Reference, client
configuration and privacy notes: [MCP Server Guide](guides/MCP_SERVER_GUIDE.md).

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
curl -s "http://127.0.0.1:8000/jobs?run_id=$RUN_ID&remote=true&sort=score&limit=10"
curl -s -OJ "http://127.0.0.1:8000/jobs/export?format=csv&run_id=$RUN_ID"
curl -s "http://127.0.0.1:8000/jobs/feed.atom?q=python&min_score=0.7"
jq -n --rawfile resume resume.txt '{resume_text: $resume, remote: true}' \
  | curl -s "http://127.0.0.1:8000/jobs/match" -H "content-type: application/json" -d @-
```
