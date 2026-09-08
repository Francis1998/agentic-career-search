"""Unit tests for CrossSourceJobDeduper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from autoapply_agent.services.cross_source_dedup import (
    CrossSourceJobDeduper,
    normalize_company,
    normalize_title,
    similarity,
    title_company_key,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@dataclass(slots=True, frozen=True)
class _Job:
    """Minimal job fixture."""

    title: str
    company: str | None
    url: str


def test_empty_input_returns_empty_result() -> None:
    """Empty job list yields empty kept indices."""

    result = CrossSourceJobDeduper().dedupe([])
    assert result.kept_indices == ()
    assert result.clusters == ()
    assert result.dropped_count == 0


def test_exact_url_dedup_keeps_first() -> None:
    """Identical URLs keep only the first occurrence."""

    jobs = [
        _Job("SWE", "Acme", "https://jobs.example/1"),
        _Job("Software Engineer", "Acme Inc", "https://jobs.example/1"),
    ]
    result = CrossSourceJobDeduper().dedupe(jobs)
    assert result.kept_indices == (0,)
    assert result.dropped_count == 1


def test_fuzzy_title_company_clusters_near_duplicates() -> None:
    """Near-identical title+company with different URLs form one cluster."""

    jobs = [
        _Job("Senior Software Engineer", "Acme Inc", "https://indeed.com/a"),
        _Job("Senior Software Engineer", "Acme", "https://linkedin.com/b"),
        _Job("Data Scientist", "Beta Corp", "https://greenhouse.io/c"),
    ]
    result = CrossSourceJobDeduper(threshold=0.85).dedupe(jobs)
    assert 0 in result.kept_indices
    assert 2 in result.kept_indices
    assert 1 not in result.kept_indices
    assert result.dropped_count == 1
    multi = [c for c in result.clusters if len(c.member_indices) > 1]
    assert len(multi) == 1
    assert multi[0].canonical_index == 0
    assert multi[0].member_indices == (0, 1)


def test_different_companies_not_merged() -> None:
    """Same title at different companies stays distinct."""

    jobs = [
        _Job("Backend Engineer", "Acme", "https://a.example/1"),
        _Job("Backend Engineer", "Globex", "https://b.example/2"),
    ]
    result = CrossSourceJobDeduper(threshold=0.85).dedupe(jobs)
    assert result.kept_indices == (0, 1)
    assert result.dropped_count == 0


def test_keep_returns_canonical_jobs() -> None:
    """keep() returns JobLike objects for kept indices."""

    jobs = [
        _Job("ML Engineer", "Acme LLC", "https://x/1"),
        _Job("ML Engineer", "Acme", "https://y/2"),
    ]
    kept = CrossSourceJobDeduper(threshold=0.85).keep(jobs)
    assert len(kept) == 1
    assert kept[0].url == "https://x/1"


def test_invalid_threshold_raises() -> None:
    """Threshold outside (0, 1] raises ValueError."""

    with pytest.raises(ValueError, match="threshold"):
        CrossSourceJobDeduper(threshold=0.0)
    with pytest.raises(ValueError, match="threshold"):
        CrossSourceJobDeduper(threshold=1.5)


def test_normalize_helpers() -> None:
    """Normalization collapses punctuation and legal suffixes."""

    assert normalize_title("  Sr. Software-Engineer!! ") == "sr software engineer"
    assert normalize_company("Acme Inc.") == "acme"
    assert title_company_key("SWE", "Acme LLC") == "swe|acme"
    assert similarity("acme|swe", "acme|swe") == 1.0


def test_deterministic() -> None:
    """Repeated dedupe calls produce identical results."""

    jobs = [
        _Job("Platform Engineer", "Nimbus", "https://a/1"),
        _Job("Platform Engineer", "Nimbus Inc", "https://b/2"),
    ]
    deduper = CrossSourceJobDeduper(threshold=0.85)
    assert deduper.dedupe(jobs) == deduper.dedupe(jobs)
