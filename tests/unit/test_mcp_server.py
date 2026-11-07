"""Protocol tests for the dual-era, read-only MCP server (2026-07-28 + legacy handshake)."""

from __future__ import annotations

import asyncio
import dataclasses
import io
import json
import logging
import os
import subprocess
import sys
import tomllib
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from autoapply_agent import __version__
from autoapply_agent.mcp import server as mcp_server
from autoapply_agent.mcp.database import open_read_only_database, sqlite_file_path
from autoapply_agent.mcp.server import (
    SUPPORTED_PROTOCOL_VERSIONS,
    CareerSearchMcpServer,
    serve_stdio,
)
from autoapply_agent.mcp.tools import ToolOutput
from tests.integration.test_jobs_search_api import SEED_JOBS, _seed

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch

MODERN = "2026-07-28"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"
REPO_ROOT = Path(__file__).resolve().parents[2]
READ_ONLY_TOOLS = [
    "explain_job_score",
    "get_job",
    "get_run",
    "list_runs",
    "list_sources",
    "search_jobs",
]


def modern_meta(version: str = MODERN) -> dict[str, Any]:
    """Per-request metadata a 2026-07-28 client sends on every request."""

    return {
        "io.modelcontextprotocol/protocolVersion": version,
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "pytest", "version": "1.0"},
    }


def rpc(method: str, params: dict[str, Any] | None = None, request_id: Any = 1) -> dict[str, Any]:
    """Build a JSON-RPC request."""

    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def modern(
    method: str, params: dict[str, Any] | None = None, request_id: Any = 1
) -> dict[str, Any]:
    """Build a modern (stateless) request carrying the required ``_meta``."""

    return rpc(method, {**(params or {}), "_meta": modern_meta()}, request_id)


def call(name: str, arguments: Any, request_id: Any = 1) -> dict[str, Any]:
    """Build a modern ``tools/call`` request."""

    return modern("tools/call", {"name": name, "arguments": arguments}, request_id)


async def initialize(server: CareerSearchMcpServer, version: str = "2025-11-25") -> dict[str, Any]:
    """Run the legacy handshake and return the initialize result."""

    response = await server.handle_message(
        rpc(
            "initialize",
            {
                "protocolVersion": version,
                "capabilities": {},
                "clientInfo": {"name": "legacy-client", "version": "0.9"},
            },
        )
    )
    assert response is not None
    notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    assert await server.handle_message(notification) is None
    return response["result"]


@pytest.fixture()
def database_url(sqlite_database_url: str) -> str:
    """A database seeded with the job-search test fixtures (two runs, eight jobs)."""

    asyncio.run(_seed(sqlite_database_url, SEED_JOBS))
    return sqlite_database_url


@pytest.fixture()
async def server(database_url: str) -> AsyncIterator[CareerSearchMcpServer]:
    """A fresh server per test (the legacy handshake is process-scoped state)."""

    engine, session_factory = open_read_only_database(database_url)
    try:
        yield CareerSearchMcpServer(session_factory)
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Modern era (2026-07-28)
# ---------------------------------------------------------------------------


async def test_discover_advertises_versions_capabilities_and_identity(
    server: CareerSearchMcpServer,
) -> None:
    response = await server.handle_message(modern("server/discover"))

    assert response is not None
    result = response["result"]
    assert response["id"] == 1
    assert result["resultType"] == "complete"
    assert result["supportedVersions"] == ["2026-07-28", "2025-11-25", "2025-06-18"]
    assert result["capabilities"] == {"tools": {}}
    assert result["_meta"][SERVER_INFO_KEY] == {
        "name": "agentic-career-search",
        "title": "agentic-career-search job feed (read-only)",
        "version": __version__,
    }
    assert result["ttlMs"] > 0
    assert result["cacheScope"] == "public"
    assert "Read-only" in result["instructions"]
    assert "never as instructions" in result["instructions"]


