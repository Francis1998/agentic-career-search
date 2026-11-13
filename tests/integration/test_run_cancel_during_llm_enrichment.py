"""Regression tests: cancelling a run while its LLM enrichment calls are in flight.

With ``LLM_ENABLE_ENRICHMENT=true`` the worker awaits one provider call per job (up to
``LLM_TIMEOUT_SECONDS``). It made those calls inside the write transaction it opens at
a source's first job and commits after the last one, so on SQLite every API write
waited for the whole source: ``POST /runs/{id}/cancel`` gave up after SQLite's busy
timeout with a 500 ("database is locked"), the cancel was lost and the run kept paying
for provider calls until it completed.

The fake provider keeps the second job's call in flight until the cancel request has
been answered, so the cancel can only succeed if the worker does not hold the write
lock while it waits on the provider.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.api import routes_runs
from autoapply_agent.core.config import Settings
from autoapply_agent.db.models import RunEvent
from autoapply_agent.main import create_app
from autoapply_agent.services.llm_enrichment import LLMEnrichmentResult, LLMEnrichmentService

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from sqlalchemy.ext.asyncio import AsyncSession

_JOB_COUNT = 3
_IN_FLIGHT_CALL = 2


class _Provider:
    """Fake LLM provider whose second call stays in flight until ``release`` is set."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.in_flight = threading.Event()
        self.release = threading.Event()

    async def enrich_job_decision(
        self, job_candidate: JobCandidate, query: str | None, deterministic_rationale: list[str]
    ) -> LLMEnrichmentResult:
        del query, deterministic_rationale
        self.calls.append(job_candidate.external_id or "")
        if len(self.calls) == _IN_FLIGHT_CALL:
            self.in_flight.set()
            for _ in range(1500):
                if self.release.is_set():
                    break
                await asyncio.sleep(0.01)
        return LLMEnrichmentResult(provider="fake", model="fake-model", summary="Strong match.")


async def _fetch_jobs(
    self: GreenhouseAdapter, base_url: str, timeout_seconds: float, max_jobs: int
) -> list[JobCandidate]:
    """Serve three postings for the run's only source."""
    del self, timeout_seconds, max_jobs
    return [
        JobCandidate(
            external_id=f"enriched-{index}",
            title=f"Python Backend Engineer {index}",
            location="Remote",
            company="example.com",
            url=f"{base_url.rstrip('/')}/jobs/enriched-{index}",
            raw={"fixture": "cancel-during-llm-enrichment"},
        )
        for index in range(_JOB_COUNT)
    ]


@pytest.fixture()
def provider(monkeypatch: MonkeyPatch) -> _Provider:
    """Route every enrichment call of the app's worker to a fake provider."""
    fake = _Provider()

    async def enrich(
        self: LLMEnrichmentService,
        job_candidate: JobCandidate,
        query: str | None,
        deterministic_rationale: list[str],
    ) -> LLMEnrichmentResult:
        del self
        return await fake.enrich_job_decision(job_candidate, query, deterministic_rationale)

    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", _fetch_jobs)
    monkeypatch.setattr(LLMEnrichmentService, "enrich_job_decision", enrich)
    return fake


@pytest.fixture()
def client(sqlite_database_url: str, provider: _Provider) -> Iterator[TestClient]:
    """App with the worker and LLM enrichment enabled on SQLite's default settings."""
    settings = Settings(
        APP_NAME="autoapply-cancel-enrichment-test",
        DATABASE_URL=sqlite_database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        HTTP_TIMEOUT_SECONDS=0.5,
        MAX_JOBS_PER_SOURCE=_JOB_COUNT,
        HTTP_USER_AGENT="integration-test-agent",
        LLM_ENABLE_ENRICHMENT=True,
        ENABLE_WORKER=True,
        ENVIRONMENT="test",
    )
    with TestClient(create_app(settings)) as test_client:
        try:
            yield test_client
        finally:
            provider.release.set()


