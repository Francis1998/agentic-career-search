"""Unit tests for the deterministic pay extractor (structured pay and posting text)."""

from __future__ import annotations

import html

import pytest

from autoapply_agent.services.compensation import (
    ANNUAL_FACTORS,
    Compensation,
    CompensationSource,
    PayInterval,
    compensation_columns,
    compensation_from_monetary_amount,
    compensation_from_text,
    describe_pay,
    make_compensation,
    normalize_currency,
)

# (text, (min, max, currency, interval, annual_min, annual_max))
ACCEPTED: list[tuple[str, tuple[float, float, str, str, int, int]]] = [
    ("Salary: $120,000 - $150,000", (120_000, 150_000, "USD", "year", 120_000, 150_000)),
    ("Pay range $120k\u2013$150k", (120_000, 150_000, "USD", "year", 120_000, 150_000)),
    ("Base pay $120K \u2014 $150K", (120_000, 150_000, "USD", "year", 120_000, 150_000)),
    ("Salary range: $120-150k", (120_000, 150_000, "USD", "year", 120_000, 150_000)),
    ("USD 120,000 to 150,000 base salary", (120_000, 150_000, "USD", "year", 120_000, 150_000)),
    ("Salary: 120,000 - 150,000 USD", (120_000, 150_000, "USD", "year", 120_000, 150_000)),
    ("Salary between $100,000 and $120,000", (100_000, 120_000, "USD", "year", 100_000, 120_000)),
    ("$45/hr", (45, 45, "USD", "hour", 93_600, 93_600)),
    ("Hourly rate: $25.50 - $30", (25.5, 30, "USD", "hour", 53_040, 62_400)),
    ("$45 to $55 per hour", (45, 55, "USD", "hour", 93_600, 114_400)),
    ("Day rate: \u00a3500", (500, 500, "GBP", "day", 130_000, 130_000)),
    ("$900/week", (900, 900, "USD", "week", 46_800, 46_800)),
    ("Pay: $4,000 - $5,000 per month", (4_000, 5_000, "USD", "month", 48_000, 60_000)),
    ("Salary \u00a350,000\u2013\u00a360,000 p.a.", (50_000, 60_000, "GBP", "year", 50_000, 60_000)),
    ("Salary: \u20ac60.000", (60_000, 60_000, "EUR", "year", 60_000, 60_000)),
    ("Salary: 60\u00a0000 \u20ac per year", (60_000, 60_000, "EUR", "year", 60_000, 60_000)),
    ("Compensation: CA$90K - CA$110K", (90_000, 110_000, "CAD", "year", 90_000, 110_000)),
    ("Salary $90k-$110k CAD", (90_000, 110_000, "CAD", "year", 90_000, 110_000)),
    (
        "Salary: $120,000 \u2212 $150,000 (2026 range)",
        (120_000, 150_000, "USD", "year", 120_000, 150_000),
    ),
    (
        "&lt;p&gt;Salary: $95,000&amp;ndash;$105,000&lt;/p&gt;",
        (95_000, 105_000, "USD", "year", 95_000, 105_000),
    ),
    (
        "We offer a 401(k) with a $5k match. Salary: $90k-$110k",
        (90_000, 110_000, "USD", "year", 90_000, 110_000),
    ),
    (
        "Salary $120k\u2013$150k plus annual bonus up to $10k and a $2,000 signing bonus",
        (120_000, 150_000, "USD", "year", 120_000, 150_000),
    ),
    (
        "Base pay: $45/hr; $500 annual learning stipend",
        (45, 45, "USD", "hour", 93_600, 93_600),
    ),
    # Several ranges (one per office): the widest envelope in the first currency/interval.
    (
        "Salary ranges: NYC $150k-$180k, SF $160k-$200k, Remote $130k-$170k",
        (130_000, 200_000, "USD", "year", 130_000, 200_000),
    ),
    # A second range in another interval is ignored, not mixed in.
    ("$45/hr (about $93,600 per year)", (45, 45, "USD", "hour", 93_600, 93_600)),
]

REJECTED: list[str] = [
    "We raised a $5M Series A led by top investors.",
    "$1B revenue and growing",
    "Total comp $5 million",
    "Generous 401(k) plan",
    "$50 stipend for your home office",
    "$100 monthly internet stipend",
    "$2,000 signing bonus",
    "In 2026 we will grow the team to 2027 people.",
    "up to $150,000 salary",
    "Pay starts at $20/hr",
    "Salary: $120,000+",
    "Salary 120,000 - 150,000",  # no currency
    "Salary: US$100k - CA$120k",  # mixed currencies
    "$150,000 - $120,000 salary",  # inverted range
    "Salary: \u00a5500,000",  # unsupported, ambiguous symbol
    "Salary: $4,000 - $5,000",  # no interval and below the yearly threshold
    "Salary: \u20b912,00,000 per year",  # lakh grouping is not parsed
    "",
]


