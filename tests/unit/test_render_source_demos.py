"""Keep ``scripts/render_source_demos.py`` reproducible and offline.

The source demo GIFs are transcripts of real adapter runs over the adapters'
recorded unit-test fixtures. These tests replay every demo (without rendering) so
a renamed fixture, a guide config the API would ignore, or an adapter that stops
parsing its fixture breaks CI instead of the next re-render.
"""

from __future__ import annotations

import asyncio
import importlib
import re
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


@pytest.fixture(scope="module")
def demos() -> ModuleType:
    """Import the generator script (it imports ``generate_demo_gif`` by name)."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        return importlib.import_module("render_source_demos")
    finally:
        sys.path.remove(str(SCRIPTS_DIR))


def test_every_source_demo_replays_its_fixture_offline(demos: ModuleType) -> None:
    """Each demo sends exactly one GET to the guide's base_url and lists real jobs."""
    for slug in demos.SOURCE_DEMOS:
        run = demos.run_demo(demos.resolve_demo(slug))
        text = demos.plain_text(demos.transcript(run))

        assert [(r.method, str(r.url)) for r in run.requests] == [
            ("GET", str(httpx.URL(run.demo.base_url)))
        ], slug
        assert run.jobs, slug
        assert demos.FIXTURE_LABEL in text, slug
        assert f"base_url={run.demo.base_url}" in text, slug
        assert all(job.title in text and job.url in text for job in run.jobs), slug


def test_transport_refuses_anything_but_the_recorded_page(demos: ModuleType) -> None:
    """A request outside the fixture aborts the demo instead of reaching the network."""
    requests: list[httpx.Request] = []

    async def fetch(url: str) -> httpx.Response:
        async with httpx.AsyncClient() as client:
            return await client.get(url)

    with demos.recorded_transport("https://acme.example.com/jobs", "<html></html>", requests):
        assert asyncio.run(fetch("https://acme.example.com/jobs")).status_code == 200
        with pytest.raises(demos.DemoError, match=re.escape("refusing GET https://example.org/")):
            asyncio.run(fetch("https://example.org/"))

    assert [str(request.url) for request in requests] == [
        "https://acme.example.com/jobs",
        "https://example.org/",
    ]
