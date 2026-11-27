"""Deterministic pay extraction: structured schema.org pay and pay ranges in posting text.

One extractor feeds every surface (capture, search filters, exports, feed, MCP):

* :func:`compensation_from_monetary_amount` reads schema.org ``MonetaryAmount`` pay,
  the ``baseSalary`` of a JSON-LD ``JobPosting`` (``source="structured"``);
* :func:`compensation_from_text` finds a pay range stated in a posting description
  (``source="description"``), rejecting funding, revenue, stipends, bonuses, 401(k)
  plans and years.

Amounts are never guessed: an unknown currency or interval, a one-sided range
("up to $150k") or an inconsistent range yields ``None``. Annual figures use the
documented :data:`ANNUAL_FACTORS` (as JobSpy's ``enforce_annual_salary`` does). Pay is
informational only: nothing here feeds the deterministic score or any decision.
"""

from __future__ import annotations

import html
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class PayInterval(StrEnum):
    """Period a stated pay amount covers."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


ANNUAL_FACTORS: dict[PayInterval, int] = {
    PayInterval.HOUR: 2080,  # 40 hours x 52 weeks
    PayInterval.DAY: 260,  # 5 days x 52 weeks
    PayInterval.WEEK: 52,
    PayInterval.MONTH: 12,
    PayInterval.YEAR: 1,
}
"""Multipliers from a stated interval to a year (full-time, no overtime or unpaid leave)."""


class CompensationSource(StrEnum):
    """Where a captured pay range came from."""

    STRUCTURED = "structured"
    DESCRIPTION = "description"


MAX_ANNUAL_AMOUNT = 10**12
"""Largest accepted annualized amount in any currency; larger values are data errors."""
SNIPPET_MAX_CHARS = 200
"""Longest evidence snippet kept with a pay range."""

ISO_4217_CODES: frozenset[str] = frozenset(
    """
    AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD
    BTN BWP BYN BZD CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB
    EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK
    JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA
    MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK
    PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SOS SRD SSP STN
    SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VED VES VND VUV
    WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG
    """.split()
)
"""ISO 4217 codes of circulating currencies (plus ANG and BGN, withdrawn in 2025-2026)."""


def normalize_currency(code: object) -> str | None:
    """Return ``code`` as an upper-case ISO 4217 code, or None when it is not one.

    Args:
        code: Candidate currency code (any case, surrounding blanks ignored).

    Returns:
        The upper-case code when it names a circulating currency, else None.
    """

    if not isinstance(code, str):
        return None
    candidate = code.strip().upper()
    return candidate if candidate in ISO_4217_CODES else None


def _amount(value: object) -> float | None:
    """Return a finite positive number from a JSON number or numeric string."""

    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = _parse_number(value.strip())
    if not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0 else None


def _plain(value: float) -> int | float:
    """JSON-friendly amount: an int when whole, else rounded to cents."""

    return int(value) if value.is_integer() else round(value, 2)


@dataclass(slots=True, frozen=True)
class Compensation:
    """A pay range in one currency and interval; a single figure has ``min == max``.

    Attributes:
        min_amount: Lowest stated amount per ``interval``.
        max_amount: Highest stated amount per ``interval``.
        currency: ISO 4217 code.
        interval: Period the amounts cover.
        source: ``structured`` (adapter data) or ``description`` (posting text).
        snippet: Evidence the range was read from (at most 200 characters).
    """

    min_amount: float
    max_amount: float
    currency: str
    interval: PayInterval
    source: CompensationSource
    snippet: str

    @property
    def annual_min(self) -> int:
        """``min_amount`` times the interval's annual factor, rounded to whole units."""

        return round(self.min_amount * ANNUAL_FACTORS[self.interval])

    @property
    def annual_max(self) -> int:
        """``max_amount`` times the interval's annual factor, rounded to whole units."""

        return round(self.max_amount * ANNUAL_FACTORS[self.interval])

    def to_payload(self) -> dict[str, object]:
        """Serialize for ``Job.raw["compensation"]`` (round-trips via :meth:`from_payload`)."""

        return {
            "min_amount": _plain(self.min_amount),
            "max_amount": _plain(self.max_amount),
            "currency": self.currency,
            "interval": self.interval.value,
            "annual_min": self.annual_min,
            "annual_max": self.annual_max,
            "source": self.source.value,
            "snippet": self.snippet,
        }

    @classmethod
    def from_payload(cls, payload: object) -> Compensation | None:
        """Rebuild a range stored by :meth:`to_payload`; None for anything else."""

        if not isinstance(payload, Mapping):
            return None
        try:
            interval = PayInterval(str(payload.get("interval")))
            source = CompensationSource(str(payload.get("source")))
        except ValueError:
            return None
        snippet = payload.get("snippet")
        return make_compensation(
            payload.get("min_amount"),
            payload.get("max_amount"),
            payload.get("currency"),
            interval,
            source,
            snippet if isinstance(snippet, str) else "",
        )


def make_compensation(
    minimum: object,
    maximum: object,
    currency: object,
    interval: PayInterval,
    source: CompensationSource,
    snippet: str,
) -> Compensation | None:
    """Validate the parts of a pay range and build it.

    Args:
        minimum: Lowest amount (number or numeric string).
        maximum: Highest amount (number or numeric string).
        currency: ISO 4217 code (any case).
        interval: Period the amounts cover.
        source: Where the range was read.
        snippet: Evidence text (whitespace collapsed, cut to 200 characters).

    Returns:
        The range, or None when an amount is missing, not positive, inverted
        (``minimum > maximum``) or too large, or the currency is not ISO 4217.
    """

    low, high, code = _amount(minimum), _amount(maximum), normalize_currency(currency)
    if low is None or high is None or code is None or low > high:
        return None
    if high * ANNUAL_FACTORS[interval] > MAX_ANNUAL_AMOUNT:
        return None
    evidence = " ".join(snippet.split())[:SNIPPET_MAX_CHARS]
    return Compensation(low, high, code, interval, source, evidence)


def compensation_columns(compensation: Compensation | None) -> dict[str, Any]:
    """Return the indexed ``Job`` salary columns for a range (all None without one)."""

    if compensation is None:
        return {
            "salary_min_annual": None,
            "salary_max_annual": None,
            "salary_currency": None,
            "salary_interval": None,
        }
    return {
        "salary_min_annual": compensation.annual_min,
        "salary_max_annual": compensation.annual_max,
        "salary_currency": compensation.currency,
        "salary_interval": compensation.interval.value,
    }


def _format_amount(value: float) -> str:
    """``120,000`` or ``45.50``: thousands separators, cents only when present."""

    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def _format_range(low: float, high: float) -> str:
    """One amount, or ``low-high`` joined with an en dash."""

    if low == high:
        return _format_amount(low)
    return f"{_format_amount(low)}\u2013{_format_amount(high)}"


def describe_pay(compensation: Compensation) -> str:
    """Human-readable range, e.g. ``USD 45-55 per hour (USD 93,600-114,400 per year)``.

    Args:
        compensation: Pay range.

    Returns:
        Stated range and interval; non-yearly ranges add the annualized range.
    """

    code = compensation.currency
    stated = _format_range(compensation.min_amount, compensation.max_amount)
    text = f"{code} {stated} per {compensation.interval.value}"
    if compensation.interval != PayInterval.YEAR:
        annual = _format_range(compensation.annual_min, compensation.annual_max)
        text += f" ({code} {annual} per year)"
    return text


# ---------------------------------------------------------------------------
# Structured pay: schema.org MonetaryAmount (JobPosting baseSalary)
# ---------------------------------------------------------------------------

_UNIT_TEXT: dict[str, PayInterval] = {
    "HOUR": PayInterval.HOUR,
    "HOURLY": PayInterval.HOUR,
    "DAY": PayInterval.DAY,
    "DAILY": PayInterval.DAY,
    "WEEK": PayInterval.WEEK,
    "WEEKLY": PayInterval.WEEK,
    "MONTH": PayInterval.MONTH,
    "MONTHLY": PayInterval.MONTH,
    "YEAR": PayInterval.YEAR,
    "YEARLY": PayInterval.YEAR,
    "ANNUAL": PayInterval.YEAR,
    "ANNUALLY": PayInterval.YEAR,
}
"""``unitText`` values (Google documents HOUR, DAY, WEEK, MONTH and YEAR)."""


def _first_text(value: object) -> str | None:
    """First non-blank string of a JSON-LD value given as text or a list."""

    for item in value if isinstance(value, list) else [value]:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def _unit_interval(unit_text: str | None) -> PayInterval | None:
    """Map ``unitText`` (also as an IRI such as ``https://schema.org/YEAR``) to an interval."""

    if unit_text is None:
        return None
    term = unit_text.rsplit("/", 1)[-1].rsplit(":", 1)[-1].strip().upper()
    return _UNIT_TEXT.get(term)


