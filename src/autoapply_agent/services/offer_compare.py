"""Offline multi-offer comparison matrix (never auto-accepts).

Closes the gap vs Levels.fyi / Blind offer comparison UIs by ranking offers
side-by-side with a deterministic total cash+equity heuristic. Assistive only —
never auto-accepts an offer and never performs network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class OfferCompareRow:
    """One ranked offer row in the comparison matrix."""

    rank: int
    company: str
    base: float
    bonus: float
    equity: float
    remote: str
    notes: str
    total_comp: float


@dataclass(slots=True, frozen=True)
class OfferCompareResult:
    """Ranked offer matrix plus a human-readable summary."""

    rows: list[OfferCompareRow]
    summary: str
    auto_accept: bool


def _as_float(value: Any, *, field: str) -> float:
    """Coerce a numeric field to float, treating blanks as 0.0."""

    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc


class OfferCompareMatrix:
    """Build a deterministic side-by-side offer comparison matrix."""

    def compare(self, offers: list[dict[str, Any]] | None) -> OfferCompareResult:
        """Rank offers by total cash + equity heuristic.

        Args:
            offers: List of offer dicts with keys ``company``, ``base``,
                ``bonus``, ``equity``, ``remote``, ``notes``.

        Returns:
            OfferCompareResult with ranked rows and summary.
            Always sets ``auto_accept=False``.

        Raises:
            ValueError: If offers is empty/None or a company is blank.
        """

        if not offers:
            raise ValueError("offers must be a non-empty list")

        scored: list[tuple[float, int, OfferCompareRow]] = []
        for index, raw in enumerate(offers):
            company = str((raw or {}).get("company") or "").strip()
            if not company:
                raise ValueError("each offer requires a non-empty company")

            base = _as_float((raw or {}).get("base"), field="base")
            bonus = _as_float((raw or {}).get("bonus"), field="bonus")
            equity = _as_float((raw or {}).get("equity"), field="equity")
            remote = str((raw or {}).get("remote") or "").strip() or "unspecified"
            notes = str((raw or {}).get("notes") or "").strip()
            total = round(base + bonus + equity, 2)

            # Placeholder rank; rewritten after sort.
            row = OfferCompareRow(
                rank=0,
                company=company,
                base=base,
                bonus=bonus,
                equity=equity,
                remote=remote,
                notes=notes,
                total_comp=total,
            )
            # Sort key: higher total first; stable tie-break by input index.
            scored.append((-total, index, row))

        scored.sort()
        ranked_rows: list[OfferCompareRow] = []
        for rank, (_, _, row) in enumerate(scored, start=1):
            ranked_rows.append(
                OfferCompareRow(
                    rank=rank,
                    company=row.company,
                    base=row.base,
                    bonus=row.bonus,
                    equity=row.equity,
                    remote=row.remote,
                    notes=row.notes,
                    total_comp=row.total_comp,
                )
            )

        leader = ranked_rows[0]
        summary = (
            f"Compared {len(ranked_rows)} offers; top by cash+equity heuristic is "
            f"{leader.company} (total_comp={leader.total_comp:.0f}). "
            "Assistive only — never auto-accept; verify equity, vesting, and remote policy."
        )

        return OfferCompareResult(
            rows=ranked_rows,
            summary=summary,
            auto_accept=False,
        )
