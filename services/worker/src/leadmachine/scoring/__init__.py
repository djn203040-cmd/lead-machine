"""Lead scoring & qualification gate (M4).

Turns the enriched signals on a lead into an explainable 0–100 "how much can we
realistically save them" score: the offer is 20% of documented savings, so the
size of the prize (savings 40) and how manual the sector is (industry 20) rank
the book. Weights sum to 100 and are tunable from the seeded
``scoring_criteria`` rows without a code change.
"""

from __future__ import annotations

from .models import FactorScore, LeadToScore, ScoreBreakdown, SCORE_VERSION
from .rubric import (
    Weights,
    gate_reason,
    score_industry,
    score_presence,
    score_recency,
    score_savings,
    score_size,
    score_tech,
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
    "score_savings",
    "score_industry",
    "score_tech",
    "score_presence",
    "score_size",
    "score_recency",
    "score_lead",
    "run_scoring",
    "ScoreStats",
    "ScoreWriter",
    "SupabaseScoreWriter",
]
