"""Robinson screening job.

Iterates sole-trader leads, matches each against a :class:`RobinsonList`, and
flags the matches as suppressed so they never reach an outreach surface.
Non-sole-traders (limited companies) are skipped — they are legal persons and
out of Robinson scope.

Orchestration (:func:`run_robinson_screening`) is decoupled from persistence
(the :class:`ScreeningWriter` Protocol) so it tests with a fake writer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .robinson import RobinsonList

ROBINSON_REASON = "robinson"


@dataclass(slots=True)
class LeadToScreen:
    """The fields needed to screen one lead against the Robinson list."""

    lead_id: str
    company_name: str
    postal_code: str | None = None
    is_sole_trader: bool = False


@dataclass(slots=True)
class ScreeningStats:
    """Tally of a screening run."""

    seen: int = 0
    sole_traders: int = 0
    suppressed: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class ScreeningWriter(Protocol):
    """Persistence boundary for screening outcomes."""

    def mark(self, lead_id: str, *, suppressed: bool, reason: str | None) -> None:
        ...


def run_robinson_screening(
    leads: list[LeadToScreen],
    robinson: RobinsonList,
    writer: ScreeningWriter,
) -> ScreeningStats:
    """Screen ``leads`` and flag Robinson-listed sole traders as suppressed.

    Every sole trader gets a write (recording that it was screened, even when
    clear) so ``robinson_screened_at`` reflects a real pass. Limited companies
    are counted as seen but skipped.
    """
    stats = ScreeningStats()
    for lead in leads:
        stats.seen += 1
        if not lead.is_sole_trader:
            continue
        stats.sole_traders += 1
        try:
            hit = robinson.contains(lead.company_name, lead.postal_code)
            writer.mark(
                lead.lead_id,
                suppressed=hit,
                reason=ROBINSON_REASON if hit else None,
            )
            if hit:
                stats.suppressed += 1
        except Exception:
            stats.errors += 1
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseScreeningWriter:
    """Writes screening outcomes to ``leads`` via the service-role client."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def mark(self, lead_id: str, *, suppressed: bool, reason: str | None) -> None:
        row: dict[str, Any] = {"robinson_screened_at": _now_iso()}
        if suppressed:
            row["suppressed"] = True
            row["suppression_reason"] = reason
        self.client.table("leads").update(row).eq("id", lead_id).execute()
