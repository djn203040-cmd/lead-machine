"""Tests for lead scoring (M4) — pure computation, no network."""

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
    score_budget,
    score_industry,
    score_lead,
    score_presence,
    score_recency,
    score_website_need,
)
from leadmachine.scoring.rubric import CRITERION_FIELD

from .conftest import FakeScoreWriter, FakeSupabase

TODAY = date(2026, 6, 22)
W = Weights()

# A fully "bad" live site: every quality signal fires.
BAD_FULL = {
    "signals": {
        "has_viewport": False,
        "has_https": False,
        "legacy_markup": True,
        "copyright_year": 2010,
        "is_one_page": True,
    },
    "pagespeed": {"performance": 40},
}


# --- rubric invariants -----------------------------------------------------
def test_factor_caps_sum_to_100() -> None:
    assert W.cap_website + W.cap_budget + W.cap_presence + W.cap_industry + W.cap_recency == 100


def test_every_seeded_criterion_maps_to_a_real_weight_field() -> None:
    valid = {f.name for f in fields(Weights)}
    assert set(CRITERION_FIELD.values()) <= valid


# --- website-need factor (45) ----------------------------------------------
@pytest.mark.parametrize("need", ["none", "dead", "parked", "facebook_only"])
def test_no_usable_site_maxes_website_need(need: str) -> None:
    fs = score_website_need(need, {}, W, TODAY)
    assert fs.points == 45
    assert fs.max == 45


def test_bad_site_sums_signals_and_caps_at_45() -> None:
    fs = score_website_need("bad", BAD_FULL, W, TODAY)
    # 12 + 10 + 8 + 6 + 6 + 3 = 45
    assert fs.points == 45
    assert fs.detail["signals"] == {
        "no_viewport": 12,
        "no_https": 10,
        "legacy": 8,
        "old_copyright": 6,
        "psi_low": 6,
        "one_page": 3,
    }


def test_bad_site_with_one_signal_is_floored() -> None:
    fs = score_website_need("bad", {"signals": {"has_https": False, "has_viewport": True}}, W, TODAY)
    assert fs.points == W.w_bad_floor == 23
    assert fs.detail["floored_to"] == 23


def test_pagespeed_mid_band_scores_less_than_low() -> None:
    mid = score_website_need("bad", {"signals": {"has_viewport": False}, "pagespeed": {"performance": 60}}, W, TODAY)
    # no_viewport 12 + psi_mid 3 = 15 -> floored to 23
    assert mid.detail["signals"]["psi_mid"] == 3


def test_outdated_and_modern_and_unknown() -> None:
    assert score_website_need("outdated", {}, W, TODAY).points == 22
    assert score_website_need("modern", {}, W, TODAY).points == 4
    assert score_website_need("unknown", {}, W, TODAY).points == 0


def test_website_need_ladder_is_monotonic() -> None:
    points = {
        need: score_website_need(need, BAD_FULL if need == "bad" else {}, W, TODAY).points
        for need in ("none", "bad", "outdated", "modern", "unknown")
    }
    assert points["none"] >= points["bad"] >= points["outdated"] >= points["modern"] >= points["unknown"]


def test_old_copyright_only_counts_when_old_enough() -> None:
    recent = score_website_need("bad", {"signals": {"has_viewport": False, "copyright_year": 2026}}, W, TODAY)
    assert "old_copyright" not in recent.detail["signals"]


# --- budget factor (20) ----------------------------------------------------
@pytest.mark.parametrize(
    "band,expected",
    [
        ("ANTAL_0_0", 4),
        ("ANTAL_1_1", 4),
        ("ANTAL_2_4", 10),
        ("ANTAL_5_9", 16),
        ("ANTAL_10_19", 20),
        ("ANTAL_20_49", 20),
        ("ANTAL_50_99", 14),
        (None, 4),
    ],
)
def test_budget_band_points(band: str | None, expected: int) -> None:
    assert score_budget(None, band, {}, W).points == expected


def test_budget_exact_overrides_band() -> None:
    # exact=7 (5–9 → 16) wins over the band's midpoint
    assert score_budget(7, "ANTAL_50_99", {}, W).points == 16


