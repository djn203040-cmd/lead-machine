"""Tests for the realistic-savings estimator — the number the whole pitch rests on."""

from __future__ import annotations

import pytest

from leadmachine.financial.savings import (
    DEFAULT_LEVERS,
    FEE_SHARE,
    GROSS_PROFIT_CAP,
    MAX_ANNUAL,
    MAX_PER_EMPLOYEE,
    OPERATING_SAVINGS_RATE,
    estimate_savings,
    group_for,
    levers_for,
    savings_rate,
)


def _fin(revenue: float | None, confidence: str = "medium", **kw) -> dict:
    fin: dict = dict(kw)
    if revenue is not None:
        fin["revenue_estimate"] = {"value": revenue, "confidence": confidence}
    return fin


# --- sector resolution -----------------------------------------------------
def test_group_for_resolves_catalog_and_division_and_unknown() -> None:
    assert group_for("962100") == "beauty_wellness"  # catalogued
    assert group_for("477110") == "retail"
    assert group_for("010000") is None  # nothing we target
    assert group_for(None) is None


def test_savings_rate_defaults_to_ten_percent() -> None:
    assert savings_rate(None) == 0.10
    assert savings_rate("010000") == 0.10


def test_goods_heavy_sectors_get_a_lower_rate_than_service_sectors() -> None:
    # You cannot systematise away someone else's invoice: a retailer's revenue
    # is mostly goods, a clinic's is mostly time.
    assert savings_rate("477110") < savings_rate("962100")
    assert savings_rate("452000") < 0.10  # auto — revenue is largely parts


# --- their own accounts come first -----------------------------------------
def test_filed_accounts_beat_the_benchmark() -> None:
    """Revenue is guesswork; bruttofortjeneste and årets resultat are filed fact.

    What they spend below the gross line is the only pool systems can save from,
    so that — not an estimated turnover — is what the claim rests on.
    """
    est = estimate_savings(
        _fin(17_000_000, gross_profit=7_667_935, profit_loss=2_611_640), "433900", employees=8
    )
    assert est is not None
    assert est.basis == "accounts"
    assert est.from_accounts
    assert est.pool == round(7_667_935 - 2_611_640)  # the operating cost base
    assert est.annual_high == 510_000  # 10% of the cost base
    assert est.confidence == "høj"
    assert est.rate == OPERATING_SAVINGS_RATE


def test_a_loss_makes_the_cost_base_bigger_than_the_gross_profit() -> None:
    """They spent more than they grossed — that overspend is real cost base."""
    est = estimate_savings(_fin(9_400_000, gross_profit=7_549_844, profit_loss=-816_321), "962100")
    assert est is not None
    assert est.pool > 7_549_844
    assert est.profit_loss == -816_321


def test_gross_profit_alone_is_used_as_an_upper_bound() -> None:
    est = estimate_savings(_fin(5_000_000, gross_profit=2_000_000), "433900")
    assert est is not None
    assert est.basis == "accounts"
    assert est.pool == 2_000_000
    # Less certain than a full filing: we know the ceiling, not the cost base.
    assert est.confidence == "middel"


def test_nothing_filed_falls_back_to_the_sector_benchmark() -> None:
    est = estimate_savings(_fin(8_750_000, "low"), "862100", employees=8)
    assert est is not None
    assert est.basis == "benchmark"
    assert not est.from_accounts
    assert est.revenue == 8_750_000
    assert est.confidence == "lav"


def test_profit_exceeding_gross_profit_falls_back() -> None:
    """A holding-shaped filing (profit from elsewhere) leaves no usable cost base."""
    est = estimate_savings(
        _fin(2_000_000, gross_profit=100_000, profit_loss=3_900_000), "433900"
    )
    assert est is not None
    assert est.basis == "benchmark"


# --- the benchmark fallback ------------------------------------------------
def test_ten_percent_of_revenue_is_the_baseline() -> None:
    # trades sits on the 10% default; 2M revenue → 200k baseline, 120k low end.
    est = estimate_savings(_fin(2_000_000), "433900")
    assert est is not None
    assert est.annual_high == 200_000
    assert est.annual_low == 120_000
    assert est.rate == 0.10


