from leadmachine.website.models import FetchResult, LeadToQualify, PageSpeedResult
from leadmachine.website.qualify import (
    SupabaseWebsiteWriter,
    WebsiteDeps,
    qualify_one,
    run_qualification,
)

from .conftest import (
    FakeResolver,
    FakeSupabase,
    FakeWebsiteWriter,
    MockPageSpeed,
    StubFetcher,
)

MODERN_HTML = (
    '<html><head><meta name="viewport" content="width=device-width"></head>'
    "<body><h1>Velkommen</h1></body></html>"
)
NOVIEWPORT_HTML = "<html><head></head><body><h1>Gammel side</h1></body></html>"


def _modern_fetch() -> FetchResult:
    return FetchResult(final_url="https://minsalon.dk/", status=200, html=MODERN_HTML)


def _deps(fetch_result: FetchResult, resolver: FakeResolver | None = None, psi=None) -> WebsiteDeps:
    return WebsiteDeps(fetcher=StubFetcher(fetch_result), resolver=resolver or FakeResolver(), pagespeed=psi)


def test_no_website() -> None:
    a = qualify_one(LeadToQualify("L", None), _deps(_modern_fetch()))
    assert a.website_need == "none"


def test_facebook_only_skips_network() -> None:
    fetcher = StubFetcher(_modern_fetch())
    deps = WebsiteDeps(fetcher=fetcher, resolver=FakeResolver())
    a = qualify_one(LeadToQualify("L", "https://facebook.com/minsalon"), deps)
    assert a.website_need == "facebook_only"
    assert fetcher.fetched == []  # no fetch for social-only


def test_dead_domain() -> None:
    deps = _deps(_modern_fetch(), resolver=FakeResolver(addr_map={"gone.dk": []}))
    a = qualify_one(LeadToQualify("L", "gone.dk"), deps)
    assert a.website_need == "dead"


def test_parked_domain() -> None:
    deps = _deps(_modern_fetch(), resolver=FakeResolver(ns_map={"forsale.dk": ["ns1.bodis.com"]}))
    a = qualify_one(LeadToQualify("L", "forsale.dk"), deps)
    assert a.website_need == "parked"


def test_live_modern_site_calls_pagespeed() -> None:
    psi = MockPageSpeed(PageSpeedResult(performance=95, seo=90))
    deps = _deps(_modern_fetch(), psi=psi)
    a = qualify_one(LeadToQualify("L", "minsalon.dk"), deps)
    assert a.website_need == "modern"
    assert psi.calls == ["https://minsalon.dk/"]  # tier-1 passed -> PSI spent


def test_bad_site_skips_pagespeed() -> None:
    psi = MockPageSpeed(PageSpeedResult(performance=95))
    bad = FetchResult(final_url="https://gammel.dk/", status=200, html=NOVIEWPORT_HTML)
    deps = _deps(bad, psi=psi)
    a = qualify_one(LeadToQualify("L", "gammel.dk"), deps)
    assert a.website_need == "bad"
    assert psi.calls == []  # tier-1 failed -> no PSI quota spent


def test_run_qualification_tallies_and_writes() -> None:
    writer = FakeWebsiteWriter()
    deps = _deps(_modern_fetch())
    leads = [
        LeadToQualify("A", None),
        LeadToQualify("B", "https://facebook.com/x"),
        LeadToQualify("C", "minsalon.dk"),
    ]
    stats = run_qualification(leads, deps, writer)

    assert stats.seen == 3
    assert stats.errors == 0
    assert stats.by_need["none"] == 1
    assert stats.by_need["facebook_only"] == 1
    assert stats.by_need["modern"] == 1
    assert set(writer.writes) == {"A", "B", "C"}


def test_supabase_writer_updates_lead_and_enrichment() -> None:
    fake = FakeSupabase()
    SupabaseWebsiteWriter(fake).write("lead-1", "bad", {"reasons": ["no_viewport"]}, {"has_fb_page": True})

    assert len(fake.log) == 2
    (t1, row1, _), (t2, row2, oc2) = fake.log
    assert t1 == "leads"
    assert row1 == {"website_need": "bad"}
    assert (t2, oc2) == ("lead_enrichment", "lead_id")
    assert row2["website"]["reasons"] == ["no_viewport"]
    assert row2["social"] == {"has_fb_page": True}
    assert "last_enriched_at" in row2
