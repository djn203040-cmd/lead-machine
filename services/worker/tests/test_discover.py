"""Tests for website discovery (find a real site when CVR has none)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from leadmachine.website.discover import (
    BraveSearchClient,
    WebsiteDiscoverer,
    email_domain_candidate,
    name_domain_candidates,
    verify_ownership,
)
from leadmachine.website.models import FetchResult, LeadToQualify

from .conftest import FakeResolver, StubFetcher

OWNED_HTML = (
    '<html><head><meta name="viewport" content="width=device-width">'
    "<title>Bager Martin</title></head><body>"
    "<h1>Bager Martin</h1><footer>CVR 12345678 · Bagergade 1, 8000 Aarhus</footer>"
    "</body></html>"
)
UNRELATED_HTML = "<html><body><h1>Helt andet firma</h1></body></html>"


def _fetch(url: str, html: str) -> FetchResult:
    return FetchResult(final_url=url, status=200, html=html)


# --- candidate generation --------------------------------------------------
def test_email_domain_candidate_business() -> None:
    assert email_domain_candidate("info@bagermartin.dk") == "bagermartin.dk"


def test_email_domain_candidate_free_provider() -> None:
    assert email_domain_candidate("baker@gmail.com") is None
    assert email_domain_candidate("x@hotmail.dk") is None


def test_email_domain_candidate_junk() -> None:
    assert email_domain_candidate(None) is None
    assert email_domain_candidate("not-an-email") is None


def test_name_domain_candidates() -> None:
    cands = name_domain_candidates("Bager Martin ApS")
    assert "bagermartin.dk" in cands
    assert "bager-martin.dk" in cands
    assert all(c.endswith((".dk", ".com")) for c in cands)
    assert len(cands) <= 4


def test_name_domain_candidates_too_generic() -> None:
    # All tokens are stop-words (company form + generic) → nothing to guess.
    assert name_domain_candidates("ApS Holding") == []


# --- ownership verification ------------------------------------------------
def test_verify_cvr_is_definitive() -> None:
    lead = LeadToQualify("L", None, "Andet Navn", cvr_number="12345678")
    conf, matched = verify_ownership(lead, _fetch("https://x.dk/", OWNED_HTML), "x.dk", "search")
    assert conf >= 0.95
    assert "cvr" in matched


def test_verify_name_plus_geo() -> None:
    lead = LeadToQualify("L", None, "Bager Martin ApS", postal_code="8000", city="Aarhus")
    conf, matched = verify_ownership(
        lead, _fetch("https://bagermartin.dk/", OWNED_HTML), "bagermartin.dk", "name_guess"
    )
    assert conf >= 0.8
    assert "name" in matched and "geo" in matched


def test_verify_rejects_unrelated_page() -> None:
    lead = LeadToQualify("L", None, "Bager Martin ApS")
    conf, _ = verify_ownership(
        lead, _fetch("https://random.dk/", UNRELATED_HTML), "random.dk", "search"
    )
    assert conf < 0.6


# --- orchestrator ----------------------------------------------------------
def test_discover_finds_via_email_domain() -> None:
    fetcher = StubFetcher(_fetch("https://bagermartin.dk/", OWNED_HTML))
    disc = WebsiteDiscoverer(fetcher, FakeResolver())
    lead = LeadToQualify("L", None, "Bager Martin ApS", email="info@bagermartin.dk")

    found = disc.discover(lead)
    assert found is not None
    assert found.source == "email_domain"
    assert found.host == "bagermartin.dk"
    assert found.fetch is not None


def test_discover_returns_none_when_unverified() -> None:
    fetcher = StubFetcher(_fetch("https://bagermartin.dk/", UNRELATED_HTML))
    disc = WebsiteDiscoverer(fetcher, FakeResolver())
    lead = LeadToQualify("L", None, "Bager Martin ApS", email="info@bagermartin.dk")
    assert disc.discover(lead) is None


class _DeadResolver:
    """Every domain is dead (no A/AAAA record)."""

    def addresses(self, domain: str) -> list[str]:
        return []

    def nameservers(self, domain: str) -> list[str]:
        return []


def test_discover_skips_dead_domain() -> None:
    fetcher = StubFetcher(_fetch("https://bagermartin.dk/", OWNED_HTML))
    disc = WebsiteDiscoverer(fetcher, _DeadResolver())
    lead = LeadToQualify("L", None, "Bager Martin ApS", email="info@bagermartin.dk")
    assert disc.discover(lead) is None
    assert fetcher.fetched == []  # never fetched — DNS short-circuited


# --- Brave client ----------------------------------------------------------
class _FakeHttpResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeHttpClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[Any] = []

    def get(self, url: str, params: Any = None, headers: Any = None) -> _FakeHttpResponse:
        self.calls.append((url, params, headers))
        return _FakeHttpResponse(self._payload)


def test_brave_filters_directories_and_dedupes() -> None:
    payload = {
        "web": {
            "results": [
                {"url": "https://proff.dk/company/x"},  # directory — dropped
                {"url": "https://www.bagermartin.dk/om"},  # kept (www stripped)
                {"url": "https://bagermartin.dk/kontakt"},  # dup host — dropped
                {"url": "https://facebook.com/bagermartin"},  # social — dropped
            ]
        }
    }
    client = BraveSearchClient("k", http_client=_FakeHttpClient(payload))
    hosts = client.candidate_hosts('"Bager Martin" Aarhus')
    assert hosts == ["bagermartin.dk"]


def test_brave_from_settings_disabled_without_key() -> None:
    assert BraveSearchClient.from_settings(SimpleNamespace(brave_api_key="")) is None
