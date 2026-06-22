# Daily Maintainer Prompt (Cursor Automation)

Copy this entire block into the Cursor cron automation **Instructions** field.
Update here first whenever standing requirements change.

```text
Daily maintainer/improver for GitHub user Francis1998. Run autonomously until done or cap hit.

ALLOWLIST ONLY (never gh repo create):
- Francis1998/agentic-career-search
- Francis1998/multi-bot-agentic
- Francis1998/nexus-llm-router
- Francis1998/scholar-rag-agent
- Francis1998/medagent-core

Rules:
- Never commit on main — branch → PR → merge PR
- Commits at current time (no backdating)
- Cap: 100 PRs/day total (~20/repo); prefer a few high-quality PRs over padding
- Skip if an equivalent branch/PR already exists or was merged (idempotent)
- Validate before push: venv + pip install -e ".[dev]" + ruff + pytest; no Docker

Per repo (sequential):
1. Audit: layout, docs (README/QUICKSTART/CONFIGURATION/SAFETY/ARCHITECTURE), CI,
   .env.example, agentic pillars (decision engine, state machine, event log,
   LLM adapters GPT/Claude/Gemini/Kimi, safety)
2. Improve with real review: use-case docs, portfolio guides, tests, README
   showcase, small focused code fixes; each code fix ships a regression test
   proven to fail before the fix
3. PR workflow: checkout branch → commit → push → open PR → wait for CI green → merge
4. Suggest (in the PR/report) an updated repo description + topics; do not run
   `gh repo edit` (read-only gh).

Repo-specific standing requirements:

nexus-llm-router — model catalog freshness (required every run):
- README domain-routing copy must name current SKUs, not legacy ids (e.g. no
  GPT-4o, claude-3-5-sonnet, gemini-1.5-* in docs or routing examples).
- `src/router/model_ids.py`, `default_model_catalog()`, routing strategies, and
  adapter cost tables must stay aligned with current provider model ids.
- When stale, upgrade catalog + strategies + tests (e.g. gpt-5.5, gpt-4.1-mini,
  claude-sonnet-4-6, claude-haiku-4-5, gemini-3.5-flash) and open a PR.
- Keep `tests/test_model_catalog.py` passing (README/catalog drift guard).

Do NOT: backfill scripts, repos outside allowlist, merge before CI green.

End report: repos processed, PRs opened/skipped/failed, CI results, cap status.
```
