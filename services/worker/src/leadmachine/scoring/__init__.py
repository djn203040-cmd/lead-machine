"""Lead scoring & qualification gate (M4).

Turns the enriched signals on a lead into an explainable 0–100 "needs a website
now" score, inverted for a website agency: **no / dead / parked / facebook-only
/ bad site = best lead.** Weights (PLAN §5) sum to 100 and are tunable from the
seeded ``scoring_criteria`` rows without a code change.
"""

from __future__ import annotations

from .models import FactorScore, LeadToScore, ScoreBreakdown, SCORE_VERSION
from .rubric import (
    Weights,
    gate_reason,
    score_budget,
    score_industry,
    score_presence,
    score_recency,
    score_website_need,
)
from .score import (
    ScoreStats,
    ScoreWriter,
    SupabaseScoreWriter,
    run_scoring,
    score_lead,
)

__all__ = [
    "LeadToScore",
    "FactorScore",
    "ScoreBreakdown",
    "SCORE_VERSION",
    "Weights",
    "gate_reason",
    "score_website_need",
    "score_budget",
    "score_presence",
    "score_industry",
    "score_recency",
    "score_lead",
    "run_scoring",
    "ScoreStats",
    "ScoreWriter",
    "SupabaseScoreWriter",
]
