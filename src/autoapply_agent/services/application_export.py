"""Spreadsheet-safe CSV, JSON Lines and iCalendar renderers for tracked applications.

* CSV reuses the OWASP CSV-injection hardening of :mod:`job_export`: every cell is
  quoted and text cells starting with ``=``, ``+``, ``-``, ``@``, tab or carriage return
  are prefixed with ``'``; only absolute ``http``/``https`` posting links are emitted.
* JSON Lines rows use the ``ApplicationRead`` API schema.
* The follow-up calendar is an iCalendar (RFC 5545) document with one ``VEVENT`` per
  application that has a follow-up: TEXT values are escaped (backslash, ``;``, ``,``,
  line breaks), other control characters are dropped and content lines are folded at
  75 octets without splitting a UTF-8 sequence. Notes are never included.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime

from autoapply_agent.db.models import Application, Job
from autoapply_agent.schemas.applications import ApplicationRead
from autoapply_agent.services.application_tracker import days_in_stage, follow_up_status
from autoapply_agent.services.job_export import neutralize_csv_cell, rfc3339, safe_http_url
from autoapply_agent.services.job_search import as_utc, is_remote_location

APPLICATION_CSV_COLUMNS: tuple[str, ...] = (
    "application_id",
    "job_id",
    "stage",
    "archived",
    "title",
    "company",
    "location",
    "remote",
    "url",
    "score",
    "applied_at",
    "next_action_at",
    "next_action",
    "follow_up_status",
    "days_in_stage",
    "stage_changed_at",
    "created_at",
    "updated_at",
    "notes",
)
ICS_PRODID = "-//Francis1998//agentic-career-search//EN"
FOLLOW_UP_DURATION = "PT30M"
_ICS_LINE_OCTETS = 75
# TEXT values may not contain control characters other than HTAB (RFC 5545 3.3.11).
_ICS_CONTROL = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
_URI_UNSAFE = re.compile(r"[\x00-\x20\x7f]")


def _timestamp(value: datetime | None) -> str:
    """RFC 3339 text of an optional timestamp (empty when missing)."""

    return rfc3339(value) if value is not None else ""


def application_csv_row(application: Application, job: Job, *, now: datetime) -> list[str]:
    """Flatten one application into a CSV row matching :data:`APPLICATION_CSV_COLUMNS`.

    Args:
        application: Tracked application.
        job: Its job.
        now: Reference time of ``follow_up_status`` and ``days_in_stage``.

    Returns:
        Cell values; untrusted text cells are neutralized.
    """

    return [
        str(application.id),
        str(application.job_id),
        application.stage,
        "true" if application.archived else "false",
        neutralize_csv_cell(job.title),
        neutralize_csv_cell(job.company or ""),
        neutralize_csv_cell(job.location or ""),
        "true" if is_remote_location(job.location) else "false",
        safe_http_url(job.url) or "",
        str(job.score),
        _timestamp(application.applied_at),
        _timestamp(application.next_action_at),
        neutralize_csv_cell(application.next_action or ""),
        follow_up_status(application.next_action_at, now).value,
        str(days_in_stage(application, now)),
        rfc3339(application.stage_changed_at),
        rfc3339(application.created_at),
        rfc3339(application.updated_at),
        neutralize_csv_cell(application.notes or ""),
    ]


def render_applications_csv(items: Sequence[tuple[Application, Job]], *, now: datetime) -> str:
    """Render a header row plus one fully quoted CSV row per application."""

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(APPLICATION_CSV_COLUMNS)
    for application, job in items:
        writer.writerow(application_csv_row(application, job, now=now))
    return buffer.getvalue()


def render_applications_jsonl(items: Sequence[tuple[Application, Job]], *, now: datetime) -> str:
    """Render one ``ApplicationRead`` JSON object per line."""

    return "".join(
        ApplicationRead.from_records(application, job, now=now).model_dump_json() + "\n"
        for application, job in items
    )


def ics_escape(value: str) -> str:
    """Escape an iCalendar TEXT value (RFC 5545 section 3.3.11).

    Args:
        value: Untrusted text.

    Returns:
        Text with ``\\``, ``;`` and ``,`` escaped, every line break (CRLF, CR or LF)
        written as ``\\n`` and any other control character except HTAB removed.
    """

    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
    return _ICS_CONTROL.sub("", text.replace("\n", "\\n"))


def fold_line(line: str) -> str:
    """Fold a content line into 75-octet lines joined by CRLF and a space.

    Continuation lines start with one space, so they carry at most 74 octets of
    content; a multi-octet UTF-8 character is never split.
    """

    chunks: list[str] = []
    current: list[str] = []
    size = 0
    limit = _ICS_LINE_OCTETS
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > limit:
            chunks.append("".join(current))
            current, size, limit = [], 0, _ICS_LINE_OCTETS - 1
        current.append(char)
        size += width
    chunks.append("".join(current))
    return "\r\n ".join(chunks)


def ics_datetime(value: datetime) -> str:
    """Format a timestamp as an iCalendar UTC DATE-TIME (``YYYYMMDDTHHMMSSZ``)."""

    moment = as_utc(value)
    # Not strftime: some C libraries drop the zero padding of years before 1000.
    return (
        f"{moment.year:04d}{moment.month:02d}{moment.day:02d}"
        f"T{moment.hour:02d}{moment.minute:02d}{moment.second:02d}Z"
    )


def _uri(value: str | None) -> str | None:
    """Return an http(s) URL that is safe as a raw URI property value, else None."""

    link = safe_http_url(value)
    return link if link is not None and not _URI_UNSAFE.search(link) else None


def follow_up_summary(application: Application, job: Job) -> str:
    """Event title: the follow-up label (or "Follow up") and the role."""

    role = f"{job.title} at {job.company}" if job.company else job.title
    return f"{application.next_action or 'Follow up'} - {role}"


def render_follow_up_calendar(
    items: Sequence[tuple[Application, Job]],
    *,
    calendar_name: str,
    generated_at: datetime,
    application_url: Callable[[Application], str],
    revisions: Mapping[int, int],
) -> bytes:
    """Render the applications' follow-ups as an iCalendar document.

    Each application with ``next_action_at`` becomes one 30-minute, transparent
    (free/busy neutral) ``VEVENT``. Its UID derives from the application's API URL,
    so a calendar updates the event in place when the follow-up moves, and
    ``SEQUENCE`` is the application's latest event sequence.

    Args:
        items: ``(application, job)`` pairs; those without a follow-up are skipped.
        calendar_name: ``X-WR-CALNAME`` shown by calendar apps.
        generated_at: ``DTSTAMP`` of every event.
        application_url: Absolute API URL of an application.
        revisions: Latest event sequence per application id.

    Returns:
        UTF-8 encoded calendar with CRLF line endings.
    """

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{ICS_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{ics_escape(calendar_name)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    stamp = ics_datetime(generated_at)
    for application, job in items:
        if application.next_action_at is None:
            continue
        link = application_url(application)
        description = [f"Stage: {application.stage}"]
        if application.applied_at is not None:
            description.append(f"Applied: {rfc3339(application.applied_at)}")
        posting = _uri(job.url)
        if posting is not None:
            description.append(f"Posting: {posting}")
        description.append(f"Application: {link}")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid5(uuid.NAMESPACE_URL, link)}@agentic-career-search",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{ics_datetime(application.next_action_at)}",
                f"DURATION:{FOLLOW_UP_DURATION}",
                f"SUMMARY:{ics_escape(follow_up_summary(application, job))}",
                f"DESCRIPTION:{ics_escape(chr(10).join(description))}",
                f"CATEGORIES:{ics_escape(application.stage)}",
                f"CREATED:{ics_datetime(application.created_at)}",
                f"LAST-MODIFIED:{ics_datetime(application.updated_at)}",
                f"SEQUENCE:{revisions.get(application.id, 0)}",
                "TRANSP:TRANSPARENT",
            ]
        )
        if posting is not None:
            lines.append(f"URL:{posting}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "".join(fold_line(line) + "\r\n" for line in lines).encode("utf-8")
