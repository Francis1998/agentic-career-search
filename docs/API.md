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

Shared filters: `q` (each term in title/company/location), `company`, `location`, `remote`, `min_score`, `source_config_id`, `run_id`, `created_after` (ISO-8601), `hours_old`, and the pay filters below. `/jobs` and `/jobs/export` also take `sort=newest|score|salary` and `dedupe=true|false`; the feed is always deduplicated. Without parameters `GET /jobs` still returns the 50 newest jobs. Semantics, recipes and security notes: [Job Search, Export & Atom Feed Guide](guides/JOB_SEARCH_EXPORT_GUIDE.md).

Job payloads include deterministic `agent_decision` traces and optional `llm_enrichment` when provider enrichment is enabled.

### Pay filters and fields

Pay stated by the posting (schema.org `baseSalary`, else the description text) is captured
for new jobs: `raw.compensation` holds `min_amount`, `max_amount`, `currency`, `interval`,
`annual_min`, `annual_max`, `source` (`structured` | `description`) and `snippet`, and
every job has `salary_min_annual`, `salary_max_annual`, `salary_currency` and
`salary_interval` (all `null` without pay). Annual factors: hour ×2080, day ×260, week ×52,
month ×12.

| Parameter | Values | Meaning |
|---|---|---|
| `salary_currency` | ISO 4217 code, case-insensitive | Only jobs paying in this currency |
| `min_salary` | integer 0 – 2^63-1 | Overlap: `salary_max_annual >= min_salary` |
| `max_salary` | integer 0 – 2^63-1 | Overlap: `salary_min_annual <= max_salary` |
| `has_salary` | `true` / `false` | Only jobs with / without captured pay |
| `sort=salary` | — | Highest `salary_max_annual` first, ties newest first, no pay last |

`min_salary`, `max_salary` and `sort=salary` **require** `salary_currency` (amounts are
never converted or compared across currencies); otherwise, for an unknown currency code or
for `min_salary > max_salary`, the response is `422` with
`{"detail": [{"type": "value_error", "loc": ["query", "salary_currency"], "msg": "min_salary needs salary_currency ..."}]}`.
The CSV export appends `salary_min`, `salary_max`, `salary_interval`, `salary_currency`,
`salary_min_annual`, `salary_max_annual`, `salary_source`; Atom summaries add `Pay: ...`.
Details: [Pay Transparency Guide](guides/PAY_TRANSPARENCY_GUIDE.md).

`POST /jobs/match` takes a JSON body (`Content-Type: application/json`, at most 1 MiB):
`resume_text` (required, 1–50,000 characters, plain text), the shared filters above
(pay filters included, errors at `["body", ...]`),
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

## Applications

Track captured jobs through `saved → applied → interview → offer → accepted / rejected`
(local bookkeeping only; nothing is submitted). Legal moves: `saved → applied | rejected`,
`applied → interview | rejected`, `interview → offer | rejected`, `offer → accepted |
rejected`; `accepted` and `rejected` are final. Ids must be 1..2^63-1; datetimes without an
offset are UTC. Errors are `{"detail": ...}`.

- `POST /applications` body `{job_id, stage?, notes?, note?, applied_at?, next_action_at?,
  next_action?}` → `201` + `Location`; `404` unknown job; `409` (with `Location`) when the
  job, or another capture of the same posting URL, is already tracked; `422` invalid fields
  (`notes` ≤ 10,000, `note` ≤ 2,000, `next_action` ≤ 200 single-line, `applied_at` not in
  the future, unknown fields).
- `GET /applications` filters `stage` (repeatable), `company`, `q`,
  `follow_up=overdue|due|scheduled|none`, `due_within_days` (0–366, default 7),
  `include_archived`, `job_id`, `sort=updated|created|next_action|applied|score`,
  `limit` (1–500, default 50) / `offset`; total in `X-Total-Count`.
- `GET /applications/board` same filters + `per_stage` (1–100, default 20): six stage
  columns in pipeline order with counts and cards, plus `follow_ups` counts.
- `GET /applications/{id}`; `PATCH /applications/{id}` with any of `stage`, `note`,
  `notes`, `applied_at`, `next_action_at`, `next_action` (`null` clears) → `409` for an
  illegal move or a concurrent update (nothing changes; retry the latter); one timeline
  event per request.
- `GET /applications/{id}/events` append-only timeline (`tracked`, `stage_changed`,
  `updated`, `note_added`, `archived`, `unarchived`), oldest first.
- `POST /applications/{id}/archive` / `POST /applications/{id}/unarchive` optional body
  `{note}`; idempotent; `409` when a concurrent update won the race (retry).
- `GET /applications/export?format=csv|jsonl` list filters + optional `limit`
  (1–100,000): attachment, CSV-injection safe, `X-Total-Count`.
- `GET /applications/calendar.ics` list filters + `limit` (1–10,000, default 1,000):
  iCalendar feed of follow-ups (30-minute free events; notes never included).

