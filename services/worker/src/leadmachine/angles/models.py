"""Dataclasses for AI Danish sales-angle generation (M6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_COMPETITOR_ANGLES = ("fomo", "first_mover", "none")


@dataclass(slots=True)
class LeadForAngle:
    """The signals the angle generator needs about one lead.

    ``website`` / ``financial`` / ``social`` are the matching ``lead_enrichment``
    jsonb payloads; ``score_breakdown`` is ``lead_scores.breakdown`` (the
    explainable "why it's a good lead" the prompt grounds itself in).
    """

    lead_id: str
    company_name: str
    city: str | None = None
    branche_text: str | None = None
    website_need: str = "unknown"
    employees: int | None = None
    score: int | None = None
    # 'mobile' (likely the owner's own phone) | 'landline' | 'service' | None.
    # Steers the opener: direct-to-owner pitch vs. gatekeeper variant.
    phone_type: str | None = None
    website: dict[str, Any] = field(default_factory=dict)
    financial: dict[str, Any] = field(default_factory=dict)
    social: dict[str, Any] = field(default_factory=dict)
    score_breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Angle:
    """A generated Danish sales angle, ready to upsert into ``lead_angles``."""

    summary_da: str
    weaknesses_da: str
    angle_da: str
    opening_line_da: str
    cta_da: str = ""
    objections: list[dict[str, str]] = field(default_factory=list)
    competitor_name: str | None = None
    competitor_angle_type: str = "none"

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "Angle":
        """Build from the model's JSON payload, coercing/validating defensively."""
        category = str(data.get("competitor_angle_type") or "none").strip().lower()
        if category not in VALID_COMPETITOR_ANGLES:
            category = "none"
        name = (str(data.get("competitor_name") or "")).strip() or None
        # A competitor name only makes sense for a competitor-based angle.
        if category == "none":
            name = None
        return cls(
            summary_da=str(data.get("summary_da") or "").strip(),
            weaknesses_da=str(data.get("weaknesses_da") or "").strip(),
            angle_da=str(data.get("angle_da") or "").strip(),
            opening_line_da=str(data.get("opening_line_da") or "").strip(),
            cta_da=str(data.get("cta_da") or "").strip(),
            objections=_parse_objections(data.get("objections")),
            competitor_name=name,
            competitor_angle_type=category,
        )

    def as_row(self) -> dict[str, Any]:
        """Column dict for an upsert into ``lead_angles`` (empty strings → null)."""
        return {
            "summary_da": self.summary_da or None,
            "weaknesses_da": self.weaknesses_da or None,
            "angle_da": self.angle_da or None,
            "opening_line_da": self.opening_line_da or None,
            "cta_da": self.cta_da or None,
            # jsonb array of {objection_da, response_da}; always a list so the UI
            # can map over it without null-guarding.
            "objections": self.objections,
            "competitor_name": self.competitor_name,
            "competitor_angle_type": self.competitor_angle_type,
        }


def _parse_objections(raw: Any) -> list[dict[str, str]]:
    """Coerce the model's objections into ≤3 clean {objection_da, response_da}."""
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        objection = str(item.get("objection_da") or "").strip()
        response = str(item.get("response_da") or "").strip()
        if objection and response:
            out.append({"objection_da": objection, "response_da": response})
        if len(out) == 3:
            break
    return out
