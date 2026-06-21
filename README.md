# agentic-career-search

![CI](https://github.com/Francis1998/agentic-career-search/actions/workflows/ci.yml/badge.svg) ![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB) ![FastAPI](https://img.shields.io/badge/framework-FastAPI-009688) ![License](https://img.shields.io/badge/license-MIT-green)

AI-agent-oriented backend for autonomous job discovery and explainable decision workflows.

## Why teams use this

This project solves a common failure mode in job-search automation: lots of scraping, little trust.

Instead of opaque outputs, you get:
- deterministic scoring with rationale traces,
- explicit run lifecycle states and event logs,
- pluggable adapters for external sources,
- optional LLM enrichment (Gemini, Kimi, Claude),
- production-style quality gates (ruff, mypy, pytest, CI).

## Real use cases (issue -> solution)

| Problem | Why it blocks adoption | How this repo solves it |
|---|---|---|
| “We can scrape jobs but can’t explain ranking decisions.” | Stakeholders cannot trust automation output. | `AgentDecisionEngine` persists score, matched terms, priority tier, and rationale per job. |
| “Agent runs fail silently.” | Debugging and reliability regress quickly. | Run timeline events (`run.*`, `source.*`, `agent.*`) give a replayable execution trail. |
| “Switching model vendors is painful.” | Provider lock-in slows experimentation. | Configurable LLM enrichment layer consumes outputs from Gemini/Kimi/Claude with graceful fallback. |
| “Pipelines break under API/provider instability.” | Operational noise and false negatives. | Deterministic baseline still produces usable decisions when LLM enrichment is unavailable. |
| “Docs don’t convince users this is production-minded.” | Hard to onboard collaborators and reviewers. | Architecture, configuration, safety, deployment, and troubleshooting docs are included. |

## Agent architecture

```mermaid
flowchart LR
    A[POST /runs] --> B[queued]
    B --> C[worker claims run]
    C --> D[source adapters fetch jobs]
    D --> E[AgentDecisionEngine]
    E --> F[optional LLM enrichment]
    F --> G[persist jobs + event logs]
    G --> H[GET /runs/{id}/events and GET /jobs]
```

## LLM integration

The code supports consumption of provider outputs from:
- Gemini API
- Kimi (Moonshot, OpenAI-compatible)
- Claude (Anthropic Messages API)

Enable with environment variables:

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=gemini   # or kimi / claude
```

Then configure matching provider keys in `.env` (see `CONFIGURATION.md`).

## Quick start

```bash
git clone https://github.com/Francis1998/agentic-career-search.git
cd agentic-career-search
uv venv
source .venv/bin/activate
uv sync --extra dev --frozen
cp .env.example .env
uv run uvicorn autoapply_agent.main:app --reload
```

## API snapshot

- `POST /source-configs` create source adapter configs
- `GET /source-configs` list enabled sources
- `POST /runs` enqueue autonomous run
- `GET /runs/{run_id}` inspect run state
- `GET /runs/{run_id}/events` inspect event timeline
- `POST /runs/{run_id}/cancel` request cancellation
- `GET /jobs` inspect normalized/scored/enriched outputs
- `GET /health/live` and `GET /health/ready`

## Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Core agent architecture and lifecycle |
| [CONFIGURATION.md](CONFIGURATION.md) | Runtime and provider configuration |
| [QUICKSTART.md](QUICKSTART.md) | Fast local setup and verification |
| [SAFETY.md](SAFETY.md) | Scope boundaries and operational guardrails |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment guidance |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common failure recovery paths |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## License

MIT © [Francis1998](https://github.com/Francis1998)
