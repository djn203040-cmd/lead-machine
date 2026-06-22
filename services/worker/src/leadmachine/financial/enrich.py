"""Financial-enrichment job (M3).

For each lead: fetch its latest XBRL annual report, parse the primary-period
financials, estimate revenue when omitted, and extract best-effort
decision-makers from the CVR payload. Writes to ``lead_enrichment.financial``
and ``lead_enrichment.contact``.

Orchestration (:func:`run_financial_enrichment`) is decoupled from persistence
(:class:`FinancialWriter`) and the data source (:class:`FinancialClient`) so it
is testable with fakes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

from ..cvr.mapper import extract_management
from .estimate import band_midpoint, estimate_revenue
from .models import Financials, LeadToEnrich
from .xbrl import parse_xbrl


@dataclass(slots=True)
class EnrichStats:
    seen: int = 0
    reports: int = 0  # leads with an XBRL annual report
    revenue: int = 0  # leads with a revenue figure (actual or estimated)
    contacts: int = 0  # leads with ≥1 decision-maker
    empty: int = 0  # leads with nothing to write
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class FinancialClientProtocol(Protocol):
    def fetch_latest_report(self, cvr_number: str | int) -> Any: ...
    def download_xbrl(self, report: Any) -> bytes | None: ...


class FinancialWriter(Protocol):
    def write(self, lead_id: str, financial: dict[str, Any], contact: dict[str, Any]) -> None: ...


def _employee_count(lead: LeadToEnrich) -> int | None:
    return lead.employees_exact or band_midpoint(lead.employees_band)


def enrich_one(
    lead: LeadToEnrich, client: FinancialClientProtocol
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the (financial, contact) payloads for a single lead."""
    employees = _employee_count(lead)
    financial: dict[str, Any] = {}

    report = client.fetch_latest_report(lead.cvr_number)
    if report is not None:
        xbrl = client.download_xbrl(report)
        fin = parse_xbrl(xbrl) if xbrl else Financials()
        rev = estimate_revenue(fin, lead.branchekode, employees)
        financial = {
            "source": "virk_xbrl",
            "currency": "DKK",
            "period": {"start": report.period_start, "end": report.period_end},
            "report_xbrl_url": report.xbrl_url,
            "published_at": report.published_at,
            **fin.as_dict(),
            "revenue_estimate": rev.as_dict() if rev else None,
        }
        financial = {k: v for k, v in financial.items() if v is not None}
    else:
        # No filed report — still size from employees if we can.
        rev = estimate_revenue(Financials(), lead.branchekode, employees)
        if rev is not None:
            financial = {
                "source": "estimate_only",
                "currency": "DKK",
                "revenue_estimate": rev.as_dict(),
            }

    contact: dict[str, Any] = {}
    if lead.raw_cvr:
        decision_makers = extract_management(lead.raw_cvr)
        if decision_makers:
            contact = {"source": "cvr", "decision_makers": decision_makers}

    return financial, contact


def run_financial_enrichment(
    leads: Iterable[LeadToEnrich],
    client: FinancialClientProtocol,
    writer: FinancialWriter,
) -> EnrichStats:
    """Enrich every lead and persist the results."""
    stats = EnrichStats()
    for lead in leads:
        stats.seen += 1
        try:
            financial, contact = enrich_one(lead, client)
        except Exception:
            stats.errors += 1
            continue

        if not financial and not contact:
            stats.empty += 1
            continue

        try:
            writer.write(lead.lead_id, financial, contact)
        except Exception:
            stats.errors += 1
            continue

        if financial.get("source") == "virk_xbrl":
            stats.reports += 1
        if financial.get("revenue_estimate"):
            stats.revenue += 1
        if contact:
            stats.contacts += 1
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseFinancialWriter:
    """Updates ``lead_enrichment`` financial/contact columns via service role."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def write(self, lead_id: str, financial: dict[str, Any], contact: dict[str, Any]) -> None:
        row: dict[str, Any] = {"lead_id": lead_id, "last_enriched_at": _now_iso()}
        if financial:
            row["financial"] = financial
        if contact:
            row["contact"] = contact
        self.client.table("lead_enrichment").upsert(row, on_conflict="lead_id").execute()
