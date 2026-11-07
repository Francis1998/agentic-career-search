"""Tool tests for the read-only MCP server against seeded SQLite databases.

``search_jobs`` is checked against ``GET /jobs`` on the job-search test fixtures, and the
detail, explanation and run tools against a database filled by the real discovery
pipeline (``scripts/seed_mcp_demo.py``: worker, scoring, decision traces, run events).
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.mcp.database import open_read_only_database
from autoapply_agent.mcp.schema import validate
from autoapply_agent.mcp.server import CareerSearchMcpServer
from autoapply_agent.mcp.tools import TOOLS_BY_NAME
from autoapply_agent.services.agent_decision import AgentDecisionEngine
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService
from tests.integration.test_jobs_search_api import (
    BASE_TIME,
    HOSTILE_JOBS,
    SEED_JOBS,
    _client_for,
    _seed,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = REPO_ROOT / "scripts" / "seed_mcp_demo.py"
META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
}
ACME_URL = "https://boards.greenhouse.io/acme/jobs/4101"
PIPER_URL = "https://jobs.lever.co/piedpiper/python-developer"


def load_seed_module() -> ModuleType:
    """Load ``scripts/seed_mcp_demo.py`` as a module."""

    spec = importlib.util.spec_from_file_location("seed_mcp_demo_script", SEED_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def call_tool(
    server: CareerSearchMcpServer, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call one tool with a modern request and return the ``result`` member."""

    response = await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments, "_meta": META},
        }
    )
    assert response is not None
    assert "result" in response, response
    result: dict[str, Any] = response["result"]
    return result


