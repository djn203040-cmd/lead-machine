"""Tests for lead scoring (M4, savings rubric v2) — pure computation, no network."""

from __future__ import annotations

from dataclasses import fields
from datetime import date

import pytest

from leadmachine.scoring import (
    LeadToScore,
    SupabaseScoreWriter,
    Weights,
    gate_reason,
    run_scoring,
    score_industry,
    score_lead,
    score_presence,
    score_recency,
    score_savings,
    score_size,
    score_tech,
)
from leadmachine.scoring.rubric import CRITERION_FIELD

from .conftest import FakeScoreWriter, FakeSupabase

TODAY = date(2026, 6, 22)
W = Weights()

# A hairdresser (beauty_wellness, 12% savings rate) big enough to land in the
# 250k–1M "prime" savings band, with margin to spare so the gross-profit cap
# never bites.
PRIME_FINANCIAL = {
    "revenue_estimate": {"value": 5_000_000, "confidence": "medium"},
    "gross_profit": 3_000_000,
}


def _financial(revenue: int, **kw) -> dict:
    return {"revenue_estimate": {"value": revenue, "confidence": "medium"}, **kw}


# --- rubric invariants -----------------------------------------------------
def test_factor_caps_sum_to_100() -> None:
    assert (
        W.cap_savings
        + W.cap_industry
        + W.cap_tech
        + W.cap_presence
        + W.cap_size
        + W.cap_recency
    ) == 100


def test_savings_is_the_dominant_factor() -> None:
    assert W.cap_savings > max(W.cap_industry, W.cap_tech, W.cap_presence, W.cap_size)


def test_every_seeded_criterion_maps_to_a_real_weight_field() -> None:
    valid = {f.name for f in fields(Weights)}
    assert set(CRITERION_FIELD.values()) <= valid


# --- savings factor (40) ---------------------------------------------------
def test_savings_scales_with_the_size_of_the_prize() -> None:
    # 962100 = frisør (beauty_wellness, 12%). Bands walk up then back down.
    tiny = score_savings(_financial(150_000), "962100", W)
    mid = score_savings(_financial(900_000), "962100", W)
    prime = score_savings(_financial(5_000_000), "962100", W)
    huge = score_savings(_financial(60_000_000), "962100", W)

    assert tiny.points < mid.points < prime.points
    assert prime.points == 40
    assert huge.points < prime.points  # too big for a one-call local sale


def test_savings_detail_carries_the_dkk_math() -> None:
    fs = score_savings(_financial(5_000_000), "962100", W)
    assert fs.detail["band"] == "prime"
    assert fs.detail["annual_low"] < fs.detail["annual_high"]
    # our cut is 20% of the saving
    assert fs.detail["fee_high"] == pytest.approx(fs.detail["annual_high"] * 0.2, rel=0.1)
    assert fs.detail["confidence"] == "middel"


def test_savings_without_revenue_is_unknown_not_zero() -> None:
    fs = score_savings({}, "962100", W)
    assert fs.points == W.sav_unknown == 12
    assert fs.detail == {"band": "unknown"}


def test_savings_is_capped_by_gross_profit() -> None:
    lean = score_savings(_financial(5_000_000, gross_profit=300_000), "962100", W)
    fat = score_savings(_financial(5_000_000, gross_profit=3_000_000), "962100", W)
    assert lean.points < fat.points
    assert lean.detail["capped_by"] == "gross_profit"


def test_savings_rate_is_sector_adjusted() -> None:
    # Same revenue: a retailer's turnover is mostly goods, a clinic's is time.
    retail = score_savings(_financial(3_000_000), "477110", W)
    clinic = score_savings(_financial(3_000_000), "862100", W)
    assert retail.detail["rate"] < clinic.detail["rate"]


# --- industry factor (20) --------------------------------------------------
def test_industry_tiers() -> None:
    assert score_industry("962100", W).points == 20  # catalogued (hairdresser)
    assert score_industry("96.21.00", W).points == 20  # dotted form normalizes
    assert score_industry("960230", W).points == 10  # same division, not catalogued
    assert score_industry("010000", W).points == 0  # unrelated division
    assert score_industry(None, W).points == 0