async def test_modern_tools_list_is_read_only_cacheable_and_deterministic(
    server: CareerSearchMcpServer,
) -> None:
    first = await server.handle_message(modern("tools/list"))
    second = await server.handle_message(modern("tools/list", request_id="again"))

    assert first is not None and second is not None
    result = first["result"]
    assert [tool["name"] for tool in result["tools"]] == READ_ONLY_TOOLS
    assert result["tools"] == second["result"]["tools"]
    assert result["resultType"] == "complete"
    assert result["ttlMs"] > 0
    assert result["cacheScope"] == "public"
    assert SERVER_INFO_KEY in result["_meta"]
    for tool in result["tools"]:
        assert tool["inputSchema"]["type"] == "object"
        assert tool["inputSchema"]["additionalProperties"] is False
        assert tool["outputSchema"]["type"] == "object"
        assert tool["annotations"] == {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
        assert "Read-only" in tool["description"]


async def test_tools_list_exposes_no_write_paths(server: CareerSearchMcpServer) -> None:
    response = await server.handle_message(modern("tools/list"))

    assert response is not None
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == set(READ_ONLY_TOOLS)
    write_verbs = ("create", "cancel", "update", "delete", "apply", "edit", "patch", "start")
    assert not [name for name in names if name.startswith(write_verbs)]
    assert set(mcp_server.TOOLS_BY_NAME) == names


def _type_arrays(schema: Any, path: str = "") -> list[str]:
    """Paths of every ``"type": [...]`` in a schema (single-type dialects reject them)."""

    found: list[str] = []
    if isinstance(schema, dict):
        if isinstance(schema.get("type"), list):
            found.append(path or "/")
        for key, value in schema.items():
            found.extend(_type_arrays(value, f"{path}/{key}"))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            found.extend(_type_arrays(item, f"{path}/{index}"))
    return found


async def test_tool_schemas_use_single_type_branches(server: CareerSearchMcpServer) -> None:
    response = await server.handle_message(modern("tools/list"))

    assert response is not None
    for tool in response["result"]["tools"]:
        assert _type_arrays(tool["inputSchema"]) == [], tool["name"]
        assert _type_arrays(tool["outputSchema"]) == [], tool["name"]


async def test_search_jobs_input_schema_mirrors_the_http_filters(
    server: CareerSearchMcpServer,
) -> None:
    response = await server.handle_message(modern("tools/list"))

    assert response is not None
    tools = {tool["name"]: tool for tool in response["result"]["tools"]}
    properties = tools["search_jobs"]["inputSchema"]["properties"]
    assert sorted(properties) == sorted(
        [
            "q",
            "company",
            "location",
            "remote",
            "min_score",
            "source_config_id",
            "run_id",
            "created_after",
            "hours_old",
            "sort",
            "dedupe",
            "limit",
            "offset",
        ]
    )
    assert properties["limit"]["maximum"] == 50
    assert properties["sort"]["enum"] == ["newest", "score"]
    assert tools["get_job"]["inputSchema"]["required"] == ["job_id"]
    assert tools["get_run"]["inputSchema"]["required"] == ["run_id"]


async def test_modern_tool_call_returns_structured_and_text_content(
    server: CareerSearchMcpServer,
) -> None:
    response = await server.handle_message(call("search_jobs", {"q": "python", "limit": 2}))

    assert response is not None
    result = response["result"]
    assert result["resultType"] == "complete"
    assert result["isError"] is False
    assert SERVER_INFO_KEY in result["_meta"]
    structured = result["structuredContent"]
    assert structured["total"] == 4
    assert len(structured["jobs"]) == 2
    summary, serialized = result["content"]
    assert summary["type"] == serialized["type"] == "text"
    assert summary["text"].startswith("4 matching jobs (sort=newest, dedupe=off); showing 1-2:")
    assert json.loads(serialized["text"]) == structured


async def test_invalid_arguments_are_tool_errors_without_echoing_unknown_names(
    server: CareerSearchMcpServer,
) -> None:
    response = await server.handle_message(
        call("search_jobs", {"limit": 500, "sort": "salary", "CANARY-secret-note": "x"})
    )

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    assert "structuredContent" not in result
    message = result["content"][0]["text"]
    assert "arguments.limit must be <= 50" in message
    assert "arguments.sort must be one of ['newest', 'score']" in message
    assert "arguments has unexpected properties (allowed: company, created_after" in message
    assert "CANARY" not in message


@pytest.mark.parametrize("name", ["create_run", "cancel_run", "update_source_config"])
async def test_unknown_or_write_tools_are_protocol_errors(
    server: CareerSearchMcpServer, name: str
) -> None:
    response = await server.handle_message(call(name, {}))

    assert response == {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32602, "message": f"Unknown tool: {name}"},
    }


