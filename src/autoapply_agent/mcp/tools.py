"""Read-only MCP tools over the persisted job feed.

Every tool reuses the services behind the HTTP API instead of re-implementing queries:

* :mod:`~autoapply_agent.services.job_search` for filters, sorting, dedupe and paging
  (the exact semantics of ``GET /jobs``);
* :class:`~autoapply_agent.services.scoring.DeterministicScoringService` and the
  priority tiers of :mod:`~autoapply_agent.services.agent_decision` to explain scores;
* :mod:`~autoapply_agent.services.read_queries` for runs, run events and sources;
* :mod:`~autoapply_agent.services.job_export` for http(s)-only links and timestamps;
* :mod:`~autoapply_agent.services.resume_match` to rank jobs against resume text (the
  ranking of ``POST /jobs/match``);
* :mod:`~autoapply_agent.services.application_tracker` for the application pipeline
  (the queries behind ``GET /applications`` and ``GET /applications/{id}/events``).

No tool writes: none can start or cancel runs, edit source configs, track or move
applications, or apply to jobs.
Results carry ``structuredContent`` that conforms to each tool's ``outputSchema`` plus a
short text rendering. Captured text (titles, companies, locations, rationale) comes from
public career pages and is returned as data.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import (
    SQLITE_MAX_INTEGER,
    Application,
    Job,
    Run,
    RunStatus,
    SourceConfig,
)
from autoapply_agent.schemas.applications import ApplicationEventRead, ApplicationRead
from autoapply_agent.services.agent_decision import (
    HIGH_PRIORITY_MIN_SCORE,
    MEDIUM_PRIORITY_MIN_SCORE,
    priority_tier_for_score,
)
from autoapply_agent.services.application_stages import PIPELINE_ORDER, ApplicationStage
from autoapply_agent.services.application_tracker import (
    DUE_SOON_DAYS,
    MAX_DUE_WITHIN_DAYS,
    ApplicationEventType,
    ApplicationFilters,
    ApplicationSort,
    FollowUpFilter,
    FollowUpStatus,
    application_events,
    count_application_events,
    follow_up_counts,
    get_tracked,
    list_applications,
    stage_counts,
)
from autoapply_agent.services.compensation import describe_pay, normalize_currency
from autoapply_agent.services.job_export import job_pay, rfc3339, safe_http_url
from autoapply_agent.services.job_search import (
    JobSearchFilters,
    JobSort,
    PostingIdentity,
    capture_window_start,
    is_remote_location,
    salary_filter_error,
    search_jobs,
)
from autoapply_agent.services.read_queries import (
    count_run_events,
    job_counts_by_run,
    job_counts_by_source,
    list_runs,
    list_source_configs,
    run_events,
)
from autoapply_agent.services.resume_match import (
    MAX_RESUME_CHARS,
    MatchSort,
    RankedJob,
    ResumeProfile,
    rank_jobs,
)
from autoapply_agent.services.scoring import (
    KEYWORD_BONUS_CAP,
    KEYWORD_BONUS_PER_TERM,
    MAX_SCORE,
    DeterministicScoringService,
)

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50
DEFAULT_EVENT_LIMIT = 20
MAX_EVENT_LIMIT = 200
_MAX_RUN_ID_LENGTH = 64
LIST_NOTES_PREVIEW_CHARS = 280

READ_ONLY_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_TIER_ORDER: tuple[tuple[str, float], ...] = (
    ("medium", MEDIUM_PRIORITY_MIN_SCORE),
    ("high", HIGH_PRIORITY_MIN_SCORE),
)
_SCORER = DeterministicScoringService()


class ToolError(Exception):
    """A failure the caller can act on, returned as an ``isError`` tool result.

    Args:
        message: Text shown to the model; must not echo free-text arguments.
        kind: Audit category, ``invalid_arguments`` or ``not_found``.
    """

    def __init__(self, message: str, *, kind: str = "invalid_arguments") -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class ToolOutput:
    """Successful tool output.

    Attributes:
        structured: ``structuredContent`` conforming to the tool's ``outputSchema``.
        summary: Short human-readable rendering of the result.
        result_count: Number of records returned (recorded in the audit log).
    """

    structured: dict[str, Any]
    summary: str
    result_count: int


ToolHandler = Callable[[AsyncSession, dict[str, Any]], Awaitable[ToolOutput]]


@dataclass(frozen=True)
class ToolSpec:
    """An MCP tool definition and the async handler that implements it."""

    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: ToolHandler

    def definition(self) -> dict[str, Any]:
        """Return the MCP ``Tool`` object advertised by ``tools/list``."""

        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "annotations": dict(READ_ONLY_ANNOTATIONS),
        }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _timestamp(value: datetime | None) -> str | None:
    """Format an optional datetime as an RFC 3339 UTC timestamp."""

    return rfc3339(value) if value is not None else None


def _int_argument(arguments: dict[str, Any], name: str, default: int) -> int:
    """Read a validated integer argument (JSON Schema also allows integral floats)."""

    return int(arguments.get(name, default))


def _optional_int_argument(arguments: dict[str, Any], name: str) -> int | None:
    """Read an optional validated integer argument."""

    value = arguments.get(name)
    return None if value is None else int(value)


def _next_offset(offset: int, returned: int, total: int) -> int | None:
    """Offset of the next page, or None when this page reaches the end."""

    return offset + returned if returned and offset + returned < total else None


def _parse_instant(value: str) -> datetime:
    """Parse an ISO-8601 date or date-time argument (naive values are UTC)."""

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ToolError(
            "created_after must be an ISO-8601 date-time such as 2026-11-01T00:00:00Z"
        ) from exc


def _salary_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    """The validated pay filters of a search or match call (``JobSearchFilters`` fields)."""

    raw_currency = arguments.get("salary_currency")
    currency = normalize_currency(raw_currency)
    if raw_currency is not None and currency is None:
        raise ToolError(f"salary_currency {raw_currency!r} is not an ISO 4217 currency code.")
    has_salary = arguments.get("has_salary")
    return {
        "min_salary": _optional_int_argument(arguments, "min_salary"),
        "max_salary": _optional_int_argument(arguments, "max_salary"),
        "salary_currency": currency,
        "has_salary": None if has_salary is None else bool(has_salary),
    }


def _checked(filters: JobSearchFilters) -> JobSearchFilters:
    """Return ``filters`` or raise the salary-filter problem as a tool error."""

    problem = salary_filter_error(filters)
    if problem is not None:
        raise ToolError(f"{problem[1]}.")
    return filters


def _strings(value: Any) -> list[str]:
    """Keep the string items of a JSON list (anything else becomes empty)."""

    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _raw_object(job: Job, key: str) -> dict[str, Any]:
    """Return ``job.raw[key]`` when it is a JSON object, else an empty dict."""

    raw = job.raw if isinstance(job.raw, dict) else {}
    value = raw.get(key)
    return value if isinstance(value, dict) else {}


def _text_or_none(mapping: dict[str, Any], key: str) -> str | None:
    """Return ``mapping[key]`` when it is a string."""

    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _recorded_tier(job: Job) -> str | None:
    """Priority tier recorded in the job's decision trace at capture time."""

    return _text_or_none(_raw_object(job, "agent_decision"), "priority_tier")


def _decision_trace(job: Job) -> dict[str, Any]:
    """Collect the persisted decision trace of a job (tolerating partial traces)."""

    decision = _raw_object(job, "agent_decision")
    enrichment = _raw_object(job, "llm_enrichment")
    llm = (
        {field: _text_or_none(enrichment, field) for field in ("provider", "model", "summary")}
        if enrichment
        else None
    )
    return {
        "priority_tier": _recorded_tier(job),
        "matched_query_terms": _strings(decision.get("matched_query_terms")),
        "rationale": _strings(decision.get("rationale")),
        "plan_steps": _strings(job.plan_steps),
        "llm_enrichment": llm,
    }


