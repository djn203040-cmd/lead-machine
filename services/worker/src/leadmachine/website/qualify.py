"""Website-qualification job (M2).

Per lead: resolve → DNS classify → fetch (only if live) → analyze → PageSpeed
(only on live real sites that pass static screens) → ``website_need`` label +
evidence. Writes ``leads.website_need`` + ``lead_enrichment.website`` / ``.social``.

Orchestration is decoupled from the network (fetcher / resolver / PageSpeed via
:class:`WebsiteDeps`) and persistence (:class:`WebsiteWriter`) for testing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

from .classify import assess
from .domain import Resolver, classify_domain, classify_from_fetch
from .fetch import WebsiteFetcher
from .independence import is_not_independent
from .models import DomainStatus, LeadToQualify, WebsiteAssessment
from .resolve import resolve_website

NEEDS = ("none", "dead", "parked", "facebook_only", "not_independent", "bad", "outdated", "modern")


@dataclass(slots=True)
class WebsiteDeps:
    fetcher: WebsiteFetcher
    resolver: Resolver
    pagespeed: Any | None = None  # PageSpeedClient | None


@dataclass(slots=True)
class QualifyStats:
    seen: int = 0
    errors: int = 0
    psi_calls: int = 0
    by_need: dict[str, int] = field(default_factory=lambda: {n: 0 for n in NEEDS})

    def bump(self, need: str) -> None:
        self.by_need[need] = self.by_need.get(need, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class WebsiteWriter(Protocol):
    def write(
        self, lead_id: str, website_need: str, website_evidence: dict[str, Any], social: dict[str, Any]
    ) -> None: ...


def _needs_pagespeed(signals: Any) -> bool:
    """Only spend PSI quota on a live site that passes Tier-1 static screens."""
    return bool(signals and signals.has_viewport and signals.has_https and not signals.legacy_markup)


def qualify_one(lead: LeadToQualify, deps: WebsiteDeps, stats: QualifyStats | None = None) -> WebsiteAssessment:
    resolve = resolve_website(lead.website)
    if resolve.kind in ("none", "social", "free_subdomain"):
        return assess(resolve)

    # Footprint test: a live site that isn't on the business's own domain
    # (a sub-page on a shared "group" platform) is a hot lead, not a real site.
    if is_not_independent(resolve.host, resolve.url, lead.company_name):
        return assess(resolve, not_independent=True)

    host = resolve.host or ""
    status = classify_domain(host, deps.resolver)
    if status is DomainStatus.DEAD:
        return assess(resolve, domain_status=DomainStatus.DEAD)
    if status is DomainStatus.PARKED:
        return assess(resolve, domain_status=DomainStatus.PARKED)

    result = deps.fetcher.fetch(resolve.url or host)
    refined = classify_from_fetch(result)
    if refined is DomainStatus.DEAD:
        return assess(resolve, fetch_failed=True)
    if refined is DomainStatus.PARKED:
        return assess(resolve, domain_status=DomainStatus.PARKED)

    from .analyze import analyze

    signals = analyze(result, host=host)
    psi = None
    if deps.pagespeed is not None and _needs_pagespeed(signals):
        psi = deps.pagespeed.analyze(result.final_url)
        if stats is not None:
            stats.psi_calls += 1
    return assess(resolve, domain_status=DomainStatus.LIVE, signals=signals, psi=psi)


def run_qualification(
    leads: Iterable[LeadToQualify], deps: WebsiteDeps, writer: WebsiteWriter
) -> QualifyStats:
    stats = QualifyStats()
    for lead in leads:
        stats.seen += 1
        try:
            assessment = qualify_one(lead, deps, stats)
        except Exception:
            stats.errors += 1
            continue
        try:
            writer.write(lead.lead_id, assessment.website_need, assessment.evidence, assessment.social)
        except Exception:
            stats.errors += 1
            continue
        stats.bump(assessment.website_need)
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseWebsiteWriter:
    """Updates ``leads.website_need`` + ``lead_enrichment.website``/``.social``."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def write(
        self, lead_id: str, website_need: str, website_evidence: dict[str, Any], social: dict[str, Any]
    ) -> None:
        self.client.table("leads").update({"website_need": website_need}).eq("id", lead_id).execute()
        row: dict[str, Any] = {
            "lead_id": lead_id,
            "website": website_evidence,
            "last_enriched_at": _now_iso(),
        }
        if social:
            row["social"] = social
        self.client.table("lead_enrichment").upsert(row, on_conflict="lead_id").execute()
