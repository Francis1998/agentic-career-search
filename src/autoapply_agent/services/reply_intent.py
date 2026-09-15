"""HITL recruiter-reply intent classifier (offline cues; never auto-sends).

Closes the gap vs Teal / Huntr / Superhuman inbox labels that keep recruiter
reply intent inside proprietary UIs. This service classifies offline recruiter
email/LinkedIn reply text into interested / scheduling / rejection / nurture
intents for HITL next actions — it never auto-sends replies and never performs
network I/O.

Distinct from ``RecruiterOutreachDraftService`` (outbound drafts) and
``ApplicationFollowUpCadencePlanner`` (follow-up schedule). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_INTENT_CUES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "interested",
        (
            "excited to move forward",
            "impressed with your",
            "great fit",
            "would love to chat",
            "next steps",
            "interested in speaking",
        ),
        "Prepare availability and a concise role-fit summary for HITL reply.",
    ),
    (
        "scheduling",
        (
            "schedule",
            "calendar",
            "availability",
            "time slots",
            "book a time",
            "15 minutes",
            "30 minutes",
            "zoom",
            "phone screen",
        ),
        "Propose 2-3 concrete time windows; do not auto-book calendars.",
    ),
    (
        "rejection",
        (
            "not moving forward",
            "other candidates",
            "decided to proceed with",
            "unfortunately",
            "not a fit",
            "role has been filled",
        ),
        "Log rejection theme and keep rapport warm for future roles.",
    ),
    (
        "nurture",
        (
            "keeping your resume",
            "talent community",
            "reach out when",
            "future opportunities",
            "stay in touch",
        ),
        "Add a 60-90 day nurture reminder; do not spam follow-ups.",
    ),
)


@dataclass(slots=True, frozen=True)
class ReplyIntentMatch:
    """One classified recruiter-reply intent with evidence."""

    intent: str
    evidence: list[str]
    suggested_action: str


@dataclass(slots=True, frozen=True)
class ReplyIntentReport:
    """Human-reviewable recruiter-reply intent report (never auto-sends)."""

    intents: list[ReplyIntentMatch]
    uncategorized: bool
    guidance: list[str]
    requires_human_review: bool
    auto_send: bool


class RecruiterReplyIntentClassifier:
    """Classify offline recruiter reply text into HITL intents."""

    def classify(self, reply_text: str) -> ReplyIntentReport:
        """Classify recruiter reply intent from free text.

        Args:
            reply_text: Recruiter email/LinkedIn reply body (required).

        Returns:
            ReplyIntentReport with ``requires_human_review=True`` and
            ``auto_send=False``.

        Raises:
            ValueError: If ``reply_text`` is blank.
        """

        cleaned = (reply_text or "").strip()
        if not cleaned:
            raise ValueError("reply_text must be a non-empty string")

        lowered = cleaned.lower()
        intents: list[ReplyIntentMatch] = []
        for name, cues, action in _INTENT_CUES:
            hits = [cue for cue in cues if cue in lowered]
            if hits:
                intents.append(
                    ReplyIntentMatch(
                        intent=name,
                        evidence=hits[:3],
                        suggested_action=action,
                    )
                )

        guidance = [
            f"Classified {len(intents)} intent(s) from recruiter reply.",
            "requires_human_review=True; auto_send=False — never auto-sends replies.",
            "Confirm tone before responding; intents are heuristic hypotheses.",
        ]
        if not intents:
            guidance.append("No strong intent cues — draft a clarifying HITL reply manually.")
        return ReplyIntentReport(
            intents=intents,
            uncategorized=not intents,
            guidance=guidance,
            requires_human_review=True,
            auto_send=False,
        )
