"""HITL negotiation talking-points service (comp counter-offer drafts).

Closes the gap vs Levels.fyi / Blind threads and Teal offer trackers that leave
candidates to improvise counter-offers. This service only builds offline talking
points for human review — it never submits counters, never emails recruiters,
and never performs network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NegotiationTalkingPoints:
    """Human-reviewable compensation negotiation talking points (never auto-sent)."""

    company: str
    role: str
    current_total_usd: int
    target_total_usd: int
    talking_points: list[str]
    risks: list[str]
    requires_human_review: bool


class NegotiationTalkingPointsService:
    """Generate offline compensation counter-offer talking points for HITL review."""

    def generate(
        self,
        *,
        company: str,
        role: str,
        current_total_usd: int,
        target_total_usd: int,
        leverage_notes: str | None = None,
    ) -> NegotiationTalkingPoints:
        """Build structured negotiation talking points without sending or networking.

        Args:
            company: Offering company (required).
            role: Role title (required for coherent framing).
            current_total_usd: Current total-comp offer in USD (must be > 0).
            target_total_usd: Candidate target total-comp in USD (must be > current).
            leverage_notes: Optional leverage context (competing offer, impact, etc.).

        Returns:
            NegotiationTalkingPoints with ``requires_human_review=True``.

        Raises:
            ValueError: If company blank, amounts invalid, or target <= current.
        """

        cleaned_company = (company or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")

        if not isinstance(current_total_usd, int) or isinstance(current_total_usd, bool):
            raise ValueError("current_total_usd must be a positive int")
        if current_total_usd <= 0:
            raise ValueError("current_total_usd must be a positive int")

        if not isinstance(target_total_usd, int) or isinstance(target_total_usd, bool):
            raise ValueError("target_total_usd must be an int greater than current_total_usd")
        if target_total_usd <= current_total_usd:
            raise ValueError("target_total_usd must be an int greater than current_total_usd")

        cleaned_role = (role or "").strip() or "the open role"
        delta = target_total_usd - current_total_usd
        pct = round(100.0 * delta / current_total_usd, 1)
        note = (leverage_notes or "").strip()

        talking_points = [
            f"Thank {cleaned_company} for the {cleaned_role} offer at "
            f"${current_total_usd:,} total.",
            f"Request a total-comp adjustment toward ${target_total_usd:,} "
            f"(+${delta:,} / +{pct}%).",
            "Anchor on scope, impact, and market data — not personal expenses.",
            "Prefer a written counter; do not auto-send (human review required).",
        ]
        if note:
            talking_points.append(f"Leverage note for human edit: {note}")

        risks = [
            "Verbal counters can drift; keep a written record.",
            "Do not invent competing offers — only cite real leverage.",
            "Optional polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 "
            "must stay advisory.",
        ]

        return NegotiationTalkingPoints(
            company=cleaned_company,
            role=cleaned_role,
            current_total_usd=current_total_usd,
            target_total_usd=target_total_usd,
            talking_points=talking_points,
            risks=risks,
            requires_human_review=True,
        )