async def structured(
    server: CareerSearchMcpServer, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call a tool that must succeed and return its ``structuredContent``."""

    result = await call_tool(server, name, arguments)
    assert result["isError"] is False, result["content"][0]["text"]
    content: dict[str, Any] = result["structuredContent"]
    assert json.loads(result["content"][1]["text"]) == content
    return content


async def call_once(database_url: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Open a read-only server on ``database_url``, call one tool and close it."""

    engine, session_factory = open_read_only_database(database_url)
    try:
        return await call_tool(CareerSearchMcpServer(session_factory), name, arguments)
    finally:
        await engine.dispose()


@pytest.fixture()
def search_db(sqlite_database_url: str) -> str:
    """The job-search test fixtures: two runs (query "python"), eight jobs."""

    asyncio.run(_seed(sqlite_database_url, SEED_JOBS))
    return sqlite_database_url


@pytest.fixture()
async def search_server(search_db: str) -> AsyncIterator[CareerSearchMcpServer]:
    """Server over the job-search fixtures."""

    engine, session_factory = open_read_only_database(search_db)
    try:
        yield CareerSearchMcpServer(session_factory)
    finally:
        await engine.dispose()


@dataclass(frozen=True)
class Pipeline:
    """A database filled by the real discovery pipeline and a server reading it."""

    server: CareerSearchMcpServer
    run_ids: list[str]
    database_path: Path


@pytest.fixture()
async def pipeline(tmp_path: Path) -> AsyncIterator[Pipeline]:
    """Two runs processed offline by the real worker (see ``scripts/seed_mcp_demo.py``)."""

    database_path = tmp_path / "pipeline.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"
    run_ids, job_total = await load_seed_module().seed_mcp_demo(database_url)
    assert job_total == 16
    engine, session_factory = open_read_only_database(database_url)
    try:
        yield Pipeline(CareerSearchMcpServer(session_factory), run_ids, database_path)
    finally:
        await engine.dispose()


async def find_job_id(pipeline: Pipeline, url: str) -> int:
    """Id of the first-run capture of the posting at ``url``."""

    page = await structured(
        pipeline.server, "search_jobs", {"run_id": pipeline.run_ids[0], "limit": 50}
    )
    return next(job["id"] for job in page["jobs"] if job["url"] == url)


# ---------------------------------------------------------------------------
# search_jobs
# ---------------------------------------------------------------------------

PARITY_CASES: list[dict[str, Any]] = [
    {},
    {"q": "PYTHON"},
    {"q": "globex berlin"},
    {"q": "100%_"},
    {"company": "acme"},
    {"location": "new york"},
    {"remote": True},
    {"remote": False},
    {"min_score": 0.9},
    {"source_config_id": 2},
    {"run_id": "run-a"},
    {"hours_old": 8},
    {"created_after": (BASE_TIME + timedelta(hours=3)).isoformat()},
    {"created_after": (BASE_TIME + timedelta(hours=3)).isoformat(), "hours_old": 6},
    {"sort": "score"},
    {"dedupe": True},
    {"dedupe": True, "sort": "score", "q": "python"},
    {"q": "python", "remote": True, "min_score": 0.89, "source_config_id": 2},
    {"limit": 3, "offset": 3},
    {"dedupe": True, "limit": 2, "offset": 4},
    {"offset": 8},
]


@pytest.mark.parametrize("arguments", PARITY_CASES, ids=[json.dumps(c) for c in PARITY_CASES])
def test_search_jobs_returns_exactly_what_get_jobs_returns(
    sqlite_database_url: str, arguments: dict[str, Any]
) -> None:
    """Same filters, sorting, dedupe and paging as the HTTP search API."""

    params = {
        key: str(value).lower() if isinstance(value, bool) else str(value)
        for key, value in arguments.items()
    }
    params.setdefault("limit", "10")
    for client in _client_for(sqlite_database_url, SEED_JOBS):
        response = client.get("/jobs", params=params)
        assert response.status_code == 200, response.text
        expected_ids = [job["id"] for job in response.json()]
        expected_total = int(response.headers["x-total-count"])

    result = asyncio.run(call_once(sqlite_database_url, "search_jobs", arguments))

    assert result["isError"] is False
    page = result["structuredContent"]
    assert [job["id"] for job in page["jobs"]] == expected_ids
    assert page["total"] == expected_total


async def test_search_jobs_pages_partition_results(search_server: CareerSearchMcpServer) -> None:
    everything = await structured(search_server, "search_jobs", {"limit": 50})
    collected: list[int] = []
    offset: int | None = 0
    while offset is not None:
        page = await structured(search_server, "search_jobs", {"limit": 3, "offset": offset})
        assert page["total"] == 8
        collected.extend(job["id"] for job in page["jobs"])
        offset = page["next_offset"]
    past_end = await call_tool(search_server, "search_jobs", {"offset": 8})

    assert collected == [job["id"] for job in everything["jobs"]]
    assert everything["next_offset"] is None
    assert past_end["structuredContent"]["jobs"] == []
    assert past_end["content"][0]["text"] == (
        "8 jobs match, but offset 8 is past the end (sort=newest, dedupe=off)."
    )


async def test_search_jobs_accepts_integral_floats_for_integers(
    search_server: CareerSearchMcpServer,
) -> None:
    page = await structured(search_server, "search_jobs", {"limit": 2.0, "offset": 1.0})

    assert (page["limit"], page["offset"], len(page["jobs"])) == (2, 1, 2)


async def test_search_jobs_dedupe_reports_first_capture(
    search_server: CareerSearchMcpServer,
) -> None:
    plain = await structured(search_server, "search_jobs", {"q": "python"})
    deduped = await structured(search_server, "search_jobs", {"q": "python", "dedupe": True})

    assert all(job["first_seen_at"] is None for job in plain["jobs"])
    assert plain["total"] == 4
    assert deduped["total"] == 2
    assert all(job["first_seen_at"] for job in deduped["jobs"])
    assert deduped["dedupe"] is True


async def test_search_jobs_reports_the_effective_time_window(
    search_server: CareerSearchMcpServer,
) -> None:
    page = await structured(search_server, "search_jobs", {"hours_old": 8})
    open_ended = await structured(search_server, "search_jobs", {})

    assert page["captured_since"] is not None
    assert page["captured_since"].endswith("Z")
    assert open_ended["captured_since"] is None


@pytest.mark.parametrize(
    ("arguments", "fragment"),
    [
        ({"created_after": "yesterday"}, "created_after must be an ISO-8601 date-time"),
        ({"created_after": "0001-01-01T00:00:00+01:00"}, "outside the supported UTC range"),
        ({"created_after": "9999-12-31T23:59:59-01:00"}, "outside the supported UTC range"),
        ({"limit": 0}, "arguments.limit must be >= 1"),
        ({"limit": 51}, "arguments.limit must be <= 50"),
        ({"offset": -1}, "arguments.offset must be >= 0"),
        ({"min_score": 1.5}, "arguments.min_score must be <= 1"),
        ({"hours_old": 0}, "arguments.hours_old must be >= 1"),
        ({"remote": "yes"}, "arguments.remote must be of type boolean"),
        ({"source_config_id": 2**63}, "arguments.source_config_id must be <="),
        ({"q": "x" * 201}, "arguments.q must be at most 200 characters"),
    ],
)
async def test_search_jobs_rejects_bad_arguments_as_tool_errors(
    search_server: CareerSearchMcpServer, arguments: dict[str, Any], fragment: str
) -> None:
    result = await call_tool(search_server, "search_jobs", arguments)

    assert result["isError"] is True
    assert fragment in result["content"][0]["text"]


def test_search_jobs_only_returns_http_links(sqlite_database_url: str) -> None:
    asyncio.run(_seed(sqlite_database_url, HOSTILE_JOBS))

    result = asyncio.run(call_once(sqlite_database_url, "search_jobs", {}))

    urls = [job["url"] for job in result["structuredContent"]["jobs"]]
    assert urls == ["https://example.com/jobs/1?a=1&b=<2>", None]
    assert "javascript:" not in json.dumps(result)


async def test_search_summary_lists_scores_tiers_and_paging(pipeline: Pipeline) -> None:
    result = await call_tool(
        pipeline.server,
        "search_jobs",
        {"remote": True, "sort": "score", "dedupe": True, "limit": 2},
    )

    page = result["structuredContent"]
    top = page["jobs"][0]
    lines = result["content"][0]["text"].splitlines()
    assert lines[0] == f"{page['total']} matching jobs (sort=score, dedupe=on); showing 1-2:"
    assert lines[1] == (
        f"#{top['id']} {top['score']:.4f} high   Senior Python Backend Engineer"
        " — Acme Robotics · Remote - US"
    )
    assert lines[-1] == "More: call search_jobs again with offset=2."
    assert top["url"] == ACME_URL
    assert top["priority_tier"] == "high"


# ---------------------------------------------------------------------------
# get_job / explain_job_score
# ---------------------------------------------------------------------------


def expected_decision(url: str, title: str, company: str, location: str, query: str) -> Any:
    """What the real decision engine decides for one fixture posting."""

    engine = AgentDecisionEngine(DeterministicScoringService(), DeterministicPlanningService())
    candidate = JobCandidate(None, title, location, company, url, None)
    return engine.evaluate(candidate, query)


async def test_get_job_returns_the_full_decision_trace(pipeline: Pipeline) -> None:
    job_id = await find_job_id(pipeline, ACME_URL)
    decision = expected_decision(
        ACME_URL,
        "Senior Python Backend Engineer",
        "Acme Robotics",
        "Remote - US",
        "python backend remote",
    )

    result = await call_tool(pipeline.server, "get_job", {"job_id": job_id})

    detail = result["structuredContent"]
    assert detail["job"]["id"] == job_id
    assert detail["job"]["external_id"] == "gh-4101"
    assert detail["job"]["remote"] is True
    assert detail["job"]["score"] == decision.score
    assert detail["decision"] == {
        "priority_tier": decision.priority_tier,
        "matched_query_terms": ["backend", "python", "remote"],
        "rationale": decision.rationale,
        "plan_steps": decision.plan_steps,
        "llm_enrichment": None,
    }
    assert detail["run"] == {
        "id": pipeline.run_ids[0],
        "query": "python backend remote",
        "status": "completed",
    }
    assert detail["source"] == {"id": 1, "name": "demo-greenhouse", "source_type": "greenhouse"}
    assert detail["source_payload"] == {"source": "fixture"}
    text = result["content"][0]["text"]
    assert text.startswith(
        f"#{job_id} Senior Python Backend Engineer — Acme Robotics · Remote - US (remote)"
    )
    assert f"Score {decision.score:.4f} · priority high" in text
    assert "source demo-greenhouse (greenhouse)" in text
    assert "- Matched query terms: backend, python, remote." in text
    assert f"1. Open posting: {ACME_URL}" in text


async def test_missing_job_is_a_not_found_tool_error(search_server: CareerSearchMcpServer) -> None:
    for tool in ("get_job", "explain_job_score"):
        result = await call_tool(search_server, tool, {"job_id": 999_999})

        assert result["isError"] is True
        assert result["content"][0]["text"] == (
            "No job with id 999999. Use search_jobs to find job ids."
        )


async def test_explain_job_score_breaks_down_a_pipeline_score(pipeline: Pipeline) -> None:
    job_id = await find_job_id(pipeline, ACME_URL)
    breakdown = DeterministicScoringService().breakdown(
        JobCandidate(
            None, "Senior Python Backend Engineer", "Remote - US", "Acme Robotics", ACME_URL, None
        ),
        "python backend remote",
    )

    result = await call_tool(pipeline.server, "explain_job_score", {"job_id": job_id})

    explained = result["structuredContent"]
    parts = explained["components"]
    assert explained["score"] == explained["recomputed_score"] == breakdown.score
    assert explained["matches_stored_score"] is True
    assert explained["priority_tier"] == explained["recorded_priority_tier"] == "high"
    assert explained["next_tier"] is None
    assert explained["run_query"] == "python backend remote"
    assert explained["query_terms"] == explained["matched_terms"] == ["backend", "python", "remote"]
    assert explained["unmatched_terms"] == []
    assert (parts["base"], parts["keyword_bonus"]) == (0.45, 0.3)
    assert round(parts["base"] + parts["keyword_bonus"] + parts["stability_bonus"], 4) == (
        breakdown.score
    )
    assert parts["stability_bonus"] == round(breakdown.stability_bonus, 4)
    assert explained["tier_thresholds"] == {"high": 0.8, "medium": 0.65}
    lines = result["content"][0]["text"].splitlines()
    assert lines == explained["explanation"]
    assert lines[1] == (
        f"Score {breakdown.score:.4f} → high priority (high ≥ 0.80, medium ≥ 0.65)."
    )
    assert "+ 0.4500  base relevance every captured job starts with" in lines
    assert lines[4].startswith("+ 0.3000  keyword bonus: 3 of 3 run query terms")
    assert lines[-1] == f"= {breakdown.score:.4f}  recomputed now; matches the stored score"


async def test_explain_job_score_reports_missing_terms_and_the_next_tier(
    pipeline: Pipeline,
) -> None:
    job_id = await find_job_id(pipeline, PIPER_URL)

    explained = await structured(pipeline.server, "explain_job_score", {"job_id": job_id})

    assert explained["priority_tier"] == "medium"
    assert explained["matched_terms"] == ["python", "remote"]
    assert explained["unmatched_terms"] == ["backend"]
    assert explained["next_tier"] == {
        "tier": "high",
        "min_score": 0.8,
        "gap": round(0.8 - explained["score"], 4),
    }
    assert "          not found: backend" in explained["explanation"]
    assert f"{explained['next_tier']['gap']:.4f} below high." in explained["explanation"][1]


async def test_explain_job_score_flags_scores_it_cannot_reproduce(
    search_server: CareerSearchMcpServer,
) -> None:
    page = await structured(search_server, "search_jobs", {"sort": "score", "limit": 1})
    job = page["jobs"][0]

    explained = await structured(search_server, "explain_job_score", {"job_id": job["id"]})

    assert explained["score"] == job["score"] == 0.93
    assert explained["matches_stored_score"] is False
    assert explained["recomputed_score"] != 0.93
    assert explained["recorded_priority_tier"] == "high"
    assert "approximate; search ranks by the stored score" in explained["explanation"][-1]


# ---------------------------------------------------------------------------
# list_runs / get_run / list_sources
# ---------------------------------------------------------------------------


async def test_list_runs_newest_first_with_job_counts(pipeline: Pipeline) -> None:
    first, second = pipeline.run_ids

    listed = await structured(pipeline.server, "list_runs", {})
    paged = await structured(pipeline.server, "list_runs", {"limit": 1})
    completed = await structured(pipeline.server, "list_runs", {"status": "completed"})
    queued = await call_tool(pipeline.server, "list_runs", {"status": "queued"})

    assert [run["id"] for run in listed["runs"]] == [second, first]
    assert [run["query"] for run in listed["runs"]] == [
        "platform kubernetes",
        "python backend remote",
    ]
    assert all(run["status"] == "completed" and run["job_count"] == 8 for run in listed["runs"])
    assert all(run["finished_at"] for run in listed["runs"])
    assert (paged["total"], paged["next_offset"], len(paged["runs"])) == (2, 1, 1)
    assert completed["total"] == 2
    assert queued["structuredContent"]["runs"] == []
    assert queued["content"][0]["text"] == "No runs match."


async def test_get_run_returns_the_most_recent_events_in_order(pipeline: Pipeline) -> None:
    run_id = pipeline.run_ids[0]

    everything = await structured(pipeline.server, "get_run", {"run_id": run_id})
    recent = await call_tool(pipeline.server, "get_run", {"run_id": run_id, "event_limit": 3})

    events = everything["events"]
    assert everything["events_truncated"] is False
    assert everything["event_count"] == len(events) == 17
    assert [event["sequence"] for event in events] == list(range(1, 18))
    assert events[0]["event_type"] == "run.created"
    assert events[-1]["event_type"] == "run.completed"
    failed = next(event for event in events if event["event_type"] == "source.failed")
    assert failed["payload"] == {"source_config_id": 3}
    decisions = [event for event in events if event["event_type"] == "agent.decision"]
    assert len(decisions) == everything["run"]["job_count"] == 8
    tail = recent["structuredContent"]
    assert tail["events_truncated"] is True
    assert tail["events"] == events[-3:]
    text = recent["content"][0]["text"]
    assert text.startswith(f'Run {run_id} completed · query "python backend remote" · 8 jobs')
    assert "Last 3 of 17 events:" in text


async def test_unknown_run_is_a_not_found_tool_error(pipeline: Pipeline) -> None:
    result = await call_tool(pipeline.server, "get_run", {"run_id": "CANARY-no-such-run"})

    assert result["isError"] is True
    assert result["content"][0]["text"] == "No run with this id. Use list_runs to find run ids."


async def test_list_sources_counts_captured_jobs(pipeline: Pipeline) -> None:
    sources = await structured(pipeline.server, "list_sources", {})
    disabled = await structured(pipeline.server, "list_sources", {"enabled": False})

    assert sources["count"] == 3
    assert [
        (source["id"], source["name"], source["source_type"], source["job_count"])
        for source in sources["sources"]
    ] == [
        (1, "demo-greenhouse", "greenhouse", 8),
        (2, "demo-lever", "lever", 8),
        (3, "demo-workday", "workday", 0),
    ]
    assert sources["sources"][0]["base_url"] == "https://boards.greenhouse.io/demo"
    assert disabled == {"count": 0, "sources": []}


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


async def test_every_tool_output_conforms_to_its_output_schema(pipeline: Pipeline) -> None:
    job_id = await find_job_id(pipeline, ACME_URL)
    calls: list[tuple[str, dict[str, Any]]] = [
        ("search_jobs", {}),
        ("search_jobs", {"dedupe": True, "sort": "score", "hours_old": 24}),
        ("get_job", {"job_id": job_id}),
        ("explain_job_score", {"job_id": job_id}),
        ("list_runs", {}),
        ("get_run", {"run_id": pipeline.run_ids[1], "event_limit": 5}),
        ("list_sources", {}),
    ]

    for name, arguments in calls:
        content = await structured(pipeline.server, name, arguments)
        assert validate(content, TOOLS_BY_NAME[name].output_schema, name) == []


async def test_tool_calls_never_change_the_database(pipeline: Pipeline) -> None:
    before = hashlib.sha256(pipeline.database_path.read_bytes()).hexdigest()
    job_id = await find_job_id(pipeline, ACME_URL)

    for name, arguments in [
        ("search_jobs", {"dedupe": True}),
        ("get_job", {"job_id": job_id}),
        ("explain_job_score", {"job_id": job_id}),
        ("list_runs", {}),
        ("get_run", {"run_id": pipeline.run_ids[0]}),
        ("list_sources", {}),
    ]:
        await structured(pipeline.server, name, arguments)

    assert hashlib.sha256(pipeline.database_path.read_bytes()).hexdigest() == before
