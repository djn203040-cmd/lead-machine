"""Scoring job (M4).

Composes the per-factor rubric into a single 0–100 score + explainable
breakdown for each lead, then persists ``leads.score`` and an upsert into
``lead_scores``. Pure computation over signals already on the lead, so it runs
with no network and is fully testable against fakes.

Orchestration (:func:`run_scoring`) is decoupled from persistence (the
:class:`ScoreWriter` Protocol) and from the rubric weights, so behaviour is
testable and weights are tunable from ``scoring_criteria``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable, Protocol

from .models import LeadToScore, ScoreBreakdown
from .rubric import (
    Weights,
    gate_reason,
    score_budget,
    score_industry,
    score_presence,
    score_recency,
    score_website_need,
)


@dataclass(slots=True)
class ScoreStats:
    seen: int = 0
    scored: int = 0
    gated: int = 0  # hard-gated to 0 (reklamebeskyttet / inactive)
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class ScoreWriter(Protocol):
    """Persistence boundary for a lead's score."""

    def write(self, lead_id: str, total: int, breakdown: dict[str, Any]) -> None: ...


def score_lead(
    lead: LeadToScore, weights: Weights | None = None, today: date | None = None
) -> ScoreBreakdown:
    """Score a single lead. Hard-gated leads return total 0 with a reason."""
    w = weights or Weights()
    today = today or date.today()

    reason = gate_reason(lead.reklamebeskyttet, lead.cvr_status, lead.phone)
    if reason is not None:
        return ScoreBreakdown(total=0, gated=True, gate_reason=reason)

    factors = {
        "website_need": score_website_need(lead.website_need, lead.website, w, today),
        "budget": score_budget(lead.employees_exact, lead.employees_band, lead.financial, w),
        "presence": score_presence(lead.social, w),
        "industry": score_industry(lead.branchekode, w),
        "recency": score_recency(lead.cvr_status, lead.founded_at, w, today),
    }
    total = max(0, min(100, sum(f.points for f in factors.values())))
    return ScoreBreakdown(total=total, factors=factors)


def run_scoring(
    leads: Iterable[LeadToScore],
    writer: ScoreWriter,
    *,
    weights: Weights | None = None,
    today: date | None = None,
) -> ScoreStats:
    """Score every lead and persist the result."""
    w = weights or Weights()
    today = today or date.today()
    stats = ScoreStats()
    for lead in leads:
        stats.seen += 1
        try:
            breakdown = score_lead(lead, w, today)
        except Exception:
            stats.errors += 1
            continue
        try:
            writer.write(lead.lead_id, breakdown.total, breakdown.as_dict())
        except Exception:
            stats.errors += 1
            continue
        if breakdown.gated:
            stats.gated += 1
        else:
            stats.scored += 1
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseScoreWriter:
    """Upserts ``lead_scores`` and mirrors the total onto ``leads.score``."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def write(self, lead_id: str, total: int, breakdown: dict[str, Any]) -> None:
        self.client.table("lead_scores").upsert(
            {
                "lead_id": lead_id,
                "total": total,
                "breakdown": breakdown,
                "scored_at": _now_iso(),
            },
            on_conflict="lead_id",
        ).execute()
        self.client.table("leads").update({"score": total}).eq("id", lead_id).execute()
