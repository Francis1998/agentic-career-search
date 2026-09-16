"""HITL phone-screen agenda planner (offline cues; never auto-books).

Closes the gap vs Interviewing.io / Exponent / Teal phone-screen prep locked
in proprietary UIs. This service builds an offline phone-screen agenda from JD
signals for HITL rehearsal — it never auto-books calendars and never performs
network I/O.

Distinct from ``InterviewPrepBriefService`` (broader interview briefs) and
``InterviewScheduleConflictGuard`` (slot overlap detection). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_AGENDA_CUES: tuple[tuple[str, tuple[str, ...], str, int], ...] = (
    (
        "role_fit",
        ("responsibilities", "you will", "own", "accountable"),
        "Clarify role scope and top 2 success metrics for month 1-3.",
        5,
    ),
    (
        "stack_depth",
        ("python", "java", "typescript", "kubernetes", "aws", "gcp", "react"),
        "Prepare one production story per primary stack keyword in the JD.",
        8,
    ),
    (
        "collaboration",
        ("cross-functional", "stakeholders", "partner", "squad", "team"),
        "Ready a collaboration example with conflict resolution notes.",
        5,
    ),
    (
        "oncall_ops",
        ("on-call", "oncall", "pager", "sla", "incident"),
        "Discuss ops maturity questions; do not invent incident history.",
        4,
    ),
    (
        "comp_logistics",
        ("salary", "compensation", "hybrid", "remote", "relocation"),
        "List logistics questions for HITL; never negotiate automatically.",
        3,
    ),
)


@dataclass(slots=True, frozen=True)
class PhoneScreenAgendaItem:
    """One phone-screen agenda block."""

    topic: str
    minutes: int
    prompt: str
    evidence: list[str]


@dataclass(slots=True, frozen=True)
class PhoneScreenAgendaPlan:
    """Human-reviewable phone-screen agenda plan."""

    items: list[PhoneScreenAgendaItem]
    total_minutes: int
    guidance: list[str]
    requires_human_review: bool
    auto_book: bool


class PhoneScreenAgendaPlanner:
    """Build an offline phone-screen agenda from JD cues (HITL only)."""

    def plan(self, job_description: str, *, target_minutes: int = 30) -> PhoneScreenAgendaPlan:
        """Plan a phone-screen agenda from JD text.

        Args:
            job_description: Target JD text (required).
            target_minutes: Soft total minutes budget (default 30).

        Returns:
            PhoneScreenAgendaPlan with ``requires_human_review=True`` and
            ``auto_book=False``.

        Raises:
            ValueError: If JD blank or target_minutes < 10.
        """

        jd = (job_description or "").strip()
        if not jd:
            raise ValueError("job_description must be a non-empty string")
        if target_minutes < 10:
            raise ValueError("target_minutes must be >= 10")

        lowered = jd.lower()
        items: list[PhoneScreenAgendaItem] = []
        for topic, cues, prompt, minutes in _AGENDA_CUES:
            hits = [cue for cue in cues if cue in lowered]
            if hits:
                items.append(
                    PhoneScreenAgendaItem(
                        topic=topic,
                        minutes=minutes,
                        prompt=prompt,
                        evidence=hits,
                    )
                )

        if not items:
            items.append(
                PhoneScreenAgendaItem(
                    topic="general_fit",
                    minutes=10,
                    prompt="Walk motivation + recent win; ask clarifying scope questions.",
                    evidence=[],
                )
            )

        # Always include a closing block for HITL.
        items.append(
            PhoneScreenAgendaItem(
                topic="candidate_questions",
                minutes=5,
                prompt="Ask 2-3 thoughtful questions; never auto-send follow-ups.",
                evidence=[],
            )
        )

        total = sum(item.minutes for item in items)
        guidance = [
            (
                f"Planned ~{total} minutes vs target {target_minutes}; "
                "trim lower-priority blocks in HITL review."
            ),
            "Rehearse aloud; do not auto-book calendar holds from this planner.",
        ]
        if total > target_minutes:
            guidance.append(
                "Over target — drop or shorten the lowest-priority topic before the call."
            )

        return PhoneScreenAgendaPlan(
            items=items,
            total_minutes=total,
            guidance=guidance,
            requires_human_review=True,
            auto_book=False,
        )
