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
    # A dentist site names the practice but never the owner "Lars Weltzer". The
    # name is generic (trade + place), so it needs a hard corroborator (their
    # phone) — street address alone matches every clinic on Algade.
    lead = LeadToQualify(
        "L", None, "TANDLÆGERNE I CENTRUM V/LARS WELTZER ApS",
        address="Algade 5-7", phone=["46321234"],
    )
    html = (
        "<html><body><h1>Tandlægerne i Centrum</h1>"
        "<p>Algade 5-7, 4000 Roskilde · tlf. 46 32 12 34</p></body></html>"
    )
    conf, matched = verify_ownership(
        lead, _fetch("https://tandicentrum.dk/", html), "tandicentrum.dk", "search"
    )
    assert conf >= 0.9  # generic business name + own phone, owner suffix ignored
    assert "name" in matched and "phone" in matched and "address_exact" in matched


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
    # The full slug is tried FIRST: "mellemrum.dk" is a dictionary word that an
    # unrelated business can own (it does — an art-print shop).
    assert cands.index("restaurantmellemrum.dk") < cands.index("mellemrum.dk")


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
    # Shopping-street directories by naming pattern, not just the known list.
    assert _is_directory("oesterbrogade-shopping.dk")
    assert _is_directory("www.valby-shopping.dk")
    assert not _is_directory("shopping.dk")  # the pattern needs the street prefix


def test_verify_rejects_generic_name_with_geo_only_corroboration() -> None:
    # roskilde-fysioterapi.dk case: a *different* Roskilde clinic matches the
    # generic name "Klinik for Fysioterapi" and the city/postal + street — every
    # competitor on the street does. Soft geo must not corroborate a generic name.
    lead = LeadToQualify(
        "L", None, "KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS",
        address="Dronning Margrethes Vej 26", postal_code="4000", city="Roskilde",
        phone=["46351234"],
    )
    html = (
        "<html><body><h1>Roskilde Fysioterapi</h1>"
        "<p>Klinik for fysioterapi · Algade 12, 4000 Roskilde · tlf 46359999</p></body></html>"
    )
    conf, matched = verify_ownership(
        lead, _fetch("https://roskilde-fysioterapi.dk/", html), "roskilde-fysioterapi.dk", "search"
    )
    assert conf < 0.6
    assert "geo" in matched  # geo DID match — and still must not be enough


def test_verify_accepts_generic_name_with_phone_corroboration() -> None:
    # Same generic name, but the page shows the lead's own phone → it's them.
    lead = LeadToQualify(
        "L", None, "KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS",
        postal_code="4000", city="Roskilde", phone=["46351234"],
    )
    html = "<html><body><h1>Klinik for Fysioterapi</h1><p>Ring 46 35 12 34</p></body></html>"
    conf, matched = verify_ownership(
        lead, _fetch("https://klinikx.dk/", html), "klinikx.dk", "search"
    )
    assert conf >= 0.9
    assert "phone" in matched


def test_verify_rejects_stripped_slug_guess_without_corroboration() -> None:
    # mellemrum.dk case: the binavn "Restaurant MellemRum" guessed the stripped
    # dictionary-word domain, which belongs to an unrelated art-print shop. The
    # shop's page of course contains the word "mellemrum" — circular evidence.
    lead = LeadToQualify(
        "L", None, "THYGESEN & THALLAUG ApS", address="Fredens Torv 2, st",
        city="Aarhus C", postal_code="8000", binavne=["RESTAURANT MELLEMRUM ApS"],
    )
    html = (
        "<html><head><title>Mellemrum – prints og original kunst</title></head>"
        "<body><h1>MELLEMrum</h1><p>Prints, comics og drawings</p></body></html>"
    )
    conf, _ = verify_ownership(
        lead, _fetch("https://mellemrum.dk/", html), "mellemrum.dk", "name_guess"
    )
    assert conf < 0.6


def test_verify_accepts_full_slug_guess_name_only() -> None:
    # The same lead at the full-name domain is self-evidencing even with no
    # phone/geo on the page: nobody else registers restaurantmellemrum.dk.
    lead = LeadToQualify(
        "L", None, "THYGESEN & THALLAUG ApS", binavne=["RESTAURANT MELLEMRUM ApS"],
    )
    html = "<html><body><h1>Restaurant MellemRum</h1><p>Menukort</p></body></html>"
    conf, matched = verify_ownership(
        lead, _fetch("https://restaurantmellemrum.dk/", html),
        "restaurantmellemrum.dk", "name_guess",
    )
    assert conf >= 0.6
    assert "binavn" in matched


def test_owner_name_extraction() -> None:
    from leadmachine.website.independence import owner_name

    assert owner_name("KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS") == "BJARKE BILDE"
    assert owner_name("Casa Frisør v/Camilla From Vedsted") == "Camilla From Vedsted"
    assert owner_name("KJ MINH /Vu Minh Nguyen") == "Vu Minh Nguyen"
    assert owner_name("LA CABRA Aarhus ApS") == ""  # no owner marker
    assert owner_name(None) == ""


def test_verify_accepts_generic_name_via_owner_and_exact_address() -> None:
    # fysroskilde.dk case: the site is branded "FysRoskilde" — it never says
    # "Klinik for Fysioterapi" as a unit, doesn't show the CVR phone (site has a
    # mobile), but credits the owner and shows the exact street + number.
    lead = LeadToQualify(
        "L", None, "KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS",
        address="Dronning Margrethes Vej 26", postal_code="4000", city="Roskilde",
        phone=["46373301"],
    )
    html = (
        "<html><body><h1>FysRoskilde</h1><p>Fysioterapi klinik i Roskilde</p>"
        "<footer>FysRoskilde v/ Bjarke Bilde · Dronning Margrethes Vej 26 - 4000 Roskilde"
        " · Ring i dag: 26 35 34 34</footer></body></html>"
    )
    conf, matched = verify_ownership(
        lead, _fetch("https://fysroskilde.dk/", html), "fysroskilde.dk", "search"
    )
    assert conf >= 0.9
    assert "owner" in matched and "address_exact" in matched


