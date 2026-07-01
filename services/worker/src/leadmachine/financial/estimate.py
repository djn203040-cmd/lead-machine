"""Revenue estimation (M3).

Class B annual reports legally omit revenue (only *bruttofortjeneste* is
disclosed), so we estimate it. Preference order:

1. **actual** — ``fsa:Revenue`` was disclosed (class C+ or voluntary).
2. **gross_margin_backout** — ``revenue ≈ gross_profit / sector_gross_margin``.
3. **per_employee** — ``revenue ≈ employees × sector_revenue_per_employee``.

Sector benchmarks are rough Danish-SMB heuristics keyed to the branchekode
catalog groups; tune against real outcomes. Revenue is never a hard gate
(PLAN.md §10), so a low-confidence estimate is acceptable for sizing.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..cvr.branchekoder import by_code, normalize_code
from .models import Financials, RevenueEstimate


@dataclass(frozen=True, slots=True)
class Benchmark:
    group: str
    revenue_per_employee: float  # DKK
    gross_margin: float  # bruttofortjeneste / nettoomsætning


BENCHMARKS: dict[str, Benchmark] = {
    "food_drink": Benchmark("food_drink", 650_000, 0.65),
    "beauty_wellness": Benchmark("beauty_wellness", 500_000, 0.80),
    "health": Benchmark("health", 1_100_000, 0.85),
    "trades": Benchmark("trades", 1_000_000, 0.45),
    "cleaning": Benchmark("cleaning", 500_000, 0.55),
    "auto": Benchmark("auto", 1_800_000, 0.30),
    "transport": Benchmark("transport", 1_400_000, 0.35),
    "retail": Benchmark("retail", 1_600_000, 0.30),
    "professional": Benchmark("professional", 1_300_000, 0.80),
    "finance": Benchmark("finance", 2_000_000, 0.85),
    "realestate": Benchmark("realestate", 1_500_000, 0.70),
    "it_media": Benchmark("it_media", 1_200_000, 0.75),
    "education": Benchmark("education", 500_000, 0.75),
    "hospitality": Benchmark("hospitality", 700_000, 0.60),
    "leisure": Benchmark("leisure", 600_000, 0.75),
    "business_services": Benchmark("business_services", 900_000, 0.70),
}
DEFAULT_BENCHMARK = Benchmark("default", 1_000_000, 0.50)

# DB25 2-digit division -> catalog group, for codes outside our curated catalog.
_PREFIX_GROUP: dict[str, str] = {
    "10": "food_drink", "11": "food_drink", "55": "hospitality", "56": "food_drink",
    "96": "beauty_wellness",
    "75": "health", "86": "health",
    "41": "trades", "42": "trades", "43": "trades",
    "81": "cleaning",
    "45": "auto", "95": "auto",
    "49": "transport", "50": "transport", "52": "transport", "53": "transport",
    "47": "retail",
    "69": "professional", "70": "professional", "71": "professional",
    "73": "professional", "74": "professional",
    "64": "finance", "65": "finance", "66": "finance",
    "68": "realestate",
    "58": "it_media", "59": "it_media", "62": "it_media", "63": "it_media",
    "85": "education",
    "79": "hospitality",
    "90": "leisure", "91": "leisure", "93": "leisure",
    "77": "business_services", "78": "business_services",
    "80": "business_services", "82": "business_services",
}

# Approximate employee count from an interval band (midpoint).
_BAND_MIDPOINT: dict[str, int] = {
    "ANTAL_0_0": 0,
    "ANTAL_1_1": 1,
    "ANTAL_2_4": 3,
    "ANTAL_5_9": 7,
    "ANTAL_10_19": 14,
    "ANTAL_20_49": 34,
    "ANTAL_50_99": 74,
    "ANTAL_100_199": 149,
    "ANTAL_200_499": 349,
    "ANTAL_500_999": 749,
    "ANTAL_1000_999999": 1500,
}


def band_midpoint(band: str | None) -> int | None:
    return _BAND_MIDPOINT.get(band) if band else None


def benchmark_for(branchekode: str | None) -> Benchmark:
    """Pick sector benchmarks for a branchekode (catalog → prefix → default)."""
    if not branchekode:
        return DEFAULT_BENCHMARK
    code = normalize_code(branchekode)
    catalogued = by_code(code)
    if catalogued is not None:
        return BENCHMARKS.get(catalogued.group, DEFAULT_BENCHMARK)
    group = _PREFIX_GROUP.get(code[:2])
    return BENCHMARKS.get(group, DEFAULT_BENCHMARK) if group else DEFAULT_BENCHMARK


def estimate_revenue(
    financials: Financials,
    branchekode: str | None,
    employees: int | None,
) -> RevenueEstimate | None:
    """Best available revenue figure (actual or estimated) with provenance."""
    if financials.revenue and financials.revenue > 0:
        return RevenueEstimate(
            value=round(financials.revenue),
            method="actual",
            confidence="high",
            inputs={"source": "xbrl"},
        )

    bench = benchmark_for(branchekode)

    if financials.gross_profit and financials.gross_profit > 0 and bench.gross_margin > 0:
        value = financials.gross_profit / bench.gross_margin
        return RevenueEstimate(
            value=round(value),
            method="gross_margin_backout",
            confidence="medium",
            inputs={
                "gross_profit": financials.gross_profit,
                "gross_margin": bench.gross_margin,
                "group": bench.group,
            },
        )

    if employees and employees > 0:
        value = employees * bench.revenue_per_employee
        return RevenueEstimate(
            value=round(value),
            method="per_employee",
            confidence="low",
            inputs={
                "employees": employees,
                "revenue_per_employee": bench.revenue_per_employee,
                "group": bench.group,
            },
        )

    return None
