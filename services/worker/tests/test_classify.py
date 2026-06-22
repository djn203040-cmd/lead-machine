from leadmachine.website.classify import assess
from leadmachine.website.models import (
    DomainStatus,
    PageSpeedResult,
    ResolveResult,
    WebsiteSignals,
)

URL = ResolveResult(kind="url", url="https://x.dk/", host="x.dk")
YEAR = 2026


def test_resolver_buckets() -> None:
    assert assess(ResolveResult(kind="none")).website_need == "none"
    fb = assess(ResolveResult(kind="social", url="https://facebook.com/x", host="facebook.com"))
    assert fb.website_need == "facebook_only"
    assert fb.social["has_fb_page"] is True
    assert assess(ResolveResult(kind="free_subdomain", host="x.wixsite.com")).website_need == "none"


def test_dead_and_parked() -> None:
    assert assess(URL, fetch_failed=True).website_need == "dead"
    assert assess(URL, domain_status=DomainStatus.DEAD).website_need == "dead"
    assert assess(URL, domain_status=DomainStatus.PARKED).website_need == "parked"


def test_bad_when_no_viewport_or_https_or_legacy() -> None:
    s = WebsiteSignals(has_viewport=False, has_https=True)
    assert assess(URL, domain_status=DomainStatus.LIVE, signals=s, current_year=YEAR).website_need == "bad"
    s2 = WebsiteSignals(has_viewport=True, has_https=True, legacy_markup=True, legacy_reasons=["font_tag"])
    a2 = assess(URL, domain_status=DomainStatus.LIVE, signals=s2, current_year=YEAR)
    assert a2.website_need == "bad"
    assert "font_tag" in a2.evidence["reasons"]


def test_modern_site() -> None:
    s = WebsiteSignals(has_viewport=True, has_https=True, copyright_year=2026)
    a = assess(URL, domain_status=DomainStatus.LIVE, signals=s, current_year=YEAR)
    assert a.website_need == "modern"


def test_outdated_from_old_copyright() -> None:
    s = WebsiteSignals(has_viewport=True, has_https=True, copyright_year=2018)
    a = assess(URL, domain_status=DomainStatus.LIVE, signals=s, current_year=YEAR)
    assert a.website_need == "outdated"


def test_pagespeed_modulates_tier() -> None:
    s = WebsiteSignals(has_viewport=True, has_https=True)
    bad = assess(URL, domain_status=DomainStatus.LIVE, signals=s, psi=PageSpeedResult(performance=40), current_year=YEAR)
    assert bad.website_need == "bad"
    mid = assess(URL, domain_status=DomainStatus.LIVE, signals=s, psi=PageSpeedResult(performance=60), current_year=YEAR)
    assert mid.website_need == "outdated"
    good = assess(URL, domain_status=DomainStatus.LIVE, signals=s, psi=PageSpeedResult(performance=95), current_year=YEAR)
    assert good.website_need == "modern"


def test_social_payload_from_signals() -> None:
    s = WebsiteSignals(has_viewport=True, has_https=True, has_fb_link=True, fb_url="https://facebook.com/x", has_meta_pixel=True)
    a = assess(URL, domain_status=DomainStatus.LIVE, signals=s, current_year=YEAR)
    assert a.social == {"has_fb_page": True, "fb_url": "https://facebook.com/x", "has_meta_pixel": True}