# --- digital-maturity factor (15) ------------------------------------------
def test_tech_rewards_digital_maturity_not_website_need() -> None:
    # The old rubric had this backwards: no site = best lead. Now a business
    # that is already digital is the easier systems conversation.
    modern = score_tech("modern", {}, W).points
    neglected = score_tech("bad", {}, W).points
    absent = score_tech("none", {}, W).points
    assert modern > neglected > absent


def test_tech_quality_bonus_is_capped() -> None:
    fs = score_tech("modern", {"quality": {"tier": "premium"}}, W)
    assert fs.points == W.cap_tech == 15
    assert fs.detail["quality"] == "premium"


def test_tech_unknown_is_neutral() -> None:
    fs = score_tech("unknown", {}, W)
    assert fs.points == W.t_unknown == 6
    assert fs.detail["need"] == "unknown"


# --- presence factor (10) --------------------------------------------------
def test_presence_fb_and_pixel() -> None:
    assert score_presence({"has_fb_page": True}, W).points == 4
    assert score_presence({"has_meta_pixel": True}, W).points == 6
    assert score_presence({"has_fb_page": True, "has_meta_pixel": True}, W).points == 10
    assert score_presence({}, W).points == 0


# --- size factor (8) -------------------------------------------------------
@pytest.mark.parametrize(
    "band,expected",
    [
        ("ANTAL_0_0", 2),
        ("ANTAL_1_1", 2),
        ("ANTAL_2_4", 5),
        ("ANTAL_5_9", 7),
        ("ANTAL_10_19", 8),
        ("ANTAL_20_49", 8),
        ("ANTAL_50_99", 6),
        (None, 2),
    ],
)
def test_size_band_points(band: str | None, expected: int) -> None:
    assert score_size(None, band, W).points == expected


def test_size_exact_overrides_band() -> None:
    assert score_size(7, "ANTAL_50_99", W).points == 7


# --- recency factor (7) ----------------------------------------------------
def test_recency_active_plus_recent_founding() -> None:
    fs = score_recency("NORMAL", "2024-06-01", W, TODAY)
    assert fs.points == 7  # active 4 + recent 3
    assert fs.detail["founded"] == "recent"


def test_recency_mid_and_old_founding() -> None:
    assert score_recency("NORMAL", "2020-01-01", W, TODAY).points == 6  # active 4 + mid 2
    assert score_recency("NORMAL", "2005-01-01", W, TODAY).points == 4  # active only


def test_recency_handles_missing_or_bad_founded_at() -> None:
    assert score_recency("AKTIV", None, W, TODAY).points == 4
    assert score_recency("AKTIV", "not-a-date", W, TODAY).points == 4


# --- hard gate -------------------------------------------------------------
def test_gate_reklamebeskyttet() -> None:
    assert gate_reason(True, "NORMAL") == "reklamebeskyttet"


def test_gate_inactive_status() -> None:
    assert gate_reason(False, "OPHØRT") == "inactive"
    assert gate_reason(False, "UNDERKONKURS") == "inactive"


def test_gate_allows_active_and_missing_status() -> None:
    ph = ["12345678"]
    assert gate_reason(False, "NORMAL", ph) is None
    assert gate_reason(False, "aktiv", ph) is None  # case-insensitive
    assert gate_reason(False, None, ph) is None  # missing status is not gated


def test_gate_no_phone_disqualifies() -> None:
    assert gate_reason(False, "NORMAL", []) == "no_phone"
    assert gate_reason(False, "NORMAL", None) == "no_phone"
    # Compliance gates still take precedence over the phone gate.
    assert gate_reason(True, "NORMAL", []) == "reklamebeskyttet"
    assert gate_reason(False, "OPHØRT", []) == "inactive"


# --- score_lead end-to-end -------------------------------------------------
def _ideal_lead(**kw) -> LeadToScore:
    base = dict(
        lead_id="L1",
        website_need="modern",
        branchekode="962100",
        employees_exact=12,
        founded_at="2024-06-01",
        cvr_status="NORMAL",
        phone=["12345678"],
        social={"has_fb_page": True, "has_meta_pixel": True},
        financial=PRIME_FINANCIAL,
    )
    base.update(kw)
    return LeadToScore(**base)


