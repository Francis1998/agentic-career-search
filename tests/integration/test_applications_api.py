"""API tests for the application tracker (``/applications``)."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import Application, ApplicationEvent
from autoapply_agent.services.application_export import APPLICATION_CSV_COLUMNS
from tests.integration.test_jobs_match_api import (
    HOSTILE_JOBS,
    MATCH_JOBS,
    MatchJob,
    client_for,
)

# Job ids follow insertion order: acme 1, hooli 2, initech 3, globex 4, acme-mirror 5,
# sre 6, hostile 7, acme-recapture 8 (same posting URL as acme, captured by a later run).
ACME, HOOLI, INITECH, GLOBEX, ACME_MIRROR, SRE, HOSTILE, ACME_RECAPTURE = range(1, 9)
RECAPTURE = MatchJob(
    "acme-recapture",
    "run-b",
    1,
    "Senior Python Engineer",
    "Acme Robotics",
    "Remote - US",
    " HTTPS://boards.greenhouse.io/acme/jobs/1 ",
    0.92,
    6,
)
SQLITE_MAX = 2**63 - 1


@pytest.fixture()
def client(sqlite_database_url: str) -> Iterator[TestClient]:
    """Client over the match fixtures, a hostile job and a re-captured posting."""

    yield from client_for(sqlite_database_url, (*MATCH_JOBS, *HOSTILE_JOBS, RECAPTURE))


def track(client: TestClient, job_id: int, **body: Any) -> dict[str, Any]:
    """Track ``job_id`` and return the new application."""

    response = client.post("/applications", json={"job_id": job_id, **body})
    assert response.status_code == 201, response.text
    created: dict[str, Any] = response.json()
    return created


def patch(client: TestClient, application_id: int, **body: Any) -> dict[str, Any]:
    """PATCH an application and return it."""

    response = client.patch(f"/applications/{application_id}", json=body)
    assert response.status_code == 200, response.text
    updated: dict[str, Any] = response.json()
    return updated


def events(client: TestClient, application_id: int) -> list[dict[str, Any]]:
    """Return the timeline of an application."""

    response = client.get(f"/applications/{application_id}/events")
    assert response.status_code == 200, response.text
    timeline: list[dict[str, Any]] = response.json()
    return timeline


def iso(delta: timedelta) -> str:
    """An ISO-8601 UTC instant ``delta`` away from now."""

    return (utc_now() + delta).replace(microsecond=0).isoformat()


def test_tracking_a_job_returns_it_with_location_and_a_first_event(client: TestClient) -> None:
    response = client.post(
        "/applications", json={"job_id": ACME, "note": "Referred by Sam", "notes": " prep "}
    )

    assert response.status_code == 201
    created = response.json()
    assert response.headers["location"].endswith(f"/applications/{created['id']}")
    assert created["job_id"] == ACME
    assert created["stage"] == "saved"
    assert created["archived"] is False
    assert created["notes"] == "prep"
    assert created["applied_at"] is None
    assert created["follow_up_status"] == "none"
    assert created["days_in_stage"] == 0
    assert created["allowed_stages"] == ["applied", "rejected"]
    assert created["job"]["title"] == "Senior Python Engineer"
    assert created["job"]["company"] == "Acme Robotics"
    assert created["job"]["remote"] is True
    assert created["job"]["priority_tier"] == "high"
    assert created["job"]["url"] == "https://boards.greenhouse.io/acme/jobs/1"
    assert client.get(f"/applications/{created['id']}").json() == created
    [event] = events(client, created["id"])
    assert event["sequence"] == 1
    assert event["event_type"] == "tracked"
    assert (event["from_stage"], event["to_stage"]) == (None, "saved")
    assert event["note"] == "Referred by Sam"
    assert event["changes"] == {"job_id": ACME}


def test_starting_at_applied_records_the_applied_time(client: TestClient) -> None:
    created = track(client, HOOLI, stage="applied", next_action_at=iso(timedelta(days=3)))

    assert created["stage"] == "applied"
    assert created["applied_at"] is not None
    assert created["follow_up_status"] == "due"
    [event] = events(client, created["id"])
    assert event["to_stage"] == "applied"
    assert set(event["changes"]) == {"job_id", "applied_at", "next_action_at"}


def test_unknown_job_is_404(client: TestClient) -> None:
    response = client.post("/applications", json={"job_id": 999})

    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_tracking_a_job_twice_is_409_pointing_at_the_application(client: TestClient) -> None:
    created = track(client, ACME)

    again = client.post("/applications", json={"job_id": ACME})

    assert again.status_code == 409
    assert again.json() == {"detail": f"job {ACME} is already tracked as application 1"}
    assert again.headers["location"].endswith(f"/applications/{created['id']}")


def test_a_recaptured_posting_is_409_not_a_second_application(client: TestClient) -> None:
    track(client, ACME)

    response = client.post("/applications", json={"job_id": ACME_RECAPTURE})

    assert response.status_code == 409
    assert "already tracked as application 1" in response.json()["detail"]
    assert "same URL" in response.json()["detail"]
    assert client.get("/applications").headers["x-total-count"] == "1"


def test_the_full_pipeline_is_recorded_in_order(client: TestClient) -> None:
    application_id = track(client, GLOBEX)["id"]

    applied = patch(client, application_id, stage="applied")
    patch(client, application_id, stage="interview", note="Phone screen booked")
    patch(client, application_id, stage="offer")
    accepted = patch(client, application_id, stage="accepted", note="Signed")

    assert applied["applied_at"] is not None
    assert accepted["stage"] == "accepted"
    assert accepted["allowed_stages"] == []
    timeline = events(client, application_id)
    assert [event["sequence"] for event in timeline] == [1, 2, 3, 4, 5]
    assert [event["event_type"] for event in timeline] == ["tracked"] + ["stage_changed"] * 4
    assert [(event["from_stage"], event["to_stage"]) for event in timeline] == [
        (None, "saved"),
        ("saved", "applied"),
        ("applied", "interview"),
        ("interview", "offer"),
        ("offer", "accepted"),
    ]
    assert timeline[1]["changes"] == {
        "applied_at": {"from": None, "to": timeline[1]["changes"]["applied_at"]["to"]}
    }
    assert timeline[2]["note"] == "Phone screen booked"
    assert timeline[4]["note"] == "Signed"


@pytest.mark.parametrize(
    ("path", "target", "detail"),
    [
        ([], "offer", "cannot move from saved to offer (allowed: applied, rejected)"),
        ([], "interview", "cannot move from saved to interview (allowed: applied, rejected)"),
        (["applied"], "saved", "cannot move from applied to saved (allowed: interview, rejected)"),
        (
            ["rejected"],
            "applied",
            "cannot move from rejected to applied (rejected is a final stage)",
        ),
        (
            ["applied", "interview", "offer", "accepted"],
            "rejected",
            "cannot move from accepted to rejected (accepted is a final stage)",
        ),
    ],
)
def test_illegal_moves_are_409_and_change_nothing(
    client: TestClient, path: list[str], target: str, detail: str
) -> None:
    application_id = track(client, INITECH)["id"]
    for stage in path:
        patch(client, application_id, stage=stage)
    before = client.get(f"/applications/{application_id}").json()

    response = client.patch(
        f"/applications/{application_id}",
        json={"stage": target, "notes": "changed", "next_action_at": iso(timedelta(days=1))},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": detail}
    assert client.get(f"/applications/{application_id}").json() == before
    assert len(events(client, application_id)) == 1 + len(path)


def test_moving_to_the_current_stage_is_not_a_move(client: TestClient) -> None:
    application_id = track(client, ACME)["id"]

    unchanged = patch(client, application_id, stage="saved")

    assert unchanged["stage"] == "saved"
    assert len(events(client, application_id)) == 1


def test_follow_up_changes_are_recorded_and_clearing_the_date_clears_the_label(
    client: TestClient,
) -> None:
    application_id = track(client, ACME)["id"]
    due = iso(timedelta(days=2))

    scheduled = patch(client, application_id, next_action_at=due, next_action="Email Sam")
    cleared = patch(client, application_id, next_action_at=None)

    assert scheduled["follow_up_status"] == "due"
    assert scheduled["next_action"] == "Email Sam"
    assert (cleared["next_action_at"], cleared["next_action"]) == (None, None)
    assert cleared["follow_up_status"] == "none"
    first, second = events(client, application_id)[1:]
    assert first["event_type"] == second["event_type"] == "updated"
    assert first["changes"]["next_action"] == {"from": None, "to": "Email Sam"}
    assert first["changes"]["next_action_at"]["from"] is None
    assert second["changes"]["next_action_at"]["to"] is None
    assert second["changes"]["next_action"] == {"from": "Email Sam", "to": None}


def test_notes_edits_record_no_event_but_timeline_notes_do(client: TestClient) -> None:
    application_id = track(client, ACME)["id"]

    edited = patch(client, application_id, notes="Ask about on-call")
    noted = patch(client, application_id, note="Recruiter replied")

    assert edited["notes"] == noted["notes"] == "Ask about on-call"
    timeline = events(client, application_id)
    assert [event["event_type"] for event in timeline] == ["tracked", "note_added"]
    assert timeline[1]["note"] == "Recruiter replied"


def test_naive_and_offset_datetimes_are_stored_as_utc(client: TestClient) -> None:
    application_id = track(client, ACME)["id"]

    offset = patch(client, application_id, next_action_at="2030-01-02T09:30:00-08:00")
    naive = patch(client, application_id, applied_at="2026-01-02T09:30:00")

    assert offset["next_action_at"] == "2030-01-02T17:30:00Z"
    assert offset["follow_up_status"] == "scheduled"
    assert naive["applied_at"] == "2026-01-02T09:30:00Z"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"stage": "ghosted"},
        {"stage": None, "unknown": 1},
        {"notes": "x" * 10_001},
        {"note": "x" * 2_001},
        {"next_action": "x" * 201},
        {"next_action": "line\nbreak"},
        {"note": "nul\x00byte"},
        {"applied_at": "2999-01-01T00:00:00Z"},
        {"next_action_at": "not-a-date"},
        {"next_action_at": "9999-12-31T23:59:59-05:00"},
    ],
)
def test_invalid_updates_are_422(client: TestClient, body: dict[str, Any]) -> None:
    application_id = track(client, ACME)["id"]

    response = client.patch(f"/applications/{application_id}", json=body)

    assert response.status_code == 422, response.text
    assert len(events(client, application_id)) == 1


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"job_id": 0},
        {"job_id": SQLITE_MAX + 1},
        {"job_id": ACME, "stage": "ghosted"},
        {"job_id": ACME, "applied_at": "2999-01-01T00:00:00Z"},
        {"job_id": ACME, "archived": True},
    ],
)
def test_invalid_creates_are_422(client: TestClient, body: dict[str, Any]) -> None:
    response = client.post("/applications", json=body)

    assert response.status_code == 422, response.text
    assert client.get("/applications").headers["x-total-count"] == "0"


@pytest.mark.parametrize("suffix", ["", "/events", "/archive", "/unarchive"])
def test_unknown_or_out_of_range_application_ids(client: TestClient, suffix: str) -> None:
    method = client.post if suffix.endswith("archive") else client.get

    assert method(f"/applications/999{suffix}").status_code == 404
    assert method(f"/applications/{SQLITE_MAX + 1}{suffix}").status_code == 422
    assert method(f"/applications/0{suffix}").status_code == 422
    assert client.patch("/applications/999", json={"note": "x"}).status_code == 404


@pytest.fixture()
def pipeline(client: TestClient) -> dict[str, int]:
    """Five applications across stages and follow-up states."""

    ids = {
        "acme": track(client, ACME, notes="Platform team")["id"],
        "hooli": track(client, HOOLI, next_action_at=iso(-timedelta(days=1)))["id"],
        "initech": track(client, INITECH, next_action_at=iso(timedelta(days=3)))["id"],
        "globex": track(client, GLOBEX, next_action_at=iso(timedelta(days=30)))["id"],
        "sre": track(client, SRE)["id"],
    }
    patch(client, ids["hooli"], stage="applied")
    patch(client, ids["initech"], stage="applied")
    patch(client, ids["initech"], stage="interview")
    patch(client, ids["sre"], stage="rejected")
    return ids


def listed(client: TestClient, **params: Any) -> list[int]:
    """Ids returned by ``GET /applications`` for ``params``."""

    response = client.get("/applications", params=params)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]


def test_list_filters_and_paging(client: TestClient, pipeline: dict[str, int]) -> None:
    ids = pipeline

    assert listed(client, stage=["applied", "interview"], sort="created") == [
        ids["initech"],
        ids["hooli"],
    ]
    assert listed(client, company="HOOLI") == [ids["hooli"]]
    assert listed(client, q="platform") == [ids["globex"], ids["acme"]]
    assert listed(client, q="platform team") == [ids["acme"]]
    assert listed(client, follow_up="overdue") == [ids["hooli"]]
    assert listed(client, follow_up="due", sort="next_action") == [ids["hooli"], ids["initech"]]
    assert listed(client, follow_up="due", due_within_days=60, sort="next_action") == [
        ids["hooli"],
        ids["initech"],
        ids["globex"],
    ]
    assert set(listed(client, follow_up="none")) == {ids["acme"], ids["sre"]}
    assert listed(client, job_id=GLOBEX) == [ids["globex"]]
    assert listed(client, sort="score")[0] == ids["acme"]
    page = client.get("/applications", params={"sort": "created", "limit": 2, "offset": 1})
    assert page.headers["x-total-count"] == "5"
    assert [item["id"] for item in page.json()] == [ids["globex"], ids["initech"]]
    assert listed(client, q="100%_match") == []


@pytest.mark.parametrize(
    "params",
    [
        {"stage": "ghosted"},
        {"follow_up": "soon"},
        {"due_within_days": 367},
        {"limit": 0},
        {"limit": 501},
        {"offset": -1},
        {"sort": "random"},
        {"q": "x" * 201},
        {"job_id": SQLITE_MAX + 1},
    ],
)
def test_invalid_list_parameters_are_422(client: TestClient, params: dict[str, Any]) -> None:
    assert client.get("/applications", params=params).status_code == 422


def test_board_groups_by_stage_in_pipeline_order(
    client: TestClient, pipeline: dict[str, int]
) -> None:
    response = client.get("/applications/board", params={"per_stage": 1})

    assert response.status_code == 200
    board = response.json()
    assert board["total"] == 5
    assert board["include_archived"] is False
    assert [(column["stage"], column["count"]) for column in board["columns"]] == [
        ("saved", 2),
        ("applied", 1),
        ("interview", 1),
        ("offer", 0),
        ("accepted", 0),
        ("rejected", 1),
    ]
    assert [len(column["applications"]) for column in board["columns"]] == [1, 1, 1, 0, 0, 1]
    assert board["columns"][1]["applications"][0]["id"] == pipeline["hooli"]
    assert board["follow_ups"] == {"overdue": 1, "due": 1, "scheduled": 1, "none": 2}
    only = client.get("/applications/board", params={"stage": "saved"}).json()
    assert [column["count"] for column in only["columns"]] == [2, 0, 0, 0, 0, 0]
    assert only["total"] == 2


def test_archive_hides_an_application_and_is_idempotent(
    client: TestClient, pipeline: dict[str, int]
) -> None:
    sre = pipeline["sre"]

    archived = client.post(f"/applications/{sre}/archive", json={"note": "Closing the loop"})
    again = client.post(f"/applications/{sre}/archive")

    assert archived.status_code == again.status_code == 200
    assert archived.json()["archived"] is True
    assert sre not in listed(client)
    assert sre in listed(client, include_archived=True)
    assert client.get("/applications/board").json()["total"] == 4
    assert client.get(f"/applications/{sre}").json()["archived"] is True
    restored = client.post(f"/applications/{sre}/unarchive")
    assert restored.json()["archived"] is False
    assert restored.json()["stage"] == "rejected"
    timeline = events(client, sre)
    assert [event["event_type"] for event in timeline[-2:]] == ["archived", "unarchived"]
    assert timeline[-2]["note"] == "Closing the loop"
    assert timeline[-2]["changes"] == {"archived": {"from": False, "to": True}}


def test_csv_export_is_spreadsheet_safe(client: TestClient) -> None:
    hostile = track(client, HOSTILE, notes="=cmd|' /C calc'!A0", next_action="+1 call")["id"]
    track(client, ACME)

    response = client.get("/applications/export", params={"format": "csv", "sort": "created"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"].startswith('attachment; filename="applications-')
    assert response.headers["x-total-count"] == "2"
    assert response.text.startswith('"application_id","job_id","stage"')
    rows = list(csv.reader(io.StringIO(response.text)))
    assert tuple(rows[0]) == APPLICATION_CSV_COLUMNS
    row = dict(zip(rows[0], rows[2], strict=True))
    assert row["application_id"] == str(hostile)
    assert row["title"] == '\'=HYPERLINK("https://evil.example","Apply here")'
    assert row["location"] == "'-1+1"
    assert row["url"] == ""
    assert row["notes"] == "'=cmd|' /C calc'!A0"
    assert row["next_action"] == "'+1 call"
    assert dict(zip(rows[0], rows[1], strict=True))["url"] == (
        "https://boards.greenhouse.io/acme/jobs/1"
    )


def test_jsonl_export_follows_filters_and_the_api_schema(
    client: TestClient, pipeline: dict[str, int]
) -> None:
    response = client.get(
        "/applications/export", params={"format": "jsonl", "stage": "applied", "limit": 5}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    lines = response.text.splitlines()
    assert [json.loads(line)["id"] for line in lines] == [pipeline["hooli"]]
    assert json.loads(lines[0]) == client.get(f"/applications/{pipeline['hooli']}").json()
    assert client.get("/applications/export", params={"format": "xlsx"}).status_code == 422


def test_calendar_feed_lists_follow_ups_with_escaped_text(client: TestClient) -> None:
    acme = track(client, ACME)["id"]
    patch(client, acme, next_action_at="2030-01-02T17:30:00Z", next_action="Call; then, email\\x")
    track(client, HOOLI)

    response = client.get("/applications/calendar.ics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    body = response.text
    assert body.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert body.endswith("END:VCALENDAR\r\n")
    assert body.count("BEGIN:VEVENT") == 1
    unfolded = body.replace("\r\n ", "")
    assert "DTSTART:20300102T173000Z" in unfolded
    assert (
        "SUMMARY:Call\\; then\\, email\\\\x - Senior Python Engineer at Acme Robotics" in unfolded
    )
    assert "SEQUENCE:2" in unfolded
    assert "URL:https://boards.greenhouse.io/acme/jobs/1" in unfolded
    assert all(len(line.encode()) <= 75 for line in body.split("\r\n"))
    assert "\n" not in body.replace("\r\n", "")


# Lost races: another request commits between this request's reads and its write.

RivalWrite = Callable[[Session], None]
CONCURRENT_UPDATE = {"detail": "application was changed by another request; retry"}


@pytest.fixture()
def rival(sqlite_database_url: str) -> Iterator[Callable[[RivalWrite], None]]:
    """Arm a write that another request commits just before the next request writes.

    ``rival(write)`` runs ``write`` in a session of its own and commits it when the next
    flush starts: the request under test has read and validated everything and is about
    to send its first ``INSERT`` / ``UPDATE``. That is the narrowest lost race, made
    deterministic.
    """

    engine = create_engine(sqlite_database_url.replace("+aiosqlite", ""))
    armed: list[RivalWrite] = []

    def commit_rival_write(*_: object) -> None:
        while armed:
            write = armed.pop()
            with Session(engine) as other, other.begin():
                write(other)

    event.listen(Session, "before_flush", commit_rival_write)
    try:
        yield armed.append
    finally:
        event.remove(Session, "before_flush", commit_rival_write)
        engine.dispose()


def rival_event(
    application_id: int, sequence: int, event_type: str, **fields: Any
) -> ApplicationEvent:
    """A timeline event recorded by the rival request."""

    return ApplicationEvent(
        application_id=application_id,
        sequence=sequence,
        event_type=event_type,
        created_at=utc_now(),
        **fields,
    )


def test_a_stage_move_that_loses_a_race_is_409_and_changes_nothing(
    client: TestClient, rival: Callable[[RivalWrite], None]
) -> None:
    acme = track(client, ACME)["id"]

    def reject(other: Session) -> None:
        application = other.get(Application, acme)
        assert application is not None
        application.stage, application.stage_changed_at = "rejected", utc_now()
        other.add(rival_event(acme, 2, "stage_changed", from_stage="saved", to_stage="rejected"))

    rival(reject)
    response = client.patch(f"/applications/{acme}", json={"stage": "applied"})

    assert response.status_code == 409, response.text
    assert response.json() == CONCURRENT_UPDATE
    current = client.get(f"/applications/{acme}").json()
    assert (current["stage"], current["applied_at"]) == ("rejected", None)
    assert [(e["sequence"], e["from_stage"], e["to_stage"]) for e in events(client, acme)] == [
        (1, None, "saved"),
        (2, "saved", "rejected"),
    ]
    retried = client.patch(f"/applications/{acme}", json={"stage": "applied"})
    assert retried.status_code == 409
    assert "rejected is a final stage" in retried.json()["detail"]


def test_a_note_that_loses_the_timeline_slot_is_409_not_500(
    client: TestClient, rival: Callable[[RivalWrite], None]
) -> None:
    acme = track(client, ACME)["id"]

    rival(lambda other: other.add(rival_event(acme, 2, "note_added", note="theirs")))
    response = client.patch(f"/applications/{acme}", json={"note": "mine"})

    assert response.status_code == 409, response.text
    assert response.json() == CONCURRENT_UPDATE
    assert [e["note"] for e in events(client, acme)] == [None, "theirs"]
    patch(client, acme, note="mine")
    assert [e["note"] for e in events(client, acme)] == [None, "theirs", "mine"]


def test_an_archive_that_loses_a_race_is_409_and_its_retry_is_a_no_op(
    client: TestClient, rival: Callable[[RivalWrite], None]
) -> None:
    acme = track(client, ACME)["id"]

    def archive(other: Session) -> None:
        application = other.get(Application, acme)
        assert application is not None
        application.archived = True
        changes = {"archived": {"from": False, "to": True}}
        other.add(rival_event(acme, 2, "archived", changes=changes))

    rival(archive)
    response = client.post(f"/applications/{acme}/archive")

    assert response.status_code == 409, response.text
    assert response.json() == CONCURRENT_UPDATE
    retried = client.post(f"/applications/{acme}/archive")
    assert retried.status_code == 200
    assert retried.json()["archived"] is True
    assert [e["event_type"] for e in events(client, acme)] == ["tracked", "archived"]


def test_tracking_a_job_another_request_just_tracked_is_409_not_500(
    client: TestClient, rival: Callable[[RivalWrite], None]
) -> None:
    def track_acme(other: Session) -> None:
        application = Application(job_id=ACME)
        other.add(application)
        other.flush()
        other.add(rival_event(application.id, 1, "tracked", to_stage="saved"))

    rival(track_acme)
    response = client.post("/applications", json={"job_id": ACME})

    assert response.status_code == 409, response.text
    assert response.json() == {"detail": f"job {ACME} is already tracked as application 1"}
    assert response.headers["location"].endswith("/applications/1")
    assert client.get("/applications").headers["x-total-count"] == "1"
