"""MCP ``list_schedules`` / ``get_schedule``: read-only views of recurring discovery runs."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from autoapply_agent.mcp.database import open_read_only_database
from autoapply_agent.mcp.schema import validate
from autoapply_agent.mcp.server import CareerSearchMcpServer
from autoapply_agent.mcp.tools import TOOLS_BY_NAME
from tests.integration.test_schedules_api import _client
from tests.unit.test_mcp_application_tools import result_of


@pytest.fixture()
def database_url(sqlite_database_url: str) -> str:
    """Two schedules created through the HTTP API: one triggered twice, one paused."""

    for client in _client(sqlite_database_url):
        hourly = client.post(
            "/schedules",
            json={"name": "hourly python", "interval_minutes": 60, "query": "python"},
        ).json()
        client.post(f"/schedules/{hourly['id']}/trigger")
        client.post(f"/schedules/{hourly['id']}/trigger")
        weekly = client.post(
            "/schedules",
            json={"name": "weekly berlin", "cron": "0 9 * * mon", "timezone": "Europe/Berlin"},
        ).json()
        client.post(f"/schedules/{weekly['id']}/pause", json={"note": "on vacation"})
    return sqlite_database_url


@pytest.fixture()
async def server(database_url: str) -> AsyncIterator[CareerSearchMcpServer]:
    """A read-only server over the schedules."""

    engine, session_factory = open_read_only_database(database_url)
    try:
        yield CareerSearchMcpServer(session_factory)
    finally:
        await engine.dispose()


def _structured(result: dict[str, Any], tool: str) -> dict[str, Any]:
    assert result["isError"] is False, result["content"][0]["text"]
    structured: dict[str, Any] = result["structuredContent"]
    assert validate(structured, TOOLS_BY_NAME[tool].output_schema, "out") == []
    return structured


async def test_list_schedules_returns_schema_valid_pages(server: CareerSearchMcpServer) -> None:
    first = _structured(await result_of(server, "list_schedules", {"limit": 1}), "list_schedules")
    paused = _structured(
        await result_of(server, "list_schedules", {"paused": True}), "list_schedules"
    )
    cron = await result_of(server, "list_schedules", {"kind": "cron"})

    assert (first["total"], first["next_offset"]) == (2, 1)
    [hourly] = first["schedules"]
    assert (hourly["name"], hourly["kind"], hourly["interval_minutes"]) == (
        "hourly python",
        "interval",
        60,
    )
    assert hourly["next_run_at"] is not None and hourly["last_run_id"] is not None
    assert [item["name"] for item in paused["schedules"]] == ["weekly berlin"]
    assert paused["schedules"][0]["pause_note"] == "on vacation"
    text = cron["content"][0]["text"]
    assert 'weekly berlin · cron "0 9 * * mon" Europe/Berlin · paused' in text


async def test_get_schedule_returns_upcoming_fires_and_history(
    server: CareerSearchMcpServer,
) -> None:
    result = await result_of(server, "get_schedule", {"schedule_id": 1, "history_limit": 1})
    structured = _structured(result, "get_schedule")

    assert structured["last_run_status"] == "queued"
    assert len(structured["upcoming"]) == 5
    assert (structured["history_count"], structured["history_truncated"]) == (2, True)
    [latest] = structured["history"]
    assert latest["kind"] == "skipped_overlap"
    assert latest["reason"].startswith("manual trigger skipped: run ")
    assert "Last 1 of 2 history events, newest first:" in result["content"][0]["text"]


async def test_get_schedule_of_a_paused_schedule_has_no_upcoming_fires(
    server: CareerSearchMcpServer,
) -> None:
    structured = _structured(
        await result_of(server, "get_schedule", {"schedule_id": 2}), "get_schedule"
    )

    assert structured["schedule"]["paused"] is True
    assert structured["upcoming"] == []
    assert [item["kind"] for item in structured["history"]] == ["paused"]


async def test_unknown_or_invalid_schedule_ids_are_tool_errors(
    server: CareerSearchMcpServer,
) -> None:
    missing = await result_of(server, "get_schedule", {"schedule_id": 99})
    invalid = await result_of(server, "get_schedule", {"schedule_id": 0})

    assert missing["isError"] is True
    assert "Use list_schedules" in missing["content"][0]["text"]
    assert invalid["isError"] is True
    assert "schedule_id" in invalid["content"][0]["text"]