async def test_unsupported_version_returns_32022_with_supported_list(
    server: CareerSearchMcpServer,
) -> None:
    request = rpc(
        "tools/list",
        {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "1900-01-01",
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
    )

    response = await server.handle_message(request)

    assert response == {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32022,
            "message": "Unsupported protocol version",
            "data": {"supported": list(SUPPORTED_PROTOCOL_VERSIONS), "requested": "1900-01-01"},
        },
    }


async def test_missing_client_capabilities_is_invalid_params(
    server: CareerSearchMcpServer,
) -> None:
    request = rpc("tools/list", {"_meta": {"io.modelcontextprotocol/protocolVersion": MODERN}})

    response = await server.handle_message(request)

    assert response is not None
    assert response["error"]["code"] == -32602
    assert "clientCapabilities" in response["error"]["message"]


async def test_request_without_meta_before_initialize_is_rejected(
    server: CareerSearchMcpServer,
) -> None:
    response = await server.handle_message(rpc("tools/list"))

    assert response is not None
    assert response["error"]["code"] == -32602
    assert response["error"]["data"] == {"supported": list(SUPPORTED_PROTOCOL_VERSIONS)}


@pytest.mark.parametrize("method", ["resources/list", "initialize", "ping", "logging/setLevel"])
async def test_methods_outside_the_modern_surface_are_not_found(
    server: CareerSearchMcpServer, method: str
) -> None:
    response = await server.handle_message(modern(method))

    assert response is not None
    assert response["error"]["code"] == -32601
    assert response["error"]["message"] == f"Method not found: {method} (protocol {MODERN})"


@pytest.mark.parametrize(
    ("message", "fragment"),
    [
        (
            rpc("tools/list", {"_meta": {"io.modelcontextprotocol/protocolVersion": 20260728}}),
            "must be a string",
        ),
        (rpc("initialize", {"capabilities": {}}), "initialize requires a string protocolVersion"),
        (modern("tools/call", {"name": 7}), "tools/call requires a string name"),
        (
            modern("tools/call", {"name": "list_runs", "arguments": ["x"]}),
            "arguments must be an object",
        ),
        (modern("tools/list", {"cursor": "page-2"}), "tools/list is not paginated"),
        ({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": ["x"]}, "params must be"),
    ],
    ids=[
        "numeric-version",
        "initialize-without-version",
        "non-string-name",
        "array-arguments",
        "tools-list-cursor",
        "array-params",
    ],
)
async def test_malformed_params_are_invalid_params(
    server: CareerSearchMcpServer, message: dict[str, Any], fragment: str
) -> None:
    response = await server.handle_message(message)

    assert response is not None
    assert response["id"] == 1
    assert response["error"]["code"] == -32602
    assert fragment in response["error"]["message"]


# ---------------------------------------------------------------------------
# Legacy era (initialize handshake)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["2025-11-25", "2025-06-18"])
async def test_legacy_initialize_negotiates_requested_version(
    server: CareerSearchMcpServer, version: str
) -> None:
    result = await initialize(server, version)

    assert result["protocolVersion"] == version
    assert result["capabilities"] == {"tools": {"listChanged": False}}
    assert result["serverInfo"]["name"] == "agentic-career-search"
    assert "Read-only" in result["instructions"]
    assert "resultType" not in result


async def test_legacy_initialize_with_unknown_version_offers_latest_legacy(
    server: CareerSearchMcpServer,
) -> None:
    assert (await initialize(server, "2024-11-05"))["protocolVersion"] == "2025-11-25"


async def test_legacy_session_results_have_legacy_shape(server: CareerSearchMcpServer) -> None:
    await initialize(server, "2025-06-18")

    listed = await server.handle_message(rpc("tools/list", request_id=2))
    called = await server.handle_message(
        rpc("tools/call", {"name": "list_runs", "arguments": {}}, request_id=3)
    )
    pinged = await server.handle_message(rpc("ping", request_id=4))

    assert listed is not None and called is not None
    assert set(listed["result"]) == {"tools"}
    assert set(called["result"]) == {"content", "structuredContent", "isError"}
    assert called["result"]["structuredContent"]["total"] == 2
    assert pinged == {"jsonrpc": "2.0", "id": 4, "result": {}}


async def test_legacy_version_in_meta_is_served_with_legacy_shape(
    server: CareerSearchMcpServer,
) -> None:
    response = await server.handle_message(
        rpc("tools/list", {"_meta": {"io.modelcontextprotocol/protocolVersion": "2025-11-25"}})
    )

    assert response is not None
    assert set(response["result"]) == {"tools"}


async def test_dual_era_process_still_serves_modern_requests(
    server: CareerSearchMcpServer,
) -> None:
    await initialize(server)

    response = await server.handle_message(modern("server/discover", request_id=9))

    assert response is not None
    assert response["result"]["resultType"] == "complete"


# ---------------------------------------------------------------------------
# JSON-RPC framing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        '{"jsonrpc": "2.0", "id": 1,',
        b"\xff\xfe not utf-8",
        "[" * 100_000,
        '{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"x": NaN}}',
    ],
    ids=["truncated", "invalid-utf8", "deeply-nested", "nan-literal"],
)
async def test_malformed_lines_return_parse_error_without_id(
    server: CareerSearchMcpServer, line: str | bytes
) -> None:
    assert await server.handle_line(line) == {
        "jsonrpc": "2.0",
        "error": {"code": -32700, "message": "Parse error"},
    }


