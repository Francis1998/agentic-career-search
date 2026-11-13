"""MCP ``match_resume_to_jobs``: listing, schemas, parity with the API, eras and privacy."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from autoapply_agent.mcp.database import open_read_only_database
from autoapply_agent.mcp.schema import validate
from autoapply_agent.mcp.server import CareerSearchMcpServer
from autoapply_agent.mcp.tools import TOOLS_BY_NAME
from autoapply_agent.services.resume_match import MAX_RESUME_CHARS
from tests.integration.test_jobs_match_api import (
    CANARY,
    MATCH_JOBS,
    RESUME,
    _seed,
    app_client,
)

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
}
TOOL = "match_resume_to_jobs"


def call(arguments: dict[str, Any], request_id: int = 1, *, modern: bool = True) -> dict[str, Any]:
    """A ``tools/call`` request for the match tool."""

    params: dict[str, Any] = {"name": TOOL, "arguments": arguments}
    if modern:
        params["_meta"] = META
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": params}


async def result_of(server: CareerSearchMcpServer, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call the tool and return the ``result`` member."""

    response = await server.handle_message(call(arguments))
    assert response is not None and "result" in response, response
    result: dict[str, Any] = response["result"]
    return result


@pytest.fixture()
def database_url(sqlite_database_url: str) -> str:
    """The match fixtures of the API tests."""

    asyncio.run(_seed(sqlite_database_url, MATCH_JOBS))
    return sqlite_database_url


@pytest.fixture()
async def server(database_url: str) -> AsyncIterator[CareerSearchMcpServer]:
    """A read-only server over the match fixtures."""

    engine, session_factory = open_read_only_database(database_url)
    try:
        yield CareerSearchMcpServer(session_factory)
    finally:
        await engine.dispose()


async def test_tool_is_listed_with_its_schemas(server: CareerSearchMcpServer) -> None:
    response = await server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": META}}
    )

    assert response is not None
    tool = next(item for item in response["result"]["tools"] if item["name"] == TOOL)
    properties = tool["inputSchema"]["properties"]
    assert tool["inputSchema"]["required"] == ["resume_text"]
    assert properties["resume_text"]["maxLength"] == MAX_RESUME_CHARS
    assert sorted(properties) == sorted(
        [
            "resume_text",
            "q",
            "company",
            "location",
            "remote",
            "min_score",
            "source_config_id",
            "run_id",
            "created_after",
            "hours_old",
            "dedupe",
            "sort",
            "limit",
            "min_match",
            "include_extra_skills",
        ]
    )
    assert properties["sort"]["enum"] == ["match", "blend"]
    assert properties["dedupe"]["default"] is True
    assert tool["annotations"]["readOnlyHint"] is True
    assert "never stored or logged" in tool["description"]


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"sort": "blend"},
        {"remote": True, "limit": 2},
        {"q": "engineer", "min_match": 0.2, "include_extra_skills": True},
        {"dedupe": False, "hours_old": 8},
    ],
)
def test_ranking_equals_the_http_api(database_url: str, arguments: dict[str, Any]) -> None:
    for client in app_client(database_url):
        response = client.post("/jobs/match", json={"resume_text": RESUME, **arguments})
        assert response.status_code == 200, response.text
        expected = response.json()

    async def run() -> dict[str, Any]:
        engine, session_factory = open_read_only_database(database_url)
        try:
            return await result_of(
                CareerSearchMcpServer(session_factory), {"resume_text": RESUME, **arguments}
            )
        finally:
            await engine.dispose()

    result = asyncio.run(run())

    assert result["isError"] is False
    content = result["structuredContent"]
    assert validate(content, TOOLS_BY_NAME[TOOL].output_schema, TOOL) == []
    assert json.loads(result["content"][1]["text"]) == content
    fields = ("id", "rank", "match_score", "blend_score", "matched_skills", "missing_skills")
    assert [[job[field] for field in fields] for job in content["jobs"]] == [
        [job[field] for field in fields] for job in expected["jobs"]
    ]
    assert [job["extra_skills"] for job in content["jobs"]] == [
        job["extra_skills"] for job in expected["jobs"]
    ]
    for key in ("resume_sha256", "resume_skills", "implied_skills", "sort", "total"):
        assert content[key] == expected[key]


