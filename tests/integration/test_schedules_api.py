"""``/schedules`` API: validation and error shapes, lifecycle endpoints, preview and wiring."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from autoapply_agent.core.config import Settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import RunSchedule
from autoapply_agent.main import create_app

WEEKDAYS = {"name": "weekday mornings", "cron": "30  8 * * 1-5", "timezone": "America/Los_Angeles"}
INTERVAL = {"name": "every 15 minutes", "interval_minutes": 15, "query": "python"}


def _client(database_url: str, **overrides: Any) -> Iterator[TestClient]:
    values: dict[str, Any] = {
        "DATABASE_URL": database_url,
        "ENABLE_WORKER": False,
        "ENABLE_SCHEDULER": False,
        "ENVIRONMENT": "test",
    }
    settings = Settings(**{**values, **overrides})
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture()
def client(sqlite_database_url: str) -> Iterator[TestClient]:
    """Client without background worker or scheduler (ticks are driven by the test)."""

    yield from _client(sqlite_database_url)


def _create(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/schedules", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _tick(client: TestClient, now: datetime | None = None) -> list[Any]:
    scheduler = client.app.state.scheduler  # type: ignore[attr-defined]
    outcomes: list[Any] = client.portal.call(
        scheduler.tick, now or utc_now() + timedelta(seconds=5)
    )
    return outcomes


def _error(response: Any) -> tuple[str, list[Any]]:
    assert response.status_code == 422, response.text
    [error] = response.json()["detail"]
    return error["type"], error["loc"]


def test_create_cron_schedule_returns_its_next_five_local_fires(client: TestClient) -> None:
    response = client.post("/schedules", json=WEEKDAYS)

    assert response.status_code == 201, response.text
    body = response.json()
    assert response.headers["location"].endswith(f"/schedules/{body['id']}")
    assert (body["kind"], body["cron"], body["interval_minutes"]) == ("cron", "30 8 * * 1-5", None)
    assert (body["overlap_policy"], body["jitter_seconds"], body["paused"]) == ("skip", 0, False)
    assert (body["last_run_id"], body["last_run_status"], body["source_config_ids"]) == (
        None,
        None,
        None,
    )
    assert len(body["upcoming"]) == 5
    assert body["next_run_at"] == body["upcoming"][0]["at"]
    for fire in body["upcoming"]:
        local = datetime.fromisoformat(fire["local"])
        assert (local.hour, local.minute, local.isoweekday() <= 5) == (8, 30, True)
        assert local == datetime.fromisoformat(fire["at"].replace("Z", "+00:00"))
    assert client.get(f"/schedules/{body['id']}").json()["upcoming"] == body["upcoming"]


def test_interval_schedule_fires_on_the_next_tick_through_the_runs_pipeline(
    client: TestClient,
) -> None:
    schedule = _create(client, {**INTERVAL, "source_config_ids": [3]})
    planned = datetime.fromisoformat(schedule["next_run_at"].replace("Z", "+00:00"))

    [outcome] = _tick(client)
    detail = client.get(f"/schedules/{schedule['id']}").json()
    run = client.get(f"/runs/{detail['last_run_id']}").json()
    events = client.get(f"/runs/{detail['last_run_id']}/events").json()

    created = datetime.fromisoformat(schedule["created_at"].replace("Z", "+00:00"))
    assert timedelta(0) < planned - created <= timedelta(seconds=1)
    assert outcome.kind.value == "fired"
    assert detail["last_run_status"] == "queued"
    assert (run["status"], run["query"], run["source_config_ids"]) == ("queued", "python", [3])
    assert events[0]["event_type"] == "run.created"
    assert events[0]["message"] == "Run queued by schedule 'every 15 minutes' (schedule)"
    assert events[0]["payload"]["schedule_id"] == schedule["id"]
    history = client.get(f"/schedules/{schedule['id']}/history").json()
    assert [(item["kind"], item["run_id"]) for item in history] == [("fired", run["id"])]


@pytest.mark.parametrize(
    ("payload", "error_type", "loc"),
    [
        ({**WEEKDAYS, "cron": "*/5 * * * *"}, "cron_invalid", ["body", "cron"]),
        ({**WEEKDAYS, "cron": "61 * * * *"}, "cron_invalid", ["body", "cron"]),
        ({**WEEKDAYS, "cron": "0 0 30 2 *"}, "cron_invalid", ["body", "cron"]),
        ({**WEEKDAYS, "timezone": "Mars/Olympus"}, "timezone_invalid", ["body", "timezone"]),
        ({**INTERVAL, "interval_minutes": 14}, "greater_than_equal", ["body", "interval_minutes"]),
        ({**INTERVAL, "cron": "@daily"}, "schedule_cadence", ["body"]),
        ({"name": "no cadence"}, "schedule_cadence", ["body"]),
        ({**INTERVAL, "kind": "cron"}, "schedule_cadence", ["body"]),
        ({**INTERVAL, "jitter_seconds": 601}, "less_than_equal", ["body", "jitter_seconds"]),
        ({**INTERVAL, "overlap_policy": "allow_all"}, "enum", ["body", "overlap_policy"]),
        ({**INTERVAL, "max_runs": 3}, "extra_forbidden", ["body", "max_runs"]),
        ({**INTERVAL, "name": "two\nlines"}, "text_control_characters", ["body", "name"]),
        ({**INTERVAL, "name": "  x "}, "name_too_short", ["body", "name"]),
        ({**INTERVAL, "pause_note": "why"}, "pause_note_unpaused", ["body"]),
        (
            {**INTERVAL, "start_at": "2099-01-01T00:00:00Z"},
            "start_at_range",
            ["body", "start_at"],
        ),
    ],
)
def test_invalid_schedules_are_422_with_the_fastapi_error_shape(
    client: TestClient, payload: dict[str, Any], error_type: str, loc: list[Any]
) -> None:
    assert _error(client.post("/schedules", json=payload)) == (error_type, loc)


def test_cron_errors_explain_what_to_fix(client: TestClient) -> None:
    response = client.post("/schedules", json={**WEEKDAYS, "cron": "*/5 * * * *"})

    [error] = response.json()["detail"]
    assert error["msg"] == (
        "invalid cron expression: fires 5 minute(s) apart; schedules fire at most every 15 minutes"
    )
    assert error["input"] == "*/5 * * * *"


@pytest.mark.parametrize(
    "parameters",
    [
        {"source_config_ids": [0]},
        {"source_config_ids": ["one"]},
        {"source_config_ids": [2**63]},
        {"query": "q" * 257},
        {"query": 5},
    ],
)
def test_run_parameters_are_validated_exactly_like_post_runs(
    client: TestClient, parameters: dict[str, Any]
) -> None:
    run_errors = client.post("/runs", json=parameters).json()["detail"]
    schedule_errors = client.post("/schedules", json={**INTERVAL, **parameters}).json()["detail"]

    assert run_errors and schedule_errors == run_errors


def test_names_are_unique_on_create_and_rename(client: TestClient) -> None:
    first = _create(client, INTERVAL)
    second = _create(client, WEEKDAYS)

    duplicate = client.post("/schedules", json=INTERVAL)
    rename = client.patch(f"/schedules/{second['id']}", json={"name": first["name"]})

    assert duplicate.status_code == rename.status_code == 409
    assert duplicate.json() == {"detail": "schedule with this name already exists"}
    assert client.get(f"/schedules/{second['id']}").json()["name"] == WEEKDAYS["name"]


def test_list_filters_pages_and_orders_soonest_first(client: TestClient) -> None:
    weekdays = _create(client, WEEKDAYS)
    interval = _create(client, INTERVAL)
    paused = _create(client, {"name": "paused nightly", "cron": "@daily", "paused": True})

    everything = client.get("/schedules")
    active = client.get("/schedules", params={"paused": "false"})
    cron = client.get("/schedules", params={"kind": "cron", "q": "NIGHT"})
    page = client.get("/schedules", params={"limit": 1, "offset": 1})

    assert [item["id"] for item in everything.json()] == [
        interval["id"],
        weekdays["id"],
        paused["id"],
    ]
    assert everything.headers["x-total-count"] == "3"
    assert [item["id"] for item in active.json()] == [interval["id"], weekdays["id"]]
    assert [item["id"] for item in cron.json()] == [paused["id"]]
    assert ([item["id"] for item in page.json()], page.headers["x-total-count"]) == (
        [weekdays["id"]],
        "3",
    )
    assert _error(client.get("/schedules", params={"limit": 201})) == (
        "less_than_equal",
        ["query", "limit"],
    )


def test_patch_switches_the_cadence_and_replans_the_next_fire(client: TestClient) -> None:
    schedule = _create(client, INTERVAL)

    to_cron = client.patch(
        f"/schedules/{schedule['id']}",
        json={"cron": "@daily", "timezone": "Europe/Berlin", "query": None},
    ).json()
    to_interval = client.patch(
        f"/schedules/{schedule['id']}", json={"interval_minutes": 60, "jitter_seconds": 30}
    ).json()

    assert (to_cron["kind"], to_cron["cron"], to_cron["interval_minutes"]) == (
        "cron",
        "@daily",
        None,
    )
    assert to_cron["query"] is None
    midnight = datetime.fromisoformat(to_cron["upcoming"][0]["local"])
    assert (midnight.hour, midnight.minute) == (0, 0)
    assert to_cron["upcoming"][0]["local"][-6:] in {"+01:00", "+02:00"}
    assert (to_interval["kind"], to_interval["cron"], to_interval["interval_minutes"]) == (
        "interval",
        None,
        60,
    )
    assert to_interval["updated_at"] >= to_cron["updated_at"]


@pytest.mark.parametrize(
    ("payload", "error_type"),
    [
        ({"name": None}, "null_not_allowed"),
        ({"timezone": None}, "null_not_allowed"),
        ({"kind": "cron"}, "schedule_cadence"),
        ({"cron": "@hourly", "interval_minutes": 30}, "schedule_cadence"),
        ({"paused": True}, "extra_forbidden"),
        ({"cron": "* * * * *"}, "cron_invalid"),
    ],
)
def test_invalid_patches_are_422(
    client: TestClient, payload: dict[str, Any], error_type: str
) -> None:
    schedule = _create(client, INTERVAL)

    assert _error(client.patch(f"/schedules/{schedule['id']}", json=payload))[0] == error_type


def test_pause_and_resume_are_idempotent_and_recorded(client: TestClient) -> None:
    schedule = _create(client, INTERVAL)
    url = f"/schedules/{schedule['id']}"

    paused = client.post(f"{url}/pause", json={"note": "board maintenance until Monday"}).json()
    again = client.post(f"{url}/pause").json()
    assert _tick(client) == []
    resumed = client.post(f"{url}/resume", json={"note": "board is back"}).json()
    client.post(f"{url}/resume")
    history = client.get(f"{url}/history")

    assert (paused["paused"], paused["next_run_at"], paused["upcoming"]) == (True, None, [])
    assert paused["pause_note"] == again["pause_note"] == "board maintenance until Monday"
    assert (resumed["paused"], resumed["pause_note"]) == (False, None)
    assert len(resumed["upcoming"]) == 5
    assert history.headers["x-total-count"] == "2"
    assert [(item["kind"], item["reason"]) for item in history.json()] == [
        ("resumed", "board is back"),
        ("paused", "board maintenance until Monday"),
    ]


def test_trigger_follows_the_overlap_policy(client: TestClient) -> None:
    tomorrow = (utc_now() + timedelta(days=1)).isoformat()
    schedule = _create(client, {**INTERVAL, "start_at": tomorrow})
    url = f"/schedules/{schedule['id']}"

    triggered = client.post(f"{url}/trigger").json()
    skipped = client.post(f"{url}/trigger").json()
    client.patch(url, json={"overlap_policy": "buffer_one"})
    buffered = client.post(f"{url}/trigger").json()
    full = client.post(f"{url}/trigger").json()
    client.post(f"/runs/{triggered['run_id']}/cancel")
    [started] = _tick(client)

    assert (triggered["outcome"], skipped["outcome"]) == ("triggered", "skipped_overlap")
    assert triggered["schedule"]["last_run_id"] == triggered["run_id"]
    assert skipped["run_id"] is None
    assert skipped["reason"] == (
        f"manual trigger skipped: run {triggered['run_id']} is still queued (overlap_policy=skip)"
    )
    assert buffered["outcome"] == "buffered"
    assert buffered["schedule"]["buffered_fire_at"] is not None
    assert full["outcome"] == "skipped_overlap"
    assert (started.kind.value, started.run_id is not None) == ("fired", True)
    assert schedule["next_run_at"] == client.get(url).json()["next_run_at"]
    kinds = client.get(f"{url}/history", params={"kind": ["skipped_overlap", "triggered"]})
    assert kinds.headers["x-total-count"] == "3"
    assert [item["kind"] for item in kinds.json()] == [
        "skipped_overlap",
        "skipped_overlap",
        "triggered",
    ]
    assert len(client.get(f"{url}/history", params={"limit": 1}).json()) == 1


def test_preview_dry_runs_an_expression(client: TestClient) -> None:
    response = client.get(
        "/schedules/preview",
        params={
            "cron": "30 2 * * *",
            "timezone": "America/Los_Angeles",
            "after": "2027-03-13T00:00:00Z",
            "count": 3,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "cron": "30 2 * * *",
        "timezone": "America/Los_Angeles",
        "min_gap_minutes": 1440,
        "upcoming": [
            {"at": "2027-03-13T10:30:00Z", "local": "2027-03-13T02:30:00-08:00"},
            {"at": "2027-03-15T09:30:00Z", "local": "2027-03-15T02:30:00-07:00"},
            {"at": "2027-03-16T09:30:00Z", "local": "2027-03-16T02:30:00-07:00"},
        ],
    }
    assert client.get("/schedules", params={}).headers["x-total-count"] == "0"


@pytest.mark.parametrize(
    ("params", "error_type", "loc"),
    [
        ({"cron": "30 2 * *"}, "cron_invalid", ["query", "cron"]),
        ({"cron": "*/10 * * * *"}, "cron_invalid", ["query", "cron"]),
        ({"cron": "@daily", "timezone": "Nowhere/City"}, "timezone_invalid", ["query", "timezone"]),
        ({"cron": "@daily", "count": 21}, "less_than_equal", ["query", "count"]),
        ({}, "missing", ["query", "cron"]),
    ],
)
def test_preview_rejects_bad_input_with_422(
    client: TestClient, params: dict[str, Any], error_type: str, loc: list[str]
) -> None:
    assert _error(client.get("/schedules/preview", params=params)) == (error_type, loc)


def test_delete_drops_the_schedule_and_its_history_but_keeps_runs(client: TestClient) -> None:
    schedule = _create(client, INTERVAL)
    run_id = client.post(f"/schedules/{schedule['id']}/trigger").json()["run_id"]

    deleted = client.delete(f"/schedules/{schedule['id']}")

    assert deleted.status_code == 204
    assert client.get(f"/schedules/{schedule['id']}").status_code == 404
    assert client.get(f"/runs/{run_id}").status_code == 200
    assert _create(client, INTERVAL)["name"] == INTERVAL["name"]


def test_a_schedule_whose_time_zone_is_unavailable_is_still_readable(
    client: TestClient,
) -> None:
    schedule = _create(client, WEEKDAYS)

    async def corrupt() -> None:
        factory = client.app.state.session_factory  # type: ignore[attr-defined]
        async with factory() as session:
            await session.execute(
                update(RunSchedule)
                .where(RunSchedule.id == schedule["id"])
                .values(timezone="Mars/Olympus")
            )
            await session.commit()

    client.portal.call(corrupt)
    response = client.get(f"/schedules/{schedule['id']}")

    assert response.status_code == 200
    assert (response.json()["timezone"], response.json()["upcoming"]) == ("Mars/Olympus", [])


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", ""),
        ("patch", ""),
        ("delete", ""),
        ("post", "/pause"),
        ("post", "/resume"),
        ("post", "/trigger"),
        ("get", "/history"),
    ],
)
def test_unknown_schedules_are_404(client: TestClient, method: str, path: str) -> None:
    kwargs: dict[str, Any] = {"json": {}} if method == "patch" else {}
    response = client.request(method.upper(), f"/schedules/999{path}", **kwargs)

    assert (response.status_code, response.json()) == (404, {"detail": "schedule not found"})
    assert client.request(method.upper(), f"/schedules/0{path}", **kwargs).status_code == 422


def test_enabled_scheduler_fires_schedules_in_the_background(sqlite_database_url: str) -> None:
    for client in _client(sqlite_database_url, ENABLE_SCHEDULER=True, SCHEDULER_TICK_SECONDS=0.05):
        schedule = _create(client, INTERVAL)
        deadline = time.monotonic() + 10
        detail = client.get(f"/schedules/{schedule['id']}").json()
        while detail["last_run_id"] is None and time.monotonic() < deadline:
            time.sleep(0.05)
            detail = client.get(f"/schedules/{schedule['id']}").json()

        assert detail["last_run_status"] == "queued"
        assert datetime.fromisoformat(detail["next_run_at"].replace("Z", "+00:00")) > datetime.now(
            UTC
        ) + timedelta(minutes=14)