def compensation_from_monetary_amount(
    value: object, *, default_currency: object = None
) -> Compensation | None:
    """Read a schema.org ``MonetaryAmount``: the ``baseSalary`` of a ``JobPosting``.

    Accepts the shape Google documents, ``{"currency": "USD", "value":
    {"@type": "QuantitativeValue", "minValue": 120000, "maxValue": 150000,
    "unitText": "YEAR"}}``, a single ``value`` instead of ``minValue``/``maxValue``,
    amounts as numeric strings, and lists of either (the first usable entry wins).

    Args:
        value: ``baseSalary`` value.
        default_currency: The posting's ``salaryCurrency``, used when the amount has
            no ``currency`` of its own.

    Returns:
        A ``structured`` range, or None when the currency, the interval
        (``unitText``) or a closed range is missing; one-sided ranges are skipped.
    """

    if isinstance(value, list):
        for item in value:
            found = compensation_from_monetary_amount(item, default_currency=default_currency)
            if found is not None:
                return found
        return None
    if not isinstance(value, Mapping):
        return None
    currency = _first_text(value.get("currency")) or _first_text(default_currency)
    inner = value.get("value")
    if isinstance(inner, list):
        inner = inner[0] if inner else None
    quantity: Mapping[str, Any] = inner if isinstance(inner, Mapping) else value
    single = quantity.get("value") if isinstance(inner, Mapping) else inner
    unit = _first_text(quantity.get("unitText")) or _first_text(value.get("unitText"))
    interval = _unit_interval(unit)
    minimum, maximum = _amount(quantity.get("minValue")), _amount(quantity.get("maxValue"))
    if minimum is None and maximum is None:
        minimum = maximum = _amount(single)
    if interval is None or minimum is None or maximum is None:
        return None
    snippet = f"baseSalary {currency} {_format_range(minimum, maximum)} {unit}"
    return make_compensation(
        minimum, maximum, currency, interval, CompensationSource.STRUCTURED, snippet
    )


# ---------------------------------------------------------------------------
# Pay stated in posting text
# ---------------------------------------------------------------------------

_DOLLAR_PREFIXES: dict[str, str] = {
    "US$": "USD",
    "CA$": "CAD",
    "C$": "CAD",
    "AU$": "AUD",
    "A$": "AUD",
    "NZ$": "NZD",
    "SG$": "SGD",
    "S$": "SGD",
    "HK$": "HKD",
    "MX$": "MXN",
}
_SYMBOLS: dict[str, str] = {"\u00a3": "GBP", "\u20ac": "EUR", "\u20b9": "INR"}
TEXT_CURRENCY_CODES: tuple[str, ...] = (
    "USD",
    "CAD",
    "AUD",
    "NZD",
    "SGD",
    "HKD",
    "MXN",
    "GBP",
    "EUR",
    "CHF",
    "INR",
    "JPY",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
)
"""ISO codes recognized in text, before or after an amount (``USD 120,000``, ``60.000 EUR``)."""
IMPLICIT_ANNUAL_CURRENCIES: frozenset[str] = frozenset(
    {"USD", "CAD", "AUD", "NZD", "GBP", "EUR", "CHF"}
)
"""Currencies whose unlabeled amounts of :data:`IMPLICIT_ANNUAL_MINIMUM` or more are yearly."""
IMPLICIT_ANNUAL_MINIMUM = 10_000
MAX_TEXT_CHARS = 50_000
"""Characters of plain description text that are scanned."""