@pytest.mark.parametrize(
    ("message", "expected_id"),
    [
        ([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}], None),
        ("tools/list", None),
        ({"jsonrpc": "1.0", "id": 1, "method": "tools/list"}, 1),
        ({"jsonrpc": "2.0", "id": 1, "method": 7}, 1),
        ({"jsonrpc": "2.0", "id": True, "method": "tools/list"}, None),
        ({"jsonrpc": "2.0", "id": None, "method": "tools/list"}, None),
        ({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": "x"}, 1),
        ({"jsonrpc": "2.0", "id": "abc"}, "abc"),
    ],
    ids=[
        "batch",
        "not-object",
        "wrong-version",
        "non-string-method",
        "bool-id",
        "null-id",
        "string-params",
        "no-method",
    ],
)
async def test_invalid_requests_return_invalid_request(
    server: CareerSearchMcpServer, message: Any, expected_id: Any
) -> None:
    response = await server.handle_message(message)

    assert response is not None
    assert response["error"]["code"] == -32600
    assert response.get("id") == expected_id
    assert ("id" in response) is (expected_id is not None)


@pytest.mark.parametrize(
    "message",
    [
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
        {"jsonrpc": "2.0", "method": "notifications/unknown"},
        {"jsonrpc": "2.0", "method": "tools/list", "params": ["bad"]},
        {"jsonrpc": "2.0", "id": 5, "result": {}},
    ],
    ids=["initialized", "cancelled", "unknown-notification", "bad-notification", "response"],
)
async def test_notifications_and_responses_never_get_replies(
    server: CareerSearchMcpServer, message: dict[str, Any]
) -> None:
    assert await server.handle_message(message) is None


async def test_internal_errors_are_reported_without_leaking_details(
    server: CareerSearchMcpServer, monkeypatch: MonkeyPatch, caplog: LogCaptureFixture
) -> None:
    async def explode(session: Any, arguments: dict[str, Any]) -> ToolOutput:
        raise RuntimeError("CANARY private note about Acme")

    tool = mcp_server.TOOLS_BY_NAME["list_runs"]
    monkeypatch.setitem(
        mcp_server.TOOLS_BY_NAME, "list_runs", dataclasses.replace(tool, handler=explode)
    )

    with caplog.at_level(logging.DEBUG, logger="autoapply_agent"):
        response = await server.handle_message(call("list_runs", {}))

    assert response == {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32603, "message": "Internal error"},
    }
    assert "CANARY" not in caplog.text
    failure = next(r for r in caplog.records if r.getMessage().startswith("mcp_internal_error"))
    assert "error_type=RuntimeError" in failure.getMessage()
    assert "where=test_mcp_server.py:" in failure.getMessage()


