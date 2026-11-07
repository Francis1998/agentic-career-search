"""Read-only MCP tools over the persisted job feed.

Every tool reuses the services behind the HTTP API instead of re-implementing queries:

* :mod:`~autoapply_agent.services.job_search` for filters, sorting, dedupe and paging
  (the exact semantics of ``GET /jobs``);
* :class:`~autoapply_agent.services.scoring.DeterministicScoringService` and the
  priority tiers of :mod:`~autoapply_agent.services.agent_decision` to explain scores;
* :mod:`~autoapply_agent.services.read_queries` for runs, run events and sources;
* :mod:`~autoapply_agent.services.job_export` for http(s)-only links and timestamps.

No tool writes: none can start or cancel runs, edit source configs or apply to jobs.
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
from autoapply_agent.db.models import SQLITE_MAX_INTEGER, Job, Run, RunStatus, SourceConfig
from autoapply_agent.services.agent_decision import (
    HIGH_PRIORITY_MIN_SCORE,
    MEDIUM_PRIORITY_MIN_SCORE,
    priority_tier_for_score,
)
from autoapply_agent.services.job_export import rfc3339, safe_http_url
from autoapply_agent.services.job_search import (
    JobSearchFilters,
    JobSort,
    PostingIdentity,
    capture_window_start,
    is_remote_location,
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
        sort=JobSort(arguments.get("sort", JobSort.NEWEST.value)),
        dedupe=bool(arguments.get("dedupe", False)),
    )
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
        "sort": {
            "type": "string",
            "enum": [sort.value for sort in JobSort],
            "default": JobSort.NEWEST.value,
            "description": "newest: most recently captured first; score: highest score first "
            "(ties: newest first).",
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
        name="get_job",
        title="Get one job with its decision trace",
        description=(
            "Return one captured job by id: title, company, location, remote flag, http(s) "
            "link, score, priority tier, matched query terms, rationale, plan steps, optional "
            "LLM enrichment summary, and the run and source that captured it. Read-only."
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
        name="search_jobs",
        title="Search your job feed",
        description=(
            "Search jobs your discovery runs captured, with the same filters as the HTTP API "
            "(GET /jobs): free-text q, company, location, remote, min_score, source_config_id, "
            "run_id, created_after, hours_old; sort=newest|score; dedupe collapses re-captures "
            f"and cross-board mirrors; limit (max {MAX_PAGE_SIZE}) and offset paging with the "
            "total match count. Read-only; never scrapes or applies."
        ),
        input_schema=_SEARCH_INPUT,
        output_schema=_SEARCH_OUTPUT,
        handler=_search_jobs,
    ),
)

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}