_DOLLAR = "$"
_DOLLAR_CODES = frozenset({"USD", *_DOLLAR_PREFIXES.values()})
_CODES = "|".join(TEXT_CURRENCY_CODES)
_PREFIX = (
    r"(?<![A-Za-z])(?:"
    + "|".join(re.escape(p) for p in sorted(_DOLLAR_PREFIXES, key=len, reverse=True))
    + r")|\$|"
    + "|".join(_SYMBOLS)
)
_NUMBER = r"\d{1,3}(?:[,.' ]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
_AMOUNT = re.compile(
    rf"(?:(?:(?P<pre>{_PREFIX})|(?<![A-Za-z])(?P<precode>{_CODES})(?![A-Za-z]))[ ]?)?"
    rf"(?<![\d.,])(?P<num>{_NUMBER})(?!\d|[.,]\d)"
    rf"(?:[ ]?(?P<k>[kK]))?"
    rf"(?:[ ]?(?P<post>(?:{_CODES})(?![A-Za-z])|[\u20ac\u00a3]))?"
    rf"(?![A-Za-z\d])"
)
_NUMBER_PARTS = re.compile(r"(\d+(?:[.,]\d{3})*)(?:[.,](\d{1,2}))?")
_RANGE_SEPARATOR = re.compile(r"\s*(?:[-~\u2010-\u2015\u2212]|to|and)\s*", re.IGNORECASE)
_BETWEEN = re.compile(r"\bbetween\s*\Z", re.IGNORECASE)
_MAGNITUDE_WORD = re.compile(
    r"\s*(?:millions?|billions?|trillions?|mil|mn|bn|mm|m|b)\b", re.IGNORECASE
)
_CLAUSE_BREAK = re.compile(r"[;!?\n|\u2022]|\.(?=\s|\Z)")
_FOLLOWING_INTERVAL = re.compile(
    rf"\A\s*(?:(?:{_CODES})\s*)?(?:gross\s+|base\s+)?(?:"
    r"(?P<hour>/\s*(?:hours|hour|hrs|hr|h)\b|(?:per|an|a)\s+hour\b|hourly\b|p/h\b)"
    r"|(?P<day>/\s*day\b|(?:per|a)\s+day\b|daily\b)"
    r"|(?P<week>/\s*(?:week|wk)\b|(?:per|a)\s+week\b|weekly\b)"
    r"|(?P<month>/\s*(?:month|mth|mo)\b|(?:per|a)\s+month\b|monthly\b)"
    r"|(?P<year>/\s*(?:year|yr|annum)\b|(?:per|a)\s+(?:year|annum)\b|annually\b|annual\b"
    r"|yearly\b|p\.?\s?a\b\.?))",
    re.IGNORECASE,
)
_PRECEDING_INTERVAL = re.compile(
    r"\b(?:(?P<hour>hourly|per\s+hour)|(?P<day>daily|per\s+day|day\s+rate)"
    r"|(?P<week>weekly|per\s+week)|(?P<month>monthly|per\s+month)"
    r"|(?P<year>annual|annually|yearly|per\s+(?:year|annum)))\b",
    re.IGNORECASE,
)
_ONE_SIDED = re.compile(
    r"(?:\bup\s+to|\bupto|\bfrom|\bstarting\s+(?:at|from)|\bstarts?\s+at|\bat\s+least"
    r"|\bminimum(?:\s+of)?|\bmin\.?|\bmaximum(?:\s+of)?|\bmax\.?|\bas\s+(?:much|high)\s+as"
    r"|\bover|\bmore\s+than|\bin\s+excess\s+of|\bexceeding|\babove|\bnorth\s+of)\s*:?\s*\Z",
    re.IGNORECASE,
)
_PAY_WORD = re.compile(
    r"\b(?:salary|salaries|pay|paid|pays|compensation|comp|wage|wages|rate|rates|base"
    r"|earn|earns|earning|earnings|income|remuneration|range|band)\b",
    re.IGNORECASE,
)
_PHRASE_TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]*|[+&(),]")
_PHRASE_STOPS = frozenset(
    {"+", "&", "(", ")", ",", "plus", "and", "with", "or", "including", "includes", "but"}
)
_PHRASE_WORDS = 4
_NOT_PAY_WORDS = frozenset(
    """
    stipend stipends allowance allowances bonus bonuses reimburse reimburses reimbursed
    reimbursement reimbursements budget budgets credit credits gift gifts voucher vouchers
    referral relocation signing sign-on equity stock stocks rsu rsus options funding funded
    raise raised raising revenue revenues valuation series arr investment investments
    investors round grant grants donation donations match matching fund funds fee fees
    deposit discount discounts perk perks prize prizes award awards scholarship tuition
    insurance premium premiums deductible contribution contributions assets aum sales spend
    worth diem commission commissions tips internet phone cell mobile commuter commute
    transit parking gym wellness meal meals lunch food coworking learning conference travel
    mileage equipment laptop
    """.split()
)
"""Words next to an amount that mark it as something other than base pay."""
_SPACE_LIKE = str.maketrans({"\u00a0": " ", "\u202f": " ", "\u2009": " ", "\u2007": " "})
_BLOCK_TAG = re.compile(
    r"<\s*/?\s*(?:p|br|li|ul|ol|div|h[1-6]|tr|td|th|table|section)\b[^<>]{0,500}>",
    re.IGNORECASE,
)
_HTML_TAG = re.compile(r"<[^<>]{0,500}>")


