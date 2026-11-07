"""API tests for job search filters, pagination, detail, CSV/JSONL export and Atom feed."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autoapply_agent.core.config import Settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import Job, Run, RunStatus, SourceConfig
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.main import create_app
from autoapply_agent.schemas.jobs import JobRead
from autoapply_agent.services.job_export import CSV_COLUMNS

ATOM = "{http://www.w3.org/2005/Atom}"
# Half-hour offset keeps ``hours_old`` boundaries far from the hourly seed rows.
BASE_TIME = utc_now().replace(microsecond=0) - timedelta(hours=10, minutes=30)


@dataclass(frozen=True)
class SeedJob:
    """One job row to insert before the app starts."""

    key: str
    run_id: str
    source_config_id: int
    title: str
    company: str | None
    location: str | None
    url: str
    score: float
    hours_after_base: int
    tier: str = "medium"


SEED_JOBS = (
    SeedJob(
        "py-acme-gh",
        "run-a",
        1,
        "Senior Python Engineer",
        "Acme Robotics",
        "Remote - US",
        "https://boards.greenhouse.io/acme/jobs/1",
        0.92,
        0,
        "high",
    ),
    SeedJob(
        "go-globex",
        "run-a",
        2,
        "Backend Engineer (Go)",
        "Globex",
        "Berlin, Germany",
        "https://jobs.lever.co/globex/go",
        0.55,
        1,
    ),
    SeedJob(
        "ds-initech",
        "run-a",
        1,
        "Data Scientist",
        "Initech",
        "New York, NY",
        "https://boards.greenhouse.io/initech/jobs/3",
        0.71,
        2,
    ),
    SeedJob(
        "py-globex",
        "run-b",
        2,
        "Staff Python Platform Engineer",
        "Globex",
        "Anywhere",
        "https://jobs.lever.co/globex/py",
        0.88,
        3,
        "high",
    ),
    SeedJob(
        "py-acme-lever",
        "run-b",
        2,
        "Senior Python Engineer",
        "Acme Robotics, Inc.",
        "Remote - US",
        "https://jobs.lever.co/acme/py",
        0.9,
        4,
        "high",
    ),
    SeedJob(
        "py-acme-gh-again",
        "run-b",
        1,
        "Senior Python Engineer",
        "Acme Robotics",
        "Remote - US",
        "https://boards.greenhouse.io/acme/jobs/1",
        0.93,
        4,
        "high",
    ),
    SeedJob(
        "sre-unknown",
        "run-b",
        1,
        "Site Reliability Engineer",
        None,
        None,
        "https://boards.greenhouse.io/unknown/jobs/7",
        0.4,
        5,
        "low",
    ),
    # Inserted last (highest id) but captured first: ``newest`` follows capture time.
    SeedJob(
        "legacy-import",
        "run-b",
        1,
        "Legacy Mainframe Developer",
        "Oldco",
        "Paris, France",
        "https://boards.greenhouse.io/oldco/jobs/8",
        0.2,
        -1,
        "low",
    ),
)
ALL_KEYS_NEWEST_FIRST = [
    "sre-unknown",
    "py-acme-gh-again",
    "py-acme-lever",
    "py-globex",
    "ds-initech",
    "go-globex",
    "py-acme-gh",
    "legacy-import",
]


async def _seed(database_url: str, jobs: tuple[SeedJob, ...]) -> None:
    """Create the schema and insert runs, source configs and jobs."""

    engine = create_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with create_session_factory(engine)() as session:
        session.add_all(
            [
                SourceConfig(
                    id=1,
                    name="seed-greenhouse",
                    source_type="greenhouse",
                    base_url="https://boards.greenhouse.io/seed",
                ),
                SourceConfig(
                    id=2, name="seed-lever", source_type="lever", base_url="https://jobs.lever.co/x"
                ),
                Run(id="run-a", status=RunStatus.COMPLETED.value, query="python"),
                Run(id="run-b", status=RunStatus.COMPLETED.value, query="python"),
            ]
        )
        await session.flush()
        for job in jobs:
            session.add(
                Job(
                    run_id=job.run_id,
                    source_config_id=job.source_config_id,
                    external_id=job.key,
                    title=job.title,
                    location=job.location,
                    company=job.company,
                    url=job.url,
                    score=job.score,
                    plan_steps=["Review fit"],
                    raw={"source": "seed", "agent_decision": {"priority_tier": job.tier}},
                    created_at=BASE_TIME + timedelta(hours=job.hours_after_base),
                )
            )
            await session.flush()
        await session.commit()
    await engine.dispose()


def _client_for(database_url: str, jobs: tuple[SeedJob, ...]) -> Iterator[TestClient]:
    """Seed the database and yield a client for an app without a background worker."""

    asyncio.run(_seed(database_url, jobs))
    settings = Settings(
        APP_NAME="Job Search Test",
        DATABASE_URL=database_url,
        ENABLE_WORKER=False,
        ENVIRONMENT="test",
    )
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture()
def client(sqlite_database_url: str) -> Iterator[TestClient]:
    """Client backed by the standard seed data."""

    yield from _client_for(sqlite_database_url, SEED_JOBS)


def _keys(response: Any) -> list[str]:
    """Return the external ids of a ``GET /jobs`` response, asserting success."""

    assert response.status_code == 200, response.text
    return [job["external_id"] for job in response.json()]


def test_list_without_params_is_backward_compatible(client: TestClient) -> None:
    """No parameters: newest capture first, default page, and the total in a header."""

    response = client.get("/jobs")

    assert _keys(response) == ALL_KEYS_NEWEST_FIRST
    assert response.headers["x-total-count"] == "8"


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"q": "PYTHON"}, ["py-acme-gh-again", "py-acme-lever", "py-globex", "py-acme-gh"]),
        ({"q": "globex berlin"}, ["go-globex"]),
        ({"q": "initech"}, ["ds-initech"]),
        ({"q": "100%_"}, []),
        ({"company": "acme"}, ["py-acme-gh-again", "py-acme-lever", "py-acme-gh"]),
        ({"location": "new york"}, ["ds-initech"]),
        ({"remote": "true"}, ["py-acme-gh-again", "py-acme-lever", "py-globex", "py-acme-gh"]),
        ({"remote": "false"}, ["sre-unknown", "ds-initech", "go-globex", "legacy-import"]),
        ({"min_score": "0.9"}, ["py-acme-gh-again", "py-acme-lever", "py-acme-gh"]),
        ({"source_config_id": "2"}, ["py-acme-lever", "py-globex", "go-globex"]),
        ({"run_id": "run-a"}, ["ds-initech", "go-globex", "py-acme-gh"]),
    ],
)
def test_single_filters(client: TestClient, params: dict[str, str], expected: list[str]) -> None:
    """Each filter narrows the results on its own and the header counts matches."""

    response = client.get("/jobs", params=params)

    assert _keys(response) == expected
    assert response.headers["x-total-count"] == str(len(expected))


def test_created_after_normalizes_offsets_and_combines_with_hours_old(client: TestClient) -> None:
    """``created_after`` honours UTC offsets; ``hours_old`` is a capture-age bound."""

    pacific = timezone(timedelta(hours=-8))
    cutoff = (BASE_TIME + timedelta(hours=3)).astimezone(pacific).isoformat()
    expected = ["sre-unknown", "py-acme-gh-again", "py-acme-lever", "py-globex"]

    assert _keys(client.get("/jobs", params={"created_after": cutoff})) == expected
    assert _keys(client.get("/jobs", params={"hours_old": "8"})) == expected
    both = client.get("/jobs", params={"created_after": cutoff, "hours_old": "6"})
    assert _keys(both) == ["sre-unknown"]
    assert client.get("/jobs", params={"created_after": "yesterday"}).status_code == 422


def test_combined_filters(client: TestClient) -> None:
    """Filters combine with AND semantics."""

    response = client.get(
        "/jobs",
        params={"q": "python", "remote": "true", "min_score": "0.89", "source_config_id": "2"},
    )

    assert _keys(response) == ["py-acme-lever"]
    assert response.headers["x-total-count"] == "1"


def test_sort_by_score_orders_highest_first(client: TestClient) -> None:
    """``sort=score`` orders by score descending."""

    response = client.get("/jobs", params={"sort": "score"})

    assert [job["score"] for job in response.json()] == [
        0.93,
        0.92,
        0.9,
        0.88,
        0.71,
        0.55,
        0.4,
        0.2,
    ]
    assert client.get("/jobs", params={"sort": "salary"}).status_code == 422


def test_pagination_pages_partition_results(client: TestClient) -> None:
    """``limit``/``offset`` pages are disjoint, ordered, and report the same total."""

    pages: list[str] = []
    for offset in (0, 3, 6):
        response = client.get("/jobs", params={"limit": "3", "offset": str(offset)})
        assert response.headers["x-total-count"] == "8"
        pages.extend(_keys(response))

    assert pages == ALL_KEYS_NEWEST_FIRST
    past_end = client.get("/jobs", params={"offset": "8"})
    assert _keys(past_end) == []
    assert past_end.headers["x-total-count"] == "8"


@pytest.mark.parametrize(
    "params",
    [{"limit": "0"}, {"limit": "501"}, {"offset": "-1"}, {"min_score": "1.5"}, {"hours_old": "0"}],
)
def test_out_of_range_parameters_are_rejected(client: TestClient, params: dict[str, str]) -> None:
    """Invalid bounds fail validation instead of being clamped silently."""

    assert client.get("/jobs", params=params).status_code == 422


def test_dedupe_collapses_repeat_captures_and_cross_source_mirrors(client: TestClient) -> None:
    """The first capture of a posting wins over re-captures and other-source mirrors."""

    newest = client.get("/jobs", params={"dedupe": "true"})
    by_score = client.get("/jobs", params={"dedupe": "true", "sort": "score"})
    last_page = client.get("/jobs", params={"dedupe": "true", "limit": "2", "offset": "4"})

    assert _keys(newest) == [
        "sre-unknown",
        "py-globex",
        "ds-initech",
        "go-globex",
        "py-acme-gh",
        "legacy-import",
    ]
    assert newest.headers["x-total-count"] == "6"
    assert _keys(by_score) == [
        "py-acme-gh",
        "py-globex",
        "ds-initech",
        "go-globex",
        "sre-unknown",
        "legacy-import",
    ]
    assert _keys(last_page) == ["py-acme-gh", "legacy-import"]
    assert last_page.headers["x-total-count"] == "6"


def test_job_detail_and_missing_job(client: TestClient) -> None:
    """Detail returns the list representation; unknown ids are a JSON 404."""

    listed = client.get("/jobs", params={"limit": "1"}).json()[0]

    assert client.get(f"/jobs/{listed['id']}").json() == listed
    missing = client.get("/jobs/999999")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "job not found"}
    assert client.get("/jobs/not-a-number").status_code == 422


def test_csv_export_streams_filtered_rows_with_download_headers(client: TestClient) -> None:
    """CSV export applies filters/sort and is served as a named attachment."""

    response = client.get("/jobs/export", params={"remote": "true", "sort": "score"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="jobs-')
    assert disposition.endswith('.csv"')
    rows = list(csv.reader(io.StringIO(response.text)))
    assert tuple(rows[0]) == CSV_COLUMNS
    records = [dict(zip(CSV_COLUMNS, row, strict=True)) for row in rows[1:]]
    assert [record["external_id"] for record in records] == [
        "py-acme-gh-again",
        "py-acme-gh",
        "py-acme-lever",
        "py-globex",
    ]
    first = records[0]
    assert first["remote"] == "true"
    assert first["priority_tier"] == "high"
    assert first["url"] == "https://boards.greenhouse.io/acme/jobs/1"
    assert first["created_at"].endswith("Z")
    assert response.text.startswith('"id","title",')


def test_jsonl_export_round_trips_through_the_api_schema(client: TestClient) -> None:
    """Every JSON Lines record equals the job detail payload."""

    response = client.get("/jobs/export", params={"format": "jsonl", "dedupe": "true"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-ndjson"
    assert response.headers["content-disposition"].endswith('.jsonl"')
    lines = response.text.splitlines()
    assert len(lines) == 6
    for line in lines:
        record = JobRead.model_validate_json(line)
        assert json.loads(line) == client.get(f"/jobs/{record.id}").json()


def test_exports_of_empty_results(client: TestClient) -> None:
    """No matches: CSV keeps its header row, JSON Lines is empty."""

    csv_response = client.get("/jobs/export", params={"q": "cobol"})
    jsonl_response = client.get("/jobs/export", params={"q": "cobol", "format": "jsonl"})

    assert list(csv.reader(io.StringIO(csv_response.text))) == [list(CSV_COLUMNS)]
    assert jsonl_response.status_code == 200
    assert jsonl_response.text == ""
    assert client.get("/jobs/export", params={"format": "xlsx"}).status_code == 422


def test_export_limit_caps_rows(client: TestClient) -> None:
    """``limit`` caps the export (newest first)."""

    response = client.get("/jobs/export", params={"format": "jsonl", "limit": "2"})

    assert [json.loads(line)["external_id"] for line in response.text.splitlines()] == [
        "sre-unknown",
        "py-acme-gh-again",
    ]


def _feed(client: TestClient, params: dict[str, str] | None = None) -> ET.Element:
    """Fetch and parse the Atom feed, asserting the media type."""

    response = client.get("/jobs/feed.atom", params=params)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/atom+xml; charset=utf-8"
    return ET.fromstring(response.content)


def test_atom_feed_is_well_formed_rfc4287(client: TestClient) -> None:
    """Feed metadata and deduplicated entries carry the RFC 4287 required elements."""

    feed = _feed(client, {"q": "python"})

    assert feed.tag == f"{ATOM}feed"
    assert feed.findtext(f"{ATOM}id", "").startswith("urn:uuid:")
    assert feed.findtext(f"{ATOM}title") == "Job Search Test jobs (q=python)"
    assert feed.findtext(f"{ATOM}author/{ATOM}name") == "agentic-career-search"
    self_link = feed.find(f"{ATOM}link[@rel='self']")
    assert self_link is not None
    assert self_link.get("href") == "http://testserver/jobs/feed.atom?q=python"
    entries = feed.findall(f"{ATOM}entry")
    assert [entry.findtext(f"{ATOM}title") for entry in entries] == [
        "Staff Python Platform Engineer at Globex",
        "Senior Python Engineer at Acme Robotics",
    ]
    newest = entries[0]
    assert feed.findtext(f"{ATOM}updated") == newest.findtext(f"{ATOM}updated")
    assert newest.findtext(f"{ATOM}updated", "").endswith("Z")
    alternate = newest.find(f"{ATOM}link[@rel='alternate']")
    assert alternate is not None
    assert alternate.get("href") == "https://jobs.lever.co/globex/py"
    assert newest.findtext(f"{ATOM}summary") == (
        "Company: Globex | Location: Anywhere | Remote: yes | Score: 0.88 | Priority: high"
    )
    ids = [entry.findtext(f"{ATOM}id") for entry in entries]
    assert len(set(ids)) == len(ids)
    assert all(entry_id and entry_id.startswith("urn:uuid:") for entry_id in ids)


def test_atom_feed_ids_are_stable_and_limit_does_not_change_feed_identity(
    client: TestClient,
) -> None:
    """Refreshing the feed yields the same ids; ``limit`` trims entries only."""

    first = _feed(client, {"remote": "true"})
    second = _feed(client, {"remote": "true", "limit": "1"})

    assert first.findtext(f"{ATOM}id") == second.findtext(f"{ATOM}id")
    first_ids = [entry.findtext(f"{ATOM}id") for entry in first.findall(f"{ATOM}entry")]
    second_ids = [entry.findtext(f"{ATOM}id") for entry in second.findall(f"{ATOM}entry")]
    assert len(first_ids) == 2
    assert second_ids == first_ids[:1]
    assert _feed(client, {"remote": "false"}).findtext(f"{ATOM}id") != first.findtext(f"{ATOM}id")


def test_atom_entry_identity_survives_time_windows(client: TestClient) -> None:
    """``hours_old`` must not re-identify a posting whose first capture aged out.

    ``py-acme-gh`` (first capture) falls outside an 8-hour window while its Lever
    mirror and a re-capture stay inside it; the entry keeps the first capture's id and
    publication time, so feed readers do not notify twice.
    """

    def acme_entry(params: dict[str, str]) -> ET.Element:
        feed = _feed(client, params)
        entries = [
            entry
            for entry in feed.findall(f"{ATOM}entry")
            if "Acme" in entry.findtext(f"{ATOM}title", "")
        ]
        assert len(entries) == 1
        return entries[0]

    everything = acme_entry({"q": "acme"})
    recent = acme_entry({"q": "acme", "hours_old": "8"})

    assert recent.findtext(f"{ATOM}id") == everything.findtext(f"{ATOM}id")
    assert recent.findtext(f"{ATOM}published") == everything.findtext(f"{ATOM}published")
    assert everything.findtext(f"{ATOM}published") == (BASE_TIME.isoformat().replace("+00:00", "Z"))


def test_atom_feed_id_includes_the_installation_url(client: TestClient) -> None:
    """Feeds served from different hosts never share an id; parameter order does not matter."""

    here = _feed(client, {"q": "python", "remote": "true"}).findtext(f"{ATOM}id")
    reordered = ET.fromstring(
        client.get("/jobs/feed.atom?remote=true&limit=5&q=python").content
    ).findtext(f"{ATOM}id")
    elsewhere = ET.fromstring(
        client.get(
            "/jobs/feed.atom",
            params={"q": "python", "remote": "true"},
            headers={"host": "jobs.example"},
        ).content
    ).findtext(f"{ATOM}id")

    assert here == reordered
    assert here != elsewhere


def test_atom_feed_without_matches_is_still_valid(client: TestClient) -> None:
    """An empty feed keeps id, title and updated."""

    feed = _feed(client, {"q": "cobol"})

    assert feed.findall(f"{ATOM}entry") == []
    assert feed.findtext(f"{ATOM}updated", "").endswith("Z")
    assert feed.findtext(f"{ATOM}id", "").startswith("urn:uuid:")


UNICODE_JOBS = (
    SeedJob(
        "tokyo",
        "run-a",
        1,
        "ソフトウェアエンジニア",
        "株式会社サンプル",
        "東京",
        "https://example.jp/jobs/1",
        0.8,
        0,
    ),
    SeedJob(
        "osaka",
        "run-a",
        1,
        "ソフトウェアエンジニア",
        "株式会社サンプル",
        "大阪",
        "https://example.jp/jobs/2",
        0.7,
        1,
    ),
    SeedJob(
        "tokyo-mirror",
        "run-a",
        2,
        "ソフトウェア・エンジニア",
        "株式会社サンプル",
        "東京",
        "https://boards.example.com/jp/9",
        0.75,
        2,
    ),
)


def test_dedupe_keeps_distinct_non_latin_postings(sqlite_database_url: str) -> None:
    """Same title and company in two cities stay two postings; the mirror collapses."""

    for client in _client_for(sqlite_database_url, UNICODE_JOBS):
        response = client.get("/jobs", params={"dedupe": "true"})
        feed = _feed(client)

        assert _keys(response) == ["osaka", "tokyo"]
        assert response.headers["x-total-count"] == "2"
        summaries = [entry.findtext(f"{ATOM}summary", "") for entry in feed.findall(f"{ATOM}entry")]
        assert [summary.split(" | ")[1] for summary in summaries] == [
            "Location: 大阪",
            "Location: 東京",
        ]


HOSTILE_JOBS = (
    SeedJob(
        "+cmd|' /C calc'!A0",
        "run-a",
        1,
        '=HYPERLINK("https://evil.example","Apply")',
        "@SUM(1+1)",
        "-2+3",
        "javascript:alert(1)",
        0.5,
        0,
    ),
    SeedJob(
        "markup",
        "run-a",
        1,
        '<script>alert("x")</script> & Co ]]>\x0b\tSenior',
        'Quote "Co", Ltd.\nSecond line',
        "\tTabbed City",
        "https://example.com/jobs/1?a=1&b=<2>",
        0.6,
        1,
    ),
)


@pytest.fixture()
def hostile_client(sqlite_database_url: str) -> Iterator[TestClient]:
    """Client backed by rows crafted to attack CSV and XML consumers."""

    yield from _client_for(sqlite_database_url, HOSTILE_JOBS)


def test_csv_export_neutralizes_formulas_and_non_http_urls(hostile_client: TestClient) -> None:
    """OWASP CSV-injection triggers are prefixed and only http(s) URLs are emitted."""

    response = hostile_client.get("/jobs/export", params={"sort": "score"})
    rows = list(csv.reader(io.StringIO(response.text)))
    records = [dict(zip(CSV_COLUMNS, row, strict=True)) for row in rows[1:]]
    markup, formula = records

    assert formula["title"] == '\'=HYPERLINK("https://evil.example","Apply")'
    assert formula["company"] == "'@SUM(1+1)"
    assert formula["location"] == "'-2+3"
    assert formula["external_id"] == "'+cmd|' /C calc'!A0"
    assert formula["url"] == ""
    assert markup["company"] == 'Quote "Co", Ltd.\nSecond line'
    assert markup["location"] == "'\tTabbed City"
    assert markup["url"] == "https://example.com/jobs/1?a=1&b=<2>"
    assert '"\'=HYPERLINK(""https://evil.example"",""Apply"")"' in response.text


def test_atom_feed_escapes_hostile_titles_and_falls_back_for_unsafe_links(
    hostile_client: TestClient,
) -> None:
    """Markup stays text, invalid XML characters are dropped, unsafe links never ship."""

    response = hostile_client.get("/jobs/feed.atom")
    feed = ET.fromstring(response.content)
    entries = {entry.findtext(f"{ATOM}title"): entry for entry in feed.findall(f"{ATOM}entry")}

    markup_title = '<script>alert("x")</script> & Co ]]>\tSenior at Quote "Co", Ltd.\nSecond line'
    assert markup_title in entries
    assert b"<script>" not in response.content
    markup_link = entries[markup_title].find(f"{ATOM}link[@rel='alternate']")
    assert markup_link is not None
    assert markup_link.get("href") == "https://example.com/jobs/1?a=1&b=<2>"
    formula_entry = entries['=HYPERLINK("https://evil.example","Apply") at @SUM(1+1)']
    formula_link = formula_entry.find(f"{ATOM}link[@rel='alternate']")
    assert formula_link is not None
    job_id = hostile_client.get("/jobs", params={"q": "HYPERLINK"}).json()[0]["id"]
    assert formula_link.get("href") == f"http://testserver/jobs/{job_id}"
    assert b"javascript:" not in response.content