def _pay_record(job: Job) -> dict[str, Any] | None:
    """Captured pay of a job (stated range plus the annualized columns), or None."""

    pay = job_pay(job)
    if pay is None:
        return None
    payload = pay.to_payload()
    return {
        key: payload[key]
        for key in (
            "min_amount",
            "max_amount",
            "currency",
            "interval",
            "annual_min",
            "annual_max",
            "source",
        )
    }


def _job_summary(job: Job, posting: PostingIdentity | None = None) -> dict[str, Any]:
    """Compact job record used in search results."""

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote": is_remote_location(job.location),
        "score": job.score,
        "priority_tier": _recorded_tier(job),
        "url": safe_http_url(job.url),
        "source_config_id": job.source_config_id,
        "run_id": job.run_id,
        "captured_at": rfc3339(job.created_at),
        "first_seen_at": _timestamp(posting.first_seen) if posting is not None else None,
        "pay": _pay_record(job),
    }


def _job_heading(job: Job) -> str:
    """One-line ``#id title — company · location`` heading."""

    place = " · ".join(part for part in (job.company, job.location) if part)
    return f"#{job.id} {job.title}" + (f" — {place}" if place else "")


async def _load_job(session: AsyncSession, arguments: dict[str, Any]) -> Job:
    """Load the job named by ``job_id`` or raise a ``not_found`` tool error."""

    job_id = _int_argument(arguments, "job_id", 0)
    job = await session.get(Job, job_id)
    if job is None:
        raise ToolError(
            f"No job with id {job_id}. Use search_jobs to find job ids.", kind="not_found"
        )
    return job


def _run_record(run: Run, job_count: int) -> dict[str, Any]:
    """Serializable run record."""

    source_ids = run.source_config_ids if isinstance(run.source_config_ids, list) else None
    return {
        "id": run.id,
        "status": run.status,
        "query": run.query,
        "source_config_ids": (
            None
            if source_ids is None
            else [
                item for item in source_ids if isinstance(item, int) and not isinstance(item, bool)
            ]
        ),
        "cancel_requested": run.cancel_requested,
        "error_message": run.error_message,
        "created_at": rfc3339(run.created_at),
        "started_at": _timestamp(run.started_at),
        "finished_at": _timestamp(run.finished_at),
        "job_count": job_count,
    }


def _run_line(run: dict[str, Any]) -> str:
    """One-line run summary used by list_runs and get_run."""

    query = f'query "{run["query"]}"' if run["query"] else "no query"
    jobs = f"{run['job_count']} job{'' if run['job_count'] == 1 else 's'}"
    return f"{run['id']} {run['status']} · {query} · {jobs} · created {run['created_at']}"


# ---------------------------------------------------------------------------
# search_jobs
# ---------------------------------------------------------------------------


