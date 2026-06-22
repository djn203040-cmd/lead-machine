"""Firmographic & financial enrichment (M3).

Pulls free XBRL annual reports from Virk's offentliggørelser channel, parses
the primary-period financials, estimates revenue when omitted (class B), and
extracts best-effort decision-makers from CVR — attaching budget-proxy data so
leads can be sized and prioritized for the website pitch.
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
from .xbrl import parse_xbrl

__all__ = [
    "FinancialClient",
    "parse_xbrl",
    "estimate_revenue",
    "benchmark_for",
    "band_midpoint",
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
