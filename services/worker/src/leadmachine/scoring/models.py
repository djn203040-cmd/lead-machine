"""Dataclasses for lead scoring (M4).

The scorer turns the signals already attached to a lead (``leads`` columns +
``lead_enrichment`` jsonb) into an explainable 0–100 "needs a website now"
score. Inputs only — no network — so the whole milestone is testable here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCORE_VERSION = 1  # bump when the rubric shape changes (lets the UI migrate)


@dataclass(slots=True)
class LeadToScore:
    """Minimal view of a lead the scorer needs.

    ``website`` / ``social`` / ``financial`` are the matching ``lead_enrichment``
    jsonb payloads (may be empty dicts when a lead hasn't been enriched yet).
    """

    lead_id: str
    website_need: str = "unknown"
    branchekode: str | None = None
    employees_band: str | None = None
    employees_exact: int | None = None
    founded_at: str | None = None  # ISO date "YYYY-MM-DD"
    cvr_status: str | None = None
    reklamebeskyttet: bool = False
    website: dict[str, Any] = field(default_factory=dict)  # lead_enrichment.website
    social: dict[str, Any] = field(default_factory=dict)  # lead_enrichment.social
    financial: dict[str, Any] = field(default_factory=dict)  # lead_enrichment.financial


@dataclass(slots=True)
class FactorScore:
    """One factor's contribution to the total, with an explainable trail."""

    points: int
    max: int
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScoreBreakdown:
    """Full, explainable score for a lead (persisted to ``lead_scores.breakdown``)."""

    total: int
    factors: dict[str, FactorScore] = field(default_factory=dict)
    gated: bool = False
    gate_reason: str | None = None
    version: int = SCORE_VERSION

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "version": self.version,
            "total": self.total,
            "gated": self.gated,
            "factors": {k: v.as_dict() for k, v in self.factors.items()},
        }
        if self.gate_reason:
            out["gate_reason"] = self.gate_reason
        return out
