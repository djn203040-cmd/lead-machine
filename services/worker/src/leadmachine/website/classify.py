"""Combine all signals into a ``website_need`` label + evidence (M2, issue #21).

The need ladder (best lead → worst lead for a website agency):

    none > dead > parked > facebook_only > bad > outdated > modern

`none`/`facebook_only`/`free_subdomain(→none)` come straight from the resolver;
`dead`/`parked` from DNS + fetch; the live-site quality tiers (`bad` /
`outdated` / `modern`) from static signals + (optional) PageSpeed.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from .models import (
    DomainStatus,
    PageSpeedResult,
    ResolveResult,
    WebsiteAssessment,
    WebsiteSignals,
)

OUTDATED_COPYRIGHT_GAP = 3  # hardcoded footer year this many years old ⇒ outdated


def _social_payload(signals: WebsiteSignals | None, resolve: ResolveResult) -> dict[str, Any]:
    social: dict[str, Any] = {}
    if resolve.kind == "social":
        social = {"has_fb_page": True, "fb_url": resolve.url, "source": "cvr_website"}
    if signals:
        if signals.has_fb_link:
            social.setdefault("has_fb_page", True)
            if signals.fb_url:
                social.setdefault("fb_url", signals.fb_url)
        if signals.has_meta_pixel:
            social["has_meta_pixel"] = True
    return social


def _quality_need(signals: WebsiteSignals | None, psi: PageSpeedResult | None, current_year: int) -> tuple[str, list[str]]:
    reasons: list[str] = []
    bad = False
    if signals is not None:
        if not signals.has_viewport:
            bad = True
            reasons.append("no_viewport")
        if not signals.has_https:
            bad = True
            reasons.append("no_https")
        if signals.legacy_markup:
            bad = True
            reasons.extend(signals.legacy_reasons or ["legacy_markup"])
    if psi is not None and psi.performance is not None and psi.performance < 50:
        bad = True
        reasons.append("psi_perf_low")
    if bad:
        return "bad", reasons

    outdated = False
    if signals and signals.copyright_year and signals.copyright_year <= current_year - OUTDATED_COPYRIGHT_GAP:
        outdated = True
        reasons.append(f"old_copyright_{signals.copyright_year}")
    if psi is not None and psi.performance is not None and 50 <= psi.performance < 70:
        outdated = True
        reasons.append("psi_perf_mid")
    if signals and signals.is_one_page:
        reasons.append("one_page")
    return ("outdated" if outdated else "modern"), reasons


def assess(
    resolve: ResolveResult,
    *,
    domain_status: DomainStatus | None = None,
    signals: WebsiteSignals | None = None,
    psi: PageSpeedResult | None = None,
    fetch_failed: bool = False,
    not_independent: bool = False,
    current_year: int | None = None,
) -> WebsiteAssessment:
    year = current_year or date.today().year
    evidence: dict[str, Any] = {"resolved": resolve.as_dict()}

    if resolve.kind == "none":
        return WebsiteAssessment("none", evidence)
    if resolve.kind == "social":
        return WebsiteAssessment("facebook_only", evidence, _social_payload(None, resolve))
    if resolve.kind == "free_subdomain":
        evidence["note"] = "free_subdomain_no_real_site"
        return WebsiteAssessment("none", evidence)

    # Lives on a shared "group" platform — not the business's own domain.
    if not_independent:
        evidence["note"] = "not_independent_platform"
        if resolve.host:
            evidence["platform_host"] = resolve.host
        return WebsiteAssessment("not_independent", evidence, _social_payload(signals, resolve))

    # Real custom-domain site.
    if fetch_failed:
        evidence["note"] = "fetch_failed"
        return WebsiteAssessment("dead", evidence)
    if domain_status == DomainStatus.DEAD:
        return WebsiteAssessment("dead", evidence)
    if domain_status == DomainStatus.PARKED:
        return WebsiteAssessment("parked", evidence)

    need, reasons = _quality_need(signals, psi, year)
    if signals is not None:
        evidence["signals"] = signals.as_dict()
    if psi is not None:
        evidence["pagespeed"] = psi.as_dict()
    evidence["reasons"] = reasons
    return WebsiteAssessment(need, evidence, _social_payload(signals, resolve))
