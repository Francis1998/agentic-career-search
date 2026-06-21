# SAFETY

## Scope and Safety Boundaries

- This project only fetches public career pages over HTTP.
- No login, account handling, CAPTCHA bypass, or anti-bot evasion is implemented.
- No browser credential automation is included.

## Operational Controls

- Adapter requests use explicit timeouts.
- Source-level and run-level failures are persisted as events.
- Runs support cancellation and surface cancellation events.

## Data Handling

- Persisted data includes fetched posting metadata and deterministic scoring/planning outputs.
- Avoid storing secrets in source configs.
- Use `.env` for local configuration and keep it out of git.
