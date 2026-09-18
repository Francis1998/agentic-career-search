"""HITL application packet completeness gate (offline; never auto-submits).

Closes the gap vs Teal / Huntr / Simplify packet checklists locked in closed
CRMs. Validates that resume, cover letter, and optional portfolio/referral
artifacts are present before a human submits — never auto-submits and never
performs network I/O.

Distinct from ``ApplicationDraftService`` (draft generation) and
``AtsKeywordCoverageScorer`` (keyword coverage). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PacketArtifact:
    """One application packet artifact."""

    name: str
    present: bool
    required: bool
    notes: str = ""


@dataclass(slots=True, frozen=True)
class PacketCompletenessReport:
    """Human-reviewable packet completeness report."""

    artifacts: list[PacketArtifact]
    missing_required: list[str]
    completeness_score: float
    ready_for_human_submit: bool
    guidance: list[str]
    requires_human_review: bool
    auto_submit: bool


class ApplicationPacketCompletenessGate:
    """Gate application packets on required local artifacts (HITL only)."""

    _DEFAULT_REQUIRED = ("resume", "cover_letter")

    def evaluate(
        self,
        *,
        resume_text: str = "",
        cover_letter_text: str = "",
        portfolio_url: str = "",
        referral_note: str = "",
        require_portfolio: bool = False,
        require_referral: bool = False,
    ) -> PacketCompletenessReport:
        """Evaluate whether the packet has required artifacts.

        Args:
            resume_text: Resume body (non-blank counts as present).
            cover_letter_text: Cover letter body.
            portfolio_url: Optional portfolio link text.
            referral_note: Optional referral / warm-intro note.
            require_portfolio: When True, portfolio_url is required.
            require_referral: When True, referral_note is required.

        Returns:
            PacketCompletenessReport with ``auto_submit=False``.

        Raises:
            ValueError: Never raised for blank optional fields; reserved for
                invalid flag combinations (none today).
        """

        artifacts = [
            PacketArtifact(
                name="resume",
                present=bool(resume_text.strip()),
                required=True,
                notes="Primary resume body",
            ),
            PacketArtifact(
                name="cover_letter",
                present=bool(cover_letter_text.strip()),
                required=True,
                notes="Role-specific cover letter",
            ),
            PacketArtifact(
                name="portfolio",
                present=bool(portfolio_url.strip()),
                required=require_portfolio,
                notes="Portfolio / project link",
            ),
            PacketArtifact(
                name="referral",
                present=bool(referral_note.strip()),
                required=require_referral,
                notes="Referral or warm-intro note",
            ),
        ]

        missing = [item.name for item in artifacts if item.required and not item.present]
        required_total = sum(1 for item in artifacts if item.required)
        present_required = required_total - len(missing)
        score = (present_required / required_total) if required_total else 1.0
        ready = len(missing) == 0
        guidance = [
            "Completeness is advisory; a human must submit the packet.",
            "Do not auto-submit applications from this gate.",
        ]
        if missing:
            guidance.append("Missing required: " + ", ".join(missing))
        else:
            guidance.append("Required artifacts present — proceed to HITL submit review.")

        return PacketCompletenessReport(
            artifacts=artifacts,
            missing_required=missing,
            completeness_score=round(score, 3),
            ready_for_human_submit=ready,
            guidance=guidance,
            requires_human_review=True,
            auto_submit=False,
        )
