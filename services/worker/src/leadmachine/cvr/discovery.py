"""Discovery job (issue #17).

Runs a search through a :class:`CvrClient`, maps each company, and upserts it
into ``leads`` keyed by CVR number (idempotent — re-running never duplicates),
storing the raw CVR payload in ``lead_enrichment.cvr``. Marketing-protected
(``reklamebeskyttet``) and inactive/bankrupt/dissolved entities are suppressed
and never enter the pipeline.

Orchestration (:func:`run_discovery`) is decoupled from persistence (the
:class:`LeadWriter` Protocol) so it can be tested with a fake client + writer
before live CVR credentials arrive.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Protocol

from .mapper import SUPPRESS_INACTIVE, SUPPRESS_REKLAME, MappedLead, map_company
from .query import SearchParameters

if TYPE_CHECKING:
    from . import CvrClient


@dataclass(slots=True)
class DiscoveryStats:
    """Tally of a discovery run; stored on ``searches.stats``."""

    seen: int = 0
    upserted: int = 0
    suppressed_reklame: int = 0
    suppressed_inactive: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class LeadWriter(Protocol):
    """Persistence boundary for discovered leads."""

    def upsert(self, lead: MappedLead, raw_cvr: dict[str, Any], search_id: str | None) -> None:
        ...


def run_discovery(
    client: "CvrClient",
    params: SearchParameters,
    writer: LeadWriter,
    *,
    search_id: str | None = None,
) -> DiscoveryStats:
    """Discover companies for ``params`` and upsert the qualifying ones."""
    stats = DiscoveryStats()
    for raw in client.search(params):
        stats.seen += 1
        try:
            lead = map_company(raw)
        except Exception:
            stats.errors += 1
            continue

        reason = lead.suppression_reason
        if reason == SUPPRESS_REKLAME:
            stats.suppressed_reklame += 1
            continue
        if reason == SUPPRESS_INACTIVE:
            stats.suppressed_inactive += 1
            continue

        try:
            writer.upsert(lead, raw, search_id)
            stats.upserted += 1
        except Exception:
            stats.errors += 1
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseLeadWriter:
    """Writes leads + raw enrichment to Supabase via the service-role client."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def upsert(self, lead: MappedLead, raw_cvr: dict[str, Any], search_id: str | None) -> None:
        row = lead.to_lead_row()
        if search_id:
            row["search_id"] = search_id
        res = (
            self.client.table("leads")
            .upsert(row, on_conflict="cvr_number")
            .execute()
        )
        lead_id = res.data[0]["id"]
        self.client.table("lead_enrichment").upsert(
            {"lead_id": lead_id, "cvr": raw_cvr, "last_enriched_at": _now_iso()},
            on_conflict="lead_id",
        ).execute()
