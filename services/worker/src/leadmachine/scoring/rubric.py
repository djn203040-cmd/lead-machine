"""The scoring rubric (M4, PLAN §5) — **savings offer, v2**.

We no longer sell websites, so the rubric no longer ranks "who lacks a site".
We follow a business, build systems that remove its manual work, and take 20% of
what is actually saved — so the best lead is simply **the one where the most
money can realistically be saved**, in a sector whose day-to-day is full of the
manual work we remove.

Weights sum to 100 across six factors — **savings 40, industry 20, tech 15,
presence 10, size 8, recency 7**. The website signal survives at 15, demoted
from the old 45: it no longer says what we're selling, only how digitally
mature (and therefore how easy to talk systems with) the business is.

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
from ..financial.savings import estimate_savings
from .models import FactorScore

# DB07 2-digit divisions our catalog targets — a non-catalogued code in one of
# these is "marginal" (local-service adjacent); anything else is "poor".
_CATALOG_DIVISIONS: frozenset[str] = frozenset(b.code[:2] for b in all_branches())

RECENT_FOUNDED_YEARS = 3
MID_FOUNDED_YEARS = 8

# website_need → the Weights field holding its digital-maturity points.
_TECH_FIELD: dict[str, str] = {
    "modern": "t_modern",
    "bad": "t_bad",
    "outdated": "t_outdated",
    "facebook_only": "t_facebook",
    "not_independent": "t_not_independent",
    "none": "t_none",
    "dead": "t_dead_parked",
    "parked": "t_dead_parked",
}


@dataclass(slots=True)
class Weights:
    """Every tunable number in the rubric.

    Factor caps sum to 100. The ``cap_*`` fields bound each factor; the rest are
    the per-signal points summed within a factor.
    """

    # factor caps (sum = 100)
    cap_savings: int = 40
    cap_industry: int = 20
    cap_tech: int = 15
    cap_presence: int = 10
    cap_size: int = 8
    cap_recency: int = 7

    # savings potential, by estimated annual saving (band midpoint, DKK).
    # The curve peaks in the 250k–1M range: big enough that our 20% is a real
    # income, small enough that a local owner still decides alone and fast.
    sav_unknown: int = 12  # criterion: savings_unknown (no revenue signal yet)
    sav_tiny: int = 6  # < 25k — too little to be worth the engagement
    sav_small: int = 14  # 25–50k
    sav_mid: int = 24  # 50–100k
    sav_good: int = 34  # 100–250k
    sav_prime: int = 40  # criterion: savings_potential — 250k–1M, the sweet spot
    sav_large: int = 34  # 1–3M — real money, but a longer, more committee-ish sale
    sav_enterprise: int = 24  # > 3M — outside a one-call-close local business

    # industry tiers — catalogued local service = the manual-work-heavy target
    i_local: int = 20  # criterion: industry_local_service
    i_marginal: int = 10
    i_poor: int = 0

    # digital maturity, read off website_need. A business that is already
    # digital is the *easiest* systems conversation; one with nothing online is
    # the biggest raw upside but the hardest sell — so this runs the other way
    # round from the old website-need rubric.
    t_modern: int = 15  # criterion: digital_mature
    t_bad: int = 11  # criterion: bad_website
    t_outdated: int = 11
    t_facebook: int = 9  # criterion: facebook_only
    t_not_independent: int = 8  # criterion: not_independent
    t_none: int = 5  # criterion: no_website
    t_dead_parked: int = 5  # criterion: dead_or_parked
    t_unknown: int = 6  # not qualified yet — don't punish, don't reward
    t_quality_bonus: int = 3  # live site graded modern/premium

    # presence — markets online ⇒ commercially minded, already spends on growth
    p_fb: int = 4  # criterion: cares_online_presence
    p_pixel: int = 6  # criterion: runs_paid_ads

    # size — headcount as a proxy for how many processes there are to systematise
    z_solo: int = 2  # 0 / 1 / unknown
    z_2_4: int = 5
    z_5_9: int = 7
    z_10_49: int = 8  # criterion: employees_target (the ideal band)
    z_50_plus: int = 6

    # recency
    r_active: int = 4
    r_founded_recent: int = 3  # criterion: recently_founded (≤3y)
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
    "savings_potential": "sav_prime",
    "savings_unknown": "sav_unknown",
    "industry_local_service": "i_local",
    "digital_mature": "t_modern",
    "bad_website": "t_bad",
    "facebook_only": "t_facebook",
    "not_independent": "t_not_independent",
    "no_website": "t_none",
    "dead_or_parked": "t_dead_parked",
    "cares_online_presence": "p_fb",
    "runs_paid_ads": "p_pixel",
    "employees_target": "z_10_49",
    "recently_founded": "r_founded_recent",
}


def gate_reason(
    reklamebeskyttet: bool, cvr_status: str | None, phone: list[str] | None = None
) -> str | None:
    """Why a lead must score 0 (hard gate), or ``None`` to score normally.

    Discovery already suppresses reklamebeskyttet/inactive, but we gate
    defensively. A *missing* status is not gated (it would zero otherwise-valid
    leads); only an explicitly non-active status is. **No phone number** hard-
    gates too: outreach is phone-first, so an uncallable lead is disqualified
    (we hunt CVR → P-enhed → website for a number before this runs).
    """
    if reklamebeskyttet:
        return "reklamebeskyttet"
    status = (cvr_status or "").strip().upper()
    if status and status not in ACTIVE_STATUSES:
        return "inactive"
    if not phone:
        return "no_phone"
    return None


def _savings_points(midpoint: float, w: Weights) -> tuple[int, str]:
    if midpoint < 25_000:
        return w.sav_tiny, "tiny"
    if midpoint < 50_000:
        return w.sav_small, "small"
    if midpoint < 100_000:
        return w.sav_mid, "mid"
    if midpoint < 250_000:
        return w.sav_good, "good"
    if midpoint < 1_000_000:
        return w.sav_prime, "prime"
    if midpoint < 3_000_000:
        return w.sav_large, "large"
    return w.sav_enterprise, "enterprise"


def score_savings(
    financial: dict[str, Any],
    branchekode: str | None,
    w: Weights,
    employees: int | None = None,
) -> FactorScore:
    """The dominant factor (40): how much money we can realistically free up.

    This *is* the deal size — our fee is 20% of it — so it outranks everything
    else. With no revenue signal the lead is unknown rather than bad, and scores
    a neutral middle so it still surfaces for a call.
    """
    savings = estimate_savings(financial, branchekode, employees)
    if savings is None:
        return FactorScore(
            min(w.sav_unknown, w.cap_savings), w.cap_savings, {"band": "unknown"}
        )

    midpoint = (savings.annual_low + savings.annual_high) / 2
    points, band = _savings_points(midpoint, w)
    detail: dict[str, Any] = {
        "band": band,
        "basis": savings.basis,  # 'accounts' (their filing) | 'benchmark' (a guess)
        "pool": savings.pool,  # operating cost base, or estimated revenue
        "annual_low": savings.annual_low,
        "annual_high": savings.annual_high,
        "fee_low": savings.fee_low,
        "fee_high": savings.fee_high,
        "rate": savings.rate,
        "confidence": savings.confidence,
    }
    if savings.capped_by:
        detail["capped_by"] = savings.capped_by
    return FactorScore(min(points, w.cap_savings), w.cap_savings, detail)


def score_industry(branchekode: str | None, w: Weights) -> FactorScore:
    """Industry fit (20): catalogued local-service verticals score highest —
    they run on bookings, shifts, quotes and follow-up, which is exactly the
    manual work the systems remove."""
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


def score_tech(website_need: str, website: dict[str, Any], w: Weights) -> FactorScore:
    """Digital maturity (15): how easy this business is to talk systems with.

    Not a need-signal any more — an indicator. A business already running a real
    site understands tools and buys systems faster; one with nothing online has
    the most manual work but is the slowest, most hands-on sale.
    """
    field_name = _TECH_FIELD.get(website_need)
    points = getattr(w, field_name) if field_name else w.t_unknown
    detail: dict[str, Any] = {"need": website_need}

    tier = ((website or {}).get("quality") or {}).get("tier")
    if tier in ("modern", "premium"):
        points += w.t_quality_bonus
        detail["quality"] = tier

    return FactorScore(min(points, w.cap_tech), w.cap_tech, detail)


def score_presence(social: dict[str, Any], w: Weights) -> FactorScore:
    """Presence (10): a business already spending on reach has budget and intent."""
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


def _size_points(employees: int | None, w: Weights) -> int:
    if employees is None or employees <= 1:
        return w.z_solo
    if employees <= 4:
        return w.z_2_4
    if employees <= 9:
        return w.z_5_9
    if employees <= 49:
        return w.z_10_49
    return w.z_50_plus


def score_size(
    employees_exact: int | None, employees_band: str | None, w: Weights
) -> FactorScore:
    """Size (8): more people ⇒ more coordination, shifts and admin to systematise."""
    employees = employees_exact if employees_exact is not None else band_midpoint(employees_band)
    points = _size_points(employees, w)
    return FactorScore(
        min(points, w.cap_size), w.cap_size, {"employees": employees, "points": points}
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
    """Recency (7): an active company, bonus for a recent founding."""
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
