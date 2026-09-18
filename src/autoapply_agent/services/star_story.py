"""HITL STAR behavioral story matcher (offline cues; never auto-sends).

Closes the gap vs Interviewing.io / Exponent / Teal behavioral-bank matchers
locked in proprietary UIs. Matches a local STAR story bank to JD competency
cues for HITL interview rehearsal — never auto-sends answers and never
performs network I/O.

Distinct from ``InterviewPrepBriefService`` (generic STAR prompts) and
``PhoneScreenAgendaPlanner`` (minute agenda). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_COMPETENCY_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "leadership",
        ("lead", " mentored", "owned", "drove", "stakeholder", "cross-functional"),
    ),
    (
        "conflict",
        ("conflict", "disagreement", "pushback", "negotiat", "escalat"),
    ),
    (
        "delivery",
        ("deadline", "shipped", "delivered", "launch", "on time", "milestone"),
    ),
    (
        "incident",
        ("incident", "outage", "on-call", "oncall", "pager", "postmortem", "root cause"),
    ),
    (
        "growth",
        ("learned", " mentorship", "feedback", "improved", "upskill", "coached"),
    ),
)


@dataclass(slots=True, frozen=True)
class StarStory:
    """One STAR story in the candidate bank."""

    story_id: str
    situation: str
    task: str
    action: str
    result: str
    tags: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class StarStoryMatch:
    """One story matched to a JD competency cue."""

    story_id: str
    competency: str
    score: float
    evidence: list[str]
    rehearsal_prompt: str


@dataclass(slots=True, frozen=True)
class StarStoryMatchPlan:
    """Human-reviewable STAR match plan."""

    matches: list[StarStoryMatch]
    uncovered_competencies: list[str]
    guidance: list[str]
    requires_human_review: bool
    auto_send: bool


class StarBehavioralStoryMatcher:
    """Match a STAR story bank to JD competency cues (HITL only)."""

    def match(
        self,
        job_description: str,
        stories: list[StarStory],
        *,
        top_k: int = 3,
    ) -> StarStoryMatchPlan:
        """Return ranked STAR matches for JD competency cues.

        Args:
            job_description: Target JD text (required).
            stories: Candidate STAR story bank (may be empty).
            top_k: Maximum matches to return (default 3).

        Returns:
            StarStoryMatchPlan with ``requires_human_review=True`` and
            ``auto_send=False``.

        Raises:
            ValueError: If JD blank or top_k < 1.
        """

        jd = (job_description or "").strip()
        if not jd:
            raise ValueError("job_description must be a non-empty string")
        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        lowered = jd.lower()
        needed: list[tuple[str, list[str]]] = []
        for competency, cues in _COMPETENCY_CUES:
            hits = [cue.strip() for cue in cues if cue.strip() in lowered]
            if hits:
                needed.append((competency, hits))

        if not needed:
            needed.append(("general_fit", ["general"]))

        scored: list[StarStoryMatch] = []
        covered: set[str] = set()
        for story in stories:
            blob = " ".join(
                [
                    story.situation,
                    story.task,
                    story.action,
                    story.result,
                    " ".join(story.tags),
                ]
            ).lower()
            for competency, evidence in needed:
                tag_hit = competency in {tag.lower() for tag in story.tags}
                cue_hits = [cue for cue in evidence if cue != "general" and cue in blob]
                if not tag_hit and not cue_hits and competency != "general_fit":
                    continue
                score = 0.35 if tag_hit else 0.0
                score += min(0.65, 0.2 * len(cue_hits))
                if competency == "general_fit":
                    score = max(score, 0.25)
                if score <= 0:
                    continue
                covered.add(competency)
                scored.append(
                    StarStoryMatch(
                        story_id=story.story_id,
                        competency=competency,
                        score=round(score, 3),
                        evidence=cue_hits or list(story.tags[:3]),
                        rehearsal_prompt=(
                            f"Rehearse {story.story_id} for {competency}: "
                            "Situation→Task→Action→Result in under 90s; "
                            "never auto-send answers."
                        ),
                    )
                )

        scored.sort(key=lambda item: (-item.score, item.story_id, item.competency))
        matches = scored[:top_k]
        uncovered = [comp for comp, _ev in needed if comp not in covered]
        guidance = [
            "Ranked STAR matches are advisory; rehearse aloud in HITL review.",
            "Do not auto-send interview answers from this matcher.",
        ]
        if uncovered:
            guidance.append(
                "Uncovered competencies: " + ", ".join(uncovered) + " — draft new STAR stories."
            )
        if not stories:
            guidance.append("Story bank empty — add at least one STAR story before looping.")

        return StarStoryMatchPlan(
            matches=matches,
            uncovered_competencies=uncovered,
            guidance=guidance,
            requires_human_review=True,
            auto_send=False,
        )
