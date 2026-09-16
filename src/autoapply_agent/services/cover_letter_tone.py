"""HITL cover-letter tone aligner (offline cues; never auto-sends).

Closes the gap vs Teal / Rezi / Kickresume tone matchers locked in proprietary
UIs. This service compares a cover-letter draft against JD culture/pace cues
and returns offline tone-alignment advice for HITL edits — it never auto-sends
applications and never performs network I/O.

Distinct from ``JdCultureSignalExtractor`` (JD-only culture cues) and
``RecruiterOutreachDraftService`` (outbound recruiter drafts). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass

_TONE_BANDS: tuple[tuple[str, tuple[str, ...], tuple[str, ...], str], ...] = (
    (
        "formal",
        ("dear hiring", "respectfully", "sincerely", "pleased to submit"),
        ("enterprise", "compliance", "regulated", "governance", "stakeholder"),
        "Keep formal salutations; emphasize reliability and process discipline.",
    ),
    (
        "energetic",
        ("excited", "thrilled", "can't wait", "passionate about"),
        ("fast-paced", "move fast", "startup", "scrappy", "high growth"),
        "Keep energy cues; mirror pace language without hype inflation.",
    ),
    (
        "collaborative",
        ("cross-functional", "partner with", "team player", "collaborate"),
        ("collaborate", "cross-functional", "pair", "squad", "together"),
        "Highlight partnership examples matched to team-oriented JD cues.",
    ),
    (
        "technical",
        ("architected", "optimized", "latency", "throughput", "production"),
        ("systems", "scalability", "distributed", "infrastructure", "reliability"),
        "Lead with concrete systems impact; keep metrics visible for HITL edit.",
    ),
)


@dataclass(slots=True, frozen=True)
class ToneAlignmentMatch:
    """One tone band match with evidence from letter and JD."""

    band: str
    letter_hits: list[str]
    jd_hits: list[str]
    guidance: str


@dataclass(slots=True, frozen=True)
class CoverLetterToneReport:
    """Human-reviewable cover-letter tone alignment report."""

    matches: list[ToneAlignmentMatch]
    missing_jd_bands: list[str]
    alignment_score: float
    guidance: list[str]
    requires_human_review: bool
    auto_send: bool


class CoverLetterToneAligner:
    """Align cover-letter tone bands to JD culture/pace cues (HITL only)."""

    def align(self, cover_letter: str, job_description: str) -> CoverLetterToneReport:
        """Score cover-letter tone alignment against JD cues.

        Args:
            cover_letter: Draft cover letter body (required).
            job_description: Target JD text (required).

        Returns:
            CoverLetterToneReport with ``requires_human_review=True`` and
            ``auto_send=False``.

        Raises:
            ValueError: If either input is blank.
        """

        letter = (cover_letter or "").strip()
        jd = (job_description or "").strip()
        if not letter:
            raise ValueError("cover_letter must be a non-empty string")
        if not jd:
            raise ValueError("job_description must be a non-empty string")

        letter_l = letter.lower()
        jd_l = jd.lower()
        matches: list[ToneAlignmentMatch] = []
        missing: list[str] = []
        for band, letter_cues, jd_cues, tip in _TONE_BANDS:
            letter_hits = [cue for cue in letter_cues if cue in letter_l]
            jd_hits = [cue for cue in jd_cues if cue in jd_l]
            if jd_hits and not letter_hits:
                missing.append(band)
            if letter_hits or jd_hits:
                matches.append(
                    ToneAlignmentMatch(
                        band=band,
                        letter_hits=letter_hits,
                        jd_hits=jd_hits,
                        guidance=tip,
                    )
                )

        jd_band_count = sum(
            1 for _b, _lc, jd_cues, _t in _TONE_BANDS if any(c in jd_l for c in jd_cues)
        )
        aligned = sum(1 for m in matches if m.jd_hits and m.letter_hits)
        score = (aligned / jd_band_count) if jd_band_count else 0.0
        guidance = [m.guidance for m in matches if m.jd_hits]
        if missing:
            guidance.append(
                "Add HITL phrasing for JD bands still missing in the letter: "
                + ", ".join(missing)
                + "."
            )
        if not guidance:
            guidance.append("No strong JD tone cues found; keep letter concise for HITL review.")

        return CoverLetterToneReport(
            matches=matches,
            missing_jd_bands=missing,
            alignment_score=round(score, 3),
            guidance=guidance,
            requires_human_review=True,
            auto_send=False,
        )