@pytest.mark.parametrize(("text", "expected"), ACCEPTED, ids=[case[0][:40] for case in ACCEPTED])
def test_text_ranges_are_extracted_and_annualized(
    text: str, expected: tuple[float, float, str, str, int, int]
) -> None:
    found = compensation_from_text(text)

    assert found is not None
    assert (
        found.min_amount,
        found.max_amount,
        found.currency,
        found.interval.value,
        found.annual_min,
        found.annual_max,
    ) == expected
    assert found.source == CompensationSource.DESCRIPTION
    plain = " ".join(html.unescape(html.unescape(text)).split())
    assert all(piece in plain for piece in found.snippet.split(" | "))


@pytest.mark.parametrize("text", REJECTED, ids=[text[:40] or "empty" for text in REJECTED])
def test_false_positives_and_ambiguous_amounts_are_rejected(text: str) -> None:
    assert compensation_from_text(text) is None


def test_none_text_is_rejected() -> None:
    assert compensation_from_text(None) is None


def test_block_tags_end_a_clause_so_a_stipend_line_never_borrows_a_pay_word() -> None:
    page = "<ul><li>Competitive salary</li><li>$1,200 per month housing stipend</li></ul>"

    assert compensation_from_text(page) is None


def test_annual_factors_are_the_documented_full_time_factors() -> None:
    assert {interval.value: factor for interval, factor in ANNUAL_FACTORS.items()} == {
        "hour": 2080,
        "day": 260,
        "week": 52,
        "month": 12,
        "year": 1,
    }


STRUCTURED_RANGE = {
    "@type": "MonetaryAmount",
    "currency": "USD",
    "value": {
        "@type": "QuantitativeValue",
        "minValue": 120000,
        "maxValue": "150000.00",
        "unitText": "YEAR",
    },
}


@pytest.mark.parametrize(
    ("base_salary", "default_currency", "expected"),
    [
        (STRUCTURED_RANGE, None, (120_000, 150_000, "USD", "year")),
        (
            {"currency": "usd", "value": {"value": 40.0, "unitText": "HOUR"}},
            None,
            (40, 40, "USD", "hour"),
        ),
        (
            {"value": {"minValue": 4000, "maxValue": 5000, "unitText": "MONTH"}},
            "EUR",
            (4_000, 5_000, "EUR", "month"),
        ),
        (
            [{"currency": "XXQ"}, {**STRUCTURED_RANGE, "currency": "GBP"}],
            None,
            (120_000, 150_000, "GBP", "year"),
        ),
        (
            {"currency": "CAD", "value": {"value": 300, "unitText": "https://schema.org/DAY"}},
            None,
            (300, 300, "CAD", "day"),
        ),
    ],
)
def test_structured_base_salary_is_read(
    base_salary: object, default_currency: str | None, expected: tuple[float, float, str, str]
) -> None:
    found = compensation_from_monetary_amount(base_salary, default_currency=default_currency)

    assert found is not None
    assert (found.min_amount, found.max_amount, found.currency, found.interval.value) == expected
    assert found.source == CompensationSource.STRUCTURED


@pytest.mark.parametrize(
    "base_salary",
    [
        {"value": {"minValue": 1, "maxValue": 2, "unitText": "YEAR"}},  # no currency
        {"currency": "USD", "value": {"minValue": 100000, "maxValue": 120000}},  # no unit
        {"currency": "USD", "value": {"minValue": 100000, "unitText": "YEAR"}},  # one-sided
        {"currency": "USD", "value": {"value": -5, "unitText": "HOUR"}},
        {"currency": "USD", "value": {"value": True, "unitText": "HOUR"}},
        {"currency": "USD", "value": {"minValue": 9, "maxValue": 5, "unitText": "HOUR"}},
        {"currency": "USD", "value": {"value": 10**12, "unitText": "HOUR"}},  # too large
        {"currency": "US Dollar", "value": {"value": 50000, "unitText": "YEAR"}},
        {"currency": "USD", "value": {"value": 50000, "unitText": "FORTNIGHT"}},
        120000,
        "competitive",
        [],
    ],
)
def test_unusable_structured_pay_is_null_never_guessed(base_salary: object) -> None:
    assert compensation_from_monetary_amount(base_salary) is None


def test_payload_round_trips_and_columns_hold_the_annualized_range() -> None:
    found = make_compensation(
        "45.5", 55, "usd", PayInterval.HOUR, CompensationSource.DESCRIPTION, "  $45.50 -\n $55/hr "
    )
    assert found is not None

    payload = found.to_payload()

    assert payload == {
        "min_amount": 45.5,
        "max_amount": 55,
        "currency": "USD",
        "interval": "hour",
        "annual_min": 94_640,
        "annual_max": 114_400,
        "source": "description",
        "snippet": "$45.50 - $55/hr",
    }
    assert Compensation.from_payload(payload) == found
    assert Compensation.from_payload({**payload, "interval": "fortnight"}) is None
    assert Compensation.from_payload("not a payload") is None
    assert compensation_columns(found) == {
        "salary_min_annual": 94_640,
        "salary_max_annual": 114_400,
        "salary_currency": "USD",
        "salary_interval": "hour",
    }
    assert set(compensation_columns(None).values()) == {None}
    assert describe_pay(found) == ("USD 45.50\u201355 per hour (USD 94,640\u2013114,400 per year)")


def test_currency_codes_are_validated_against_iso_4217() -> None:
    assert normalize_currency(" eur ") == "EUR"
    assert normalize_currency("ABC") is None
    assert normalize_currency(42) is None
