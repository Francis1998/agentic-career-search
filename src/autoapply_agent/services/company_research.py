"""Company research brief generator for HITL triage.

Produces a deterministic, offline company brief from the company name and
optional job text - closing the gap vs Teal/Levels.fyi company pages that are
UI-only, and vs OpenHands agents that invent company facts without a stable
structure. Never fetches the network; humans must verify before outreach.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)

_SIGNAL_HINTS: tuple[tuple[str, str], ...] = (
    ("remote", "Mentions remote / distributed work"),
    ("hybrid", "Mentions hybrid work model"),
    ("onsite", "Mentions on-site expectations"),
    ("startup", "Signals early-stage / startup context"),
    ("series", "May reference funding stage in JD text"),
    ("enterprise", "Signals enterprise customer focus"),
    ("b2b", "Signals B2B go-to-market"),
    ("b2c", "Signals B2C go-to-market"),
    ("healthcare", "Healthcare / life-sciences domain signal"),
    ("fintech", "Fintech domain signal"),
    ("security", "Security-sensitive domain signal"),
    ("ai", "AI / ML product signal"),
    ("open-source", "Open-source engagement signal"),
    ("opensource", "Open-source engagement signal"),
)


@dataclass(slots=True, frozen=True)
class CompanyResearchBrief:
    """Deterministic company research brief for human review."""

    company: str
    one_liner: str
    talking_points: list[str]
    jd_signals: list[str]
    open_questions: list[str]
    requires_human_review: bool


class CompanyResearchBriefService:
    """Generate offline company research briefs for HITL review."""

    def generate(
        self,
        *,
        company: str,
        job_title: str | None = None,
        job_text: str | None = None,
    ) -> CompanyResearchBrief:
        """Build a structured company brief without network access.

        Args:
            company: Company name (required).
            job_title: Optional target role title.
            job_text: Optional job description for signal extraction.

        Returns:
            CompanyResearchBrief with talking points and open questions.
            Always sets ``requires_human_review=True``.

        Raises:
            ValueError: If company is empty/blank.
        """

        cleaned = (company or "").strip()
        if not cleaned:
            raise ValueError("company must be a non-empty string")

        title = (job_title or "").strip()
        text = job_text or ""
        tokens = {token.lower() for token in _WORD_RE.findall(text)}

        signals: list[str] = []
        for needle, label in _SIGNAL_HINTS:
            parts = needle.split("-")
            if all(part in tokens for part in parts):
                if label not in signals:
                    signals.append(label)

        one_liner = (
            f"Assistive brief for {cleaned}"
            + (f" targeting '{title}'" if title else "")
            + ". Facts below are heuristics from the JD text only - verify before outreach."
        )

        talking_points = [
            f"Confirm what {cleaned} ships (product vs services) via official site / LinkedIn.",
            "Identify the hiring team's org (engineering, product, GTM) from the JD.",
        ]
        if title:
            talking_points.append(
                f"Map '{title}' responsibilities to 2-3 concrete outcomes you can discuss."
            )
        if signals:
            talking_points.append("JD signals worth validating: " + "; ".join(signals[:3]) + ".")
        else:
            talking_points.append(
                "JD text had few domain signals - ask the recruiter about product stage and stack."
            )

        open_questions = [
            f"What is {cleaned}'s primary customer segment today?",
            "How is success measured for this role in the first 90 days?",
            "Which competitors or alternatives does the team compare against?",
        ]
        if "remote" in tokens or "hybrid" in tokens:
            open_questions.append("What is the expected timezone overlap / office cadence?")

        return CompanyResearchBrief(
            company=cleaned,
            one_liner=one_liner,
            talking_points=talking_points,
            jd_signals=signals,
            open_questions=open_questions,
            requires_human_review=True,
        )
