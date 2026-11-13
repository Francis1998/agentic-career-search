"""Rank captured jobs against resume text: match score, matched and missing skills.

Deterministic and offline (no LLM, no network):

1. :class:`ResumeProfile` extracts the resume's skills once with the curated lexicon of
   :mod:`~autoapply_agent.services.skill_extraction` and adds the skills they imply
   (``postgresql`` → ``sql``). Only a SHA-256 digest and the derived skill names are
   kept; the resume text itself is never stored or logged.
2. Candidate jobs come from :func:`~autoapply_agent.services.job_search.iter_jobs` with
   the same :class:`~autoapply_agent.services.job_search.JobSearchFilters` as
   ``GET /jobs`` and the export, so filters, the remote rule and dedupe are identical.
3. Each job's skills are extracted from its title plus the description-like fields of
   ``Job.raw`` (:data:`JOB_TEXT_FIELDS`) and scored with the ATS coverage helper
   :func:`~autoapply_agent.services.ats_keyword_coverage.keyword_coverage`:
   ``match_score`` is the share of the posting's skills found on the resume.
4. Jobs are ranked by ``match`` (match score, then matched-skill count, stored score,
   capture time and id) or ``blend`` (:data:`BLEND_MATCH_WEIGHT` * match score + the
   rest * stored score, then the same tie-breaks). Only the top ``limit`` jobs are
   kept in memory while the candidates stream past.
"""

from __future__ import annotations

import csv
import hashlib
import heapq
import html
import io
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.db.models import Job
from autoapply_agent.services.ats_keyword_coverage import keyword_coverage
from autoapply_agent.services.job_export import CSV_COLUMNS, job_csv_row, neutralize_csv_cell
from autoapply_agent.services.job_search import JobSearchFilters, as_utc, iter_jobs
from autoapply_agent.services.skill_extraction import extract_skills, implied_skills

MAX_RESUME_CHARS = 50_000
"""Longest accepted resume text (about 15 pages); longer input is rejected, not cut."""
MAX_JOB_TEXT_CHARS = 20_000
"""Characters of each job's title + description text that are scanned for skills."""
JOB_TEXT_FIELDS: tuple[str, ...] = (
    "description",
    "summary",
    "requirements",
    "qualifications",
    "responsibilities",
    "skills",
)
"""Keys of ``Job.raw`` read after the title (strings or lists of strings)."""
BLEND_MATCH_WEIGHT = 0.7
"""Weight of the match score in ``sort=blend``; the stored score gets the rest."""
MATCH_CSV_COLUMNS: tuple[str, ...] = (
    "rank",
    "match_score",
    "blend_score",
    "matched_skills",
    "missing_skills",
    "extra_skills",
    "explanation",
    *CSV_COLUMNS,
)
"""CSV header: the match fields, then exactly the columns of ``GET /jobs/export``."""

_HTML_TAG = re.compile(r"<[^<>]{0,500}>")
_SKILL_SEPARATOR = "; "


class MatchSort(StrEnum):
    """Orderings of a resume match."""

    MATCH = "match"
    BLEND = "blend"


@dataclass(frozen=True, slots=True)
class ResumeProfile:
    """What matching keeps of a resume: a digest and derived skill names, never the text.

    Attributes:
        sha256: Hex SHA-256 of the UTF-8 resume text (for correlation only).
        characters: Length of the resume text.
        skills: Skills mentioned in the resume, alphabetical.
        implied: Skills the resume demonstrates without naming them, each mapped to the
            mentioned skills that imply it (``{"sql": ("postgresql",)}``).
        known: ``skills`` plus the keys of ``implied``; what a posting is matched against.
    """

    sha256: str
    characters: int
    skills: tuple[str, ...]
    implied: Mapping[str, tuple[str, ...]]
    known: frozenset[str]

    @classmethod
    def from_text(cls, text: str) -> ResumeProfile:
        """Extract the profile of one resume.

        Args:
            text: Plain resume text.

        Returns:
            Profile holding no resume text.
        """

        skills = sorted(extract_skills(text))
        implied = {skill: tuple(sources) for skill, sources in implied_skills(skills).items()}
        return cls(
            sha256=hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest(),
            characters=len(text),
            skills=tuple(skills),
            implied=implied,
            known=frozenset(skills) | frozenset(implied),
        )


