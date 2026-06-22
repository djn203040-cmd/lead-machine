"""Dataclasses shared across the financial-enrichment pipeline (M3)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


@dataclass(slots=True)
class Financials:
    """Figures parsed from an XBRL annual report (primary period only)."""

    gross_profit: float | None = None  # fsa:GrossProfitLoss (bruttofortjeneste)
    profit_loss: float | None = None  # fsa:ProfitLoss (årets resultat)
    equity: float | None = None  # fsa:Equity (egenkapital)
    assets: float | None = None  # fsa:Assets (aktiver i alt)
    revenue: float | None = None  # fsa:Revenue (nettoomsætning; often omitted)
    employee_expense: float | None = None  # fsa:EmployeeBenefitsExpense
    avg_employees: float | None = None  # fsa:AverageNumberOfEmployees

    def as_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(slots=True)
class RevenueEstimate:
    """An estimated (or actual) annual revenue with provenance."""

    value: float
    method: str  # actual | gross_margin_backout | per_employee
    confidence: str  # high | medium | low
    inputs: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Report:
    """An offentliggørelse (published annual report) for a CVR number."""

    cvr_number: str
    period_start: str | None
    period_end: str | None
    published_at: str | None
    xbrl_url: str | None
    pdf_url: str | None = None


@dataclass(slots=True)
class LeadToEnrich:
    """Minimal lead view the financial-enrichment job needs."""

    lead_id: str
    cvr_number: str
    branchekode: str | None = None
    employees_exact: int | None = None
    employees_band: str | None = None
    raw_cvr: dict[str, Any] | None = None
