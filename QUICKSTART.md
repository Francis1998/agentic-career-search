# QUICKSTART

## 1) Install

```bash
# From the repository root:
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
```

## 2) Run API

```bash
uv run uvicorn autoapply_agent.main:app --reload
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
