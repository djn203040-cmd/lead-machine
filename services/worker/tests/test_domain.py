from leadmachine.website.domain import (
    _apex,
    classify_domain,
    classify_from_fetch,
)
from leadmachine.website.models import DomainStatus, FetchResult

from .conftest import FakeResolver


def test_apex() -> None:
    assert _apex("www.eksempel.dk") == "eksempel.dk"
    assert _apex("shop.sub.eksempel.dk") == "eksempel.dk"
    assert _apex("eksempel.dk") == "eksempel.dk"


def test_no_address_is_dead() -> None:
    resolver = FakeResolver(addr_map={"gone.dk": []})
    assert classify_domain("gone.dk", resolver) is DomainStatus.DEAD


def test_parking_nameserver_is_parked() -> None:
    resolver = FakeResolver(ns_map={"forsale.dk": ["ns1.sedoparking.com.", "ns2.sedoparking.com."]})
    assert classify_domain("forsale.dk", resolver) is DomainStatus.PARKED


def test_live_domain() -> None:
    assert classify_domain("eksempel.dk", FakeResolver()) is DomainStatus.LIVE


def test_classify_from_fetch() -> None:
    assert classify_from_fetch(FetchResult(final_url="x", status=0, failed=True)) is DomainStatus.DEAD
    assert classify_from_fetch(FetchResult(final_url="x", status=404)) is DomainStatus.DEAD
    assert (
        classify_from_fetch(FetchResult(final_url="https://dan.com/buy/x.dk", status=200))
        is DomainStatus.PARKED
    )
    parked = FetchResult(final_url="https://x.dk", status=200, html="<h1>This domain is for sale</h1>")
    assert classify_from_fetch(parked) is DomainStatus.PARKED
    live = FetchResult(final_url="https://x.dk", status=200, html="<h1>Velkommen</h1>")
    assert classify_from_fetch(live) is None