def test_budget_financial_bump_is_capped() -> None:
    fs = score_budget(14, None, {"gross_profit": 500_000, "equity": 200_000}, W)
    # band 20 + bump 4, capped at 20
    assert fs.points == 20


def test_budget_financial_bump_helps_small_companies() -> None:
    fs = score_budget(3, None, {"gross_profit": 100_000, "equity": 50_000}, W)
    assert fs.points == 14  # 10 + 4
    assert fs.detail["financial_bump"] == 4


def test_budget_ignores_non_positive_financials() -> None:
    fs = score_budget(3, None, {"gross_profit": -1, "equity": 0}, W)
    assert fs.points == 10
    assert "financial_bump" not in fs.detail


# --- presence factor (15) --------------------------------------------------
def test_presence_fb_and_pixel() -> None:
    assert score_presence({"has_fb_page": True}, W).points == 8
    assert score_presence({"has_meta_pixel": True}, W).points == 7
    assert score_presence({"has_fb_page": True, "has_meta_pixel": True}, W).points == 15
    assert score_presence({}, W).points == 0


# --- industry factor (12) --------------------------------------------------
def test_industry_tiers() -> None:
    assert score_industry("962100", W).points == 12  # catalogued (hairdresser)
    assert score_industry("96.21.00", W).points == 12  # dotted form normalizes
    assert score_industry("960230", W).points == 6  # same division, not catalogued
    assert score_industry("010000", W).points == 0  # unrelated division
    assert score_industry(None, W).points == 0


# --- recency factor (8) ----------------------------------------------------
def test_recency_active_plus_recent_founding() -> None:
    fs = score_recency("NORMAL", "2024-06-01", W, TODAY)
    assert fs.points == 8  # active 4 + recent 4
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
        website_need="none",
        branchekode="962100",
        employees_exact=12,
        founded_at="2024-06-01",
        cvr_status="NORMAL",
        phone=["12345678"],
        social={"has_fb_page": True, "has_meta_pixel": True},
        financial={"gross_profit": 500_000, "equity": 200_000},
    )
    base.update(kw)
    return LeadToScore(**base)


def test_score_lead_perfect_lead_is_100() -> None:
    bd = score_lead(_ideal_lead(), W, TODAY)
    assert bd.total == 100
    assert not bd.gated
    assert set(bd.factors) == {"website_need", "budget", "presence", "industry", "recency"}
    assert bd.factors["website_need"].points == 45


def test_score_lead_gated_lead_scores_zero() -> None:
    bd = score_lead(_ideal_lead(reklamebeskyttet=True), W, TODAY)
    assert bd.total == 0
    assert bd.gated
    assert bd.gate_reason == "reklamebeskyttet"
    assert bd.factors == {}


def test_score_lead_modern_site_scores_low_on_website() -> None:
    weak = score_lead(_ideal_lead(website_need="modern"), W, TODAY).total
    strong = score_lead(_ideal_lead(website_need="none"), W, TODAY).total
    assert weak < strong  # a modern site is a worse lead for a web agency


def test_breakdown_as_dict_shape() -> None:
    out = score_lead(_ideal_lead(), W, TODAY).as_dict()
    assert out["version"] == 1
    assert out["total"] == 100
    assert out["gated"] is False
    assert out["factors"]["industry"] == {"points": 12, "max": 12, "detail": {"tier": "local_service", "branchekode": "962100"}}


# --- weights tunable from scoring_criteria ---------------------------------
def test_from_criteria_defaults_match_seed() -> None:
    seed = [
        {"key": k, "weight": "high", "config": None, "is_active": True} for k in CRITERION_FIELD
    ]
    assert Weights.from_criteria(seed) == Weights()


def test_from_criteria_config_points_override() -> None:
    w = Weights.from_criteria([{"key": "no_website", "config": {"points": 30}, "is_active": True}])
    assert w.w_none == 30
    assert score_website_need("none", {}, w, TODAY).points == 30


def test_from_criteria_inactive_disables_signal() -> None:
    w = Weights.from_criteria([{"key": "low_pagespeed", "config": None, "is_active": False}])
    assert w.s_psi_low == 0


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