def test_fee_is_twenty_percent_and_they_keep_the_rest() -> None:
    est = estimate_savings(_fin(2_000_000), "433900")
    assert est is not None
    assert est.fee_high == pytest.approx(est.annual_high * FEE_SHARE, rel=0.05)
    assert est.fee_low == pytest.approx(est.annual_low * FEE_SHARE, rel=0.05)
    assert est.keeps_high == est.annual_high - est.fee_high
    assert est.keeps_low == est.annual_low - est.fee_low
    # The business keeps the lion's share — that is the whole sales argument.
    assert est.keeps_high > est.fee_high * 3


def test_band_is_conservative_at_the_low_end() -> None:
    est = estimate_savings(_fin(5_000_000), "433900")
    assert est is not None
    assert est.annual_low < est.annual_high


def test_no_revenue_signal_means_no_number() -> None:
    assert estimate_savings({}, "962100") is None
    assert estimate_savings(None, "962100") is None
    assert estimate_savings(_fin(0), "962100") is None
    assert estimate_savings({"revenue_estimate": {"value": "lots"}}, "962100") is None


def test_gross_profit_caps_a_benchmark_claim() -> None:
    """A sector guess must not out-claim the margin they actually keep.

    Only bites on the benchmark path — here the filing leaves no usable cost
    base, so we fall back to revenue but still bound it by the gross profit.
    """
    est = estimate_savings(
        _fin(5_000_000, gross_profit=600_000, profit_loss=800_000), "433900"
    )
    assert est is not None
    assert est.basis == "benchmark"
    assert est.capped_by == "gross_profit"
    assert est.annual_high <= 600_000 * GROSS_PROFIT_CAP + 10_000  # + rounding


def test_headcount_caps_what_we_can_claim_to_free_up() -> None:
    """You can't save more work than there are people doing it."""
    est = estimate_savings(_fin(40_000_000, "low"), "433900", employees=4)
    assert est is not None
    assert est.capped_by == "headcount"
    assert est.annual_high == 4 * MAX_PER_EMPLOYEE


def test_headcount_cap_does_not_bite_a_well_staffed_firm() -> None:
    est = estimate_savings(_fin(2_000_000), "433900", employees=20)  # noqa: E501
    assert est is not None
    assert est.capped_by is None
    assert est.annual_high == 200_000


def test_unknown_headcount_leaves_the_estimate_alone() -> None:
    with_none = estimate_savings(_fin(2_000_000), "433900", employees=None)
    assert with_none is not None
    assert with_none.capped_by is None


def test_absurd_revenue_hits_the_ceiling() -> None:
    est = estimate_savings(_fin(500_000_000), "433900")
    assert est is not None
    assert est.capped_by == "ceiling"
    assert est.annual_high == MAX_ANNUAL


def test_confidence_is_inherited_from_the_revenue_estimate() -> None:
    assert estimate_savings(_fin(1_000_000, "high"), "433900").confidence == "høj"
    assert estimate_savings(_fin(1_000_000, "medium"), "433900").confidence == "middel"
    assert estimate_savings(_fin(1_000_000, "low"), "433900").confidence == "lav"
    # Unknown provenance is never presented as more certain than it is.
    assert estimate_savings(_fin(1_000_000, ""), "433900").confidence == "lav"


def test_numbers_are_rounded_to_speakable_amounts() -> None:
    est = estimate_savings(_fin(1_234_567), "433900")
    assert est is not None
    assert est.annual_high % 5_000 == 0
    assert est.annual_low % 1_000 == 0


def test_as_dict_round_trips_the_math() -> None:
    est = estimate_savings(_fin(2_000_000, gross_profit=900_000, profit_loss=100_000), "433900")
    assert est is not None
    out = est.as_dict()
    assert out["annual_high"] == est.annual_high
    assert out["basis"] == "accounts"
    assert out["pool"] == 800_000
    assert out["gross_profit"] == 900_000
    assert out["capped_by"] is None


# --- sector levers ---------------------------------------------------------
def test_levers_are_sector_specific() -> None:
    salon = levers_for("962100")
    builder = levers_for("433900")
    assert salon != builder
    assert any("afbud" in lever or "udeblivelser" in lever for lever in salon)
    assert any("tilbud" in lever for lever in builder)


def test_unknown_sector_falls_back_to_generic_levers() -> None:
    assert levers_for("010000") == DEFAULT_LEVERS
    assert levers_for(None) == DEFAULT_LEVERS
