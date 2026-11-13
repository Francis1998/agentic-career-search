# SAFETY

## Scope and Safety Boundaries

- This project only fetches public career pages over HTTP.
- No login, account handling, CAPTCHA bypass, or anti-bot evasion is implemented.
- No browser credential automation is included.
- No hidden background submission behavior is implemented.

## Operational Controls

- Adapter requests use explicit timeouts.
- Source-level and run-level failures are persisted as events.
- Runs support cancellation and surface cancellation events.
- Per-source result volume is bounded by configuration (`MAX_JOBS_PER_SOURCE`).
- The MCP server (`career-search-mcp`) is read-only: its tools search and explain stored
  jobs and runs but cannot start or cancel runs, edit sources or apply; SQLite connections
  run `PRAGMA query_only`, and logs/audit records never contain tool arguments or results.
- Resume matching (`POST /jobs/match`, MCP `match_resume_to_jobs`) is bounded: request
  bodies are capped at 1 MiB while they stream in (`413`), `resume_text` at 50,000
  characters, results at `limit` ≤ 500 (MCP 50), and 20,000 characters of each posting are
  scanned.

## Data Handling

- Persisted data includes fetched posting metadata and deterministic scoring/planning outputs.
- Avoid storing secrets in source configs.
- Use `.env` for local configuration and keep it out of git.
- Resume text sent to `POST /jobs/match` or `match_resume_to_jobs` is processed in memory
  for that request only: it is never written to the database, logs or the MCP audit log,
  and validation errors never echo it. The API logs one line per match with the SHA-256
  digest of the resume and counts; the audit log keeps its keyed argument hash.

## Responsible Use

- Respect career-site terms of service and robots policies.
- Keep request rates conservative to avoid degrading target systems.
- Treat agent decisions as assistive triage, not automatic truth.
- Manually review high-priority postings before downstream actions.
- Skills-profile fit scores are assistive triage signals, not auto-apply triggers.
- Resume match scores are keyword-coverage evidence for triage, not predictions of hiring
  outcomes; matching never applies, contacts employers or edits the resume.
- Salary-band estimates are assistive triage signals, not offers, market truth, or legal advice.
- Application stage tracking is local pipeline state only; it never submits applications or contacts employers.
- Interview-prep briefs are assistive coaching content, not recruiter outreach or scheduling automation.
- Equity vesting/cliff math is assistive triage only — never auto-accepts offers or writes broker orders.
- Interview-round progress tracking is local pipeline state only; it never advances candidates or contacts employers.
- Remote timezone-overlap bands are assistive triage signals, not auto-apply or calendar-write triggers.
