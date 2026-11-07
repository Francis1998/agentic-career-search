# Portfolio walkthrough: one job search, end to end

This walkthrough follows one realistic search from an empty database to a triaged
shortlist, an alert feed and a duplicate-free re-run. Every command below was run for
real on 2026-11-07 against two public boards, GitLab (Greenhouse) and Palantir (Lever).
The complete, unedited session is in
[`PORTFOLIO_WALKTHROUGH_TRANSCRIPT.txt`](PORTFOLIO_WALKTHROUGH_TRANSCRIPT.txt). Postings
change daily, so your titles and counts will differ.

## The scenario

Maya is a backend engineer looking for **remote Python/backend roles**. She wants:

1. an explainable shortlist, not just a list of links;
2. a spreadsheet she can triage;
3. an alert when new matching postings appear;
4. no duplicates when she re-runs the search every day.

Tools used: `uv`, `curl`, `jq`, `xmllint` and `python3`. No API keys are needed;
LLM enrichment is optional (step 11).

## 1. Start the service

```bash
uv sync --extra dev --frozen
DATABASE_URL=sqlite+aiosqlite:///./walkthrough.db \
  uv run uvicorn autoapply_agent.main:app --port 8000 --log-level warning &
# Wait up to 10 s for the server to accept connections
for _ in $(seq 50); do curl -sf localhost:8000/health/live >/dev/null && break; sleep 0.2; done
curl -s localhost:8000/health/ready
```

```text
{"status":"ready"}
```

Continue only once this prints `{"status":"ready"}`. Empty output means the server did not
start: check the uvicorn output, for example for a port that is already in use. The
in-process worker starts with the API and polls for queued runs.

## 2. Register the boards she cares about

Each board is a *source config* that selects one of the 119 adapters by `source_type`.

```bash
curl -s -X POST localhost:8000/source-configs -H 'content-type: application/json' \
  -d '{"name":"gitlab","source_type":"greenhouse","base_url":"https://boards.greenhouse.io/gitlab"}' \
  | jq -c '{id, name, source_type}'
curl -s -X POST localhost:8000/source-configs -H 'content-type: application/json' \
  -d '{"name":"palantir","source_type":"lever","base_url":"https://jobs.lever.co/palantir"}' \
  | jq -c '{id, name, source_type}'
```

```text
{"id":1,"name":"gitlab","source_type":"greenhouse"}
{"id":2,"name":"palantir","source_type":"lever"}
```

## 3. Start an agentic discovery run

```bash
curl -s -X POST localhost:8000/runs -H 'content-type: application/json' \
  -d '{"query":"backend engineer python remote"}' | jq -r .id | tee run_id.txt
# Poll for up to 60 s until the run reaches a terminal state
for _ in $(seq 120); do
  state=$(curl -s localhost:8000/runs/$(cat run_id.txt) | jq -r .status)
  case "$state" in completed|failed|cancelled) break ;; esac
  sleep 0.5
done
curl -s localhost:8000/runs/$(cat run_id.txt) | jq -c '{status, started_at, finished_at, error_message}'
```

```text
f26996a3-ce5e-4230-ac1f-65b150c108c0
{"status":"completed","started_at":"2026-11-07T08:53:53.594746","finished_at":"2026-11-07T08:53:54.200458","error_message":null}
```

The run moved `queued → running → completed`. With the default
`MAX_JOBS_PER_SOURCE=50`, each board contributed up to 50 postings. Continue only once
the status is `completed`. `failed` comes with an `error_message`. A run still `queued`
or `running` after the loop is just slow, so poll again.

## 4. See what the agent did

Every step is a persisted, ordered run event:

```bash
curl -s localhost:8000/runs/$(cat run_id.txt)/events | jq -r '.[].event_type' | sort | uniq -c
```

```text
 100 agent.decision
   1 run.completed
   1 run.created
   1 run.started
   2 source.completed
   2 source.started
```

One `agent.decision` per posting, plus lifecycle and per-source events. A failing board
would show `source.failed` instead of aborting the run.

## 5. Read the decision trace

The best-scored jobs, with the deterministic trace each one carries:

```bash
curl -s 'localhost:8000/jobs?sort=score&limit=3' | jq -c '.[] | {title, company, location, score,
  tier: .raw.agent_decision.priority_tier, matched: .raw.agent_decision.matched_query_terms}'
```

