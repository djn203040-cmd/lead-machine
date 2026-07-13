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


# --- owner-suffix stripping ------------------------------------------------
def test_strip_owner_suffix() -> None:
    from leadmachine.website.independence import search_name, strip_owner_suffix

    assert strip_owner_suffix("TANDLÆGERNE I CENTRUM V/LARS WELTZER ApS") == "TANDLÆGERNE I CENTRUM"
    assert strip_owner_suffix("Casa Frisør v/Camilla From Vedsted") == "Casa Frisør"
    assert strip_owner_suffix("KJ MINH /Vu Minh Nguyen") == "KJ MINH"
    assert strip_owner_suffix("LA CABRA Aarhus ApS") == "LA CABRA Aarhus ApS"  # no owner marker
    # search_name also drops the legal form.
    assert search_name("TANDLÆGERNE I CENTRUM V/LARS WELTZER ApS") == "TANDLÆGERNE I CENTRUM"


def test_verify_owner_named_company_matches_on_business_name() -> None:
    # A dentist site names the practice but never the owner "Lars Weltzer".
    lead = LeadToQualify(
        "L", None, "TANDLÆGERNE I CENTRUM V/LARS WELTZER ApS", address="Algade 5-7"
    )
    html = (
        "<html><body><h1>Tandlægerne i Centrum</h1>"
        "<p>Algade 5-7, 4000 Roskilde</p></body></html>"
    )
    conf, matched = verify_ownership(
        lead, _fetch("https://tandicentrum.dk/", html), "tandicentrum.dk", "search"
    )
    assert conf >= 0.9  # business name + address, owner suffix ignored
    assert "name" in matched and "address" in matched


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


def test_name_candidates_include_full_slug_with_trade_word() -> None:
    # Businesses register the trade word in the domain: restaurantmellemrum.dk.
    cands = name_domain_candidates("RESTAURANT MELLEMRUM ApS")
    assert "restaurantmellemrum.dk" in cands
    assert "mellemrum.dk" in cands  # short form still tried


# --- www-only domains ------------------------------------------------------
class _WwwOnlyResolver:
    """Apex has no A record; only the www host resolves (roskildesvaneapotek.dk)."""

    def addresses(self, domain: str) -> list[str]:
        return ["1.2.3.4"] if domain.startswith("www.") else []

    def nameservers(self, domain: str) -> list[str]:
        return ["ns1.hosting.dk"]


def test_discover_falls_back_to_www_when_apex_has_no_dns() -> None:
    html = (
        "<html><body><h1>Roskilde Svane Apotek</h1>"
        "<p>Skomagergade 19, 4000 Roskilde</p></body></html>"
    )
    fetcher = StubFetcher(
        {"https://www.roskildesvaneapotek.dk/": _fetch("https://www.roskildesvaneapotek.dk/", html)}
    )
    disc = WebsiteDiscoverer(fetcher, _WwwOnlyResolver())
    lead = LeadToQualify(
        "L", None, "Roskilde Svane Apotek V/Ulla Charlotte Andersen",
        address="Skomagergade 19", postal_code="4000", city="Roskilde",
    )

    found = disc.discover(lead)
    assert found is not None
    assert found.url == "https://www.roskildesvaneapotek.dk/"  # www kept in the URL
    assert found.host == "roskildesvaneapotek.dk"  # canonical host
    assert fetcher.fetched == ["https://www.roskildesvaneapotek.dk/"]


# --- binavne (registered secondary trading names) --------------------------
MELLEMRUM_HTML = (
    "<html><body><h1>Restaurant MellemRum</h1>"
    "<footer>Fredens Torv 2, 8000 Aarhus C · CVR 30598881</footer></body></html>"
)


def test_verify_via_binavn() -> None:
    # The site never says "Thygesen & Thallaug" — only the secondary name.
    lead = LeadToQualify(
        "L", None, "THYGESEN & THALLAUG ApS", address="Fredens Torv 2, st",
        binavne=["RESTAURANT MELLEMRUM ApS"],
    )
    conf, matched = verify_ownership(
        lead, _fetch("https://restaurantmellemrum.dk/", MELLEMRUM_HTML),
        "restaurantmellemrum.dk", "name_guess",
    )
    assert conf >= 0.9
    assert "binavn" in matched and "name" not in matched


def test_discover_via_binavn_name_guess() -> None:
    fetcher = StubFetcher(
        {"https://restaurantmellemrum.dk/": _fetch("https://restaurantmellemrum.dk/", MELLEMRUM_HTML)}
    )
    disc = WebsiteDiscoverer(fetcher, FakeResolver())
    lead = LeadToQualify(
        "L", None, "THYGESEN & THALLAUG ApS", address="Fredens Torv 2, st",
        binavne=["RESTAURANT MELLEMRUM ApS"],
    )

    found = disc.discover(lead)
    assert found is not None
    assert found.host == "restaurantmellemrum.dk"
    assert found.brand_name == "RESTAURANT MELLEMRUM ApS"


def test_is_distinctive() -> None:
    from leadmachine.website.independence import is_distinctive

    assert not is_distinctive("København Frisør v/Azad Salahi")  # city + trade
    assert not is_distinctive("Tandlægerne i Centrum")  # trade + place
    assert not is_distinctive("FRISØRSALON")  # bare trade
    assert is_distinctive("Det Glade Vanvid, Aarhus ApS")  # "glade"/"vanvid" distinctive
    assert is_distinctive("LA CABRA Aarhus ApS")  # "cabra" distinctive
    assert is_distinctive("Noribar")