def test_verify_exact_address_is_hard_but_street_alone_is_not() -> None:
    # goldentouchgt.dk case: same street, DIFFERENT house number → still reject;
    # but the exact street+number pins the building → accept even w/o owner.
    lead = LeadToQualify(
        "L", None, "København Frisør v/Azad Salahi",
        address="Nørrebrogade 61", postal_code="2200", city="København N",
    )
    other_number = "<html><body><h1>Frisørsalon · Nørrebrogade 110, 2200 København</h1></body></html>"
    conf, _ = verify_ownership(
        lead, _fetch("https://goldentouchgt.dk/", other_number), "goldentouchgt.dk", "search"
    )
    assert conf < 0.6

    same_number = "<html><body><h1>Frisør · Nørrebrogade 61, 2200 København</h1></body></html>"
    conf, matched = verify_ownership(
        lead, _fetch("https://salonx.dk/", same_number), "salonx.dk", "search"
    )
    assert conf >= 0.9
    assert "address_exact" in matched


def test_verify_owner_only_without_corroboration_rejected() -> None:
    # A page mentioning "Bjarke Bilde" with no other signal could be a different
    # person with the same name.
    lead = LeadToQualify("L", None, "KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS")
    html = "<html><body><p>Foredrag med Bjarke Bilde om fysioterapi og klinik</p></body></html>"
    conf, _ = verify_ownership(lead, _fetch("https://blog.dk/", html), "blog.dk", "search")
    assert conf < 0.6


def test_brave_query_includes_owner_for_generic_names() -> None:
    class _CapturingBrave:
        def __init__(self) -> None:
            self.queries: list[str] = []

        def candidate_hosts(self, query: str) -> list[str]:
            self.queries.append(query)
            return []

        def close(self) -> None:
            pass

    brave = _CapturingBrave()
    disc = WebsiteDiscoverer(StubFetcher({}), FakeResolver(), brave=brave)  # type: ignore[arg-type]
    lead = LeadToQualify(
        "L", None, "KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS", city="Roskilde"
    )
    disc.discover(lead)
    assert brave.queries == ["KLINIK FOR FYSIOTERAPI BJARKE BILDE Roskilde"]

    # Distinctive names keep the plain query — the owner would hurt recall.
    brave2 = _CapturingBrave()
    disc2 = WebsiteDiscoverer(StubFetcher({}), FakeResolver(), brave=brave2)  # type: ignore[arg-type]
    disc2.discover(LeadToQualify("L", None, "Noribar v/Anna Hansen", city="Aarhus"))
    assert brave2.queries == ["Noribar Aarhus"]


def test_verify_rejects_name_tokens_inside_other_words() -> None:
    # salonnorth.dk case: "charm" appears only inside "charmerende" and the
    # owner token "reda" inside "fredag" — word fragments are not evidence.
    lead = LeadToQualify(
        "L", None, "Salon Charm v/Reda Abdel-Mohssen Moustafa Aly",
        address="Nørrebrogade 57", postal_code="2200", city="København N",
    )
    html = (
        "<html><body><h1>Salon North</h1><p>Velkommen til vores charmerende salon"
        " i Nordvest. Åbent mandag til fredag.</p></body></html>"
    )
    conf, _ = verify_ownership(
        lead, _fetch("https://www.salonnorth.dk/", html), "salonnorth.dk", "search"
    )
    assert conf < 0.6


def test_verify_name_tokens_allow_danish_inflection() -> None:
    # "klinik" must still match "klinikken" (definite form) — whole-word with a
    # short suffix, not bare substring.
    lead = LeadToQualify(
        "L", None, "KLINIK FOR FYSIOTERAPI V/BJARKE BILDE ApS",
        address="Dronning Margrethes Vej 26", postal_code="4000", city="Roskilde",
    )
    html = (
        "<html><body><h1>Klinikken for fysioterapien</h1>"
        "<p>Dronning Margrethes Vej 26, 4000 Roskilde</p></body></html>"
    )
    conf, matched = verify_ownership(
        lead, _fetch("https://fys.dk/", html), "fys.dk", "search"
    )
    assert conf >= 0.9  # name (inflected) + exact address
    assert "name" in matched and "address_exact" in matched


def test_discover_prefers_full_slug_domain_over_stripped() -> None:
    # Both domains are live: the stripped guess is an unrelated art shop, the
    # full guess is the restaurant. Discovery must land on the restaurant.
    art = "<html><body><h1>MELLEMrum</h1><p>Prints og original kunst</p></body></html>"
    fetcher = StubFetcher(
        {
            "https://mellemrum.dk/": _fetch("https://mellemrum.dk/", art),
            "https://restaurantmellemrum.dk/": _fetch(
                "https://restaurantmellemrum.dk/", MELLEMRUM_HTML
            ),
        }
    )
    disc = WebsiteDiscoverer(fetcher, FakeResolver())
    lead = LeadToQualify(
        "L", None, "THYGESEN & THALLAUG ApS", address="Fredens Torv 2, st",
        binavne=["RESTAURANT MELLEMRUM ApS"],
    )

    found = disc.discover(lead)
    assert found is not None
    assert found.host == "restaurantmellemrum.dk"


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
    assert "brand" in matched and "address_exact" in matched
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