async def test_database_errors_are_tool_errors_that_hide_sql(
    tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    empty = tmp_path / "empty.db"
    empty.touch()
    engine, session_factory = open_read_only_database(f"sqlite+aiosqlite:///{empty}")
    try:
        server = CareerSearchMcpServer(session_factory)
        with caplog.at_level(logging.DEBUG, logger="autoapply_agent"):
            response = await server.handle_message(call("search_jobs", {"q": "CANARY"}))
    finally:
        await engine.dispose()

    assert response is not None
    result = response["result"]
    assert result["isError"] is True
    message = result["content"][0]["text"]
    assert message.startswith("The job database could not be read.")
    assert "SELECT" not in message and "CANARY" not in message
    assert "CANARY" not in caplog.text
    assert "error_type=OperationalError" in caplog.text


# ---------------------------------------------------------------------------
# Privacy: audit log and logs
# ---------------------------------------------------------------------------


async def test_audit_log_records_hashes_and_counts_never_arguments(
    database_url: str, tmp_path: Path
) -> None:
    audit_path = tmp_path / "audit" / "mcp.jsonl"
    engine, session_factory = open_read_only_database(database_url)
    try:
        server = CareerSearchMcpServer(session_factory, audit_log_path=audit_path)
        arguments = {"q": "python", "company": "CANARY-Acme", "location": "Remote"}
        first = await server.handle_message(call("search_jobs", {"q": "python", "limit": 3}))
        await server.handle_message(call("search_jobs", {"q": "python", "limit": 3}))
        await server.handle_message(call("search_jobs", arguments))
        await server.handle_message(call("get_job", {"job_id": 424242}))
        await server.handle_message(call("search_jobs", {"q": "CANARY-q", "limit": 99}))
    finally:
        await engine.dispose()

    assert first is not None
    raw = audit_path.read_text(encoding="utf-8")
    for leaked in ("python", "CANARY", "Acme", "Remote", "Senior"):
        assert leaked not in raw
    records = [json.loads(line) for line in raw.splitlines()]
    assert [record["tool"] for record in records] == [
        "search_jobs",
        "search_jobs",
        "search_jobs",
        "get_job",
        "search_jobs",
    ]
    for record in records:
        assert set(record) == {
            "timestamp",
            "event",
            "tool",
            "arguments_hash",
            "result_count",
            "duration_ms",
            "is_error",
            "error_kind",
        }
        assert record["arguments_hash"].startswith("hmac-sha256:")
        assert len(record["arguments_hash"]) == len("hmac-sha256:") + 64
    ok, repeat, other, missing, invalid = records
    assert ok["result_count"] == len(first["result"]["structuredContent"]["jobs"]) == 3
    assert ok["arguments_hash"] == repeat["arguments_hash"] != other["arguments_hash"]
    assert (ok["is_error"], ok["error_kind"]) == (False, None)
    assert (missing["is_error"], missing["error_kind"], missing["result_count"]) == (
        True,
        "not_found",
        0,
    )
    assert (invalid["is_error"], invalid["error_kind"]) == (True, "invalid_arguments")
    if os.name == "posix":
        assert audit_path.stat().st_mode & 0o777 == 0o600


async def test_argument_hashes_differ_between_server_processes(
    database_url: str, tmp_path: Path
) -> None:
    hashes = []
    for name in ("a.jsonl", "b.jsonl"):
        engine, session_factory = open_read_only_database(database_url)
        try:
            server = CareerSearchMcpServer(session_factory, audit_log_path=tmp_path / name)
            await server.handle_message(call("get_job", {"job_id": 1}))
        finally:
            await engine.dispose()
        hashes.append(json.loads((tmp_path / name).read_text())["arguments_hash"])

    assert hashes[0] != hashes[1]


async def test_audit_log_write_failure_does_not_break_tool_calls(
    database_url: str, tmp_path: Path
) -> None:
    engine, session_factory = open_read_only_database(database_url)
    try:
        server = CareerSearchMcpServer(session_factory, audit_log_path=tmp_path)
        response = await server.handle_message(call("list_sources", {}))
    finally:
        await engine.dispose()

    assert response is not None
    assert response["result"]["isError"] is False


async def test_logs_never_contain_arguments_or_results(
    server: CareerSearchMcpServer, caplog: LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger="autoapply_agent"):
        await server.handle_message(call("search_jobs", {"q": "CANARY python"}))
        await server.handle_message(call("search_jobs", {"q": "python"}))
        await server.handle_message(call("get_job", {"job_id": 1}))
        await server.handle_message(
            rpc("initialize", {"protocolVersion": "CANARY 2099", "capabilities": {}})
        )

    ours = "\n".join(
        record.getMessage() for record in caplog.records if record.name.startswith("autoapply")
    )
    assert "mcp_tool_call tool=search_jobs" in ours
    for leaked in ("CANARY", "python", "Senior", "Acme", "greenhouse.io"):
        assert leaked not in ours


# ---------------------------------------------------------------------------
# Read-only guarantees
# ---------------------------------------------------------------------------


async def test_read_only_database_rejects_writes(database_url: str) -> None:
    engine, session_factory = open_read_only_database(database_url)
    try:
        async with session_factory() as session:
            assert (await session.execute(text("SELECT count(*) FROM jobs"))).scalar_one() == 8
            with pytest.raises(OperationalError, match="readonly"):
                await session.execute(text("UPDATE runs SET status = 'cancelled'"))
            with pytest.raises(OperationalError, match="readonly"):
                await session.execute(text("DELETE FROM jobs"))
    finally:
        await engine.dispose()


def test_sqlite_file_path_resolves_file_urls_only(tmp_path: Path) -> None:
    assert sqlite_file_path(f"sqlite+aiosqlite:///{tmp_path}/x.db") == tmp_path / "x.db"
    assert sqlite_file_path("sqlite+aiosqlite:///./x.db") == Path.cwd() / "x.db"
    assert sqlite_file_path("sqlite+aiosqlite:///:memory:") is None
    assert sqlite_file_path("sqlite+aiosqlite://") is None
    assert sqlite_file_path("sqlite+aiosqlite:///file:x.db?mode=ro&uri=true") is None
    assert sqlite_file_path("postgresql+asyncpg://u:p@db/jobs") is None


# ---------------------------------------------------------------------------
# stdio transport and CLI
# ---------------------------------------------------------------------------


def test_serve_stdio_skips_blank_lines_and_rejects_oversized_messages(
    database_url: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(mcp_server, "MAX_MESSAGE_BYTES", 512)
    oversized = json.dumps(modern("tools/list", {"pad": "x" * 1200})).encode()
    stdin = io.BytesIO(
        b"\n" + oversized + b"\n" + json.dumps(modern("server/discover")).encode() + b"\n"
    )
    stdout = io.BytesIO()
    engine, session_factory = open_read_only_database(database_url)

    with asyncio.Runner() as runner:
        try:
            serve_stdio(CareerSearchMcpServer(session_factory), stdin, stdout, runner.run)
        finally:
            runner.run(engine.dispose())

    first, second = (json.loads(line) for line in stdout.getvalue().splitlines())
    assert first == {
        "jsonrpc": "2.0",
        "error": {"code": -32600, "message": "Message exceeds 512 bytes"},
    }
    assert second["result"]["resultType"] == "complete"


def test_lone_surrogate_request_id_does_not_end_the_stdio_session(database_url: str) -> None:
    bad_id = b'{"jsonrpc":"2.0","id":"\\ud800","method":"ping"}'
    stdin = io.BytesIO(bad_id + b"\n" + json.dumps(modern("server/discover")).encode() + b"\n")
    stdout = io.BytesIO()
    engine, session_factory = open_read_only_database(database_url)

    with asyncio.Runner() as runner:
        try:
            serve_stdio(CareerSearchMcpServer(session_factory), stdin, stdout, runner.run)
        finally:
            runner.run(engine.dispose())

    first, second = (json.loads(line) for line in stdout.getvalue().splitlines())
    assert first["id"] == "\ud800"
    assert second["result"]["resultType"] == "complete"
    assert stdout.getvalue().isascii()


def _subprocess_env() -> dict[str, str]:
    """Environment for server subprocesses (source tree importable, no inherited DB URL)."""

    env = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(REPO_ROOT / "src"), env.get("PYTHONPATH")) if part
    )
    return env


