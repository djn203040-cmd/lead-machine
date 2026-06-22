"""Angle-generation job (M6).

For each lead, build a Danish prompt from its signals, ask Claude for a
structured sales angle, and upsert it into ``lead_angles``. Orchestration
(:func:`run_angles`) is decoupled from the model (:class:`AnglesClientProtocol`)
and persistence (:class:`AngleWriter`) so it tests against fakes — no key,
no network.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

from .models import Angle, LeadForAngle
from .prompt import build_prompt

# website_need values that mean the lead hasn't been qualified yet.
_UNQUALIFIED = frozenset({"unknown", ""})


@dataclass(slots=True)
class AngleStats:
    seen: int = 0
    generated: int = 0
    skipped: int = 0  # not yet qualified — nothing concrete to pitch
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


class AnglesClientProtocol(Protocol):
    def generate(self, system: str, user: str) -> dict[str, Any]: ...


class AngleWriter(Protocol):
    def write(self, lead_id: str, angle: dict[str, Any]) -> None: ...


def generate_one(lead: LeadForAngle, client: AnglesClientProtocol) -> Angle:
    """Build the prompt, call the model, and parse the angle for one lead."""
    system, user = build_prompt(lead)
    payload = client.generate(system, user)
    return Angle.from_payload(payload)


def run_angles(
    leads: Iterable[LeadForAngle],
    client: AnglesClientProtocol,
    writer: AngleWriter,
    *,
    skip_unqualified: bool = True,
) -> AngleStats:
    """Generate and persist an angle for each lead."""
    stats = AngleStats()
    for lead in leads:
        stats.seen += 1
        if skip_unqualified and lead.website_need in _UNQUALIFIED:
            stats.skipped += 1
            continue
        try:
            angle = generate_one(lead, client)
        except Exception:
            stats.errors += 1
            continue
        try:
            writer.write(lead.lead_id, angle.as_row())
        except Exception:
            stats.errors += 1
            continue
        stats.generated += 1
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseAngleWriter:
    """Upserts a generated angle into ``lead_angles`` (1:1 with leads)."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def write(self, lead_id: str, angle: dict[str, Any]) -> None:
        row = {"lead_id": lead_id, "generated_at": _now_iso(), **angle}
        self.client.table("lead_angles").upsert(row, on_conflict="lead_id").execute()
