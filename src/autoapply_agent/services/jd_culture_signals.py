"""HITL JD culture-signal extractor (offline cues; never auto-applies).

Closes the gap vs Teal / LinkedIn job-insight panels that bury culture cues
inside proprietary UIs. This service scans offline JD text for pace,
collaboration, on-call, and meeting-load signals — it never auto-applies,
never contacts employers, and never performs network I/O.

Distinct from ``LocationRemoteFitScorer`` (geo/remote policy fit) and
``CompanyResearchBriefService`` (company brief synthesis). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_SIGNAL_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fast_pace", ("fast-paced", "fast paced", "high velocity", "move fast", "urgency")),
    ("oncall", ("on-call", "on call", "pager", "oncall", "incident response")),
    (
        "collaboration",
        ("cross-functional", "collaborat", "pair program", "team-oriented", "together"),
    ),
    ("meeting_load", ("meetings", "sync-heavy", "calendar", "stand-up", "standup")),
    ("autonomy", ("autonomy", "ownership", "self-directed", "end-to-end ownership")),
    ("work_life_balance", ("work-life", "work life", "flexible hours", "sustainable pace")),
)


@dataclass(slots=True, frozen=True)
class CultureSignal:
    """One extracted culture signal with evidence snippets."""

    signal: str
    evidence: list[str]


@dataclass(slots=True, frozen=True)
class CultureSignalReport:
    """Human-reviewable JD culture-signal report (never auto-applies)."""

    company: str
    role: str
    signals: list[CultureSignal]
    guidance: list[str]
    requires_human_review: bool
    auto_apply: bool


class JdCultureSignalExtractor:
    """Extract offline culture signals from JD text for HITL review."""

    def extract(
        self,
        *,
        company: str,
        role: str,
        jd_text: str,
    ) -> CultureSignalReport:
        """Extract culture cues from a job description.

        Args:
            company: Company name (required).
            role: Role title (required).
            jd_text: Job description text (required).

        Returns:
            CultureSignalReport with ``requires_human_review=True`` and
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
        signals: list[CultureSignal] = []
        for name, cues in _SIGNAL_CUES:
            hits = [cue for cue in cues if cue in lowered]
            if hits:
                signals.append(CultureSignal(signal=name, evidence=hits[:3]))

        guidance = [
            f"{cleaned_role} @ {cleaned_company}: {len(signals)} culture signal(s) found.",
            "requires_human_review=True; auto_apply=False — never auto-applies.",
            "Treat cues as hypotheses; confirm in interviews before deciding.",
        ]
        if not signals:
            guidance.append("No strong cues matched — ask about pace/on-call in screening.")
        return CultureSignalReport(
            company=cleaned_company,
            role=cleaned_role,
            signals=signals,
            guidance=guidance,
            requires_human_review=True,
            auto_apply=False,
        )