def test_stdio_subprocess_keeps_stdout_pure_for_both_eras(
    database_url: str, tmp_path: Path
) -> None:
    meta = modern_meta()
    audit_path = tmp_path / "audit.jsonl"
    messages: list[Any] = [
        rpc("server/discover", {"_meta": meta}, 1),
        rpc("tools/list", {"_meta": meta}, 2),
        rpc(
            "tools/call",
            {
                "name": "search_jobs",
                "arguments": {"q": "CANARY python", "remote": True, "sort": "score"},
                "_meta": meta,
            },
            3,
        ),
        rpc(
            "tools/call",
            {"name": "explain_job_score", "arguments": {"job_id": 1}, "_meta": meta},
            4,
        ),
        rpc("tools/call", {"name": "create_run", "arguments": {}, "_meta": meta}, 5),
        "this line is not JSON",
        rpc(
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "x"}},
            6,
        ),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        rpc("tools/call", {"name": "list_runs", "arguments": {"limit": 1}}, 7),
        rpc("tools/call", {"name": "get_job", "arguments": {"job_id": 99999}}, 8),
    ]
    payload = "".join(
        (message if isinstance(message, str) else json.dumps(message)) + "\n"
        for message in messages
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "autoapply_agent.mcp",
            "--database-url",
            database_url,
            "--audit-log",
            str(audit_path),
            "--log-level",
            "DEBUG",
        ],
        input=payload.encode(),
        capture_output=True,
        cwd=tmp_path,
        env=_subprocess_env(),
        timeout=60,
        check=False,
    )

    stderr = completed.stderr.decode()
    assert completed.returncode == 0, stderr
    stdout = completed.stdout.decode("ascii")
    assert stdout.endswith("\n")
    lines = stdout.splitlines()
    responses = [json.loads(line) for line in lines]
    for response in responses:
        assert response["jsonrpc"] == "2.0"
        assert ("result" in response) != ("error" in response)
        assert "id" not in response or isinstance(response["id"], (int, str))
    assert [response.get("id") for response in responses] == [1, 2, 3, 4, 5, None, 6, 7, 8]
    discover, listed, searched, explained, write, parse, initialized, legacy, missing = responses
    assert discover["result"]["supportedVersions"][0] == MODERN
    assert [tool["name"] for tool in listed["result"]["tools"]] == READ_ONLY_TOOLS
    assert searched["result"]["structuredContent"]["total"] == 0
    assert explained["result"]["structuredContent"]["job_id"] == 1
    assert write["error"]["code"] == -32602
    assert parse["error"]["code"] == -32700
    assert initialized["result"]["protocolVersion"] == "2025-06-18"
    assert "resultType" not in legacy["result"]
    assert legacy["result"]["structuredContent"]["runs"][0]["job_count"] == 5
    assert missing["result"]["isError"] is True
    # Logs went to STDERR, at DEBUG, without arguments, results or SQL.
    assert "mcp_tool_call tool=search_jobs" in stderr
    for leaked in ("CANARY", "Senior Python", "SELECT"):
        assert leaked not in stderr
    # Four tool calls ran (the unknown create_run never reached a tool).
    assert len(audit_path.read_text().splitlines()) == 4