async def _search_jobs(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """Search captured jobs with the filters, sorting and paging of ``GET /jobs``."""

    created_after = (
        _parse_instant(arguments["created_after"]) if "created_after" in arguments else None
    )
    try:
        window_start = capture_window_start(
            created_after, _optional_int_argument(arguments, "hours_old"), now=utc_now()
        )
    except OverflowError as exc:
        raise ToolError("created_after is outside the supported UTC range") from exc
    min_score = arguments.get("min_score")
    filters = JobSearchFilters(
        q=arguments.get("q"),
        company=arguments.get("company"),
        location=arguments.get("location"),
        remote=arguments.get("remote"),
        min_score=None if min_score is None else float(min_score),
        source_config_id=_optional_int_argument(arguments, "source_config_id"),
        run_id=arguments.get("run_id"),
        created_after=window_start,
        **_salary_arguments(arguments),
        sort=JobSort(arguments.get("sort", JobSort.NEWEST.value)),
        dedupe=bool(arguments.get("dedupe", False)),
    )
    _checked(filters)
    limit = _int_argument(arguments, "limit", DEFAULT_PAGE_SIZE)
    offset = _int_argument(arguments, "offset", 0)
    page = await search_jobs(session, filters, limit=limit, offset=offset)
    jobs = [_job_summary(job, page.postings.get(job.id)) for job in page.items]
    structured: dict[str, Any] = {
        "total": page.total,
        "offset": offset,
        "limit": limit,
        "next_offset": _next_offset(offset, len(jobs), page.total),
        "sort": filters.sort.value,
        "dedupe": filters.dedupe,
        "captured_since": _timestamp(window_start),
        "jobs": jobs,
    }
    return ToolOutput(structured, _search_summary(structured), len(jobs))


def _pay_suffix(pay: dict[str, Any] | None) -> str:
    """`` · USD 120,000-150,000/yr`` (annualized) for a search line; empty without pay."""

    if pay is None:
        return ""
    low, high = pay["annual_min"], pay["annual_max"]
    amount = f"{low:,}" if low == high else f"{low:,}-{high:,}"
    return f" · {pay['currency']} {amount}/yr"


def _search_summary(result: dict[str, Any]) -> str:
    """Render a search page as text."""

    mode = f"sort={result['sort']}, dedupe={'on' if result['dedupe'] else 'off'}"
    total = result["total"]
    jobs = result["jobs"]
    if not jobs:
        if total:
            return f"{total} jobs match, but offset {result['offset']} is past the end ({mode})."
        return f"No jobs match these filters ({mode})."
    first = result["offset"] + 1
    last = result["offset"] + len(jobs)
    noun = "job" if total == 1 else "jobs"
    lines = [f"{total} matching {noun} ({mode}); showing {first}-{last}:"]
    for job in jobs:
        place = " · ".join(part for part in (job["company"], job["location"]) if part)
        tier = job["priority_tier"] or "-"
        lines.append(
            f"#{job['id']} {job['score']:.4f} {tier:<6} {job['title']}"
            + (f" — {place}" if place else "")
            + _pay_suffix(job["pay"])
        )
    if result["next_offset"] is not None:
        lines.append(f"More: call search_jobs again with offset={result['next_offset']}.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------


async def _get_job(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """Return one job with its score, decision trace and provenance."""

    job = await _load_job(session, arguments)
    run = await session.get(Run, job.run_id)
    source = (
        await session.get(SourceConfig, job.source_config_id)
        if job.source_config_id is not None
        else None
    )
    raw = job.raw if isinstance(job.raw, dict) else {}
    structured: dict[str, Any] = {
        "job": {**_job_summary(job), "external_id": job.external_id},
        "decision": _decision_trace(job),
        "run": None if run is None else {"id": run.id, "query": run.query, "status": run.status},
        "source": None
        if source is None
        else {"id": source.id, "name": source.name, "source_type": source.source_type},
        "source_payload": {
            key: value
            for key, value in raw.items()
            if key not in {"agent_decision", "llm_enrichment"}
        },
    }
    return ToolOutput(structured, _job_detail_summary(job, structured), 1)


def _job_detail_summary(job: Job, result: dict[str, Any]) -> str:
    """Render a job and its decision trace as text."""

    record = result["job"]
    decision = result["decision"]
    lines = [_job_heading(job) + (" (remote)" if record["remote"] else "")]
    lines.append(
        f"Score {job.score:.4f} · priority {decision['priority_tier'] or 'not recorded'}"
        f" · captured {record['captured_at']}"
    )
    run = result["run"]
    source = result["source"]
    provenance = [f"run {job.run_id}"]
    if run is not None and run["query"]:
        provenance.append(f'query "{run["query"]}"')
    if source is not None:
        provenance.append(f"source {source['name']} ({source['source_type']})")
    lines.append("From " + " · ".join(provenance))
    lines.append(f"URL: {record['url'] or 'not an http(s) link (withheld)'}")
    pay = job_pay(job)
    lines.append(
        f"Pay: {describe_pay(pay)} (from the posting's {pay.source.value} data; informational)"
        if pay is not None
        else "Pay: not stated in the captured posting"
    )
    if decision["rationale"]:
        lines.append("Rationale:")
        lines.extend(f"- {line}" for line in decision["rationale"])
    if decision["plan_steps"]:
        lines.append("Plan steps:")
        lines.extend(
            f"{index}. {step}" for index, step in enumerate(decision["plan_steps"], start=1)
        )
    llm = decision["llm_enrichment"]
    if llm is not None:
        lines.append(
            f"LLM enrichment ({llm['provider'] or '?'} / {llm['model'] or '?'}): "
            f"{llm['summary'] or ''}".rstrip()
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# explain_job_score
# ---------------------------------------------------------------------------


async def _explain_job_score(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """Break a stored score into the deterministic scorer's components, in plain language."""

    job = await _load_job(session, arguments)
    run = await session.get(Run, job.run_id)
    query = run.query if run is not None else None
    breakdown = _SCORER.breakdown(
        JobCandidate(
            external_id=job.external_id,
            title=job.title,
            location=job.location,
            company=job.company,
            url=job.url,
            raw=None,
        ),
        query,
    )
    keyword_bonus = round(breakdown.keyword_bonus, 4)
    # Derived from the rounded total so the displayed components add up exactly.
    stability_bonus = (
        round(breakdown.score - breakdown.base - keyword_bonus, 4)
        if not breakdown.capped
        else round(breakdown.stability_bonus, 4)
    )
    tier = priority_tier_for_score(job.score)
    next_tier = next(
        (
            {"tier": name, "min_score": minimum, "gap": round(minimum - job.score, 4)}
            for name, minimum in _TIER_ORDER
            if job.score < minimum
        ),
        None,
    )
    decision = _decision_trace(job)
    matched = list(breakdown.matched_terms)
    structured: dict[str, Any] = {
        "job_id": job.id,
        "title": job.title,
        "score": job.score,
        "priority_tier": tier,
        "recorded_priority_tier": decision["priority_tier"],
        "tier_thresholds": {"high": HIGH_PRIORITY_MIN_SCORE, "medium": MEDIUM_PRIORITY_MIN_SCORE},
        "next_tier": next_tier,
        "run_query": query,
        "query_terms": list(breakdown.query_terms),
        "matched_terms": matched,
        "unmatched_terms": [term for term in breakdown.query_terms if term not in matched],
        "components": {
            "base": breakdown.base,
            "keyword_bonus": keyword_bonus,
            "keyword_bonus_per_term": KEYWORD_BONUS_PER_TERM,
            "keyword_bonus_cap": KEYWORD_BONUS_CAP,
            "stability_bonus": stability_bonus,
            "max_score": MAX_SCORE,
            "capped": breakdown.capped,
        },
        "recomputed_score": breakdown.score,
        "matches_stored_score": breakdown.score == job.score,
        "rationale": decision["rationale"],
        "llm_enrichment": decision["llm_enrichment"],
    }
    structured["explanation"] = _explanation_lines(job, structured)
    return ToolOutput(structured, "\n".join(structured["explanation"]), 1)


def _explanation_lines(job: Job, result: dict[str, Any]) -> list[str]:
    """Explain a score breakdown in plain language (deterministic, no LLM)."""

    parts = result["components"]
    headline = (
        f"Score {job.score:.4f} → {result['priority_tier']} priority "
        f"(high ≥ {HIGH_PRIORITY_MIN_SCORE:.2f}, medium ≥ {MEDIUM_PRIORITY_MIN_SCORE:.2f})."
    )
    if result["next_tier"] is not None:
        headline += f" {result['next_tier']['gap']:.4f} below {result['next_tier']['tier']}."
    lines = [_job_heading(job), headline, "How the deterministic scorer built it (no LLM):"]
    lines.append(f"+ {parts['base']:.4f}  base relevance every captured job starts with")
    query_terms = result["query_terms"]
    matched = result["matched_terms"]
    if query_terms:
        keyword = (
            f"+ {parts['keyword_bonus']:.4f}  keyword bonus: {len(matched)} of {len(query_terms)}"
            " run query terms found in title/company/location"
        )
        if matched:
            keyword += f" ({', '.join(matched)})"
        lines.append(keyword + f"; {KEYWORD_BONUS_PER_TERM:.2f} each, max {KEYWORD_BONUS_CAP:.2f}")
        if result["unmatched_terms"]:
            lines.append(f"          not found: {', '.join(result['unmatched_terms'])}")
    else:
        lines.append(f"+ {parts['keyword_bonus']:.4f}  keyword bonus: the run had no query terms")
    lines.append(
        f"+ {parts['stability_bonus']:.4f}  URL-hash tiebreaker: keeps equal matches in a "
        "stable order; not a fit signal"
    )
    if parts["capped"]:
        lines.append(f"  The sum is capped at {MAX_SCORE:.2f}.")
    if result["matches_stored_score"]:
        lines.append(
            f"= {result['recomputed_score']:.4f}  recomputed now; matches the stored score"
        )
    else:
        lines.append(
            f"= {result['recomputed_score']:.4f}  recomputed now, but {job.score:.4f} is stored: "
            "the job was scored by another scorer version or imported, so this breakdown is "
            "approximate; search ranks by the stored score"
        )
    recorded = result["recorded_priority_tier"]
    if recorded is not None and recorded != result["priority_tier"]:
        lines.append(f"The decision trace recorded tier {recorded} at capture time.")
    llm = result["llm_enrichment"]
    if llm is not None:
        lines.append(
            f"LLM enrichment ({llm['provider'] or '?'}) only added a summary; "
            "it never changes the score."
        )
    return lines


# ---------------------------------------------------------------------------
# list_runs / get_run
# ---------------------------------------------------------------------------


async def _list_runs(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """List discovery runs, newest first."""

    limit = _int_argument(arguments, "limit", DEFAULT_PAGE_SIZE)
    offset = _int_argument(arguments, "offset", 0)
    total, runs = await list_runs(
        session, status=arguments.get("status"), limit=limit, offset=offset
    )
    counts = await job_counts_by_run(session, [run.id for run in runs])
    records = [_run_record(run, counts.get(run.id, 0)) for run in runs]
    structured: dict[str, Any] = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "next_offset": _next_offset(offset, len(records), total),
        "runs": records,
    }
    if records:
        noun = "run" if total == 1 else "runs"
        lines = [f"{total} {noun}, newest first; showing {offset + 1}-{offset + len(records)}:"]
        lines.extend(_run_line(record) for record in records)
        if structured["next_offset"] is not None:
            lines.append(f"More: call list_runs again with offset={structured['next_offset']}.")
        summary = "\n".join(lines)
    else:
        summary = "No runs match." if not total else f"{total} runs; offset is past the end."
    return ToolOutput(structured, summary, len(records))


async def _get_run(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """Return one run with its most recent events."""

    run_id: str = arguments["run_id"]
    run = await session.get(Run, run_id)
    if run is None:
        raise ToolError("No run with this id. Use list_runs to find run ids.", kind="not_found")
    event_limit = _int_argument(arguments, "event_limit", DEFAULT_EVENT_LIMIT)
    events = await run_events(session, run.id, limit=event_limit)
    event_count = await count_run_events(session, run.id)
    job_count = (await job_counts_by_run(session, [run.id])).get(run.id, 0)
    record = _run_record(run, job_count)
    structured: dict[str, Any] = {
        "run": record,
        "event_count": event_count,
        "events_truncated": len(events) < event_count,
        "events": [
            {
                "sequence": event.sequence,
                "event_type": event.event_type,
                "message": event.message,
                "payload": event.payload if isinstance(event.payload, dict) else None,
                "created_at": rfc3339(event.created_at),
            }
            for event in events
        ],
    }
    lines = [f"Run {_run_line(record)}"]
    timeline = [
        f"{label} {value}"
        for label, value in (("started", record["started_at"]), ("finished", record["finished_at"]))
        if value
    ]
    if timeline:
        lines.append(" · ".join(timeline))
    if record["error_message"]:
        lines.append(f"Error: {record['error_message']}")
    shown = "Last" if structured["events_truncated"] else "All"
    lines.append(f"{shown} {len(events)} of {event_count} events:")
    lines.extend(
        f"{item['sequence']:>4} {item['event_type']:<22} {item['message']}"
        for item in structured["events"]
    )
    return ToolOutput(structured, "\n".join(lines), len(events))


# ---------------------------------------------------------------------------
# list_sources
# ---------------------------------------------------------------------------


async def _list_sources(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """List configured sources with how many jobs each captured."""

    sources = await list_source_configs(session, enabled=arguments.get("enabled"))
    counts = await job_counts_by_source(session)
    records = [
        {
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "enabled": source.enabled,
            "base_url": safe_http_url(source.base_url),
            "job_count": counts.get(source.id, 0),
        }
        for source in sources
    ]
    if records:
        lines = [f"{len(records)} source config{'' if len(records) == 1 else 's'}:"]
        lines.extend(
            f"#{record['id']} {record['name']} ({record['source_type']})"
            f" · {'enabled' if record['enabled'] else 'disabled'} · {record['job_count']} jobs"
            for record in records
        )
        summary = "\n".join(lines)
    else:
        summary = "No source configs match."
    return ToolOutput({"count": len(records), "sources": records}, summary, len(records))


# ---------------------------------------------------------------------------
# match_resume_to_jobs
# ---------------------------------------------------------------------------


def _match_filters(arguments: dict[str, Any]) -> JobSearchFilters:
    """The search_jobs filters of a match request; dedupe defaults to on."""

    created_after = (
        _parse_instant(arguments["created_after"]) if "created_after" in arguments else None
    )
    try:
        window_start = capture_window_start(
            created_after, _optional_int_argument(arguments, "hours_old"), now=utc_now()
        )
    except OverflowError as exc:
        raise ToolError("created_after is outside the supported UTC range") from exc
    min_score = arguments.get("min_score")
    return _checked(
        JobSearchFilters(
            q=arguments.get("q"),
            company=arguments.get("company"),
            location=arguments.get("location"),
            remote=arguments.get("remote"),
            min_score=None if min_score is None else float(min_score),
            source_config_id=_optional_int_argument(arguments, "source_config_id"),
            run_id=arguments.get("run_id"),
            created_after=window_start,
            **_salary_arguments(arguments),
            dedupe=bool(arguments.get("dedupe", True)),
        )
    )


def _match_record(item: RankedJob, include_extra_skills: bool) -> dict[str, Any]:
    """Job record of one ranked job (search fields without ``first_seen_at``)."""

    record = _job_summary(item.job)
    del record["first_seen_at"]
    return {
        **record,
        "rank": item.rank,
        "match_score": item.match.match_score,
        "blend_score": item.blend_score,
        "matched_skills": list(item.match.matched),
        "missing_skills": list(item.match.missing),
        "extra_skills": list(item.match.extra) if include_extra_skills else None,
        "explanation": item.explanation,
    }


async def _match_resume_to_jobs(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """Rank captured jobs against resume text, like ``POST /jobs/match``."""

    resume_text: str = arguments["resume_text"]
    if not resume_text.strip():
        raise ToolError("resume_text must contain the plain text of a resume.")
    filters = _match_filters(arguments)
    profile = ResumeProfile.from_text(resume_text)
    sort = MatchSort(arguments.get("sort", MatchSort.MATCH.value))
    limit = _int_argument(arguments, "limit", DEFAULT_PAGE_SIZE)
    min_match = arguments.get("min_match")
    page = await rank_jobs(
        session,
        filters,
        profile,
        sort=sort,
        limit=limit,
        min_match=None if min_match is None else float(min_match),
    )
    include_extra_skills = bool(arguments.get("include_extra_skills", False))
    structured: dict[str, Any] = {
        "resume_sha256": profile.sha256,
        "resume_skills": list(profile.skills),
        "implied_skills": {skill: list(sources) for skill, sources in profile.implied.items()},
        "sort": sort.value,
        "dedupe": filters.dedupe,
        "captured_since": _timestamp(filters.created_after),
        "total": page.total,
        "limit": limit,
        "jobs": [_match_record(item, include_extra_skills) for item in page.items],
    }
    return ToolOutput(structured, _match_summary(structured), len(page.items))


def _match_summary(result: dict[str, Any]) -> str:
    """Render a resume match as text."""

    mode = f"sort={result['sort']}, dedupe={'on' if result['dedupe'] else 'off'}"
    skills = result["resume_skills"]
    lines = [
        f"Resume: {len(skills)} skill{'' if len(skills) == 1 else 's'} recognized"
        + (f" ({', '.join(skills)})." if skills else ".")
    ]
    if not skills:
        lines.append(
            "No lexicon skill was recognized in resume_text, so every match score is 0; "
            "pass the resume as plain text."
        )
    jobs = result["jobs"]
    if not jobs:
        lines.append(f"No jobs match these filters ({mode}).")
        return "\n".join(lines)
    noun = "job" if result["total"] == 1 else "jobs"
    lines.append(f"{result['total']} {noun} ranked ({mode}); top {len(jobs)}:")
    for job in jobs:
        place = " · ".join(part for part in (job["company"], job["location"]) if part)
        lines.append(
            f"{job['rank']}. #{job['id']} match {job['match_score']:.4f} {job['title']}"
            + (f" — {place}" if place else "")
        )
        lines.append(f"   {job['explanation']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# list_applications / get_application
# ---------------------------------------------------------------------------


def _application_record(
    application: Application, job: Job, *, now: datetime, preview_notes: bool
) -> dict[str, Any]:
    """The ``GET /applications`` record of one application, plus ``notes_truncated``."""

    view = ApplicationRead.from_records(application, job, now=now)
    record = view.model_dump(mode="json")
    # Second-precision RFC 3339 like every other tool (the API keeps microseconds).
    record.update(
        applied_at=_timestamp(view.applied_at),
        next_action_at=_timestamp(view.next_action_at),
        stage_changed_at=rfc3339(view.stage_changed_at),
        created_at=rfc3339(view.created_at),
        updated_at=rfc3339(view.updated_at),
    )
    record["job"]["captured_at"] = rfc3339(view.job.captured_at)
    notes = record["notes"]
    truncated = preview_notes and notes is not None and len(notes) > LIST_NOTES_PREVIEW_CHARS
    if truncated:
        record["notes"] = notes[:LIST_NOTES_PREVIEW_CHARS] + "…"
    record["notes_truncated"] = truncated
    return record


def _follow_up_text(record: dict[str, Any]) -> str:
    """``follow-up overdue 2026-11-18T17:00:00Z: Check in`` or ``no follow-up``."""

    if record["next_action_at"] is None:
        return f"next: {record['next_action']}" if record["next_action"] else "no follow-up"
    label = f": {record['next_action']}" if record["next_action"] else ""
    return f"follow-up {record['follow_up_status']} {record['next_action_at']}{label}"


def _application_line(record: dict[str, Any]) -> str:
    """One-line ``#id stage · title — company · follow-up`` summary."""

    job = record["job"]
    role = f"{job['title']} — {job['company']}" if job["company"] else job["title"]
    archived = " (archived)" if record["archived"] else ""
    return (
        f"#{record['id']} {record['stage']}{archived} · {role} · job #{record['job_id']}"
        f" · {_follow_up_text(record)}"
    )


async def _list_applications(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """List tracked applications with the filters, sorting and paging of the HTTP API."""

    now = utc_now()
    stages = [ApplicationStage(stage) for stage in arguments.get("stage", [])]
    filters = ApplicationFilters(
        stages=tuple(dict.fromkeys(stages)),
        company=arguments.get("company"),
        q=arguments.get("q"),
        follow_up=FollowUpFilter(arguments["follow_up"]) if "follow_up" in arguments else None,
        due_within_days=_int_argument(arguments, "due_within_days", DUE_SOON_DAYS),
        include_archived=bool(arguments.get("include_archived", False)),
        job_id=_optional_int_argument(arguments, "job_id"),
        sort=ApplicationSort(arguments.get("sort", ApplicationSort.UPDATED.value)),
    )
    limit = _int_argument(arguments, "limit", DEFAULT_PAGE_SIZE)
    offset = _int_argument(arguments, "offset", 0)
    page = await list_applications(session, filters, now=now, limit=limit, offset=offset)
    records = [
        _application_record(application, job, now=now, preview_notes=True)
        for application, job in page.items
    ]
    structured: dict[str, Any] = {
        "total": page.total,
        "offset": offset,
        "limit": limit,
        "next_offset": _next_offset(offset, len(records), page.total),
        "sort": filters.sort.value,
        "include_archived": filters.include_archived,
        "stage_counts": await stage_counts(session, filters, now=now),
        "follow_ups": await follow_up_counts(session, filters, now=now),
        "applications": records,
    }
    return ToolOutput(structured, _applications_summary(structured), len(records))


def _applications_summary(result: dict[str, Any]) -> str:
    """Render an application page as text."""

    total = result["total"]
    records = result["applications"]
    scope = "including archived" if result["include_archived"] else "archived hidden"
    board = " · ".join(f"{stage} {count}" for stage, count in result["stage_counts"].items())
    follow_ups = result["follow_ups"]
    lines: list[str] = []
    if records:
        noun = "application" if total == 1 else "applications"
        lines.append(
            f"{total} tracked {noun} ({scope}, sort={result['sort']}); showing "
            f"{result['offset'] + 1}-{result['offset'] + len(records)}:"
        )
        lines.extend(_application_line(record) for record in records)
    elif total:
        lines.append(f"{total} applications match, but offset {result['offset']} is past the end.")
    else:
        lines.append(f"No tracked applications match ({scope}).")
    lines.append(f"Board: {board}")
    lines.append(
        f"Follow-ups: {follow_ups['overdue']} overdue · {follow_ups['due']} due within "
        f"{DUE_SOON_DAYS} days · {follow_ups['scheduled']} later · {follow_ups['none']} none"
    )
    if result["next_offset"] is not None:
        lines.append(f"More: call list_applications again with offset={result['next_offset']}.")
    return "\n".join(lines)


async def _get_application(session: AsyncSession, arguments: dict[str, Any]) -> ToolOutput:
    """Return one application, its job summary and its most recent timeline events."""

    application_id = _int_argument(arguments, "application_id", 0)
    tracked = await get_tracked(session, application_id)
    if tracked is None:
        raise ToolError(
            f"No application with id {application_id}. Use list_applications to find ids.",
            kind="not_found",
        )
    application, job = tracked
    now = utc_now()
    event_limit = _int_argument(arguments, "event_limit", DEFAULT_EVENT_LIMIT)
    events = await application_events(session, application.id, limit=event_limit)
    event_count = await count_application_events(session, application.id)
    structured: dict[str, Any] = {
        "application": _application_record(application, job, now=now, preview_notes=False),
        "event_count": event_count,
        "events_truncated": len(events) < event_count,
        "events": [
            {
                **ApplicationEventRead.from_record(event).model_dump(mode="json"),
                "created_at": rfc3339(event.created_at),
            }
            for event in events
        ],
    }
    return ToolOutput(structured, _application_detail_summary(structured), 1)


def _event_line(event: dict[str, Any]) -> str:
    """One timeline entry as text."""

    if event["event_type"] in (ApplicationEventType.TRACKED, ApplicationEventType.STAGE_CHANGED):
        move = f"{event['from_stage'] or '·'} → {event['to_stage']}"
    else:
        move = ", ".join(sorted(event["changes"])) or "-"
    note = f' "{event["note"]}"' if event["note"] else ""
    return f"{event['sequence']:>4} {event['created_at']} {event['event_type']:<13} {move}{note}"


def _application_detail_summary(result: dict[str, Any]) -> str:
    """Render one application and its timeline as text."""

    record = result["application"]
    job = record["job"]
    allowed = ", ".join(record["allowed_stages"]) or f"none, {record['stage']} is final"
    lines = [
        f"Application #{record['id']} · {record['stage']}"
        + (" (archived)" if record["archived"] else "")
        + f" for {record['days_in_stage']} day{'' if record['days_in_stage'] == 1 else 's'}"
        + f" (next: {allowed})",
        " · ".join(
            part
            for part in (job["title"], job["company"], job["location"], f"job #{job['id']}")
            if part
        ),
    ]
    facts = [f"applied {record['applied_at']}" if record["applied_at"] else "not applied yet"]
    facts.append(_follow_up_text(record))
    lines.append("; ".join(facts))
    if record["notes"]:
        lines.append(f"Notes: {record['notes']}")
    shown = "Last" if result["events_truncated"] else "All"
    lines.append(f"{shown} {len(result['events'])} of {result['event_count']} timeline events:")
    lines.extend(_event_line(event) for event in result["events"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


def _nullable(schema: dict[str, Any], description: str | None = None) -> dict[str, Any]:
    """Allow ``null`` besides ``schema`` with single-type ``anyOf`` branches.

    Type arrays such as ``["string", "null"]`` are valid JSON Schema, but clients that map
    tool schemas onto a single-``type`` dialect (for example the OpenAPI subset used for
    Gemini function declarations) may reject them.
    """

    nullable: dict[str, Any] = {"anyOf": [schema, {"type": "null"}]}
    if description is not None:
        nullable["description"] = description
    return nullable


_STRING: dict[str, Any] = {"type": "string"}
_NULLABLE_STRING: dict[str, Any] = _nullable(_STRING)
_STRING_LIST: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
_TIMESTAMP: dict[str, Any] = {"type": "string", "description": "RFC 3339 UTC timestamp."}
_NULLABLE_TIMESTAMP: dict[str, Any] = _nullable(_STRING, "RFC 3339 UTC timestamp.")
_COUNT: dict[str, Any] = {"type": "integer", "minimum": 0}
_NULLABLE_INTEGER: dict[str, Any] = _nullable({"type": "integer"})
_ID_ARGUMENT: dict[str, Any] = {"type": "integer", "minimum": 1, "maximum": SQLITE_MAX_INTEGER}
_PAGE_ARGUMENTS: dict[str, Any] = {
    "limit": {
        "type": "integer",
        "minimum": 1,
        "maximum": MAX_PAGE_SIZE,
        "default": DEFAULT_PAGE_SIZE,
        "description": f"Page size (1-{MAX_PAGE_SIZE}).",
    },
    "offset": {
        "type": "integer",
        "minimum": 0,
        "maximum": SQLITE_MAX_INTEGER,
        "default": 0,
        "description": "Matches to skip; use next_offset from the previous page.",
    },
}
_PAGE_FIELDS: dict[str, Any] = {
    "total": _COUNT,
    "offset": _COUNT,
    "limit": _COUNT,
    "next_offset": _nullable(_COUNT, "Offset of the next page; null on the last page."),
}
_RUN_STATUSES = [status.value for status in RunStatus]


def _closed_object(properties: dict[str, Any]) -> dict[str, Any]:
    """Object schema where every listed property is required and no other is allowed."""

    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


_LLM_ENRICHMENT_OUTPUT: dict[str, Any] = _nullable(
    _closed_object(
        {"provider": _NULLABLE_STRING, "model": _NULLABLE_STRING, "summary": _NULLABLE_STRING}
    )
)
_JOB_SUMMARY_PROPERTIES: dict[str, Any] = {
    "id": {"type": "integer"},
    "title": _STRING,
    "company": _NULLABLE_STRING,
    "location": _NULLABLE_STRING,
    "remote": {"type": "boolean"},
    "score": {"type": "number"},
    "priority_tier": _nullable(
        _STRING, "Tier recorded in the decision trace (null when not recorded)."
    ),
    "url": _nullable(_STRING, "Posting link; null unless it is an absolute http(s) URL."),
    "source_config_id": _NULLABLE_INTEGER,
    "run_id": _STRING,
    "captured_at": _TIMESTAMP,
    "first_seen_at": _nullable(
        _STRING, "With dedupe: RFC 3339 time of the posting's first capture; otherwise null."
    ),
    "pay": _nullable(
        _closed_object(
            {
                "min_amount": {"type": "number"},
                "max_amount": {"type": "number"},
                "currency": _STRING,
                "interval": {"type": "string", "enum": ["hour", "day", "week", "month", "year"]},
                "annual_min": {"type": "integer"},
                "annual_max": {"type": "integer"},
                "source": {"type": "string", "enum": ["structured", "description"]},
            }
        ),
        "Pay the posting states (ISO 4217 currency; annual_* use hour x2080, day x260, "
        "week x52, month x12); null when none was captured. Informational only.",
    ),
}
_RUN_OUTPUT: dict[str, Any] = _closed_object(
    {
        "id": _STRING,
        "status": _STRING,
        "query": _NULLABLE_STRING,
        "source_config_ids": _nullable({"type": "array", "items": {"type": "integer"}}),
        "cancel_requested": {"type": "boolean"},
        "error_message": _NULLABLE_STRING,
        "created_at": _TIMESTAMP,
        "started_at": _NULLABLE_TIMESTAMP,
        "finished_at": _NULLABLE_TIMESTAMP,
        "job_count": _COUNT,
    }
)

_SEARCH_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "q": {
            "type": "string",
            "maxLength": 200,
            "description": "Space-separated terms; each must appear in the title, company or "
            "location (case-insensitive substring).",
        },
        "company": {
            "type": "string",
            "maxLength": 256,
            "description": "Case-insensitive company substring.",
        },
        "location": {
            "type": "string",
            "maxLength": 256,
            "description": "Case-insensitive location substring.",
        },
        "remote": {
            "type": "boolean",
            "description": "true: location mentions remote, anywhere, work from home, wfh, "
            "telecommute or distributed; false: it does not (or is empty).",
        },
        "min_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Minimum deterministic score (inclusive).",
        },
        "source_config_id": {
            **_ID_ARGUMENT,
            "description": "Only jobs captured from this source config (see list_sources).",
        },
        "run_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": _MAX_RUN_ID_LENGTH,
            "description": "Only jobs captured by this run (see list_runs).",
        },
        "created_after": {
            "type": "string",
            "format": "date-time",
            "maxLength": 64,
            "description": "ISO-8601 instant; only jobs captured at or after it (naive = UTC).",
        },
        "hours_old": {
            "type": "integer",
            "minimum": 1,
            "maximum": 8760,
            "description": "Only jobs captured within the last N hours (JobSpy hours_old).",
        },
        "min_salary": {
            "type": "integer",
            "minimum": 0,
            "maximum": SQLITE_MAX_INTEGER,
            "description": "Annualized pay floor: jobs whose range reaches it "
            "(annual_max >= min_salary). Needs salary_currency.",
        },
        "max_salary": {
            "type": "integer",
            "minimum": 0,
            "maximum": SQLITE_MAX_INTEGER,
            "description": "Annualized pay ceiling: jobs whose range starts at or below it "
            "(annual_min <= max_salary). Needs salary_currency.",
        },
        "salary_currency": {
            "type": "string",
            "pattern": "^[A-Za-z]{3}$",
            "description": "ISO 4217 code such as USD, EUR or GBP: only jobs paying in it. "
            "Required by min_salary, max_salary and sort=salary (no conversion).",
        },
        "has_salary": {
            "type": "boolean",
            "description": "true: only jobs with captured pay; false: only jobs without.",
        },
        "sort": {
            "type": "string",
            "enum": [sort.value for sort in JobSort],
            "default": JobSort.NEWEST.value,
            "description": "newest: most recently captured first; score: highest score first; "
            "salary: highest annualized pay first, needs salary_currency (ties: newest first).",
        },
        "dedupe": {
            "type": "boolean",
            "default": False,
            "description": "Collapse repeated captures of one URL and cross-board mirrors "
            "(same normalized title, company and location).",
        },
        **_PAGE_ARGUMENTS,
    },
    "additionalProperties": False,
}
_SEARCH_OUTPUT: dict[str, Any] = _closed_object(
    {
        **_PAGE_FIELDS,
        "sort": {"type": "string", "enum": [sort.value for sort in JobSort]},
        "dedupe": {"type": "boolean"},
        "captured_since": _nullable(
            _STRING, "Effective capture-time lower bound (RFC 3339) from created_after/hours_old."
        ),
        "jobs": {"type": "array", "items": _closed_object(_JOB_SUMMARY_PROPERTIES)},
    }
)
_JOB_ID_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {"job_id": {**_ID_ARGUMENT, "description": "Job id from search_jobs."}},
    "required": ["job_id"],
    "additionalProperties": False,
}
_GET_JOB_OUTPUT: dict[str, Any] = _closed_object(
    {
        "job": _closed_object({**_JOB_SUMMARY_PROPERTIES, "external_id": _NULLABLE_STRING}),
        "decision": _closed_object(
            {
                "priority_tier": _NULLABLE_STRING,
                "matched_query_terms": _STRING_LIST,
                "rationale": _STRING_LIST,
                "plan_steps": _STRING_LIST,
                "llm_enrichment": _LLM_ENRICHMENT_OUTPUT,
            }
        ),
        "run": _nullable(
            _closed_object({"id": _STRING, "query": _NULLABLE_STRING, "status": _STRING})
        ),
        "source": _nullable(
            _closed_object({"id": {"type": "integer"}, "name": _STRING, "source_type": _STRING})
        ),
        "source_payload": {
            "type": "object",
            "description": "Adapter fields captured with the job (decision trace excluded).",
        },
    }
)
_TIER_ENUM: dict[str, Any] = {"type": "string", "enum": ["high", "medium", "low"]}
_EXPLAIN_OUTPUT: dict[str, Any] = _closed_object(
    {
        "job_id": {"type": "integer"},
        "title": _STRING,
        "score": {"type": "number", "description": "Stored score (what search ranks by)."},
        "priority_tier": {**_TIER_ENUM, "description": "Tier of the stored score today."},
        "recorded_priority_tier": _NULLABLE_STRING,
        "tier_thresholds": _closed_object(
            {"high": {"type": "number"}, "medium": {"type": "number"}}
        ),
        "next_tier": _nullable(
            _closed_object(
                {"tier": _TIER_ENUM, "min_score": {"type": "number"}, "gap": {"type": "number"}}
            )
        ),
        "run_query": _NULLABLE_STRING,
        "query_terms": _STRING_LIST,
        "matched_terms": _STRING_LIST,
        "unmatched_terms": _STRING_LIST,
        "components": _closed_object(
            {
                "base": {"type": "number"},
                "keyword_bonus": {"type": "number"},
                "keyword_bonus_per_term": {"type": "number"},
                "keyword_bonus_cap": {"type": "number"},
                "stability_bonus": {"type": "number"},
                "max_score": {"type": "number"},
                "capped": {"type": "boolean"},
            }
        ),
        "recomputed_score": {"type": "number"},
        "matches_stored_score": {"type": "boolean"},
        "rationale": _STRING_LIST,
        "llm_enrichment": _LLM_ENRICHMENT_OUTPUT,
        "explanation": _STRING_LIST,
    }
)
_LIST_RUNS_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": _RUN_STATUSES,
            "description": "Only runs in this state.",
        },
        **_PAGE_ARGUMENTS,
    },
    "additionalProperties": False,
}
_LIST_RUNS_OUTPUT: dict[str, Any] = _closed_object(
    {**_PAGE_FIELDS, "runs": {"type": "array", "items": _RUN_OUTPUT}}
)
_GET_RUN_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "run_id": {
            "type": "string",
            "minLength": 1,
            "maxLength": _MAX_RUN_ID_LENGTH,
            "description": "Run id from list_runs.",
        },
        "event_limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_EVENT_LIMIT,
            "default": DEFAULT_EVENT_LIMIT,
            "description": "How many of the most recent events to return.",
        },
    },
    "required": ["run_id"],
    "additionalProperties": False,
}
_GET_RUN_OUTPUT: dict[str, Any] = _closed_object(
    {
        "run": _RUN_OUTPUT,
        "event_count": _COUNT,
        "events_truncated": {"type": "boolean"},
        "events": {
            "type": "array",
            "items": _closed_object(
                {
                    "sequence": {"type": "integer"},
                    "event_type": _STRING,
                    "message": _STRING,
                    "payload": _nullable({"type": "object"}),
                    "created_at": _TIMESTAMP,
                }
            ),
        },
    }
)
_LIST_SOURCES_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean",
            "description": "true/false keeps only enabled/disabled sources.",
        }
    },
    "additionalProperties": False,
}
_LIST_SOURCES_OUTPUT: dict[str, Any] = _closed_object(
    {
        "count": _COUNT,
        "sources": {
            "type": "array",
            "items": _closed_object(
                {
                    "id": {"type": "integer"},
                    "name": _STRING,
                    "source_type": _STRING,
                    "enabled": {"type": "boolean"},
                    "base_url": _NULLABLE_STRING,
                    "job_count": _COUNT,
                }
            ),
        },
    }
)
_MATCH_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "resume_text": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_RESUME_CHARS,
            "description": "Plain text of the user's resume (not a file path or URL). Used in "
            "memory only: never stored, logged or written to the audit log.",
        },
        **{
            name: _SEARCH_INPUT["properties"][name]
            for name in (
                "q",
                "company",
                "location",
                "remote",
                "min_score",
                "source_config_id",
                "run_id",
                "created_after",
                "hours_old",
                "min_salary",
                "max_salary",
                "salary_currency",
                "has_salary",
            )
        },
        "dedupe": {
            "type": "boolean",
            "default": True,
            "description": "Rank each posting once (re-captures and cross-board mirrors "
            "collapsed); on by default.",
        },
        "sort": {
            "type": "string",
            "enum": [sort.value for sort in MatchSort],
            "default": MatchSort.MATCH.value,
            "description": "match: highest match score first (ties: more matched skills, "
            "higher score, newer); blend: 0.7 * match score + 0.3 * deterministic score.",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_PAGE_SIZE,
            "default": DEFAULT_PAGE_SIZE,
            "description": f"Number of top jobs returned (1-{MAX_PAGE_SIZE}).",
        },
        "min_match": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Drop jobs whose match score is lower.",
        },
        "include_extra_skills": {
            "type": "boolean",
            "default": False,
            "description": "Also list the resume skills each posting does not mention.",
        },
    },
    "required": ["resume_text"],
    "additionalProperties": False,
}
_MATCH_JOB_PROPERTIES: dict[str, Any] = {
    **{name: value for name, value in _JOB_SUMMARY_PROPERTIES.items() if name != "first_seen_at"},
    "rank": {"type": "integer", "minimum": 1},
    "match_score": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "description": "Share of the posting's skills found on the resume.",
    },
    "blend_score": {"type": "number", "description": "0.7 * match_score + 0.3 * score."},
    "matched_skills": {
        **_STRING_LIST,
        "description": "Posting skills the resume names or implies, in posting order.",
    },
    "missing_skills": {
        **_STRING_LIST,
        "description": "Posting skills the resume lacks, in posting order.",
    },
    "extra_skills": _nullable(
        _STRING_LIST, "Resume skills the posting does not mention; null unless requested."
    ),
    "explanation": _STRING,
}
_MATCH_OUTPUT: dict[str, Any] = _closed_object(
    {
        "resume_sha256": {"type": "string", "description": "SHA-256 of the UTF-8 resume text."},
        "resume_skills": {**_STRING_LIST, "description": "Skills recognized in the resume."},
        "implied_skills": {
            "type": "object",
            "additionalProperties": _STRING_LIST,
            "description": "Skills the resume demonstrates without naming them, with the "
            "resume skills that imply them.",
        },
        "sort": {"type": "string", "enum": [sort.value for sort in MatchSort]},
        "dedupe": {"type": "boolean"},
        "captured_since": _nullable(
            _STRING, "Effective capture-time lower bound (RFC 3339) from created_after/hours_old."
        ),
        "total": {**_COUNT, "description": "Jobs ranked (filters and min_match applied)."},
        "limit": _COUNT,
        "jobs": {"type": "array", "items": _closed_object(_MATCH_JOB_PROPERTIES)},
    }
)

