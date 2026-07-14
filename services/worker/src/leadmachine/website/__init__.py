"""Website qualification (M2) — the core "no/bad website" qualifier.

For each lead, determine whether the business has no website / a dead / parked /
Facebook-only / bad-outdated site (the strongest buying signal for a website
agency) and attach a ``website_need`` label + structured evidence.
"""

from __future__ import annotations

from .analyze import analyze
from .classify import assess
from .discover import BraveSearchClient, WebsiteDiscoverer
from .domain import DnsResolver, Resolver, classify_domain, classify_from_fetch
from .fetch import HttpxFetcher, WebsiteFetcher
from .grade import ClaudeGrader
from .models import (
    DiscoveryResult,
    DomainStatus,
    FetchResult,
    LeadToQualify,
    PageSpeedResult,
    ResolveResult,
    WebsiteAssessment,
    WebsiteQuality,
    WebsiteSignals,
)
from .pagespeed import PageSpeedClient, parse_pagespeed
from .phones import best_phone_type, classify_phone, extract_phones, normalize_phone
from .qualify import (
    QualifyStats,
    SupabaseWebsiteWriter,
    WebsiteDeps,
    WebsiteWriter,
    qualify_one,
    run_qualification,
)
from .resolve import resolve_website

__all__ = [
    "analyze",
    "assess",
    "resolve_website",
    "classify_domain",
    "classify_from_fetch",
    "DnsResolver",
    "Resolver",
    "HttpxFetcher",
    "WebsiteFetcher",
    "PageSpeedClient",
    "parse_pagespeed",
    "best_phone_type",
    "classify_phone",
    "extract_phones",
    "normalize_phone",
    "BraveSearchClient",
    "WebsiteDiscoverer",
    "ClaudeGrader",
    "qualify_one",
    "run_qualification",
    "QualifyStats",
    "WebsiteDeps",
    "WebsiteWriter",
    "SupabaseWebsiteWriter",
    "DomainStatus",
    "FetchResult",
    "ResolveResult",
    "WebsiteSignals",
    "PageSpeedResult",
    "WebsiteAssessment",
    "WebsiteQuality",
    "DiscoveryResult",
    "LeadToQualify",
]
