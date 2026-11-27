"""In-house cron parser: grammar, day-of-month / day-of-week rule and DST-correct fire times."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import islice

import pytest

from autoapply_agent.services.cron import CronError, load_zone, parse_cron

LOS_ANGELES = load_zone("America/Los_Angeles")
BERLIN = load_zone("Europe/Berlin")


def _local_fires(expression: str, zone_name: str, after: str, count: int) -> list[str]:
    zone = load_zone(zone_name)
    start = datetime.fromisoformat(after)
    fires = islice(parse_cron(expression).iter_fires(start, zone), count)
    return [fire.astimezone(zone).isoformat() for fire in fires]


@pytest.mark.parametrize(
    ("expression", "minutes_of_day"),
    [
        ("30 8 * * 1-5", (510,)),
        ("0,30 9-10 * * *", (540, 570, 600, 630)),
        ("*/20 0 * * *", (0, 20, 40)),
        ("15-45/15 23 * * *", (1395, 1410, 1425)),
        ("50/5 1 * * *", (110, 115)),
        ("@hourly", tuple(hour * 60 for hour in range(24))),
        ("  0   12  *  *  * ", (720,)),
    ],
)
def test_minute_and_hour_fields(expression: str, minutes_of_day: tuple[int, ...]) -> None:
    assert parse_cron(expression).minutes_of_day == minutes_of_day


@pytest.mark.parametrize(
    ("expression", "months", "days_of_week"),
    [
        ("0 0 * jan,MAR-may *", {1, 3, 4, 5}, set(range(7))),
        ("0 0 * * mon-fri", set(range(1, 13)), {1, 2, 3, 4, 5}),
        ("0 0 * * 7", set(range(1, 13)), {0}),
        ("0 0 * * fri-sun", set(range(1, 13)), {5, 6, 0}),
        ("0 0 * */3 */2", {1, 4, 7, 10}, {0, 2, 4, 6}),
    ],
)
def test_names_sunday_seven_and_steps(
    expression: str, months: set[int], days_of_week: set[int]
) -> None:
    parsed = parse_cron(expression)

    assert parsed.months == months
    assert parsed.days_of_week == days_of_week


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("", "empty"),
        ("* * * *", "expected 5 fields"),
        ("* * * * * *", "expected 5 fields"),
        ("60 * * * *", "minute: 60 is outside 0-59"),
        ("* 24 * * *", "hour: 24 is outside 0-23"),
        ("* * 0 * *", "day-of-month: 0 is outside 1-31"),
        ("* * * 13 *", "month: 13 is outside 1-12"),
        ("* * * * 8", "day-of-week: 8 is outside 0-7"),
        ("*/0 * * * *", "step '0'"),
        ("*/x * * * *", "step 'x'"),
        ("5-1 * * * *", "runs backwards"),
        ("1,,2 * * * *", "empty item"),
        ("a * * * *", "'a' is not a number"),
        ("0 0 * * funday", "or a name such as sun"),
        ("0 0 30 2 *", "day-of-month 30 never occurs in month"),
        ("0 0 31 4,6,9,11 *", "never occurs"),
        ("@reboot", "unknown macro"),
        ("-1 * * * *", "is not a number"),
    ],
)
def test_invalid_expressions_explain_the_problem(expression: str, message: str) -> None:
    with pytest.raises(CronError, match=message):
        parse_cron(expression)


def test_day_of_month_or_day_of_week_when_both_are_restricted() -> None:
    # crontab(5): the 1st of the month OR any Monday.
    assert _local_fires("0 9 1 * mon", "UTC", "2026-11-27T00:00:00+00:00", 4) == [
        "2026-11-30T09:00:00+00:00",
        "2026-12-01T09:00:00+00:00",
        "2026-12-07T09:00:00+00:00",
        "2026-12-14T09:00:00+00:00",
    ]


def test_a_field_starting_with_star_defers_to_the_other_day_field() -> None:
    # "*/2" starts with "*", so both fields must match: odd days that are Mondays.
    expression = parse_cron("0 9 */2 * 1")

    assert not expression.day_or
    assert _local_fires("0 9 */2 * 1", "UTC", "2026-11-27T00:00:00+00:00", 3) == [
        "2026-12-07T09:00:00+00:00",
        "2026-12-21T09:00:00+00:00",
        "2027-01-11T09:00:00+00:00",
    ]


def test_february_29_fires_only_in_leap_years() -> None:
    assert _local_fires("0 0 29 2 *", "UTC", "2026-11-27T00:00:00+00:00", 3) == [
        "2028-02-29T00:00:00+00:00",
        "2032-02-29T00:00:00+00:00",
        "2036-02-29T00:00:00+00:00",
    ]


@pytest.mark.parametrize(
    ("zone", "after", "expected"),
    [
        # Spring forward: 02:30 does not exist on 2027-03-14 (Los Angeles) / 03-28 (Berlin).
        (
            "America/Los_Angeles",
            "2027-03-13T00:00:00-08:00",
            ["2027-03-13T02:30:00-08:00", "2027-03-15T02:30:00-07:00"],
        ),
        (
            "Europe/Berlin",
            "2027-03-27T00:00:00+01:00",
            ["2027-03-27T02:30:00+01:00", "2027-03-29T02:30:00+02:00"],
        ),
        # Fall back: 02:30 happens twice on 2026-10-25 in Berlin; it fires once (first).
        (
            "Europe/Berlin",
            "2026-10-24T00:00:00+02:00",
            ["2026-10-24T02:30:00+02:00", "2026-10-25T02:30:00+02:00", "2026-10-26T02:30:00+01:00"],
        ),
    ],
)
def test_daily_fire_skips_nonexistent_and_fires_ambiguous_times_once(
    zone: str, after: str, expected: list[str]
) -> None:
    assert _local_fires("30 2 * * *", zone, after, len(expected)) == expected


def test_los_angeles_fall_back_fires_the_repeated_hour_once() -> None:
    # 01:30 happens at 08:30Z (PDT) and 09:30Z (PST) on 2026-11-01: only the first fires.
    assert _local_fires("30 1 * * *", "America/Los_Angeles", "2026-10-31T12:00:00-07:00", 2) == [
        "2026-11-01T01:30:00-07:00",
        "2026-11-02T01:30:00-08:00",
    ]


def test_hourly_schedule_waits_two_hours_across_fall_back() -> None:
    fires = list(
        islice(
            parse_cron("0 * * * *").iter_fires(
                datetime(2026, 11, 1, 7, 30, tzinfo=UTC), LOS_ANGELES
            ),
            3,
        )
    )

    assert [fire.isoformat() for fire in fires] == [
        "2026-11-01T08:00:00+00:00",
        "2026-11-01T10:00:00+00:00",
        "2026-11-01T11:00:00+00:00",
    ]


def test_weekdays_at_0830_los_angeles_from_a_friday() -> None:
    assert _local_fires("30 8 * * 1-5", "America/Los_Angeles", "2026-11-27T11:00:00-08:00", 3) == [
        "2026-11-30T08:30:00-08:00",
        "2026-12-01T08:30:00-08:00",
        "2026-12-02T08:30:00-08:00",
    ]


def test_next_fire_is_strictly_after_unless_inclusive() -> None:
    expression = parse_cron("0 12 * * *")
    noon = datetime(2026, 12, 1, 12, tzinfo=UTC)

    assert expression.next_fire(noon, BERLIN) == datetime(2026, 12, 2, 11, tzinfo=UTC)
    assert expression.next_fire(datetime(2026, 12, 1, 11, tzinfo=UTC), BERLIN, inclusive=True) == (
        datetime(2026, 12, 1, 11, tzinfo=UTC)
    )
    assert expression.next_fire(noon.replace(tzinfo=None), load_zone("UTC")) == datetime(
        2026, 12, 2, 12, tzinfo=UTC
    )


@pytest.mark.parametrize(
    ("expression", "gap"),
    [
        ("*/15 * * * *", 15),
        ("*/10 * * * *", 10),
        ("0 */6 * * *", 360),
        ("30 8 * * 1-5", 1440),
        ("0,59 0,23 * * *", 1),
    ],
)
def test_min_gap_minutes_includes_the_wrap_to_the_next_day(expression: str, gap: int) -> None:
    assert parse_cron(expression).min_gap_minutes == gap


@pytest.mark.parametrize(
    "name", ["Mars/Olympus", "America", "", "../etc/passwd", "/etc/localtime", "zone.tab", "x" * 65]
)
def test_load_zone_rejects_names_outside_the_iana_database(name: str) -> None:
    with pytest.raises(CronError, match="unknown time zone"):
        load_zone(name)


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        ("2026-11-27T00:00:00+00:00", "2032-02-29T00:00:00+00:00"),
        ("2032-03-01T00:00:00+00:00", "2060-02-29T00:00:00+00:00"),
        # 2100 is not a leap year: the next Sunday, 29 February is 40 years later.
        ("2088-03-01T00:00:00+00:00", "2128-02-29T00:00:00+00:00"),
    ],
)
def test_sparse_day_of_month_and_weekday_intersections_keep_firing(
    after: str, expected: str
) -> None:
    # "*/7" starts with "*", so both day fields must match: 29 February on a Sunday.
    expression = parse_cron("0 0 29 2 */7")

    fire = expression.next_fire(datetime.fromisoformat(after), load_zone("UTC"))

    assert fire == datetime.fromisoformat(expected)