_STAGE_VALUES = [stage.value for stage in PIPELINE_ORDER]
_NULLABLE_STAGE: dict[str, Any] = _nullable({"type": "string", "enum": _STAGE_VALUES})
_LIST_APPLICATIONS_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "stage": {
            "type": "array",
            "items": {"type": "string", "enum": _STAGE_VALUES},
            "minItems": 1,
            "maxItems": len(_STAGE_VALUES),
            "description": 'Keep only these stages, e.g. ["applied", "interview"].',
        },
        "company": {
            "type": "string",
            "maxLength": 256,
            "description": "Case-insensitive company substring.",
        },
        "q": {
            "type": "string",
            "maxLength": 200,
            "description": "Space-separated terms; each must appear in the job title, company "
            "or location, or in the application's notes or next action.",
        },
        "follow_up": {
            "type": "string",
            "enum": [item.value for item in FollowUpFilter],
            "description": "overdue: follow-up time passed; due: before now + due_within_days "
            "(overdue included); scheduled: any follow-up; none: no follow-up.",
        },
        "due_within_days": {
            "type": "integer",
            "minimum": 0,
            "maximum": MAX_DUE_WITHIN_DAYS,
            "default": DUE_SOON_DAYS,
            "description": "Horizon of follow_up=due, in days.",
        },
        "include_archived": {
            "type": "boolean",
            "default": False,
            "description": "Include archived applications.",
        },
        "job_id": {**_ID_ARGUMENT, "description": "Only the application tracking this job."},
        "sort": {
            "type": "string",
            "enum": [item.value for item in ApplicationSort],
            "default": ApplicationSort.UPDATED.value,
            "description": "updated / created (newest first), next_action (soonest first), "
            "applied (latest first), score (job score, highest first).",
        },
        **_PAGE_ARGUMENTS,
    },
    "additionalProperties": False,
}
_APPLICATION_JOB_OUTPUT: dict[str, Any] = _closed_object(
    {
        "id": {"type": "integer"},
        "title": _STRING,
        "company": _NULLABLE_STRING,
        "location": _NULLABLE_STRING,
        "remote": {"type": "boolean"},
        "url": _nullable(_STRING, "Posting link; null unless it is an absolute http(s) URL."),
        "score": {"type": "number"},
        "priority_tier": _NULLABLE_STRING,
        "run_id": _STRING,
        "captured_at": _TIMESTAMP,
    }
)
_APPLICATION_OUTPUT: dict[str, Any] = _closed_object(
    {
        "id": {"type": "integer"},
        "job_id": {"type": "integer"},
        "stage": {"type": "string", "enum": _STAGE_VALUES},
        "archived": {"type": "boolean"},
        "notes": _nullable(_STRING, "The user's notes (list_applications shows a preview)."),
        "notes_truncated": {"type": "boolean"},
        "applied_at": _NULLABLE_TIMESTAMP,
        "next_action_at": _nullable(_STRING, "Follow-up time (RFC 3339 UTC)."),
        "next_action": _NULLABLE_STRING,
        "follow_up_status": {
            "type": "string",
            "enum": [item.value for item in FollowUpStatus],
            "description": f"overdue, due (within {DUE_SOON_DAYS} days), scheduled or none.",
        },
        "days_in_stage": _COUNT,
        "stage_changed_at": _TIMESTAMP,
        "allowed_stages": {
            "type": "array",
            "items": {"type": "string", "enum": _STAGE_VALUES},
            "description": "Legal next stages (empty when the stage is final).",
        },
        "created_at": _TIMESTAMP,
        "updated_at": _TIMESTAMP,
        "job": _APPLICATION_JOB_OUTPUT,
    }
)
_STAGE_COUNTS_OUTPUT: dict[str, Any] = {
    **_closed_object({stage: _COUNT for stage in _STAGE_VALUES}),
    "description": "Applications per stage for every filter except stage (the board).",
}
_FOLLOW_UPS_OUTPUT: dict[str, Any] = {
    **_closed_object({item.value: _COUNT for item in FollowUpStatus}),
    "description": "Matching applications per follow_up_status.",
}
_LIST_APPLICATIONS_OUTPUT: dict[str, Any] = _closed_object(
    {
        **_PAGE_FIELDS,
        "sort": {"type": "string", "enum": [item.value for item in ApplicationSort]},
        "include_archived": {"type": "boolean"},
        "stage_counts": _STAGE_COUNTS_OUTPUT,
        "follow_ups": _FOLLOW_UPS_OUTPUT,
        "applications": {"type": "array", "items": _APPLICATION_OUTPUT},
    }
)
_GET_APPLICATION_INPUT: dict[str, Any] = {
    "type": "object",
    "properties": {
        "application_id": {
            **_ID_ARGUMENT,
            "description": "Application id from list_applications.",
        },
        "event_limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_EVENT_LIMIT,
            "default": DEFAULT_EVENT_LIMIT,
            "description": "How many of the most recent timeline events to return.",
        },
    },
    "required": ["application_id"],
    "additionalProperties": False,
}
_GET_APPLICATION_OUTPUT: dict[str, Any] = _closed_object(
    {
        "application": _APPLICATION_OUTPUT,
        "event_count": _COUNT,
        "events_truncated": {"type": "boolean"},
        "events": {
            "type": "array",
            "items": _closed_object(
                {
                    "id": {"type": "integer"},
                    "application_id": {"type": "integer"},
                    "sequence": {"type": "integer"},
                    "event_type": {
                        "type": "string",
                        "enum": [item.value for item in ApplicationEventType],
                    },
                    "from_stage": _NULLABLE_STAGE,
                    "to_stage": _NULLABLE_STAGE,
                    "note": _NULLABLE_STRING,
                    "changes": {
                        "type": "object",
                        "description": "Changed fields as {field: {from, to}}.",
                    },
                    "created_at": _TIMESTAMP,
                }
            ),
        },
    }
)

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="explain_job_score",
        title="Explain a job's score",
        description=(
            "Explain in plain language how one job's deterministic score was built: base "
            "relevance, the keyword bonus for the run's query terms it matched (and missed), "
            "the URL-hash tiebreaker, the priority tier thresholds and how far the job is from "
            "the next tier. Recomputed with the current scorer from stored data; no LLM. Read-only."
        ),
        input_schema=_JOB_ID_INPUT,
        output_schema=_EXPLAIN_OUTPUT,
        handler=_explain_job_score,
    ),
    ToolSpec(
        name="get_application",
        title="Get a tracked application and its timeline",
        description=(
            "Return one tracked job application: stage, days in stage, legal next stages, "
            "applied date, follow-up (next_action_at, next_action, overdue/due status), the "
            "user's notes, a summary of the job, and its most recent timeline events (tracked, "
            "stage_changed, updated, note_added, archived, unarchived). Read-only: stages are "
            "moved through the HTTP API, never from here."
        ),
        input_schema=_GET_APPLICATION_INPUT,
        output_schema=_GET_APPLICATION_OUTPUT,
        handler=_get_application,
    ),
    ToolSpec(
        name="get_job",
        title="Get one job with its decision trace",
        description=(
            "Return one captured job by id: title, company, location, remote flag, http(s) "
            "link, score, priority tier, stated pay (currency, interval, annualized range), "
            "matched query terms, rationale, plan steps, optional LLM enrichment summary, and "
            "the run and source that captured it. Read-only."
        ),
        input_schema=_JOB_ID_INPUT,
        output_schema=_GET_JOB_OUTPUT,
        handler=_get_job,
    ),
    ToolSpec(
        name="get_run",
        title="Get a discovery run and its events",
        description=(
            "Return one discovery run's status, query, timestamps, captured job count and its "
            "most recent events (run.*, source.*, agent.decision ...). Read-only: runs cannot "
            "be started or cancelled from here."
        ),
        input_schema=_GET_RUN_INPUT,
        output_schema=_GET_RUN_OUTPUT,
        handler=_get_run,
    ),
    ToolSpec(
        name="list_applications",
        title="List tracked job applications",
        description=(
            "List the user's tracked job applications (saved → applied → interview → offer → "
            "accepted / rejected) with the filters of GET /applications: stage, company, q, "
            "follow_up=overdue|due|scheduled|none, due_within_days, include_archived, job_id; "
            "sort=updated|created|next_action|applied|score; limit (max "
            f"{MAX_PAGE_SIZE}) and offset paging. Also returns per-stage board counts and "
            "follow-up counts. Read-only: nothing is tracked, moved or submitted."
        ),
        input_schema=_LIST_APPLICATIONS_INPUT,
        output_schema=_LIST_APPLICATIONS_OUTPUT,
        handler=_list_applications,
    ),
    ToolSpec(
        name="list_runs",
        title="List discovery runs",
        description=(
            "List discovery runs newest first with status, query, timestamps and how many jobs "
            "each captured; filter by status and page with limit/offset. Read-only."
        ),
        input_schema=_LIST_RUNS_INPUT,
        output_schema=_LIST_RUNS_OUTPUT,
        handler=_list_runs,
    ),
    ToolSpec(
        name="list_sources",
        title="List configured job sources",
        description=(
            "List configured career-board sources (id, name, adapter type, enabled flag, URL) "
            "with how many jobs each captured. Use the ids as search_jobs source_config_id. "
            "Read-only."
        ),
        input_schema=_LIST_SOURCES_INPUT,
        output_schema=_LIST_SOURCES_OUTPUT,
        handler=_list_sources,
    ),
    ToolSpec(
        name="match_resume_to_jobs",
        title="Rank your job feed against a resume",
        description=(
            "Rank the jobs your discovery runs captured by how well they fit resume text the "
            "user provides. Skills are extracted deterministically (curated lexicon with "
            "aliases such as k8s → kubernetes, postgres → postgresql) from the resume and "
            "from each posting's title and description; match_score is the share of the "
            "posting's skills found on the resume, with matched_skills, missing_skills and a "
            "one-line explanation. sort=match|blend (blend mixes in the stored score); takes "
            "the search_jobs filters; dedupe is on by default. The resume is used in memory "
            "only and never stored or logged. Read-only; no LLM."
        ),
        input_schema=_MATCH_INPUT,
        output_schema=_MATCH_OUTPUT,
        handler=_match_resume_to_jobs,
    ),
    ToolSpec(
        name="search_jobs",
        title="Search your job feed",
        description=(
            "Search jobs your discovery runs captured, with the same filters as the HTTP API "
            "(GET /jobs): free-text q, company, location, remote, min_score, source_config_id, "
            "run_id, created_after, hours_old, pay (min_salary/max_salary annualized, "
            "salary_currency, has_salary); sort=newest|score|salary; dedupe collapses "
            f"re-captures and cross-board mirrors; limit (max {MAX_PAGE_SIZE}) and offset "
            "paging with the total match count. Read-only; never scrapes or applies."
        ),
        input_schema=_SEARCH_INPUT,
        output_schema=_SEARCH_OUTPUT,
        handler=_search_jobs,
    ),
)

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}
