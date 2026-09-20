"""HITL non-compete restrictiveness flagger (offline; never auto-accepts).

Closes the gap vs Blind / Levels.fyi / Candor offer reviews that leave
non-compete severity buried in closed UIs. Scans offer/agreement text for
duration, geography, and garden-leave cues — never auto-accepts and never
performs network I/O.

Distinct from ``VisaSponsorshipSignalExtractor`` (work-auth cues) and
``JdCultureSignalExtractor`` (culture pace cues). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_DURATION = re.compile(
    r"\b(?:non[- ]?compete|noncompete).{0,40}?(?:for\s+)?(\d{1,2})\s*(?:month|months|year|years)\b|"
    r"\b(\d{1,2})\s*(?:month|months|year|years).{0,20}?non[- ]?compete\b",
    re.IGNORECASE,
)
_GEO = re.compile(
    r"\b(?:worldwide|anywhere|global|nationwide|within\s+\d+\s*(?:miles?|km))\b",
    re.IGNORECASE,
)
_GARDEN = re.compile(r"\bgarden\s*leave\b|\bpaid\s+garden\b", re.IGNORECASE)
_NONCOMPETE = re.compile(
    r"\bnon[- ]?compete\b|\bnoncompete\b|\brestrictive\s+covenant\b",
    re.IGNORECASE,
)


@dataclass(slots=True, frozen=True)
class NonCompeteRestrictivenessReport:
    """Human-reviewable non-compete restrictiveness report."""

    duration_months: int | None
    geography_cues: tuple[str, ...]
    has_garden_leave: bool
    restrictiveness_band: str
    matched: tuple[str, ...]
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class NonCompeteRestrictivenessFlagger:
    """Flag non-compete restrictiveness cues from offer/agreement text."""

    def flag(self, text: str) -> NonCompeteRestrictivenessReport:
        """Scan ``text`` for non-compete restrictiveness cues.

        Args:
            text: Offer letter / agreement excerpt.

        Returns:
            NonCompeteRestrictivenessReport with ``auto_accept=False``.

        Raises:
            ValueError: When ``text`` is empty/whitespace.
        """

        body = text.strip()
        if not body:
            raise ValueError("text must be non-empty")

        matched: list[str] = []
        duration_months: int | None = None
        dur = _DURATION.search(body)
        if dur:
            matched.append(dur.group(0).strip())
            raw = dur.group(1) or dur.group(2)
            if raw is not None:
                value = int(raw)
                # Treat bare "year(s)" matches as months*12 when unit says year.
                unit_span = dur.group(0).lower()
                if "year" in unit_span:
                    duration_months = value * 12
                else:
                    duration_months = value

        geo_cues: list[str] = []
        for geo in _GEO.finditer(body):
            cue = geo.group(0).strip()
            geo_cues.append(cue)
            matched.append(cue)

        has_garden = bool(_GARDEN.search(body))
        if has_garden:
            matched.append("garden leave")

        has_nc = bool(_NONCOMPETE.search(body))
        if has_nc and not any("non" in m.lower() for m in matched):
            matched.append("non-compete")

        months = duration_months or 0
        wide_geo = any(
            g.lower() in {"worldwide", "anywhere", "global", "nationwide"} for g in geo_cues
        )
        if not has_nc and duration_months is None:
            band = "none_detected"
        elif months >= 24 or (months >= 12 and wide_geo):
            band = "highly_restrictive"
        elif months >= 12 or wide_geo:
            band = "moderately_restrictive"
        elif has_nc:
            band = "mildly_restrictive"
        else:
            band = "none_detected"

        guidance = [
            "Non-compete cues are advisory; have counsel review enforceability.",
            "Do not auto-accept from this flagger.",
        ]
        if band == "highly_restrictive":
            guidance.append("Long duration and/or broad geography — negotiate carve-outs.")
        elif band == "none_detected":
            guidance.append("No clear non-compete cues found in the provided excerpt.")
        if has_garden:
            guidance.append("Garden leave noted; confirm pay and restricted activities.")

        return NonCompeteRestrictivenessReport(
            duration_months=duration_months,
            geography_cues=tuple(geo_cues),
            has_garden_leave=has_garden,
            restrictiveness_band=band,
            matched=tuple(matched),
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )
