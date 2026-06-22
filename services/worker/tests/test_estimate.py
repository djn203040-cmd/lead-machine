from leadmachine.financial.estimate import (
    DEFAULT_BENCHMARK,
    band_midpoint,
    benchmark_for,
    estimate_revenue,
)
from leadmachine.financial.models import Financials


def test_actual_revenue_wins() -> None:
    est = estimate_revenue(Financials(revenue=2_000_000, gross_profit=900_000), "960210", 3)
    assert est is not None
    assert est.value == 2_000_000
    assert est.method == "actual"
    assert est.confidence == "high"


def test_gross_margin_backout() -> None:
    # 960210 = frisør -> beauty_wellness group, gross_margin 0.80
    est = estimate_revenue(Financials(gross_profit=800_000), "96.02.10", 3)
    assert est is not None
    assert est.method == "gross_margin_backout"
    assert est.value == round(800_000 / 0.80)
    assert est.confidence == "medium"


def test_per_employee_when_no_financials() -> None:
    est = estimate_revenue(Financials(), "960210", 4)
    assert est is not None
    assert est.method == "per_employee"
    assert est.value == 4 * 500_000
    assert est.confidence == "low"


def test_none_when_nothing_to_go_on() -> None:
    assert estimate_revenue(Financials(), "960210", None) is None
    assert estimate_revenue(Financials(), "960210", 0) is None


def test_benchmark_lookup_prefers_catalog_then_prefix_then_default() -> None:
    assert benchmark_for("960210").group == "beauty_wellness"  # catalogued
    assert benchmark_for("561010").group == "food_drink"  # catalogued
    assert benchmark_for("433900").group == "trades"  # uncatalogued, prefix 43
    assert benchmark_for("011100") is DEFAULT_BENCHMARK  # unknown prefix
    assert benchmark_for(None) is DEFAULT_BENCHMARK


def test_band_midpoint() -> None:
    assert band_midpoint("ANTAL_2_4") == 3
    assert band_midpoint("ANTAL_10_19") == 14
    assert band_midpoint(None) is None
    assert band_midpoint("BOGUS") is None
