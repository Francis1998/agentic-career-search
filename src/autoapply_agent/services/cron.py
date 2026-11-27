"""Five-field cron expressions evaluated in an IANA time zone (standard library only).

Grammar (Vixie cron, ``crontab(5)``)::

    minute hour day-of-month month day-of-week
    0-59   0-23 1-31         1-12  0-7 (0 and 7 are Sunday)

* ``*``, single values, ranges ``a-b``, lists ``a,b,c`` and steps ``*/n``, ``a-b/n`` and
  ``a/n`` (``a`` to the field maximum).
* Month names ``jan``-``dec`` and day names ``sun``-``sat``, case-insensitive.
* Macros ``@hourly``, ``@daily`` (``@midnight``), ``@weekly``, ``@monthly`` and
  ``@yearly`` (``@annually``).
* Day-of-month and day-of-week: when both fields are restricted (neither starts with
  ``*``) a day matches if **either** field matches; otherwise both must match, so ``*``
  (and ``*/n``) defer to the other field.

Fire times are wall-clock times in the expression's time zone, computed with
:mod:`zoneinfo`: a local time that does not exist (the spring-forward gap) is skipped, and
a local time that happens twice (the fall-back overlap) fires once, at its first
occurrence.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MINUTES_PER_DAY = 24 * 60
SEARCH_HORIZON_DAYS = 3660
"""How far ahead to look for a fire time (ten years: Feb 29 can be eight years apart)."""
MAX_ZONE_NAME_CHARS = 64

MACROS: dict[str, str] = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}
_MONTH_NAMES = {
    name: number
    for number, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"),
        start=1,
    )
}
_DAY_NAMES = {
    name: number for number, name in enumerate(("sun", "mon", "tue", "wed", "thu", "fri", "sat"))
}
_DAYS_IN_MONTH = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_NUMBER = re.compile(r"[0-9]{1,2}")
_ZONE_KEY = re.compile(r"[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+)*")


class CronError(ValueError):
    """An invalid cron expression or time zone name; the message says what to fix."""


@dataclass(frozen=True)
class _Field:
    name: str
    low: int
    high: int
    names: dict[str, int]


_FIELDS = (
    _Field("minute", 0, 59, {}),
    _Field("hour", 0, 23, {}),
    _Field("day-of-month", 1, 31, {}),
    _Field("month", 1, 12, _MONTH_NAMES),
    _Field("day-of-week", 0, 7, _DAY_NAMES),
)


def _parse_value(token: str, field: _Field) -> int:
    """Parse one number or name of ``field``."""

    named = field.names.get(token.lower())
    if named is not None:
        return named
    if not _NUMBER.fullmatch(token):
        hint = " or a name such as " + next(iter(field.names)) if field.names else ""
        raise CronError(f"{field.name}: {token!r} is not a number{hint}")
    value = int(token)
    if not field.low <= value <= field.high:
        raise CronError(f"{field.name}: {value} is outside {field.low}-{field.high}")
    return value


def _parse_field(text: str, field: _Field) -> frozenset[int]:
    """Parse one comma-separated field into the set of values it allows."""

    values: set[int] = set()
    for part in text.split(","):
        if not part:
            raise CronError(f"{field.name}: empty item in {text!r}")
        base, slash, step_text = part.partition("/")
        step = 1
        if slash:
            if not _NUMBER.fullmatch(step_text) or int(step_text) == 0:
                raise CronError(f"{field.name}: step {step_text!r} must be a number from 1 to 99")
            step = int(step_text)
        if base == "*":
            start, end = field.low, field.high
        elif "-" in base:
            first, _, last = base.partition("-")
            start, end = _parse_value(first, field), _parse_value(last, field)
            if field.high == 7 and end == 0 < start:
                end = 7  # ``fri-sun``: Sunday closes the week
            if start > end:
                raise CronError(f"{field.name}: range {base!r} runs backwards")
        else:
            start = _parse_value(base, field)
            end = field.high if slash else start
        values.update(range(start, end + 1, step))
    return frozenset(values)


@dataclass(frozen=True)
class CronExpression:
    """A parsed cron expression.

    Attributes:
        source: The expression with whitespace normalised (macros kept as written).
        minutes_of_day: Sorted local fire times of a matching day, as minutes after midnight.
        days_of_month: Allowed days of the month.
        months: Allowed months (1-12).
        days_of_week: Allowed weekdays, 0 (Sunday) to 6 (Saturday).
        day_or: True when both day fields are restricted, so either one may match.
    """

    source: str
    minutes_of_day: tuple[int, ...]
    days_of_month: frozenset[int]
    months: frozenset[int]
    days_of_week: frozenset[int]
    day_or: bool

    def matches_day(self, day: date) -> bool:
        """Return whether the expression fires on ``day`` (at some time of day)."""

        if day.month not in self.months:
            return False
        dom = day.day in self.days_of_month
        dow = day.isoweekday() % 7 in self.days_of_week
        return dom or dow if self.day_or else dom and dow

    @property
    def min_gap_minutes(self) -> int:
        """Smallest wall-clock gap between two consecutive fire times.

        Exact within a day; the gap from the last fire of a day to the first of the next
        is included even when consecutive days never both match (a safe lower bound).
        DST transitions are not considered: they can shorten one gap per transition.
        """

        times = self.minutes_of_day
        gaps = [later - earlier for earlier, later in pairwise(times)]
        gaps.append(times[0] + MINUTES_PER_DAY - times[-1])
        return min(gaps)

    def iter_fires(
        self, after: datetime, zone: ZoneInfo, *, inclusive: bool = False
    ) -> Iterator[datetime]:
        """Yield fire instants after ``after`` (or at it when ``inclusive``), in order.

        Args:
            after: Reference instant (aware; naive values are UTC).
            zone: Time zone whose wall clock the expression describes.
            inclusive: Whether a fire exactly at ``after`` counts.

        Yields:
            Increasing aware UTC instants, for at most ten years after ``after``.
        """

        last = _as_utc(after)
        if inclusive:
            last -= timedelta(microseconds=1)
        # One day earlier: a fall-back transition at midnight can move the local date back.
        first_day = last.astimezone(zone).date() - timedelta(days=1)
        for offset in range(SEARCH_HORIZON_DAYS + 2):
            day = first_day + timedelta(days=offset)
            if not self.matches_day(day):
                continue
            for minute_of_day in self.minutes_of_day:
                instant = resolve_local(day, minute_of_day, zone)
                if instant is not None and instant > last:
                    yield instant
                    last = instant

    def next_fire(
        self, after: datetime, zone: ZoneInfo, *, inclusive: bool = False
    ) -> datetime | None:
        """Return the first fire instant after ``after`` (or at it when ``inclusive``).

        Returns:
            Aware UTC instant, or None when nothing fires within ten years.
        """

        return next(self.iter_fires(after, zone, inclusive=inclusive), None)


def resolve_local(day: date, minute_of_day: int, zone: ZoneInfo) -> datetime | None:
    """Map a local wall-clock time to its UTC instant.

    Args:
        day: Local date.
        minute_of_day: Minutes after local midnight.
        zone: Time zone.

    Returns:
        The instant (first occurrence when the time is ambiguous), or None when the
        local time does not exist on that day (spring-forward gap).
    """

    naive = datetime.combine(day, time(minute_of_day // 60, minute_of_day % 60))
    instant = naive.replace(tzinfo=zone).astimezone(UTC)
    if instant.astimezone(zone).replace(tzinfo=None) != naive:
        return None
    return instant


def _as_utc(value: datetime) -> datetime:
    """Aware UTC copy of ``value`` (naive values are UTC)."""

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _check_possible(fields: tuple[frozenset[int], ...], day_or: bool) -> None:
    """Reject day-of-month / month combinations that never happen (e.g. 30 February)."""

    days_of_month, months = fields[2], fields[3]
    if day_or:
        return
    longest = max(_DAYS_IN_MONTH[month - 1] for month in months)
    if min(days_of_month) > longest:
        raise CronError(
            f"day-of-month {min(days_of_month)} never occurs in month(s) "
            + ",".join(str(month) for month in sorted(months))
        )


def parse_cron(expression: str) -> CronExpression:
    """Parse a five-field cron expression or macro.

    Args:
        expression: Text such as ``"30 8 * * 1-5"`` or ``"@daily"``.

    Returns:
        Parsed expression.

    Raises:
        CronError: If the expression is malformed or can never fire.
    """

    source = " ".join(expression.split())
    if not source:
        raise CronError("cron expression is empty")
    if source.startswith("@"):
        macro = MACROS.get(source.lower())
        if macro is None:
            raise CronError(f"unknown macro {source!r}; use one of {', '.join(MACROS)}")
        texts = macro.split(" ")
    else:
        texts = source.split(" ")
    if len(texts) != len(_FIELDS):
        raise CronError(
            f"expected 5 fields (minute hour day-of-month month day-of-week), got {len(texts)}"
        )
    fields = tuple(_parse_field(text, field) for text, field in zip(texts, _FIELDS, strict=True))
    day_or = not texts[2].startswith("*") and not texts[4].startswith("*")
    _check_possible(fields, day_or)
    minutes, hours = sorted(fields[0]), sorted(fields[1])
    return CronExpression(
        source=source,
        minutes_of_day=tuple(hour * 60 + minute for hour in hours for minute in minutes),
        days_of_month=fields[2],
        months=fields[3],
        days_of_week=frozenset(day % 7 for day in fields[4]),
        day_or=day_or,
    )


@lru_cache(maxsize=256)
def load_zone(name: str) -> ZoneInfo:
    """Load an IANA time zone such as ``America/Los_Angeles``.

    Args:
        name: Time zone key.

    Returns:
        The zone.

    Raises:
        CronError: If the name is not a known IANA time zone.
    """

    message = f"unknown time zone {name!r}; use an IANA name such as America/Los_Angeles"
    if len(name) > MAX_ZONE_NAME_CHARS or not _ZONE_KEY.fullmatch(name):
        raise CronError(message)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise CronError(message) from None