def _parse_number(text: str) -> float | None:
    """Parse ``120,000``, ``60.000``, ``60 000``, ``45.50`` or ``45,50`` (None otherwise)."""

    compact = re.sub(r"[ '\u2019]", "", text)
    match = _NUMBER_PARTS.fullmatch(compact)
    if match is None:
        return None
    whole = re.sub(r"[.,]", "", match.group(1))
    return float(f"{whole}.{match.group(2)}" if match.group(2) else whole)


@dataclass(slots=True, frozen=True)
class _Token:
    """One amount found in text: position, value, ``k`` suffix and currency marker."""

    start: int
    end: int
    value: float
    has_k: bool
    currency: str | None


def _token(match: re.Match[str]) -> _Token | None:
    """Build a token from an :data:`_AMOUNT` match (None when the number is unusable)."""

    value = _parse_number(match.group("num"))
    if value is None:
        return None
    markers = [
        _DOLLAR_PREFIXES.get(marker, _SYMBOLS.get(marker, marker))
        for marker in (match.group("pre"), match.group("precode"), match.group("post"))
        if marker
    ]
    specific = {marker for marker in markers if marker != _DOLLAR}
    currency: str | None = None
    if len(specific) == 1:
        currency = specific.pop()
        if _DOLLAR in markers and currency not in _DOLLAR_CODES:
            return None
    elif len(specific) > 1:
        return None
    elif markers:
        currency = _DOLLAR
    return _Token(match.start(), match.end(), value, bool(match.group("k")), currency)


def _plain_text(text: str) -> str:
    """Description as plain text: tags dropped (block tags end a clause), entities decoded."""

    decoded = html.unescape(text[: MAX_TEXT_CHARS * 2])
    without_tags = _HTML_TAG.sub(" ", _BLOCK_TAG.sub("\n", decoded))
    return html.unescape(without_tags).translate(_SPACE_LIKE)[:MAX_TEXT_CHARS]


