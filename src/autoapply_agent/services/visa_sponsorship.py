"""HITL visa-sponsorship signal extractor (offline JD cues; never auto-applies).

Closes the gap vs Simplify / Teal / LinkedIn job boards that bury work-auth and
visa-sponsorship signals inside proprietary filters. This service scans offline
JD text for sponsorship, citizenship-only, and visa-transfer cues — it never
auto-applies, never contacts employers, and never performs network I/O.

Distinct from ``JdCultureSignalExtractor`` (culture/pace cues) and
``LocationRemoteFitScorer`` (geo/remote policy). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_SIGNAL_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "sponsors_visa",
        (
            "visa sponsorship",
            "sponsor visas",
            "sponsorship available",
            "will sponsor",
            "h-1b",
            "h1b",
            "h1-b",
            "work authorization sponsorship",
        ),
    ),
    (
        "citizenship_required",
        (
            "us citizen",
            "u.s. citizen",
            "citizens only",
            "must be a citizen",
            "security clearance",
            "clearance required",
        ),
    ),
    (
        "no_sponsorship",
        (
            "no sponsorship",
            "not sponsor",
            "unable to sponsor",
            "cannot sponsor",
            "without sponsorship",
            "must already be authorized",
        ),
    ),
    (
        "visa_transfer_ok",
        (
            "visa transfer",
            "transfer existing visa",
            "cap-exempt",
            "cap exempt",
            "change of employer",
        ),
    ),
)


@dataclass(slots=True, frozen=True)
class VisaSponsorshipSignal:
    """One extracted work-auth / sponsorship signal with evidence snippets."""

    signal: str
    evidence: list[str]


@dataclass(slots=True, frozen=True)
class VisaSponsorshipReport:
    """Human-reviewable visa-sponsorship report (never auto-applies)."""

    company: str
    role: str
    signals: list[VisaSponsorshipSignal]
    guidance: list[str]
    requires_human_review: bool
    auto_apply: bool


class VisaSponsorshipSignalExtractor:
    """Extract offline visa/work-auth cues from JD text for HITL review."""

    def extract(
        self,
        *,
        company: str,
        role: str,
        jd_text: str,
    ) -> VisaSponsorshipReport:
        """Extract visa sponsorship cues from a job description.

        Args:
            company: Company name (required).
            role: Role title (required).
            jd_text: Job description text (required).

        Returns:
            VisaSponsorshipReport with ``requires_human_review=True`` and
            ``auto_apply=False``.

        Raises:
            ValueError: If required fields are blank.
        """

        cleaned_company = (company or "").strip()
        cleaned_role = (role or "").strip()
        cleaned_jd = (jd_text or "").strip()
        if not cleaned_company:
            raise ValueError("company must be a non-empty string")
        if not cleaned_role:
            raise ValueError("role must be a non-empty string")
        if not cleaned_jd:
            raise ValueError("jd_text must be a non-empty string")

        lowered = cleaned_jd.lower()
        signals: list[VisaSponsorshipSignal] = []
        for name, cues in _SIGNAL_CUES:
            hits = [cue for cue in cues if cue in lowered]
            if hits:
                signals.append(VisaSponsorshipSignal(signal=name, evidence=hits[:3]))

        guidance = [
            f"{cleaned_role} @ {cleaned_company}: {len(signals)} visa/work-auth signal(s).",
            "requires_human_review=True; auto_apply=False — never auto-applies.",
            "Confirm sponsorship policy with the recruiter before investing time.",
        ]
        if not signals:
            guidance.append("No explicit visa cues — ask about work authorization in screening.")
        conflicting = {item.signal for item in signals}
        if "sponsors_visa" in conflicting and "no_sponsorship" in conflicting:
            guidance.append("Conflicting cues detected — treat as high-priority HITL check.")
        return VisaSponsorshipReport(
            company=cleaned_company,
            role=cleaned_role,
            signals=signals,
            guidance=guidance,
            requires_human_review=True,
            auto_apply=False,
        )
