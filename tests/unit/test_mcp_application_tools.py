"""MCP ``list_applications`` / ``get_application``: read-only views of the tracker."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from autoapply_agent.mcp.database import open_read_only_database
from autoapply_agent.mcp.schema import validate
from autoapply_agent.mcp.server import CareerSearchMcpServer
from autoapply_agent.mcp.tools import LIST_NOTES_PREVIEW_CHARS, TOOLS_BY_NAME
from tests.integration.test_jobs_match_api import MATCH_JOBS, _seed, app_client

META = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientCapabilities": {},
}
LONG_NOTES = "Prep: " + "system design " * 40


def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """A modern ``tools/call`` request."""

    params = {"name": name, "arguments": arguments, "_meta": META}
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}


async def result_of(
    server: CareerSearchMcpServer, name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call a tool and return its ``result``."""

    response = await server.handle_message(call(name, arguments))
    assert response is not None and "result" in response, response
    result: dict[str, Any] = response["result"]
    return result


@pytest.fixture()
def database_url(sqlite_database_url: str) -> str:
    """Match fixtures with three applications tracked through the HTTP API."""

    asyncio.run(_seed(sqlite_database_url, MATCH_JOBS))
    for client in app_client(sqlite_database_url):
        acme = client.post("/applications", json={"job_id": 1, "notes": LONG_NOTES}).json()
        client.patch(f"/applications/{acme['id']}", json={"stage": "applied"})
        client.patch(
            f"/applications/{acme['id']}",
            json={"stage": "interview", "note": "Onsite", "next_action_at": "2020-01-01T09:00Z"},
        )
        client.post("/applications", json={"job_id": 2})
        hooli = client.post("/applications", json={"job_id": 4}).json()
        client.post(f"/applications/{hooli['id']}/archive")
    return sqlite_database_url


@pytest.fixture()
async def server(database_url: str) -> AsyncIterator[CareerSearchMcpServer]:
    """A read-only server over the tracked applications."""

    engine, session_factory = open_read_only_database(database_url)
    try:
        yield CareerSearchMcpServer(session_factory)
    finally:
        await engine.dispose()


async def test_list_applications_returns_schema_valid_pages(
    server: CareerSearchMcpServer,
) -> None:
    result = await result_of(server, "list_applications", {"limit": 1})

    assert result["isError"] is False, result["content"][0]["text"]
    structured = result["structuredContent"]
    assert validate(structured, TOOLS_BY_NAME["list_applications"].output_schema, "out") == []
    assert structured["total"] == 2
    assert structured["next_offset"] == 1
    assert structured["stage_counts"] == {
        "saved": 1,
        "applied": 0,
        "interview": 1,
        "offer": 0,
        "accepted": 0,
        "rejected": 0,
    }
    assert structured["follow_ups"] == {"overdue": 1, "due": 0, "scheduled": 0, "none": 1}
    text = result["content"][0]["text"]
    assert text.startswith("2 tracked applications (archived hidden, sort=updated); showing 1-1:")
    assert "More: call list_applications again with offset=1." in text


async def test_list_applications_filters_and_previews_notes(
    server: CareerSearchMcpServer,
) -> None:
    overdue = await result_of(server, "list_applications", {"follow_up": "overdue"})
    archived = await result_of(
        server, "list_applications", {"include_archived": True, "stage": ["saved"]}
    )

    [record] = overdue["structuredContent"]["applications"]
    assert record["stage"] == "interview"
    assert record["follow_up_status"] == "overdue"
    assert record["next_action_at"] == "2020-01-01T09:00:00Z"
    assert record["notes_truncated"] is True
    assert record["notes"] == LONG_NOTES[:LIST_NOTES_PREVIEW_CHARS] + "…"
    assert "follow-up overdue 2020-01-01T09:00:00Z" in overdue["content"][0]["text"]
    assert archived["structuredContent"]["total"] == 2
    assert any(item["archived"] for item in archived["structuredContent"]["applications"])


async def test_get_application_returns_the_full_notes_and_timeline(
    server: CareerSearchMcpServer,
) -> None:
    result = await result_of(server, "get_application", {"application_id": 1, "event_limit": 2})

    assert result["isError"] is False, result["content"][0]["text"]
    structured = result["structuredContent"]
    assert validate(structured, TOOLS_BY_NAME["get_application"].output_schema, "out") == []
    assert structured["application"]["notes"] == LONG_NOTES.strip()
    assert structured["application"]["notes_truncated"] is False
    assert structured["application"]["allowed_stages"] == ["offer", "rejected"]
    assert structured["event_count"] == 3
    assert structured["events_truncated"] is True
    assert [event["to_stage"] for event in structured["events"]] == ["applied", "interview"]
    assert structured["events"][1]["note"] == "Onsite"
    text = result["content"][0]["text"]
    assert text.startswith("Application #1 · interview for 0 days (next: offer, rejected)")
    assert "Last 2 of 3 timeline events:" in text


@pytest.mark.parametrize(
    ("name", "arguments", "message"),
    [
        (
            "get_application",
            {"application_id": 99},
            "No application with id 99. Use list_applications to find ids.",
        ),
        ("get_application", {}, None),
        ("list_applications", {"stage": ["ghosted"]}, None),
        ("list_applications", {"follow_up": "soon"}, None),
        ("list_applications", {"limit": 51}, None),
    ],
)
async def test_bad_arguments_are_tool_errors(
    server: CareerSearchMcpServer, name: str, arguments: dict[str, Any], message: str | None
) -> None:
    result = await result_of(server, name, arguments)

    assert result["isError"] is True
    if message is not None:
        assert result["content"][0]["text"] == message
