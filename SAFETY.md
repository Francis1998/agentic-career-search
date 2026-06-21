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

## Data Handling

- Persisted data includes fetched posting metadata and deterministic scoring/planning outputs.
- Avoid storing secrets in source configs.
- Use `.env` for local configuration and keep it out of git.

## Responsible Use

- Respect career-site terms of service and robots policies.
- Keep request rates conservative to avoid degrading target systems.
- Treat agent decisions as assistive triage, not automatic truth.
- Manually review high-priority postings before downstream actions.
