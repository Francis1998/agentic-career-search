"""Spreadsheet-safe CSV, JSON Lines and Atom 1.0 renderers for persisted jobs.

* CSV follows the OWASP CSV Injection guidance: every cell is quoted and text
  cells that start with ``=``, ``+``, ``-``, ``@``, tab or carriage return are
  prefixed with ``'`` so spreadsheets show them as text instead of formulas.
* Only absolute ``http``/``https`` job URLs are emitted as links (CSV + Atom).
* JSON Lines rows use the ``JobRead`` API schema, so they round-trip losslessly.
* The Atom feed (RFC 4287) is built with :mod:`xml.etree.ElementTree`, which
  escapes markup; characters that XML 1.0 forbids are stripped first.
"""

from __future__ import annotations

import csv
import io
import re
import uuid

# ElementTree only builds and serializes the feed here; it never parses input.
import xml.etree.ElementTree as ET  # nosec B405
from collections.abc import AsyncIterable, AsyncIterator, Callable, Sequence
from datetime import datetime
from urllib.parse import urlsplit

from autoapply_agent.db.models import Job
from autoapply_agent.schemas.jobs import JobRead
from autoapply_agent.services.job_search import PostingIdentity, as_utc, is_remote_location

CSV_COLUMNS: tuple[str, ...] = (
    "id",
    "title",
    "company",
    "location",
    "remote",
    "score",
    "priority_tier",
    "source",
    "url",
    "source_config_id",
    "run_id",
    "external_id",
    "created_at",
)
ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"
PROJECT_URL = "https://github.com/Francis1998/agentic-career-search"

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_INVALID_XML_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_FLUSH_THRESHOLD = 64 * 1024


def neutralize_csv_cell(value: str) -> str:
    """Make a text cell inert in spreadsheet applications.

    Args:
        value: Untrusted cell text.

    Returns:
        ``value`` prefixed with ``'`` when it starts with a formula trigger.
    """

    if value.startswith(_FORMULA_PREFIXES):
        return f"'{value}"
    return value


def safe_http_url(url: str | None) -> str | None:
    """Return ``url`` only when it is an absolute ``http``/``https`` URL.

    Args:
        url: Untrusted URL captured from a career page.

    Returns:
        The stripped URL, or None for other schemes (``javascript:``, ``data:``...).
    """

    candidate = (url or "").strip()
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    if parts.scheme.lower() in {"http", "https"} and parts.netloc:
        return candidate
    return None


def rfc3339(value: datetime) -> str:
    """Format a datetime as an RFC 3339 UTC timestamp (``...Z``)."""

    return as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _raw_text(job: Job, *path: str) -> str:
    """Read a nested string from ``job.raw`` (empty string when missing)."""

    node: object = job.raw or {}
    for key in path:
        if not isinstance(node, dict):
            return ""
        node = node.get(key)
    return node if isinstance(node, str) else ""


def job_csv_row(job: Job) -> list[str]:
    """Flatten one job into a CSV row matching :data:`CSV_COLUMNS`.

    Args:
        job: Persisted job.

    Returns:
        Cell values; untrusted text cells are neutralized.
    """

    return [
        str(job.id),
        neutralize_csv_cell(job.title),
        neutralize_csv_cell(job.company or ""),
        neutralize_csv_cell(job.location or ""),
        "true" if is_remote_location(job.location) else "false",
        str(job.score),
        neutralize_csv_cell(_raw_text(job, "agent_decision", "priority_tier")),
        neutralize_csv_cell(_raw_text(job, "source")),
        safe_http_url(job.url) or "",
        "" if job.source_config_id is None else str(job.source_config_id),
        neutralize_csv_cell(job.run_id),
        neutralize_csv_cell(job.external_id or ""),
        rfc3339(job.created_at),
    ]


def job_jsonl_line(job: Job) -> str:
    """Serialize one job as a JSON Lines record using the ``JobRead`` schema."""

    return JobRead.model_validate(job).model_dump_json() + "\n"


