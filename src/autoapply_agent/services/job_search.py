"""JobSpy-style search, filters and pagination over persisted jobs.

``GET /jobs``, ``GET /jobs/export`` and ``GET /jobs/feed.atom`` all build their
queries here, so every surface applies exactly the same filter semantics.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import ColumnElement, and_, func, not_, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.db.models import Job
from autoapply_agent.services.cross_source_dedup import normalize_company, normalize_title

REMOTE_LOCATION_KEYWORDS: tuple[str, ...] = (
    "remote",
    "anywhere",
    "work from home",
    "wfh",
    "telecommute",
    "distributed",
)
"""Case-insensitive substrings of ``Job.location`` that mark a job as remote."""

_BATCH_SIZE = 500


class JobSort(StrEnum):
    """Supported result orderings."""

    NEWEST = "newest"
    SCORE = "score"


@dataclass(slots=True, frozen=True)
class JobSearchFilters:
    """Filters shared by the list, export and feed endpoints.

    Attributes:
        q: Whitespace-separated terms; each must match title, company or location.
        company: Case-insensitive substring of the company.
        location: Case-insensitive substring of the location.
        remote: ``True``/``False`` to keep only remote/non-remote jobs (see
            :func:`is_remote_location`); ``None`` keeps both.
        min_score: Minimum deterministic score (inclusive).
        source_config_id: Only jobs captured from this source config.
        run_id: Only jobs captured by this run.
        created_after: Only jobs captured at or after this instant.
        sort: Result ordering.
        dedupe: Collapse repeated captures and cross-source mirrors.
    """

    q: str | None = None
    company: str | None = None
    location: str | None = None
    remote: bool | None = None
    min_score: float | None = None
    source_config_id: int | None = None
    run_id: str | None = None
    created_after: datetime | None = None
    sort: JobSort = JobSort.NEWEST
    dedupe: bool = False


@dataclass(slots=True, frozen=True)
class PostingIdentity:
    """Identity of one posting, resolved over its whole capture history.

    Attributes:
        url: URL of the posting's first capture.
        first_seen: UTC time of that first capture.
    """

    url: str
    first_seen: datetime


@dataclass(slots=True, frozen=True)
class JobSearchPage:
    """One page of matching jobs plus the total number of matches.

    Attributes:
        total: Number of matches before ``limit``/``offset``.
        items: Jobs on this page.
        postings: With ``dedupe``, the posting identity of every job on the page.
    """

    total: int
    items: list[Job]
    postings: dict[int, PostingIdentity] = field(default_factory=dict)


def as_utc(value: datetime) -> datetime:
    """Return ``value`` as an aware UTC datetime.

    Args:
        value: Aware or naive datetime; naive values (SQLite drops tzinfo) are UTC.

    Returns:
        Timezone-aware UTC datetime.
    """

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_remote_location(location: str | None) -> bool:
    """Apply the remote rule used by the ``remote`` filter to one location.

    Args:
        location: Normalized job location, possibly missing.

    Returns:
        True when the location contains one of :data:`REMOTE_LOCATION_KEYWORDS`.
    """

    lowered = (location or "").lower()
    return any(keyword in lowered for keyword in REMOTE_LOCATION_KEYWORDS)


def posting_key(title: str, company: str | None, location: str | None) -> str:
    """Build the identity used to collapse one posting mirrored across sources.

    Reuses the Unicode-aware title/company normalization of :mod:`cross_source_dedup`
    (case, punctuation and legal suffixes ignored) and adds the location, so
    same-title openings in different cities stay distinct. Token separators are
    dropped too, so ``Front-end``/``Frontend`` and ``ソフトウェア・エンジニア``/
    ``ソフトウェアエンジニア`` mirrors match.

    Args:
        title: Job title.
        company: Company name, possibly missing.
        location: Job location, possibly missing.

    Returns:
        ``"{title}|{company}|{location}"`` normalized key.
    """

    parts = (normalize_title(title), normalize_company(company), normalize_title(location or ""))
    return "|".join(part.replace(" ", "") for part in parts)


def build_conditions(filters: JobSearchFilters) -> list[ColumnElement[bool]]:
    """Translate filters into SQL ``WHERE`` conditions (combined with AND).

    Text matches are case-insensitive substring matches with LIKE wildcards escaped.

    Args:
        filters: Requested filters.

    Returns:
        SQLAlchemy boolean conditions.
    """

    conditions: list[ColumnElement[bool]] = []
    for term in (filters.q or "").split():
        conditions.append(
            or_(
                Job.title.icontains(term, autoescape=True),
                Job.company.icontains(term, autoescape=True),
                Job.location.icontains(term, autoescape=True),
            )
        )
    if filters.company and filters.company.strip():
        conditions.append(Job.company.icontains(filters.company.strip(), autoescape=True))
    if filters.location and filters.location.strip():
        conditions.append(Job.location.icontains(filters.location.strip(), autoescape=True))
    if filters.remote is not None:
        remote_match = or_(
            *(
                Job.location.icontains(keyword, autoescape=True)
                for keyword in REMOTE_LOCATION_KEYWORDS
            )
        )
        conditions.append(
            remote_match if filters.remote else or_(Job.location.is_(None), not_(remote_match))
        )
    if filters.min_score is not None:
        conditions.append(Job.score >= filters.min_score)
    if filters.source_config_id is not None:
        conditions.append(Job.source_config_id == filters.source_config_id)
    if filters.run_id:
        conditions.append(Job.run_id == filters.run_id)
    if filters.created_after is not None:
        conditions.append(Job.created_at >= as_utc(filters.created_after))
    return conditions


def _order_by(sort: JobSort) -> tuple[ColumnElement[Any], ...]:
    """Return ``ORDER BY`` clauses; ``id`` breaks ties so pagination is stable."""

    if sort == JobSort.SCORE:
        return (Job.score.desc(), Job.created_at.desc(), Job.id.desc())
    return (Job.created_at.desc(), Job.id.desc())


async def _distinct_postings(
    session: AsyncSession, filters: JobSearchFilters
) -> list[tuple[int, PostingIdentity]]:
    """Collapse matching jobs into distinct postings, in the requested order.

    Identity ignores the filters: every stored job is visited in capture order
    (``created_at``, then ``id``) and joins the posting of an earlier job with the
    same URL (case-insensitive) or the same :func:`posting_key`; when the two lookups
    find different postings, the one first seen earlier wins. A job's posting depends
    only on earlier captures, so it never changes as new captures arrive. The filters
    only decide which postings match and which capture represents each one (the first
    matching capture), so a posting keeps its identity when, for example,
    ``hours_old`` drops its oldest captures. Only narrow columns are loaded.

    Args:
        session: Active async DB session.
        filters: Requested filters and sort.

    Returns:
        ``(representative job id, posting identity)`` pairs; ``newest`` orders by
        first capture time, ``score`` by the representative's score.
    """

    conditions = build_conditions(filters)
    matches = and_(*conditions) if conditions else true()
    statement = select(
        Job.id, Job.url, Job.title, Job.company, Job.location, Job.score, Job.created_at, matches
    ).order_by(Job.created_at.asc(), Job.id.asc())
    by_url: dict[str, PostingIdentity] = {}
    by_key: dict[str, PostingIdentity] = {}
    first_seen_order: dict[PostingIdentity, int] = {}
    representatives: dict[PostingIdentity, tuple[int, float]] = {}
    rows = (await session.execute(statement)).all()
    for position, row in enumerate(rows):
        job_id, url, title, company, location, score, created_at, matched = row
        url_key = url.strip().lower()
        key = posting_key(title, company, location)
        known = [found for found in (by_url.get(url_key), by_key.get(key)) if found is not None]
        if known:
            identity = min(known, key=first_seen_order.__getitem__)
        else:
            identity = PostingIdentity(url=url, first_seen=as_utc(created_at))
            first_seen_order[identity] = position
        by_url.setdefault(url_key, identity)
        by_key.setdefault(key, identity)
        if matched and identity not in representatives:
            representatives[identity] = (job_id, score)

    if filters.sort == JobSort.SCORE:
        order = sorted(
            representatives.items(),
            key=lambda item: (item[1][1], item[0].first_seen, item[1][0]),
            reverse=True,
        )
    else:
        order = sorted(
            representatives.items(),
            key=lambda item: (item[0].first_seen, item[1][0]),
            reverse=True,
        )
    return [(job_id, identity) for identity, (job_id, _) in order]


async def _load_in_order(session: AsyncSession, job_ids: Sequence[int]) -> list[Job]:
    """Load jobs by id, preserving the order of ``job_ids``."""

    if not job_ids:
        return []
    rows = await session.scalars(select(Job).where(Job.id.in_(job_ids)))
    by_id = {job.id: job for job in rows}
    return [by_id[job_id] for job_id in job_ids if job_id in by_id]


async def search_jobs(
    session: AsyncSession,
    filters: JobSearchFilters,
    *,
    limit: int,
    offset: int = 0,
) -> JobSearchPage:
    """Return one page of matching jobs and the total match count.

    Args:
        session: Active async DB session.
        filters: Requested filters, sort and dedupe mode.
        limit: Maximum number of jobs in the page.
        offset: Number of matches to skip.

    Returns:
        Page of jobs plus the total number of matches.
    """

    if filters.dedupe:
        postings = await _distinct_postings(session, filters)
        page = postings[offset : offset + limit]
        return JobSearchPage(
            total=len(postings),
            items=await _load_in_order(session, [job_id for job_id, _ in page]),
            postings=dict(page),
        )

    conditions = build_conditions(filters)
    total = await session.scalar(select(func.count()).select_from(Job).where(*conditions))
    rows = await session.scalars(
        select(Job)
        .where(*conditions)
        .order_by(*_order_by(filters.sort))
        .offset(offset)
        .limit(limit)
    )
    return JobSearchPage(total=int(total or 0), items=list(rows))


async def iter_jobs(
    session: AsyncSession,
    filters: JobSearchFilters,
    *,
    limit: int | None = None,
) -> AsyncIterator[Job]:
    """Stream every matching job in the requested order (used by exports).

    Args:
        session: Active async DB session, kept open while iterating.
        filters: Requested filters, sort and dedupe mode.
        limit: Optional maximum number of jobs.

    Yields:
        Matching jobs, fetched in batches.
    """

    if filters.dedupe:
        job_ids = [job_id for job_id, _ in await _distinct_postings(session, filters)]
        if limit is not None:
            job_ids = job_ids[:limit]
        for start in range(0, len(job_ids), _BATCH_SIZE):
            for job in await _load_in_order(session, job_ids[start : start + _BATCH_SIZE]):
                yield job
        return

    statement = select(Job).where(*build_conditions(filters)).order_by(*_order_by(filters.sort))
    if limit is not None:
        statement = statement.limit(limit)
    result = await session.stream_scalars(statement.execution_options(yield_per=_BATCH_SIZE))
    async for job in result:
        yield job
