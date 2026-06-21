# QUICKSTART

## 0) Prerequisites

- Python `3.11+`
- `uv` installed
- Network access to public career pages

## 1) Install

```bash
# From the repository root:
uv venv
source .venv/bin/activate
uv sync --extra dev --frozen
cp .env.example .env
```

## 2) Run API

```bash
uv run uvicorn autoapply_agent.main:app --reload
```

Health checks:

```bash
curl -s "http://127.0.0.1:8000/health/live"
curl -s "http://127.0.0.1:8000/health/ready"
```

## 3) Configure a source

```bash
curl -X POST "http://127.0.0.1:8000/source-configs" \
  -H "content-type: application/json" \
  -d '{
    "name": "example-greenhouse",
    "source_type": "greenhouse",
    "base_url": "https://boards.greenhouse.io/embed/job_board?for=example"
  }'
```

## 4) Create a run

```bash
RUN_ID=$(curl -s -X POST "http://127.0.0.1:8000/runs" \
  -H "content-type: application/json" \
  -d '{"query":"python backend"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "$RUN_ID"
```

## 5) Track run and results

```bash
curl -s "http://127.0.0.1:8000/runs/$RUN_ID"
curl -s "http://127.0.0.1:8000/runs/$RUN_ID/events"
curl -s "http://127.0.0.1:8000/jobs?run_id=$RUN_ID"
```

## 6) Optional: cancel an active run

```bash
curl -s -X POST "http://127.0.0.1:8000/runs/$RUN_ID/cancel"
```

## 7) Optional: enable LLM provider enrichment

Add to `.env` before starting the API:

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=gemini   # or kimi / claude
GEMINI_API_KEY=your_key_here
```

When enabled, run events include `agent.llm_enrichment`, and job payloads contain `llm_enrichment`.

## 8) Local quality checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```
