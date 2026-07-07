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

from .analyze import analyze
from .classify import _social_payload, assess
from .domain import Resolver, classify_domain, classify_from_fetch
from .fetch import WebsiteFetcher
from .independence import is_not_independent
from .models import DomainStatus, LeadToQualify, ResolveResult, WebsiteAssessment
from .resolve import resolve_website

NEEDS = ("none", "dead", "parked", "facebook_only", "not_independent", "bad", "outdated", "modern")


@dataclass(slots=True)
class WebsiteDeps:
    fetcher: WebsiteFetcher
    resolver: Resolver
    pagespeed: Any | None = None  # PageSpeedClient | None
    discoverer: Any | None = None  # WebsiteDiscoverer | None — find a site when CVR has none
    grader: Any | None = None  # ClaudeGrader | None — LLM quality tier for live sites


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
    def write(self, lead_id: str, assessment: WebsiteAssessment) -> None: ...


def _needs_pagespeed(signals: Any) -> bool:
    """Only spend PSI quota on a live site that passes Tier-1 static screens."""
    return bool(signals and signals.has_viewport and signals.has_https and not signals.legacy_markup)


def _pagespeed(deps: WebsiteDeps, signals: Any, final_url: str, stats: QualifyStats | None) -> Any:
    """Spend PSI quota only on a live site that passes the static screens."""
    if deps.pagespeed is None or not _needs_pagespeed(signals):
        return None
    psi = deps.pagespeed.analyze(final_url)
    if stats is not None:
        stats.psi_calls += 1
    return psi


def _grade_into(
    a: WebsiteAssessment, deps: WebsiteDeps, signals: Any, result: Any, psi: Any, url: str
) -> None:
    """Attach an LLM quality tier to a live-site assessment (best-effort)."""
    if deps.grader is None:
        return
    try:
        quality = deps.grader.grade(signals=signals, fetch=result, psi=psi, url=url)
    except Exception:
        return  # grading never fails qualification
    a.website_quality = quality.tier
    a.evidence["quality"] = quality.as_dict()


def _discover_and_grade(
    lead: LeadToQualify, resolve: ResolveResult, deps: WebsiteDeps, stats: QualifyStats | None
) -> WebsiteAssessment | None:
    """Try to find + grade a real site for a lead CVR reported as having none."""
    if deps.discoverer is None:
        return None
    try:
        found = deps.discoverer.discover(lead)
    except Exception:
        return None
    if found is None or found.fetch is None:
        return None

    signals = analyze(found.fetch, host=found.host)
    disc_resolve = ResolveResult(
        kind="url", url=found.url, host=found.host, raw=resolve.raw, confidence="discovered"
    )
    a = assess(disc_resolve, domain_status=DomainStatus.LIVE, signals=signals, psi=None)
    a.evidence["discovery"] = found.as_dict()
    # Keep any social signal the original CVR field carried (e.g. a Facebook URL).
    a.social = {**_social_payload(signals, resolve), **a.social}
    a.website_source = found.source
    a.discovered_url = found.url
    _grade_into(a, deps, signals, found.fetch, None, found.url)
    return a


def qualify_one(lead: LeadToQualify, deps: WebsiteDeps, stats: QualifyStats | None = None) -> WebsiteAssessment:
    resolve = resolve_website(lead.website)
    if resolve.kind in ("none", "social", "free_subdomain"):
        # CVR has no real site — go looking before concluding "none".
        discovered = _discover_and_grade(lead, resolve, deps, stats)
        if discovered is not None:
            return discovered
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

    signals = analyze(result, host=host)
    psi = _pagespeed(deps, signals, result.final_url, stats)
    a = assess(resolve, domain_status=DomainStatus.LIVE, signals=signals, psi=psi)
    a.website_source = "cvr"
    _grade_into(a, deps, signals, result, psi, result.final_url)
    return a


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
            writer.write(lead.lead_id, assessment)
        except Exception:
            stats.errors += 1
            continue
        stats.bump(assessment.website_need)
    return stats


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseWebsiteWriter:
    """Updates ``leads`` (need + discovery provenance + quality) and
    ``lead_enrichment.website``/``.social``."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def write(self, lead_id: str, assessment: WebsiteAssessment) -> None:
        lead_update: dict[str, Any] = {"website_need": assessment.website_need}
        # Provenance + quality: write when present, and clear the discovery
        # columns for a normally-resolved (cvr) site so a re-run can't leave a
        # stale discovered_url behind.
        lead_update["website_source"] = assessment.website_source
        lead_update["discovered_url"] = assessment.discovered_url
        lead_update["website_quality"] = assessment.website_quality
        self.client.table("leads").update(lead_update).eq("id", lead_id).execute()

        row: dict[str, Any] = {
            "lead_id": lead_id,
            "website": assessment.evidence,
            "last_enriched_at": _now_iso(),
        }
        if assessment.social:
            row["social"] = assessment.social
        self.client.table("lead_enrichment").upsert(row, on_conflict="lead_id").execute()