async def test_summary_lists_resume_skills_and_explanations(
    server: CareerSearchMcpServer,
) -> None:
    result = await result_of(server, {"resume_text": RESUME, "limit": 2})

    lines = result["content"][0]["text"].splitlines()
    content = result["structuredContent"]
    top = content["jobs"][0]
    assert lines[0] == (
        "Resume: 8 skills recognized (aws, docker, fastapi, helm, kubernetes, postgresql, "
        "python, terraform)."
    )
    assert lines[1] == "5 jobs ranked (sort=match, dedupe=on); top 2:"
    assert lines[2] == (
        f"1. #{top['id']} match 0.7500 Senior Python Engineer — Acme Robotics · Remote - US"
    )
    assert lines[3] == f"   {top['explanation']}"
    assert content["dedupe"] is True and content["limit"] == 2
    assert [job["title"] for job in content["jobs"]] == [
        "Senior Python Engineer",
        "Staff Platform Engineer (Python, Kubernetes)",
    ]


async def test_legacy_clients_get_the_legacy_result_shape(server: CareerSearchMcpServer) -> None:
    await server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
        }
    )

    response = await server.handle_message(call({"resume_text": RESUME}, 2, modern=False))

    assert response is not None
    result = response["result"]
    assert "resultType" not in result
    assert result["isError"] is False
    assert result["structuredContent"]["total"] == 5


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (
            {"resume_text": CANARY + "x" * MAX_RESUME_CHARS},
            f"arguments.resume_text must be at most {MAX_RESUME_CHARS} characters",
        ),
        ({"resume_text": ""}, "arguments.resume_text must be at least 1 character(s)"),
        ({"resume_text": " \n "}, "resume_text must contain the plain text of a resume."),
        ({"resume_text": RESUME, "limit": 51}, "arguments.limit must be <= 50"),
        ({"resume_text": RESUME, "sort": "newest"}, "arguments.sort must be one of"),
        ({"resume_text": RESUME, "offset": 3}, "arguments has unexpected properties"),
        ({"resume": CANARY}, "arguments.resume_text is required"),
    ],
)
async def test_bad_arguments_are_tool_errors_that_never_echo_the_resume(
    server: CareerSearchMcpServer, arguments: dict[str, Any], message: str
) -> None:
    result = await result_of(server, arguments)

    assert result["isError"] is True
    assert message in result["content"][0]["text"]
    assert CANARY not in json.dumps(result)


def test_resume_never_reaches_logs_audit_log_or_database(
    database_url: str, tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    database = Path(database_url.removeprefix("sqlite+aiosqlite:///"))
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    audit_path = tmp_path / "audit.jsonl"

    async def run() -> dict[str, Any]:
        engine, session_factory = open_read_only_database(database_url)
        try:
            server = CareerSearchMcpServer(session_factory, audit_log_path=audit_path)
            ok = await result_of(server, {"resume_text": RESUME, "limit": 3})
            await result_of(server, {"resume_text": CANARY + "x" * MAX_RESUME_CHARS})
            return ok
        finally:
            await engine.dispose()

    with caplog.at_level(logging.DEBUG):
        ok = asyncio.run(run())

    audit = audit_path.read_text(encoding="utf-8")
    records = [json.loads(line) for line in audit.splitlines()]
    assert [(record["tool"], record["result_count"]) for record in records] == [
        (TOOL, len(ok["structuredContent"]["jobs"])),
        (TOOL, 0),
    ]
    assert records[1]["error_kind"] == "invalid_arguments"
    assert all(record["arguments_hash"].startswith("hmac-sha256:") for record in records)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert f"mcp_tool_call tool={TOOL}" in logged
    for text in (audit, logged):
        assert CANARY not in text and "Senior engineer" not in text and "python" not in text
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