def _start_run(client: TestClient) -> str:
    """Configure one source, queue a run and return its id."""
    source = client.post(
        "/source-configs",
        json={
            "name": "cancel-during-enrichment",
            "source_type": "greenhouse",
            "base_url": "https://boards.greenhouse.io/embed/job_board?for=enrich",
        },
    )
    assert source.status_code == 201, source.text
    run = client.post("/runs", json={"query": "python backend"})
    assert run.status_code == 201, run.text
    run_id: str = run.json()["id"]
    return run_id


def _cancel_during_second_call(client: TestClient, provider: _Provider, run_id: str) -> Any:
    """Send the cancel while the second provider call is in flight, then let it return."""
    assert provider.in_flight.wait(timeout=10), "the worker never reached the provider call"
    try:
        return client.post(f"/runs/{run_id}/cancel")
    finally:
        provider.release.set()


def _wait_for_terminal_run(client: TestClient, run_id: str) -> dict[str, Any]:
    """Poll the run until it reaches a terminal status."""
    payload: dict[str, Any] = {}
    for _ in range(200):
        payload = client.get(f"/runs/{run_id}").json()
        if payload["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.05)
    return payload


_EXPECTED_EVENTS = [
    "run.created",
    "run.started",
    "source.started",
    "agent.llm_enrichment",
    "agent.decision",
    "run.cancel_requested",
    "agent.llm_enrichment",
    "agent.decision",
    "run.cancelled",
]


def test_cancel_while_a_provider_call_is_in_flight_stops_the_run(
    client: TestClient, provider: _Provider
) -> None:
    """The cancel is accepted mid-call and no further job reaches the provider."""
    run_id = _start_run(client)

    cancel = _cancel_during_second_call(client, provider, run_id)
    run = _wait_for_terminal_run(client, run_id)
    events = client.get(f"/runs/{run_id}/events").json()
    jobs = client.get("/jobs", params={"run_id": run_id}).json()

    assert cancel.status_code == 200, cancel.text
    assert cancel.json()["status"] == "cancel_requested"
    assert run["status"] == "cancelled", f"events: {[e['event_type'] for e in events]}"
    assert provider.calls == ["enriched-0", "enriched-1"]
    assert sorted(job["external_id"] for job in jobs) == ["enriched-0", "enriched-1"]
    assert [event["event_type"] for event in events] == _EXPECTED_EVENTS
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))


def test_cancel_committing_while_the_worker_resumes_keeps_event_sequences_unique(
    client: TestClient, provider: _Provider, monkeypatch: MonkeyPatch
) -> None:
    """A cancel that commits while the worker stores the in-flight job does not fail the run.

    The cancel's transaction stays open (its ``run.cancel_requested`` event written but
    not committed) while the provider call returns and the worker records that job.
    The worker must number its events only once it holds the write lock; numbering
    them from the last committed event collides with the cancel's event when it
    commits, and the run ends ``failed`` on a UNIQUE constraint instead of
    ``cancelled``.
    """
    append_run_event = routes_runs.append_run_event

    async def append_and_hold_cancel_open(
        session: AsyncSession,
        run_id: str,
        event_type: str,
        message: str,
        payload: dict[str, object] | None = None,
    ) -> RunEvent:
        run_event = await append_run_event(session, run_id, event_type, message, payload)
        if event_type == "run.cancel_requested":
            provider.release.set()
            await asyncio.sleep(0.3)
        return run_event

    monkeypatch.setattr(routes_runs, "append_run_event", append_and_hold_cancel_open)
    run_id = _start_run(client)

    cancel = _cancel_during_second_call(client, provider, run_id)
    run = _wait_for_terminal_run(client, run_id)
    events = client.get(f"/runs/{run_id}/events").json()

    assert cancel.status_code == 200, cancel.text
    assert run["status"] == "cancelled", f"events: {[e['event_type'] for e in events]}"
    assert run["error_message"] is None
    assert [event["event_type"] for event in events] == _EXPECTED_EVENTS
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