def test_score_lead_perfect_lead_is_100() -> None:
    bd = score_lead(_ideal_lead(), W, TODAY)
    assert bd.total == 100
    assert not bd.gated
    assert set(bd.factors) == {
        "savings",
        "industry",
        "tech",
        "presence",
        "size",
        "recency",
    }
    assert bd.factors["savings"].points == 40


def test_score_lead_gated_lead_scores_zero() -> None:
    bd = score_lead(_ideal_lead(reklamebeskyttet=True), W, TODAY)
    assert bd.total == 0
    assert bd.gated
    assert bd.gate_reason == "reklamebeskyttet"
    assert bd.factors == {}


def test_savings_outweighs_the_website_signal() -> None:
    """The point of rubric v2: money beats web presence.

    A big business with no website must outrank a tiny one with a modern site —
    under the old website rubric it was the other way round.
    """
    big_no_site = score_lead(
        _ideal_lead(website_need="none", financial=PRIME_FINANCIAL), W, TODAY
    ).total
    small_modern = score_lead(
        _ideal_lead(website_need="modern", financial=_financial(300_000)), W, TODAY
    ).total
    assert big_no_site > small_modern


def test_score_lead_survives_an_unqualified_website() -> None:
    """No website verdict yet is no longer a reason to bury a lead."""
    bd = score_lead(_ideal_lead(website_need="unknown"), W, TODAY)
    assert bd.total >= 85


def test_breakdown_as_dict_shape() -> None:
    out = score_lead(_ideal_lead(), W, TODAY).as_dict()
    assert out["version"] == 2
    assert out["total"] == 100
    assert out["gated"] is False
    assert out["factors"]["industry"] == {
        "points": 20,
        "max": 20,
        "detail": {"tier": "local_service", "branchekode": "962100"},
    }


# --- weights tunable from scoring_criteria ---------------------------------
def test_from_criteria_defaults_match_seed() -> None:
    seed = [
        {"key": k, "weight": "high", "config": None, "is_active": True} for k in CRITERION_FIELD
    ]
    assert Weights.from_criteria(seed) == Weights()


def test_from_criteria_config_points_override() -> None:
    w = Weights.from_criteria(
        [{"key": "savings_potential", "config": {"points": 30}, "is_active": True}]
    )
    assert w.sav_prime == 30
    assert score_savings(PRIME_FINANCIAL, "962100", w).points == 30


def test_from_criteria_inactive_disables_signal() -> None:
    w = Weights.from_criteria([{"key": "runs_paid_ads", "config": None, "is_active": False}])
    assert w.p_pixel == 0


def test_from_criteria_ignores_unknown_keys_and_bool_points() -> None:
    w = Weights.from_criteria(
        [
            {"key": "totally_made_up", "config": {"points": 99}, "is_active": True},
            {"key": "no_website", "config": {"points": True}, "is_active": True},  # bool ≠ number
        ]
    )
    assert w == Weights()


# --- run_scoring + persistence ---------------------------------------------
def test_run_scoring_tallies_and_persists() -> None:
    writer = FakeScoreWriter()
    leads = [
        _ideal_lead(lead_id="A"),
        _ideal_lead(lead_id="B", reklamebeskyttet=True),  # gated
        LeadToScore(lead_id="C", website_need="unknown", phone=["12345678"]),  # sparse, still scores
    ]
    stats = run_scoring(leads, writer, weights=W, today=TODAY)

    assert stats.seen == 3
    assert stats.scored == 2
    assert stats.gated == 1
    assert stats.errors == 0
    assert set(writer.writes) == {"A", "B", "C"}
    assert writer.writes["A"][0] == 100
    assert writer.writes["B"][0] == 0


def test_supabase_score_writer_writes_both_tables() -> None:
    fake = FakeSupabase()
    SupabaseScoreWriter(fake).write("lead-1", 87, {"total": 87, "factors": {}})

    assert len(fake.log) == 2
    (scores_tbl, scores_row, on_conflict), (leads_tbl, leads_row, _) = fake.log
    assert (scores_tbl, on_conflict) == ("lead_scores", "lead_id")
    assert scores_row["lead_id"] == "lead-1"
    assert scores_row["total"] == 87
    assert "scored_at" in scores_row
    assert leads_tbl == "leads"
    assert leads_row == {"score": 87}