def _candidates(text: str, tokens: list[_Token]) -> list[tuple[_Token, ...]]:
    """Group tokens into ranges (``A - B``, ``A to B``, ``between A and B``) and singles.

    A range needs a currency marker on either end; a single amount needs its own.
    """

    candidates: list[tuple[_Token, ...]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 1 < len(tokens):
            following = tokens[index + 1]
            separator = _RANGE_SEPARATOR.fullmatch(text[token.end : following.start])
            if (
                separator is not None
                and (token.currency or following.currency)
                and (
                    separator.group(0).strip().lower() != "and"
                    or _BETWEEN.search(text[max(0, token.start - 24) : token.start])
                )
            ):
                candidates.append((token, following))
                index += 2
                continue
        if token.currency:
            candidates.append((token,))
        index += 1
    return candidates


def _clause_before(text: str, start: int) -> str:
    """Up to 80 characters before ``start``, from the last clause break on."""

    window = text[max(0, start - 80) : start]
    breaks = list(_CLAUSE_BREAK.finditer(window))
    return window[breaks[-1].end() :] if breaks else window


def _clause_after(text: str, end: int) -> str:
    """Up to 48 characters after ``end``, up to the first clause break."""

    window = text[end : end + 48]
    found = _CLAUSE_BREAK.search(window)
    return window[: found.start()] if found else window


def _phrase(words: list[str]) -> list[str]:
    """Lower-cased words up to the first stop token, at most :data:`_PHRASE_WORDS`."""

    phrase: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered in _PHRASE_STOPS or len(phrase) == _PHRASE_WORDS:
            break
        phrase.append(lowered)
    return phrase


def _interval(match: re.Match[str] | None) -> PayInterval | None:
    """Interval named by the group that matched in an interval-cue regex."""

    if match is None:
        return None
    for interval in PayInterval:
        if match.group(interval.value):
            return interval
    return None


def _range_values(tokens: tuple[_Token, ...]) -> tuple[float, float]:
    """Amounts of a candidate; a ``k`` on one end of ``$120-150k`` applies to both."""

    first, last = tokens[0], tokens[-1]
    low = first.value * (1000 if first.has_k or (last.has_k and first.value < 1000) else 1)
    high = last.value * (1000 if last.has_k or (first.has_k and last.value < 1000) else 1)
    return low, high


def _currency(tokens: tuple[_Token, ...]) -> str | None:
    """ISO code of a candidate: one specific code, else ``$`` read as USD."""

    markers = {token.currency for token in tokens if token.currency}
    specific = markers - {_DOLLAR}
    if len(specific) > 1 or (_DOLLAR in markers and specific - _DOLLAR_CODES):
        return None
    if specific:
        return specific.pop()
    return "USD" if markers else None


def _evaluate(text: str, tokens: tuple[_Token, ...]) -> Compensation | None:
    """Accept one candidate as pay, or reject it (see :func:`compensation_from_text`)."""

    start, end = tokens[0].start, tokens[-1].end
    before, after = _clause_before(text, start), _clause_after(text, end)
    currency = _currency(tokens)
    if currency is None or _MAGNITUDE_WORD.match(after):
        return None
    if len(tokens) == 1 and (_ONE_SIDED.search(before) or after.startswith("+")):
        return None
    words_after = _phrase(_PHRASE_TOKEN.findall(after))
    words_before = _phrase(_PHRASE_TOKEN.findall(before)[::-1])
    if _NOT_PAY_WORDS.intersection([*words_after, *words_before]):
        return None
    cue = _FOLLOWING_INTERVAL.match(after)
    interval = _interval(cue) or _interval(([None, *_PRECEDING_INTERVAL.finditer(before)])[-1])
    low, high = _range_values(tokens)
    if interval is None:
        has_pay_word = _PAY_WORD.search(before) or _PAY_WORD.search(" ".join(words_after[:3]))
        if not (
            has_pay_word
            and currency in IMPLICIT_ANNUAL_CURRENCIES
            and low >= IMPLICIT_ANNUAL_MINIMUM
        ):
            return None
        interval = PayInterval.YEAR
    snippet = text[start : end + (cue.end() if cue else 0)]
    return make_compensation(low, high, currency, interval, CompensationSource.DESCRIPTION, snippet)


def compensation_from_text(text: str | None) -> Compensation | None:
    """Find the pay range a posting description states, deterministically.

    Recognized: ``$120,000 - $150,000``, ``$120k-$150k`` (any dash, ``to``, or
    ``between ... and ...``), ``USD 120,000 to 150,000``, ``120.000 EUR``, ``$45/hr``,
    ``GBP``/``EUR``/``INR`` symbols and dollar prefixes such as ``CA$90K``; HTML is
    reduced to text first. An amount counts as pay only with a currency and either
    an explicit interval (``/hr``, ``per month``, ``annually``, ``p.a.``; also an
    ``Hourly rate:`` style lead-in) or a pay word before it (salary, pay,
    compensation, wage, rate, base, range...). Without an interval, an amount of at
    least 10,000 in USD, CAD, AUD, NZD, GBP, EUR or CHF is yearly; anything else is
    rejected. Rejected outright: millions/billions (``$5M Series A``, ``$1B
    revenue``), amounts next to non-pay words (stipend, bonus, budget, equity,
    funding, 401(k) match...), one-sided figures (``up to $150k``, ``from $20/hr``,
    ``$150k+``) and mixed or unknown currencies.

    When several ranges are accepted, those in the first range's currency and
    interval are combined into their widest envelope (lowest minimum, highest
    maximum), e.g. one range per office location; others are ignored.

    Args:
        text: Posting description (plain text or HTML).

    Returns:
        A ``description`` range, or None when no pay is stated unambiguously.
    """

    if not text:
        return None
    plain = _plain_text(text)
    tokens = [token for token in map(_token, _AMOUNT.finditer(plain)) if token is not None]
    accepted = [
        found
        for found in (_evaluate(plain, candidate) for candidate in _candidates(plain, tokens))
        if found is not None
    ]
    if not accepted:
        return None
    first = accepted[0]
    same = [
        item
        for item in accepted
        if item.currency == first.currency and item.interval == first.interval
    ]
    return make_compensation(
        min(item.min_amount for item in same),
        max(item.max_amount for item in same),
        first.currency,
        first.interval,
        CompensationSource.DESCRIPTION,
        " | ".join(item.snippet for item in same),
    )