def test_verify_rejects_generic_name_only_search_match() -> None:
    # A generic city+trade name matched on a page by name alone (no address/
    # phone/geo) from web search must be rejected — any frisør site matches.
    lead = LeadToQualify("L", None, "København Frisør v/Azad Salahi")
    html = "<html><body><h1>P Nørgaard · Frisør i København</h1></body></html>"
    conf, _ = verify_ownership(lead, _fetch("https://pnoergaard.dk/", html), "pnoergaard.dk", "search")
    assert conf < 0.6


def test_verify_accepts_distinctive_name_only_search_match() -> None:
    lead = LeadToQualify("L", None, "Det Glade Vanvid, Aarhus ApS")
    html = "<html><body><h1>Det Glade Vanvid</h1><p>Besøg os i Aarhus</p></body></html>"
    conf, matched = verify_ownership(
        lead, _fetch("https://detgladevanvid.dk/", html), "detgladevanvid.dk", "search"
    )
    assert conf >= 0.6 and "name" in matched


def test_directory_hosts_rejected() -> None:
    from leadmachine.website.discover import _is_directory

    assert _is_directory("frisorfinder.dk")
    assert _is_directory("spiseguidenaarhus.dk")
    assert _is_directory("aafrobarber7365.setmore.com")  # subdomain of a portal


def test_verify_rejects_unrelated_page() -> None:
    lead = LeadToQualify("L", None, "Bager Martin ApS")
    conf, _ = verify_ownership(
        lead, _fetch("https://random.dk/", UNRELATED_HTML), "random.dk", "search"
    )
    assert conf < 0.6


# A storefront site that names the brand ("Noribar") + its address, never the
# operating company ("Kakurega ApS").
BRAND_HTML = (
    "<html><head><title>Noribar</title></head><body>"
    "<h1>Noribar</h1><p>Skt. Clemens Stræde 7, 8000 Aarhus C</p></body></html>"
)


def test_verify_via_brand_name_and_address() -> None:
    lead = LeadToQualify("L", None, "Kakurega ApS", address="Skt. Clemens Stræde 7")
    brand = SimpleNamespace(name="Noribar", phone=[], email=None, address=None)
    conf, matched = verify_ownership(
        lead, _fetch("https://noribar.dk/", BRAND_HTML), "noribar.dk", "penhed", brand=brand
    )
    assert conf >= 0.9  # brand name + street address
    assert "brand" in matched and "address" in matched
    assert "name" not in matched  # the company name never appears


def test_verify_penhed_name_only_accepts_at_threshold() -> None:
    lead = LeadToQualify("L", None, "Kakurega ApS")  # no address to corroborate
    brand = SimpleNamespace(name="Noribar", phone=[], email=None, address=None)
    html = "<html><body><h1>Noribar</h1></body></html>"
    conf, matched = verify_ownership(
        lead, _fetch("https://noribar.dk/", html), "noribar.dk", "penhed", brand=brand
    )
    assert conf >= 0.6  # trusted source (penhed) + brand name → accept
    assert "brand" in matched


def test_verify_street_match_ignores_house_number() -> None:
    from leadmachine.website.discover import _street_name

    assert _street_name("Skt. Clemens Stræde 7, 2. th") == "skt clemens straede"
    assert _street_name("Bagergade 1") == "bagergade"
    assert _street_name(None) == ""


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


class _StubPenhed:
    """Returns a canned PenhedInfo-shaped object for any pNummer."""

    def __init__(self, info: Any) -> None:
        self.info = info
        self.requested: list[Any] = []

    def fetch_by_pnummer(self, pnummer: Any) -> Any:
        self.requested.append(pnummer)
        return self.info


def test_discover_via_penhed_website() -> None:
    # The operating company has no email/name match; the storefront site is only
    # reachable via the production unit's trading name + registered website.
    brand = SimpleNamespace(
        name="Noribar",
        website="www.noribar.dk",
        email=None,
        phone=[],
        address="Skt. Clemens Stræde 7",
        city="Aarhus C",
    )
    fetcher = StubFetcher({"https://noribar.dk/": _fetch("https://noribar.dk/", BRAND_HTML)})
    penhed = _StubPenhed(brand)
    disc = WebsiteDiscoverer(fetcher, FakeResolver(), penhed_client=penhed)
    lead = LeadToQualify(
        "L", None, "Kakurega ApS", address="Skt. Clemens Stræde 7", pnummer="1024698951"
    )

    found = disc.discover(lead)
    assert found is not None
    assert found.source == "penhed"
    assert found.host == "noribar.dk"
    assert found.brand_name == "Noribar"
    assert penhed.requested == ["1024698951"]


def test_discover_penhed_skipped_without_pnummer() -> None:
    penhed = _StubPenhed(SimpleNamespace(name="Noribar", website="www.noribar.dk"))
    disc = WebsiteDiscoverer(StubFetcher(_fetch("https://x.dk/", UNRELATED_HTML)), FakeResolver(), penhed_client=penhed)
    lead = LeadToQualify("L", None, "Kakurega ApS")  # no pnummer
    assert disc.discover(lead) is None
    assert penhed.requested == []  # never looked up


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