```text
{"title":"Backend Engineer (Python),AI Engineering: Agent Foundations","company":"gitlab","location":"Remote, Canada; Remote, Poland; Remote, United Kingdom","score":0.9204,"tier":"high","matched":["backend","engineer","python","remote"]}
{"title":"Backend Engineer, Source Code: Repository Services (Ruby)","company":"gitlab","location":"Remote, United Kingdom","score":0.8418,"tier":"high","matched":["backend","engineer","remote"]}
{"title":"Senior Backend Engineer, AI Engineering: Chat","company":"gitlab","location":"Remote, United Kingdom","score":0.8282,"tier":"high","matched":["backend","engineer","remote"]}
```

The rationale explains *why* the top job ranks first:

```bash
curl -s 'localhost:8000/jobs?limit=1&sort=score' | jq -r '.[0].raw.agent_decision.rationale[]'
```

```text
Priority tier set to high from deterministic score.
Role title considered: Backend Engineer (Python),AI Engineering: Agent Foundations.
Matched query terms: backend, engineer, python, remote.
Location signal observed: Remote, Canada; Remote, Poland; Remote, United Kingdom.
```

## 6. Search the shortlist

The [search API](JOB_SEARCH_EXPORT_GUIDE.md) filters stored jobs without re-scraping.
The total match count comes back in a header:

```bash
curl -s -D - -o /dev/null 'localhost:8000/jobs?remote=true&q=engineer' | grep -i x-total-count
curl -s 'localhost:8000/jobs?remote=true&q=engineer&sort=score&limit=5' \
  | jq -r '.[] | [.score, .company, .title] | @tsv'
```

```text
x-total-count: 29
0.9204	gitlab	Backend Engineer (Python),AI Engineering: Agent Foundations
0.8418	gitlab	Backend Engineer, Source Code: Repository Services (Ruby)
0.8282	gitlab	Senior Backend Engineer, AI Engineering: Chat
0.8166	gitlab	Senior Backend Engineer, Core DevOps
0.8096	gitlab	Backend Engineer, Source Code: Repository Services (Ruby)
```

## 7. Narrow by company

```bash
curl -s 'localhost:8000/jobs?company=palantir&q=engineer&sort=score&limit=3' \
  | jq -r '.[] | [.score, .title, .location] | @tsv'
```

```text
0.6427	Forward Deployed Infrastructure Engineer, New Grad - US Government	New York, NY
0.6416	Forward Deployed Infrastructure Engineer - US Government	Washington, D.C.
0.6378	Forward Deployed Security Engineer - US Government	Washington, D.C.
```

These Palantir roles are on-site, which is why they score lower against a "remote"
query.

## 8. Export the shortlist for spreadsheet triage

```bash
csv_file=$(curl -s -OJ -w '%{filename_effective}' \
  'localhost:8000/jobs/export?format=csv&min_score=0.8&sort=score')
echo "$csv_file"
python3 - "$csv_file" <<'EOF'
import csv, sys

with open(sys.argv[1], newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
print(len(rows), "rows")
for row in rows[:3]:
    print(row["score"], row["company"], row["title"], row["remote"], sep=" | ")
EOF
```

```text
jobs-20261107T085354Z.csv
6 rows
0.9204 | gitlab | Backend Engineer (Python),AI Engineering: Agent Foundations | true
0.8418 | gitlab | Backend Engineer, Source Code: Repository Services (Ruby) | true
0.8282 | gitlab | Senior Backend Engineer, AI Engineering: Chat | true
```

`curl -OJ` saves the file under the server's timestamped name, and
`-w '%{filename_effective}'` reports that name, so the script reads exactly this export
and never an older `jobs-*.csv` in the same directory.

The CSV is safe to open in Excel or Google Sheets: cells that start with formula
characters are neutralized, and only http(s) links are emitted.

## 9. Subscribe to new matches

First, a short preview of the two newest entries:

```bash
curl -s 'localhost:8000/jobs/feed.atom?remote=true&q=engineer&limit=2' \
  | xmllint --format - | grep -E '<(title|updated)>'
```

