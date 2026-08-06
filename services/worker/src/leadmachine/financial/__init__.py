"""Firmographic & financial enrichment (M3).

Pulls free XBRL annual reports from Virk's offentliggørelser channel, parses
the primary-period financials, estimates revenue when omitted (class B), and
extracts best-effort decision-makers from CVR. Revenue is the input to
:mod:`.savings`, which turns it into the realistic DKK saving the offer is
priced on (20% of what we actually save) — the number the whole call rests on.
"""

from __future__ import annotations

from .client import FinancialClient
from .enrich import (
    EnrichStats,
    FinancialWriter,
    SupabaseFinancialWriter,
    enrich_one,
    run_financial_enrichment,
)
from .estimate import band_midpoint, benchmark_for, estimate_revenue
from .models import Financials, LeadToEnrich, Report, RevenueEstimate
from .savings import (
    FEE_SHARE,
    SavingsEstimate,
    estimate_savings,
    group_for,
    levers_for,
    savings_rate,
)
from .xbrl import parse_xbrl

__all__ = [
    "FinancialClient",
    "parse_xbrl",
    "estimate_revenue",
    "benchmark_for",
    "band_midpoint",
    "estimate_savings",
    "savings_rate",
    "levers_for",
    "group_for",
    "SavingsEstimate",
    "FEE_SHARE",
    "run_financial_enrichment",
    "enrich_one",
    "EnrichStats",
    "FinancialWriter",
    "SupabaseFinancialWriter",
    "Financials",
    "RevenueEstimate",
    "Report",
    "LeadToEnrich",
]