@dataclass(frozen=True, slots=True)
class SkillMatch:
    """How one posting's skills compare with a resume.

    Attributes:
        match_score: Share of ``job_skills`` found on the resume, in ``[0, 1]``.
        job_skills: Skills the posting mentions, in order of first mention.
        matched: ``job_skills`` the resume has (named or implied), posting order.
        missing: ``job_skills`` the resume lacks, posting order.
        extra: Skills the resume names that the posting does not mention, alphabetical.
    """

    match_score: float
    job_skills: tuple[str, ...]
    matched: tuple[str, ...]
    missing: tuple[str, ...]
    extra: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankedJob:
    """One ranked job.

    Attributes:
        rank: 1-based position in the ranking.
        job: The persisted job.
        match: Skill comparison with the resume.
        blend_score: :func:`blend_score` of the match and stored scores.
        explanation: One-paragraph plain-language summary of the match.
    """

    rank: int
    job: Job
    match: SkillMatch
    blend_score: float
    explanation: str


@dataclass(frozen=True, slots=True)
class MatchPage:
    """The top jobs of a ranking.

    Attributes:
        total: Jobs that passed the filters (and ``min_match``) before ``limit``.
        sort: Ordering used.
        items: The top jobs, best first.
    """

    total: int
    sort: MatchSort
    items: list[RankedJob]


def job_match_text(job: Job) -> str:
    """Text of a job that is scanned for skills.

    The title comes first, then every :data:`JOB_TEXT_FIELDS` value of ``job.raw``
    (company and location are never skill evidence). HTML tags are dropped and
    entities decoded; at most :data:`MAX_JOB_TEXT_CHARS` characters are kept.

    Args:
        job: Persisted job.

    Returns:
        Plain text, title first.
    """

    raw = job.raw if isinstance(job.raw, dict) else {}
    parts = [job.title]
    budget = MAX_JOB_TEXT_CHARS - len(job.title)
    for name in JOB_TEXT_FIELDS:
        value = raw.get(name)
        texts = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        for text in texts:
            if isinstance(text, str) and budget > 0:
                parts.append(text[:budget])
                budget -= len(parts[-1]) + 1
    joined = "\n".join(parts)[:MAX_JOB_TEXT_CHARS]
    return html.unescape(_HTML_TAG.sub(" ", joined))


def match_skills(job_skills: Sequence[str], profile: ResumeProfile) -> SkillMatch:
    """Compare a posting's skills with a resume profile.

    Args:
        job_skills: Distinct posting skills in order of first mention.
        profile: Resume profile.

    Returns:
        Coverage of the posting's skills by the resume (named or implied).
    """

    coverage = keyword_coverage(job_skills, profile.known)
    posting = set(job_skills)
    return SkillMatch(
        match_score=coverage.coverage_score,
        job_skills=tuple(job_skills),
        matched=tuple(coverage.present_keywords),
        missing=tuple(coverage.missing_keywords),
        extra=tuple(skill for skill in profile.skills if skill not in posting),
    )


def blend_score(match_score: float, score: float) -> float:
    """Mix a match score with a job's stored deterministic score (``sort=blend``)."""

    return round(BLEND_MATCH_WEIGHT * match_score + (1 - BLEND_MATCH_WEIGHT) * score, 4)


def explain_match(
    match: SkillMatch,
    profile: ResumeProfile,
    *,
    score: float,
    blend: float | None = None,
) -> str:
    """Explain a match in one short paragraph (deterministic, no LLM).

    Args:
        match: Skill comparison.
        profile: Resume profile (names the resume skills behind implied matches).
        score: The job's stored deterministic score.
        blend: The blend score, when the ranking used it.

    Returns:
        Plain-language explanation.
    """

    total = len(match.job_skills)
    if not total:
        text = (
            "No skills from the lexicon appear in this posting's title or description, "
            "so there is nothing to match."
        )
    else:
        noun = "skill" if total == 1 else "skills"
        if match.matched:
            listed = ", ".join(
                f"{skill} (via {', '.join(profile.implied[skill])})"
                if skill in profile.implied
                else skill
                for skill in match.matched
            )
            text = f"Matches {len(match.matched)} of {total} {noun} in this posting: {listed}."
        else:
            text = f"Matches none of the {total} {noun} in this posting."
        if match.missing:
            text += f" Missing: {', '.join(match.missing)}."
    if blend is not None:
        text += (
            f" Blend {blend:.4f} = {BLEND_MATCH_WEIGHT:g} * match {match.match_score:.4f}"
            f" + {1 - BLEND_MATCH_WEIGHT:g} * score {score:.4f}."
        )
    return text