async def iter_csv(jobs: AsyncIterable[Job]) -> AsyncIterator[str]:
    """Stream a header row plus one fully quoted CSV row per job.

    Args:
        jobs: Jobs to export.

    Yields:
        CSV text chunks of roughly 64 KiB.
    """

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    async for job in jobs:
        writer.writerow(job_csv_row(job))
        if buffer.tell() >= _FLUSH_THRESHOLD:
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()
    yield buffer.getvalue()


async def iter_jsonl(jobs: AsyncIterable[Job]) -> AsyncIterator[str]:
    """Stream one JSON object per line.

    Args:
        jobs: Jobs to export.

    Yields:
        JSON Lines text chunks of roughly 64 KiB.
    """

    chunk: list[str] = []
    size = 0
    async for job in jobs:
        line = job_jsonl_line(job)
        chunk.append(line)
        size += len(line)
        if size >= _FLUSH_THRESHOLD:
            yield "".join(chunk)
            chunk, size = [], 0
    if chunk:
        yield "".join(chunk)


def _xml_text(value: str) -> str:
    """Drop characters that are not allowed anywhere in an XML 1.0 document."""

    return _INVALID_XML_CHARS.sub("", value)


def _add_text(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Append ``<tag>text</tag>`` to ``parent``."""

    element = ET.SubElement(parent, tag)
    element.text = _xml_text(text)
    return element


def entry_id(posting: PostingIdentity) -> str:
    """Return the Atom entry id: a UUIDv5 URN of the posting's first-capture URL.

    The id survives re-captures and cross-board mirrors of the same posting, so feed
    readers do not notify twice for one job.
    """

    return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, posting.url)}"


def entry_summary(job: Job) -> str:
    """Build the plain-text Atom entry summary."""

    priority = _raw_text(job, "agent_decision", "priority_tier") or "n/a"
    return (
        f"Company: {job.company or 'n/a'} | Location: {job.location or 'n/a'} | "
        f"Remote: {'yes' if is_remote_location(job.location) else 'no'} | "
        f"Score: {job.score:.2f} | Priority: {priority}"
    )


def render_atom_feed(
    entries: Sequence[tuple[Job, PostingIdentity]],
    *,
    feed_id: str,
    title: str,
    self_url: str,
    fallback_link: Callable[[Job], str],
    generated_at: datetime,
) -> bytes:
    """Render jobs as an Atom 1.0 (RFC 4287) feed document.

    Args:
        entries: ``(job, posting)`` pairs, newest first; the job supplies the content,
            the posting the stable id and publication time.
        feed_id: Permanent IRI identifying this feed.
        title: Human-readable feed title.
        self_url: URL the feed was requested from (``rel="self"``).
        fallback_link: Link for jobs whose URL is not ``http(s)``.
        generated_at: Feed ``updated`` value when there are no entries.

    Returns:
        UTF-8 encoded XML document.
    """

    feed = ET.Element("feed", {"xmlns": ATOM_NAMESPACE})
    _add_text(feed, "id", feed_id)
    _add_text(feed, "title", title)
    updated = max((posting.first_seen for _, posting in entries), default=as_utc(generated_at))
    _add_text(feed, "updated", rfc3339(updated))
    ET.SubElement(
        feed,
        "link",
        {"rel": "self", "type": "application/atom+xml", "href": _xml_text(self_url)},
    )
    _add_text(ET.SubElement(feed, "author"), "name", "agentic-career-search")
    generator = _add_text(feed, "generator", "agentic-career-search")
    generator.set("uri", PROJECT_URL)

    for job, posting in entries:
        entry = ET.SubElement(feed, "entry")
        _add_text(entry, "id", entry_id(posting))
        _add_text(entry, "title", f"{job.title} at {job.company}" if job.company else job.title)
        link = safe_http_url(job.url) or fallback_link(job)
        ET.SubElement(
            entry, "link", {"rel": "alternate", "type": "text/html", "href": _xml_text(link)}
        )
        first_seen = rfc3339(posting.first_seen)
        _add_text(entry, "published", first_seen)
        _add_text(entry, "updated", first_seen)
        _add_text(entry, "summary", entry_summary(job))

    return ET.tostring(feed, encoding="utf-8", xml_declaration=True)