Details: [Application Tracker Guide](guides/APPLICATION_TRACKER_GUIDE.md).

## Schedules

Recurring discovery runs: the run parameters of `POST /runs` plus a cadence. The in-process
scheduler (`ENABLE_SCHEDULER`, `SCHEDULER_TICK_SECONDS`) queues a normal run when one is
due, applies the overlap policy and coalesces missed fires into one run. Schedules only
discover and score jobs. Errors are `{"detail": ...}`; invalid input is the standard `422`
list with types such as `cron_invalid`, `timezone_invalid` and `schedule_cadence`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/schedules` | Create a schedule → `201` + `Location`; `409` name taken |
| `GET` | `/schedules` | List (`paused`, `kind`, `q`, `limit` 1–200 / `offset`; `X-Total-Count`), soonest next fire first |
| `GET` | `/schedules/preview` | Dry-run `cron` in `timezone` (`count` 1–20, `after`): next fires in UTC and local time |
| `GET` | `/schedules/{schedule_id}` | One schedule + `last_run_status` + next five fires (`upcoming`) |
| `PATCH` | `/schedules/{schedule_id}` | Change name, `query`, `source_config_ids`, cadence, `overlap_policy`, `jitter_seconds` |
| `DELETE` | `/schedules/{schedule_id}` | Delete it and its history (`204`); its runs and jobs stay |
| `POST` | `/schedules/{schedule_id}/pause` | Pause, optional body `{note}` (idempotent; drops a buffered fire) |
| `POST` | `/schedules/{schedule_id}/resume` | Resume from the next fire after now (no catch-up) |
| `POST` | `/schedules/{schedule_id}/trigger` | Run now honouring the overlap policy: `outcome` `triggered` / `buffered` / `skipped_overlap` (`409` on a concurrent fire) |
| `GET` | `/schedules/{schedule_id}/history` | Append-only history newest first (`kind` repeatable, `limit` 1–500 / `offset`; `X-Total-Count`) |

- `POST /schedules` body `{name, query?, source_config_ids?, interval_minutes | cron, kind?,
  timezone?, start_at?, overlap_policy?, jitter_seconds?, paused?, pause_note?}`:
  `interval_minutes` 15–43,200 (anchored at `start_at`, default the next second, so it fires
  on the next tick); `cron` five fields or `@hourly`/`@daily`/`@weekly`/`@monthly`/`@yearly`,
  at least 15 minutes between fires, evaluated in the IANA `timezone` (default `UTC`;
  nonexistent local times are skipped, repeated ones fire once); `overlap_policy`
  `skip` (default) or `buffer_one`; `jitter_seconds` 0–600; `query` and
  `source_config_ids` are validated exactly like `POST /runs`; unknown fields are `422`.
- History kinds: `fired`, `coalesced_misfire` (`details.missed_fires`), `triggered`,
  `buffered`, `skipped_overlap`, `paused`, `resumed`; each has `scheduled_for`, `run_id`,
  `reason` and `details`. Runs a schedule queues carry `run.created` with
  `{schedule_id, schedule_name, trigger, scheduled_for}`.

Details: [Run Schedules Guide](guides/RUN_SCHEDULES_GUIDE.md).

## MCP (stdio)

The same data is available read-only to AI assistants through the Model Context Protocol:
`career-search-mcp` (or `python -m autoapply_agent.mcp`) speaks newline-delimited JSON-RPC
2.0 on stdio, protocol `2026-07-28` plus the `2025-11-25` / `2025-06-18` `initialize`
handshake.

| Tool | HTTP equivalent |
|---|---|
| `search_jobs` | `GET /jobs` (same filters incl. pay, `sort=newest\|score\|salary`, `dedupe`, `limit` ≤ 50 / `offset`, total in the result; each job has a `pay` object or `null`) |
| `get_job` | `GET /jobs/{job_id}`, with the decision trace unpacked and the stated `pay` |
| `explain_job_score` | — (score breakdown recomputed by the deterministic scorer) |
| `list_runs` | — (runs newest first, with job counts) |
| `get_run` | `GET /runs/{run_id}` + the most recent `GET /runs/{run_id}/events` |
| `list_sources` | `GET /source-configs`, with job counts |
| `match_resume_to_jobs` | `POST /jobs/match` (same ranking; `limit` ≤ 50) |
| `list_applications` | `GET /applications` (same filters; `limit` ≤ 50) + board and follow-up counts |
| `get_application` | `GET /applications/{id}` + its most recent `GET /applications/{id}/events` |
| `list_schedules` | `GET /schedules` (`paused`, `kind`; `limit` ≤ 50) |
| `get_schedule` | `GET /schedules/{id}` (next five fires) + its most recent `GET /schedules/{id}/history` |

There are no MCP tools for the routes that change state (`POST /source-configs`, `PATCH`,
`POST /runs`, `POST /runs/{run_id}/cancel`, `POST`/`PATCH /applications...`, `POST`/`PATCH`/`DELETE /schedules...`); `POST /jobs/match`
only reads. Reference, client
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
