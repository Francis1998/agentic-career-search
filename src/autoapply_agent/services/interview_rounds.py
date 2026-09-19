"""HITL interview-round progress tracker (offline; never auto-advances).

Closes the gap vs Huntr / Teal / Jobtracker multi-round pipeline boards locked
in closed CRMs. Tracks explicit round transitions
(``phone_screen → hiring_manager → onsite → offer``) with allowed edges —
never auto-advances candidates and never performs network I/O.

Distinct from ``ApplicationStageTracker`` (saved/applied/interview/offer CRM
stages) and ``PhoneScreenAgendaPlanner`` (single-screen agendas). Optional
later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay
advisory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_ALLOWED: dict[str, frozenset[str]] = {
    "phone_screen": frozenset({"hiring_manager", "rejected", "withdrawn"}),
    "hiring_manager": frozenset({"onsite", "rejected", "withdrawn"}),
    "onsite": frozenset({"offer", "rejected", "withdrawn"}),
    "offer": frozenset({"accepted", "declined", "withdrawn"}),
    "rejected": frozenset(),
    "withdrawn": frozenset(),
    "accepted": frozenset(),
    "declined": frozenset(),
}

_START = "phone_screen"


@dataclass(slots=True)
class InterviewRoundSnapshot:
    """Current interview-round pipeline snapshot."""

    application_id: str
    round_name: str
    history: list[str] = field(default_factory=list)
    terminal: bool = False
    requires_human_review: bool = True
    auto_advance: bool = False


class InterviewRoundProgressTracker:
    """Track multi-round interview progress with explicit allowed transitions."""

    def __init__(self) -> None:
        """Create an empty in-memory round tracker."""

        self._rounds: dict[str, InterviewRoundSnapshot] = {}

    def start(self, application_id: str) -> InterviewRoundSnapshot:
        """Start tracking at ``phone_screen``.

        Args:
            application_id: Non-empty application identifier.

        Returns:
            InterviewRoundSnapshot at phone_screen.

        Raises:
            ValueError: If ``application_id`` blank or already tracked.
        """

        app_id = (application_id or "").strip()
        if not app_id:
            raise ValueError("application_id must be a non-empty string")
        if app_id in self._rounds:
            raise ValueError(f"application_id already tracked: {app_id}")
        snap = InterviewRoundSnapshot(
            application_id=app_id,
            round_name=_START,
            history=[_START],
        )
        self._rounds[app_id] = snap
        return snap

    def advance(self, application_id: str, next_round: str) -> InterviewRoundSnapshot:
        """Advance to ``next_round`` when the edge is allowed.

        Args:
            application_id: Tracked application id.
            next_round: Target round name.

        Returns:
            Updated InterviewRoundSnapshot (``auto_advance=False``).

        Raises:
            ValueError: On unknown id, blank next_round, or illegal transition.
        """

        app_id = (application_id or "").strip()
        nxt = (next_round or "").strip().lower()
        if not app_id:
            raise ValueError("application_id must be a non-empty string")
        if not nxt:
            raise ValueError("next_round must be a non-empty string")
        snap = self._rounds.get(app_id)
        if snap is None:
            raise ValueError(f"unknown application_id: {app_id}")
        if snap.terminal:
            raise ValueError(f"application_id already terminal: {app_id}")
        allowed = _ALLOWED.get(snap.round_name, frozenset())
        if nxt not in allowed:
            raise ValueError(
                f"illegal transition {snap.round_name!r} -> {nxt!r}; allowed={sorted(allowed)}"
            )
        snap.round_name = nxt
        snap.history.append(nxt)
        snap.terminal = nxt in {"rejected", "withdrawn", "accepted", "declined"}
        snap.auto_advance = False
        snap.requires_human_review = True
        return snap

    def get(self, application_id: str) -> InterviewRoundSnapshot | None:
        """Return snapshot for ``application_id``, or ``None``."""

        app_id = (application_id or "").strip()
        if not app_id:
            raise ValueError("application_id must be a non-empty string")
        return self._rounds.get(app_id)