def test_cli_refuses_a_missing_database_file_without_creating_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "nope" / "jobs.db"

    with pytest.raises(SystemExit) as exc_info:
        mcp_server.main(["--database-url", f"sqlite+aiosqlite:///{missing}"])

    assert exc_info.value.code == 2
    assert f"database file not found: {missing}" in capsys.readouterr().err
    assert not missing.exists()


@pytest.mark.parametrize(
    ("url", "fragment"),
    [
        ("not a url", "is not a valid SQLAlchemy URL"),
        ("sqlite:///:memory:", "an async driver is required"),
    ],
)
def test_cli_rejects_unusable_database_urls(
    url: str, fragment: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        mcp_server.main(["--database-url", url])

    assert exc_info.value.code == 2
    assert fragment in capsys.readouterr().err


def test_invalid_log_level_is_rejected_by_the_cli() -> None:
    with pytest.raises(SystemExit) as exc_info:
        mcp_server.main(["--log-level", "LOUD"])

    assert exc_info.value.code == 2


def test_module_entry_point_reports_version(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "autoapply_agent.mcp", "--version"],
        capture_output=True,
        cwd=tmp_path,
        env=_subprocess_env(),
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.decode().strip() == (
        f"career-search-mcp {__version__} (MCP 2026-07-28, 2025-11-25, 2025-06-18)"
    )


def test_console_script_is_declared() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["career-search-mcp"] == (
        "autoapply_agent.mcp.server:main"
    )
