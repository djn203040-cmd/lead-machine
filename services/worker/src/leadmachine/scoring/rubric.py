"""The website-selling scoring rubric (M4, PLAN §5).

Weights sum to 100 across five factors — **website-need 45, budget 20,
presence 15, industry 12, recency 8** — and the whole rubric is *inverted* vs
the old leadforge: **no / dead / parked / facebook-only / bad site = best lead.**

All numbers live on :class:`Weights` so they are tunable from the database:
:meth:`Weights.from_criteria` overlays the seeded ``scoring_criteria`` rows, so
weights can be retuned (or a signal disabled) without a code change.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date
from typing import Any

from ..cvr.branchekoder import all_branches, by_code, normalize_code
from ..cvr.query import ACTIVE_STATUSES
from ..financial.estimate import band_midpoint
from .models import FactorScore

# Buckets where the business has no usable site at all → max website-need.
_FULL_NEED_FIELD: dict[str, str] = {
    "none": "w_none",
    "dead": "w_dead_parked",
    "parked": "w_dead_parked",
    "facebook_only": "w_facebook",
}

# DB07 2-digit divisions our catalog targets — a non-catalogued code in one of
# these is "marginal" (local-service adjacent); anything else is "poor".
_CATALOG_DIVISIONS: frozenset[str] = frozenset(b.code[:2] for b in all_branches())

OUTDATED_COPYRIGHT_GAP = 3  # footer year this many years old ⇒ "old copyright"
RECENT_FOUNDED_YEARS = 3
MID_FOUNDED_YEARS = 8


@dataclass(slots=True)
class Weights:
    """Every tunable number in the rubric (defaults = PLAN §5).

    Factor caps sum to 100. The ``cap_*`` fields bound each factor; the rest are
    the per-signal points summed within a factor.
    """

    # factor caps (sum = 100)
    cap_website: int = 45
    cap_budget: int = 20
    cap_presence: int = 15
    cap_industry: int = 12
    cap_recency: int = 8

    # website-need buckets
    w_none: int = 45  # criterion: no_website
    w_dead_parked: int = 45  # criterion: dead_or_parked
    w_facebook: int = 45  # criterion: facebook_only
    w_bad_floor: int = 23  # criterion: bad_website (floor; capped at cap_website)
    w_outdated: int = 22
    w_modern: int = 4

    # website "bad" sub-signals (sum, capped at cap_website)
    s_no_viewport: int = 12  # criterion: not_mobile_friendly
    s_no_https: int = 10  # criterion: no_https
    s_legacy: int = 8
    s_old_copyright: int = 6
    s_psi_low: int = 6  # criterion: low_pagespeed (<50)
    s_psi_mid: int = 3  # 50–69
    s_one_page: int = 3

    # budget by employee count
    b_solo: int = 4  # 0 / 1 / unknown
    b_2_4: int = 10
    b_5_9: int = 16
    b_10_49: int = 20  # criterion: employees_target (the ideal band)
    b_50_plus: int = 14
    fin_gross: int = 2  # criterion: has_gross_profit
    fin_equity: int = 2

    # presence (markets online → values web)
    p_fb: int = 8  # criterion: cares_online_presence
    p_pixel: int = 7

    # industry tiers
    i_local: int = 12
    i_marginal: int = 6
    i_poor: int = 0

    # recency
    r_active: int = 4
    r_founded_recent: int = 4  # criterion: recently_founded (≤3y)
    r_founded_mid: int = 2  # ≤8y

    @classmethod
    def default(cls) -> "Weights":
        return cls()

    @classmethod
    def from_criteria(cls, rows: list[dict[str, Any]] | None) -> "Weights":
        """Build weights from ``scoring_criteria`` rows.

        For each seeded key: ``is_active = false`` zeroes the signal; a numeric
        ``config.points`` overrides the default. Unknown keys are ignored (they
        stay valid catalog rows for the dashboard); the coarse ``weight``
        (low/medium/high) is a human label, not a numeric override.
        """
        w = cls()
        valid = {f.name for f in fields(cls)}
        for row in rows or []:
            field_name = CRITERION_FIELD.get(row.get("key", ""))
            if field_name is None or field_name not in valid:
                continue
            if row.get("is_active") is False:
                setattr(w, field_name, 0)
                continue
            points = (row.get("config") or {}).get("points")
            if isinstance(points, (int, float)) and not isinstance(points, bool):
                setattr(w, field_name, int(points))
        return w


# Seeded scoring_criteria.key -> the Weights field it tunes.
CRITERION_FIELD: dict[str, str] = {
    "no_website": "w_none",
    "dead_or_parked": "w_dead_parked",
    "facebook_only": "w_facebook",
    "bad_website": "w_bad_floor",
    "not_mobile_friendly": "s_no_viewport",
    "no_https": "s_no_https",
    "low_pagespeed": "s_psi_low",
    "employees_target": "b_10_49",
    "has_gross_profit": "fin_gross",
    "cares_online_presence": "p_fb",
    "recently_founded": "r_founded_recent",
}


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def gate_reason(reklamebeskyttet: bool, cvr_status: str | None) -> str | None:
    """Why a lead must score 0 (hard gate), or ``None`` to score normally.

    Discovery already suppresses these, but we gate defensively. A *missing*
    status is not gated (it would zero otherwise-valid leads); only an
    explicitly non-active status is.
    """
    if reklamebeskyttet:
        return "reklamebeskyttet"
    status = (cvr_status or "").strip().upper()
    if status and status not in ACTIVE_STATUSES:
        return "inactive"
    return None


def _bad_subpoints(
    signals: dict[str, Any], pagespeed: dict[str, Any], w: Weights, year: int
) -> tuple[int, dict[str, int]]:
    points = 0
    detail: dict[str, int] = {}
    if signals.get("has_viewport") is False:
        points += w.s_no_viewport
        detail["no_viewport"] = w.s_no_viewport
    if signals.get("has_https") is False:
        points += w.s_no_https
        detail["no_https"] = w.s_no_https
    if signals.get("legacy_markup"):
        points += w.s_legacy
        detail["legacy"] = w.s_legacy
    copyright_year = signals.get("copyright_year")
    if isinstance(copyright_year, int) and copyright_year <= year - OUTDATED_COPYRIGHT_GAP:
        points += w.s_old_copyright
        detail["old_copyright"] = w.s_old_copyright
    perf = pagespeed.get("performance")
    if isinstance(perf, (int, float)):
        if perf < 50:
            points += w.s_psi_low
            detail["psi_low"] = w.s_psi_low
        elif perf < 70:
            points += w.s_psi_mid
            detail["psi_mid"] = w.s_psi_mid
    if signals.get("is_one_page"):
        points += w.s_one_page
        detail["one_page"] = w.s_one_page
    return points, detail


def score_website_need(
    website_need: str, website: dict[str, Any], w: Weights, today: date
) -> FactorScore:
    """The dominant factor (45). ``none/dead/parked/facebook_only`` max out;
    ``bad`` is graded from its signals; ``outdated``/``modern`` are deprioritized."""
    detail: dict[str, Any] = {"need": website_need}

    if website_need in _FULL_NEED_FIELD:
        points = getattr(w, _FULL_NEED_FIELD[website_need])
    elif website_need == "bad":
        signals = (website or {}).get("signals") or {}
        pagespeed = (website or {}).get("pagespeed") or {}
        raw, sub = _bad_subpoints(signals, pagespeed, w, today.year)
        detail["signals"] = sub
        points = _clamp(raw, w.w_bad_floor, w.cap_website)
        if raw < w.w_bad_floor:
            detail["floored_to"] = w.w_bad_floor
    elif website_need == "outdated":
        points = w.w_outdated
    elif website_need == "modern":
        points = w.w_modern
    else:  # "unknown" or anything unexpected — not yet qualified
        points = 0

    return FactorScore(min(points, w.cap_website), w.cap_website, detail)


def _band_points(employees: int | None, w: Weights) -> tuple[int, dict[str, Any]]:
    if employees is None:
        return w.b_solo, {"employees": None}
    if employees <= 1:
        return w.b_solo, {"employees": employees}
    if employees <= 4:
        return w.b_2_4, {"employees": employees}
    if employees <= 9:
        return w.b_5_9, {"employees": employees}
    if employees <= 49:
        return w.b_10_49, {"employees": employees}
    return w.b_50_plus, {"employees": employees}


def score_budget(
    employees_exact: int | None,
    employees_band: str | None,
    financial: dict[str, Any],
    w: Weights,
) -> FactorScore:
    """Budget proxy (20): employee band (2–49 ideal) + a small financial bump."""
    employees = employees_exact if employees_exact is not None else band_midpoint(employees_band)
    base, detail = _band_points(employees, w)
    detail["band_points"] = base

    bump = 0
    fin = financial or {}
    gross = fin.get("gross_profit")
    equity = fin.get("equity")
    if isinstance(gross, (int, float)) and gross > 0:
        bump += w.fin_gross
    if isinstance(equity, (int, float)) and equity > 0:
        bump += w.fin_equity
    if bump:
        detail["financial_bump"] = bump

    return FactorScore(min(w.cap_budget, base + bump), w.cap_budget, detail)


def score_presence(social: dict[str, Any], w: Weights) -> FactorScore:
    """Cares-about-presence (15): a business that markets online values a site."""
    social = social or {}
    points = 0
    detail: dict[str, Any] = {}
    if social.get("has_fb_page"):
        points += w.p_fb
        detail["has_fb_page"] = True
    if social.get("has_meta_pixel"):
        points += w.p_pixel
        detail["has_meta_pixel"] = True
    return FactorScore(min(w.cap_presence, points), w.cap_presence, detail)


def score_industry(branchekode: str | None, w: Weights) -> FactorScore:
    """Industry fit (12): catalogued local-service verticals score highest."""
    if not branchekode:
        return FactorScore(w.i_poor, w.cap_industry, {"tier": "poor"})
    code = normalize_code(branchekode)
    if by_code(code) is not None:
        tier, points = "local_service", w.i_local
    elif code[:2] in _CATALOG_DIVISIONS:
        tier, points = "marginal", w.i_marginal
    else:
        tier, points = "poor", w.i_poor
    return FactorScore(
        min(points, w.cap_industry), w.cap_industry, {"tier": tier, "branchekode": code}
    )


def _age_years(founded_at: str | None, today: date) -> float | None:
    if not founded_at:
        return None
    try:
        founded = date.fromisoformat(founded_at[:10])
    except ValueError:
        return None
    return (today - founded).days / 365.25


def score_recency(
    cvr_status: str | None, founded_at: str | None, w: Weights, today: date
) -> FactorScore:
    """Recency (8): an active company, bonus for a recent founding."""
    points = 0
    detail: dict[str, Any] = {}
    status = (cvr_status or "").strip().upper()
    if status in ACTIVE_STATUSES or not status:  # missing status: already gated if inactive
        points += w.r_active
        detail["cvr_active"] = True

    age = _age_years(founded_at, today)
    if age is not None:
        detail["age_years"] = round(age, 1)
        if age <= RECENT_FOUNDED_YEARS:
            points += w.r_founded_recent
            detail["founded"] = "recent"
        elif age <= MID_FOUNDED_YEARS:
            points += w.r_founded_mid
            detail["founded"] = "mid"

    return FactorScore(min(w.cap_recency, points), w.cap_recency, detail)
