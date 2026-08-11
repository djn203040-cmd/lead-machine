"""Angle-generation job (M6).

For each lead, build a Danish prompt from its signals, ask Claude for a
structured sales angle, and upsert it into ``lead_angles``. Orchestration
(:func:`run_angles`) is decoupled from the model (:class:`AnglesClientProtocol`)
and persistence (:class:`AngleWriter`) so it tests against fakes — no key,
no network.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Iterable, Protocol

from .models import Angle, LeadForAngle
from .prompt import build_prompt

# website_need values that mean the lead's site was never qualified. Under the
# savings offer this no longer blocks a pitch — the call is about their
# operations, not their website — so it is opt-in via ``skip_unqualified``.
_UNQUALIFIED = frozenset({"unknown", ""})

# One Opus call per lead takes tens of seconds, so a book-wide regeneration run
# sequentially is measured in hours — it has been "the slow tail" of every
# re-enrich. The calls are independent and the SDK retries rate limits itself,
# so a handful in flight turns hours into minutes. Kept modest: we are one
# client sharing an account-wide rate limit.
DEFAULT_CONCURRENCY = 6


@dataclass(slots=True)
class AngleStats:
    seen: int = 0
    generated: int = 0
    skipped: int = 0  # website never qualified, and the caller asked to skip those
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
    skip_unqualified: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> AngleStats:
    """Generate and persist an angle for each lead.

    ``skip_unqualified`` drops leads whose website was never classified. It
    defaults off: the pitch is about the money we can save them, so an
    unqualified website is no longer a reason to stay silent.

    ``concurrency`` is how many leads are in flight at once. Each lead is
    independent — its own prompt, its own row — so the only shared state is the
    tally, which is locked. Pass 1 for a strictly sequential run.
    """
    stats = AngleStats()
    lock = Lock()

    def handle(lead: LeadForAngle) -> None:
        with lock:
            stats.seen += 1
        if skip_unqualified and lead.website_need in _UNQUALIFIED:
            with lock:
                stats.skipped += 1
            return
        try:
            angle = generate_one(lead, client)
            writer.write(lead.lead_id, angle.as_row())
        except Exception:
            with lock:
                stats.errors += 1
            return
        with lock:
            stats.generated += 1

    if concurrency <= 1:
        for lead in leads:
            handle(lead)
        return stats

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        # list() drains the iterator so exceptions surface here, not silently.
        list(pool.map(handle, leads))
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