_SortKey = tuple[float, float, float, float, int]


def _sort_key(job: Job, match: SkillMatch, blended: float, sort: MatchSort) -> _SortKey:
    """Ranking key, larger is better; the job id makes every key unique."""

    captured = as_utc(job.created_at).timestamp()
    if sort == MatchSort.BLEND:
        return (blended, match.match_score, job.score, captured, job.id)
    return (match.match_score, float(len(match.matched)), job.score, captured, job.id)


async def rank_jobs(
    session: AsyncSession,
    filters: JobSearchFilters,
    profile: ResumeProfile,
    *,
    sort: MatchSort = MatchSort.MATCH,
    limit: int,
    min_match: float | None = None,
) -> MatchPage:
    """Rank every job matching ``filters`` against a resume profile.

    Args:
        session: Active async DB session (only read).
        filters: The ``GET /jobs`` filters and dedupe mode (``sort`` is ignored).
        profile: Resume profile.
        sort: ``match`` or ``blend``.
        limit: Number of top jobs to return.
        min_match: Drop jobs whose match score is below this value.

    Returns:
        Total ranked jobs and the top ``limit``, best first.

    Raises:
        ValueError: If ``limit`` is below 1.
    """

    if limit < 1:
        raise ValueError(f"limit must be >= 1, got {limit}")
    heap: list[tuple[_SortKey, int]] = []
    candidates: dict[int, tuple[Job, SkillMatch, float]] = {}
    total = 0
    async for job in iter_jobs(session, filters):
        match = match_skills(extract_skills(job_match_text(job)), profile)
        if min_match is not None and match.match_score < min_match:
            continue
        total += 1
        blended = blend_score(match.match_score, job.score)
        entry = (_sort_key(job, match, blended, sort), job.id)
        if len(heap) < limit:
            heapq.heappush(heap, entry)
        elif entry > heap[0]:
            candidates.pop(heapq.heapreplace(heap, entry)[1], None)
        else:
            continue
        candidates[job.id] = (job, match, blended)

    items: list[RankedJob] = []
    for rank, (_, job_id) in enumerate(sorted(heap, reverse=True), start=1):
        job, match, blended = candidates[job_id]
        explanation = explain_match(
            match,
            profile,
            score=job.score,
            blend=blended if sort == MatchSort.BLEND else None,
        )
        items.append(RankedJob(rank, job, match, blended, explanation))
    return MatchPage(total=total, sort=sort, items=items)


def render_match_csv(page: MatchPage, *, include_extra_skills: bool) -> str:
    """Render ranked jobs as CSV with the OWASP CSV-injection hardening of the export.

    Rows reuse :func:`~autoapply_agent.services.job_export.job_csv_row` after the match
    columns; every cell is quoted and text cells are neutralized.

    Args:
        page: Ranked jobs.
        include_extra_skills: Fill the ``extra_skills`` column (empty otherwise).

    Returns:
        CSV document with ``\\r\\n`` line endings and :data:`MATCH_CSV_COLUMNS` header.
    """

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(MATCH_CSV_COLUMNS)
    for item in page.items:
        extra = _SKILL_SEPARATOR.join(item.match.extra) if include_extra_skills else ""
        writer.writerow(
            [
                str(item.rank),
                str(item.match.match_score),
                str(item.blend_score),
                neutralize_csv_cell(_SKILL_SEPARATOR.join(item.match.matched)),
                neutralize_csv_cell(_SKILL_SEPARATOR.join(item.match.missing)),
                neutralize_csv_cell(extra),
                neutralize_csv_cell(item.explanation),
                *job_csv_row(item.job),
            ]
        )
    return buffer.getvalue()
