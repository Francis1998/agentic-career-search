"""HITL remote timezone-overlap advisor (offline; never auto-applies).

Closes the gap vs RemoteOK / FlexJobs / We Work Remotely timezone-filter UIs
locked behind proprietary boards. Computes weekday overlap hours between a
candidate IANA-like UTC offset and a team core window — never auto-applies
and never performs network I/O.

Distinct from ``LocationRemoteFitScorer`` (geo/remote policy fit) and
``InterviewScheduleConflictGuard`` (calendar slot collisions). Optional later
polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TimezoneOverlapReport:
    """Human-reviewable remote timezone overlap report."""

    candidate_utc_offset_hours: float
    team_core_start_local: float
    team_core_end_local: float
    overlap_hours: float
    overlap_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_apply: bool


class RemoteTimezoneOverlapAdvisor:
    """Advise weekday overlap between candidate offset and team core hours."""

    def advise(
        self,
        *,
        candidate_utc_offset_hours: float,
        team_core_start_local: float = 9.0,
        team_core_end_local: float = 17.0,
        team_utc_offset_hours: float = 0.0,
        candidate_day_start: float = 8.0,
        candidate_day_end: float = 20.0,
    ) -> TimezoneOverlapReport:
        """Compute overlap hours in a shared UTC frame.

        Args:
            candidate_utc_offset_hours: Candidate offset from UTC (e.g. -8.0).
            team_core_start_local: Team core window start in team-local hours.
            team_core_end_local: Team core window end in team-local hours.
            team_utc_offset_hours: Team offset from UTC.
            candidate_day_start: Candidate available start (candidate-local).
            candidate_day_end: Candidate available end (candidate-local).

        Returns:
            TimezoneOverlapReport with ``auto_apply=False``.

        Raises:
            ValueError: On invalid windows or offsets outside [-14, 14].
        """

        for name, value in (
            ("candidate_utc_offset_hours", candidate_utc_offset_hours),
            ("team_utc_offset_hours", team_utc_offset_hours),
        ):
            if value < -14 or value > 14:
                raise ValueError(f"{name} must be within [-14, 14]")
        if team_core_end_local <= team_core_start_local:
            raise ValueError("team_core_end_local must be > team_core_start_local")
        if candidate_day_end <= candidate_day_start:
            raise ValueError("candidate_day_end must be > candidate_day_start")

        # Convert local windows to UTC hours on a notional day [0, 24).
        team_start_utc = (team_core_start_local - team_utc_offset_hours) % 24
        team_end_utc = (team_core_end_local - team_utc_offset_hours) % 24
        cand_start_utc = (candidate_day_start - candidate_utc_offset_hours) % 24
        cand_end_utc = (candidate_day_end - candidate_utc_offset_hours) % 24

        def _to_segments(start: float, end: float) -> list[tuple[float, float]]:
            if start <= end:
                return [(start, end)]
            return [(start, 24.0), (0.0, end)]

        team_segs = _to_segments(team_start_utc, team_end_utc)
        cand_segs = _to_segments(cand_start_utc, cand_end_utc)
        overlap = 0.0
        for ts, te in team_segs:
            for cs, ce in cand_segs:
                lo = max(ts, cs)
                hi = min(te, ce)
                if hi > lo:
                    overlap += hi - lo
        overlap = round(overlap, 2)

        if overlap >= 6.0:
            band = "strong"
        elif overlap >= 3.0:
            band = "moderate"
        elif overlap > 0:
            band = "thin"
        else:
            band = "none"

        guidance = [
            "Timezone overlap is advisory; a human decides remote fit.",
            "Do not auto-apply from this advisor.",
        ]
        if band in {"thin", "none"}:
            guidance.append("Consider async-heavy teams or renegotiating core-hours expectations.")
        if band == "strong":
            guidance.append("Solid weekday overlap — still confirm on-call / stand-up times.")

        return TimezoneOverlapReport(
            candidate_utc_offset_hours=float(candidate_utc_offset_hours),
            team_core_start_local=float(team_core_start_local),
            team_core_end_local=float(team_core_end_local),
            overlap_hours=overlap,
            overlap_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_apply=False,
        )