```text
  <title>Agentic Career Search jobs (q=engineer, remote=true)</title>
  <updated>2026-11-07T08:53:53Z</updated>
    <title>Intermediate Fullstack Engineer (Ruby/Vue.js), Growth at gitlab</title>
    <updated>2026-11-07T08:53:53Z</updated>
    <title>Senior Backend Engineer, Core DevOps at gitlab</title>
    <updated>2026-11-07T08:53:53Z</updated>
```

`limit=2` only keeps the preview short. To subscribe, Maya drops it and uses the
default window of 50 entries (`limit` accepts up to 200):

```text
http://localhost:8000/jobs/feed.atom?remote=true&q=engineer
```

She adds this URL to her feed reader, or runs `/feed subscribe <url>` in Slack once the
API sits behind an HTTPS proxy. Entry ids are stable per posting, so she is notified once
per posting even when later runs capture it again.

A feed only lists its newest `limit` distinct matches. If more new matches arrive between
two polls, the reader never sees the oldest of them. Pick a window larger than the number
of new matches you expect per polling interval (feed readers typically poll every 15–60
minutes). For a gap-free check, page through `GET /jobs?remote=true&q=engineer&dedupe=true`
instead. It lists postings by when each was first seen, newest first, so stop at the first
posting you already know.

## 10. Re-run the next day without duplicates

Every run re-captures the postings that are still open, so the raw count doubles. With
`dedupe=true`, the search collapses re-captures and cross-board mirrors to one row per
posting:

```bash
curl -s -X POST localhost:8000/runs -H 'content-type: application/json' \
  -d '{"query":"backend engineer python remote"}' | jq -r .id > run2_id.txt
# Same bounded wait as in step 3, for the new run
for _ in $(seq 120); do
  state=$(curl -s localhost:8000/runs/$(cat run2_id.txt) | jq -r .status)
  case "$state" in completed|failed|cancelled) break ;; esac
  sleep 0.5
done
echo "$state"
curl -s -D - -o /dev/null 'localhost:8000/jobs?remote=true&q=engineer' | grep -i x-total-count
curl -s -D - -o /dev/null 'localhost:8000/jobs?remote=true&q=engineer&dedupe=true' | grep -i x-total-count
```

```text
completed
x-total-count: 58
x-total-count: 29
```

## 11. Cancel a run she no longer needs

```bash
RUN=$(curl -s -X POST localhost:8000/runs -H 'content-type: application/json' \
  -d '{"query":"site reliability"}' | jq -r .id)
curl -s -X POST localhost:8000/runs/$RUN/cancel | jq -c '{status, cancel_requested}'
```

```text
{"status":"cancelled","cancel_requested":true}
```

A queued run is cancelled immediately. A running run moves to `cancel_requested`, and the
worker stops at its next checkpoint, before the next source or job.

## 12. Optional: LLM enrichment

To add a short model-written assessment to each decision trace (under
`raw.llm_enrichment`, with an `agent.llm_enrichment` event), set a provider before
starting the API. The defaults track the current model line-ups; see the README's
*LLM enrichment* section.

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=claude          # or gpt / gemini / kimi
CLAUDE_API_KEY=...           # CLAUDE_MODEL defaults to claude-haiku-5-5
```

This step was not executed here because no API keys were used. Provider failures degrade
to the deterministic trace.

## What this demonstrates

| Capability | Where it showed up |
|---|---|
| Observe → decide → act agent loop | Steps 3–5: adapters fetch, the decision engine scores, results and events persist |
| Explicit run state machine with cooperative cancellation | Steps 3 and 11 |
| Durable, ordered event log for debugging | Step 4 |
| Explainable ranking | Step 5: score, tier, matched terms, rationale |
| Pluggable adapters over messy real-world markup | Step 2: Greenhouse and Lever boards, live |
| Product-grade API design | Steps 6–10: filters, paging header, dedupe, CSV/JSONL, Atom |
| Security hygiene | Step 8: OWASP CSV-injection defenses; http(s)-only links |

## Reproduce

Run the commands above from the repository root, then clean up only the files this
walkthrough created:

```bash
kill %1                                  # stop the API started in step 1
rm -f walkthrough.db run_id.txt run2_id.txt
rm -f -- "$csv_file"                     # the step 8 export; other jobs-*.csv files are kept
```
