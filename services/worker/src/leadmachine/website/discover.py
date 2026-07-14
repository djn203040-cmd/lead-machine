"""Discover a real website for a lead that has none registered in CVR.

Most Danish SMBs never fill in the CVR ``hjemmeside`` field, so a lead with an
empty (or social-only) website was wrongly qualified as "no website" — the
hottest bucket — even when a perfectly good site exists. This module goes and
looks, cheapest source first, and **verifies ownership** before attaching a
site (the real risk isn't missing a site, it's confidently attaching the wrong
one):

    Tier 0  email domain      — ``info@bagermartin.dk`` ⇒ the domain *is* the site
    Tier 1  name → domain      — slugify the company name against .dk / .com
    Tier 2  Brave web search   — ``"<name>" <city>`` → candidate domains

Every candidate is DNS-checked, fetched, screened for dead/parked, then scored
against data we already hold (CVR number, company name, phone, email, postal
code + city). Only a candidate that clears the confidence threshold is returned;
otherwise the lead stays ``none``.

The fetcher and resolver are shared with the qualifier (:class:`WebsiteDeps`);
Brave is optional — the free email/name tiers work without it.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from .domain import Resolver, classify_from_fetch
from .fetch import WebsiteFetcher
from .independence import (
    _TOKEN_RE,
    business_key,
    full_slug,
    is_distinctive,
    is_not_independent,
    owner_name,
    search_name,
    strip_owner_suffix,
)
from .models import DiscoveryResult, FetchResult, LeadToQualify

# Consumer mailbox providers — an @gmail.com address tells us nothing about a
# business domain, so these are never treated as a candidate site.
FREE_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com", "googlemail.com", "hotmail.com", "hotmail.dk", "live.com",
        "live.dk", "outlook.com", "outlook.dk", "yahoo.com", "yahoo.dk",
        "msn.com", "icloud.com", "me.com", "mac.com", "aol.com", "protonmail.com",
        "proton.me", "mail.dk", "post.tele.dk", "webspeed.dk", "stofanet.dk",
        "privat.dk", "jubii.dk", "email.dk", "city.dk", "get2net.dk", "mail.tele.dk",
    }
)

# Hosts that are directories / registries / social — never a business's own site.
DIRECTORY_HOSTS: frozenset[str] = frozenset(
    {
        "proff.dk", "krak.dk", "degulesider.dk", "findsmiley.dk", "118.dk",
        "eniro.dk", "opengov.dk", "virk.dk", "cvr.dk", "datacvr.virk.dk",
        "cvrapi.dk", "nordicnet.dk", "companyhouse.dk", "brreg.no", "trustpilot.com",
        "facebook.com", "m.facebook.com", "instagram.com", "linkedin.com",
        "youtube.com", "twitter.com", "x.com", "tiktok.com", "pinterest.com",
        "google.com", "google.dk", "maps.google.com", "wikipedia.org",
        "yelp.com", "foursquare.com", "tripadvisor.com", "tripadvisor.dk",
        "wolt.com", "just-eat.dk", "just-eat.com", "booking.com", "amazon.com",
        # Local/vertical directories + booking portals that list many separate
        # businesses (with address/phone) — a listing there is not the firm's
        # own site. Extend as new ones surface.
        "frisorfinder.dk", "spiseguidenaarhus.dk", "noerrebro-shopping.dk",
        "spillehalleraarhus.dk", "setmore.com", "bookinghero.io", "booking.dk",
        "sundhed.dk", "1klik.dk", "trustpilot.dk",
    }
)

_TLDS = (".dk", ".com")
_DIGITS_RE = re.compile(r"\d+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_HOUSE_RE = re.compile(r"^\d+(?:[-–]\d+)?[a-z]?$")  # house number: "7", "12b", "5-7"
_ACCEPT_THRESHOLD = 0.6  # minimum ownership confidence to attach a discovered site
_MAX_NAME_CANDIDATES = 6  # room for the full-slug variant alongside the short one
_MAX_SEARCH_CANDIDATES = 4
_MAX_SEARCH_QUERIES = 2  # cap paid Brave calls per lead (trading name, then legal name)
# Sources whose provenance is trustworthy enough to accept a name-only match, or
# a corroborated match with no name at all (the domain came from the business's
# own registered email / production unit).
_TRUSTED_SOURCES = frozenset({"email_domain", "penhed"})


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def _digits(text: str) -> str:
    return "".join(_DIGITS_RE.findall(text or ""))


def _normalize(text: str) -> str:
    text = (text or "").lower()
    for src, dst in (("æ", "ae"), ("ø", "oe"), ("å", "aa"), ("é", "e"), ("ü", "u")):
        text = text.replace(src, dst)
    return text


def _is_directory(host: str) -> bool:
    host = _strip_www(host.lower().strip("."))
    if host in DIRECTORY_HOSTS or any(host.endswith("." + d) for d in DIRECTORY_HOSTS):
        return True
    # Danish shopping-street directories share a "<street>-shopping.dk" naming
    # (noerrebro-shopping.dk, oesterbrogade-shopping.dk, …) — they list every
    # shop on the street with name/phone/address, so they'd otherwise verify.
    return host.endswith("-shopping.dk")


def _host_from_website(raw: str | None) -> str | None:
    """Extract a bare host from a registered ``hjemmeside`` value (best-effort)."""
    if not raw:
        return None
    raw = raw.strip()
    if "://" not in raw:
        raw = "//" + raw
    parts = urlsplit(raw)
    host = (parts.netloc or parts.path).split("@")[-1].split(":")[0].strip("/").lower().strip(".")
    host = _strip_www(host)
    return host if host and "." in host else None


def _street_name(address: str | None) -> str:
    """The normalized street (no house number) from an address line, or ``""``.

    ``"Skt. Clemens Stræde 7, 2. th"`` → ``"skt clemens straede"``. Short/generic
    results (< 5 chars) are dropped so we never match on a stray fragment.
    """
    if not address:
        return ""
    first = address.split(",")[0]
    tokens = _normalize(first).replace(".", " ").split()
    while tokens and _HOUSE_RE.match(tokens[-1]):
        tokens.pop()
    street = " ".join(tokens).strip()
    return street if len(street) >= 5 else ""


def _street_match(address: str | None, spaced_text: str) -> bool:
    """Whether the address's street appears as a run in the (spaced) page text."""
    street = _street_name(address)
    if not street:
        return False
    return f" {street} " in f" {spaced_text} "


def _exact_address_match(address: str | None, spaced_text: str) -> bool:
    """Whether street *and house number* appear as one run in the page text.

    "Nørrebrogade" alone matches every competitor on the street (that's a soft
    signal); "Dronning Margrethes Vej 26" pins the one building — near-unique
    for a storefront, so it counts as a hard corroborator.
    """
    if not address:
        return False
    first = address.split(",")[0]
    tokens = _normalize(first).replace(".", " ").split()
    if len(tokens) < 2 or not _HOUSE_RE.match(tokens[-1]):
        return False  # no house number registered — only the soft street match applies
    street = " ".join(tokens[:-1]).strip()
    if len(street) < 5:
        return False
    run = _NON_ALNUM_RE.sub(" ", f"{street} {tokens[-1]}").strip()
    return f" {run} " in f" {spaced_text} "


def email_domain_candidate(email: str | None) -> str | None:
    """The business domain from a work email, or ``None`` for free providers."""
    if not email or "@" not in email:
        return None
    domain = email.rsplit("@", 1)[-1].strip().lower().strip(".")
    if not domain or "." not in domain:
        return None
    if domain in FREE_EMAIL_DOMAINS or _is_directory(domain):
        return None
    return domain


def name_domain_candidates(company_name: str | None) -> list[str]:
    """Guess likely domains from the company name (cheapest, DNS-only tier).

    ``Bager Martin ApS`` → ``bagermartin.dk``, ``bager-martin.dk``,
    ``bagermartin.com`` … Legal-form and generic tokens are dropped (reusing the
    independence tokenizer), so we only guess from the distinctive words — but we
    also try the *full* slug that keeps trade words, since businesses do register
    them (``RESTAURANT MELLEMRUM`` → ``restaurantmellemrum.dk``, not just
    ``mellemrum.dk``).
    """
    tokens_set, slug = business_key(company_name)
    full = full_slug(company_name)
    if (not slug or len(slug) < 4) and len(full) < 4:
        return []
    # Keep name order for the hyphenated variant (business_key returns a set).
    from .independence import _TOKEN_RE, _STOP_TOKENS  # local: internal helpers

    ordered = [
        t for t in _TOKEN_RE.findall(_normalize(strip_owner_suffix(company_name)))
        if t not in _STOP_TOKENS
    ]
    bases: list[str] = []
    # Full slug first: "restaurantmellemrum" collides with nothing, whereas the
    # stripped "mellemrum" is a plain dictionary word — if both exist as live
    # domains, the specific one is far likelier to be theirs.
    if full and len(full) >= 4 and full != slug:
        bases.append(full)  # restaurantmellemrum
    if slug and len(slug) >= 4:
        bases.append(slug)  # bagermartin
    if len(ordered) >= 2:
        bases.append("-".join(ordered))  # bager-martin
    if len(ordered) == 1 and len(ordered[0]) >= 5:
        bases.append(ordered[0])

    seen: set[str] = set()
    candidates: list[str] = []
    for base in bases:
        for tld in _TLDS:
            host = base + tld
            if host not in seen:
                seen.add(host)
                candidates.append(host)
    return candidates[:_MAX_NAME_CANDIDATES]


class BraveSearchClient:
    """Brave Web Search API — returns candidate hosts for a company query."""

    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, *, http_client: Any | None = None, count: int = 8) -> None:
        import httpx

        self.api_key = api_key
        self.count = count
        self._owns_client = http_client is None
        # Tight timeout, single attempt (see candidate_hosts): a slow/failed
        # search must not stall the per-lead pipeline — better to skip it.
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(8.0, connect=5.0))

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> "BraveSearchClient | None":
        if not settings.brave_api_key:
            return None
        return cls(settings.brave_api_key, **kwargs)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def candidate_hosts(self, query: str) -> list[str]:
        """Distinct, non-directory hosts from the top web results (best-effort)."""
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {"q": query, "country": "dk", "search_lang": "da", "count": self.count}
        # Single attempt (no retry storm): a slow search shouldn't stall the lead.
        try:
            resp = self._client.get(self.ENDPOINT, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []
        results = ((data.get("web") or {}).get("results")) or []
        hosts: list[str] = []
        seen: set[str] = set()
        for r in results:
            url = r.get("url") or ""
            host = _strip_www(urlsplit(url).netloc.split("@")[-1].split(":")[0].lower().strip("."))
            if not host or host in seen or _is_directory(host):
                continue
            seen.add(host)
            hosts.append(host)
        return hosts


# --- ownership verification ------------------------------------------------
def _host_carries_full_name(names: list[str | None], host: str) -> bool:
    """Whether the host itself spells out a business name in full.

    ``restaurantmellemrum.dk`` carries "RESTAURANT MELLEMRUM"; ``mellemrum.dk``
    does not — it only carries the stripped slug, which for a dictionary word
    identifies nothing.
    """
    labels = _strip_www(host.lower()).split(".")[:-1]  # drop the TLD
    host_alnum = _NON_ALNUM_RE.sub("", "".join(labels))
    for name in names:
        full = full_slug(name)
        if len(full) >= 4 and full in host_alnum:
            return True
    return False


def _page_text(fetch: FetchResult) -> str:
    """Normalized haystack for name/geo matching (title + body, capped)."""
    return _normalize(fetch.html or "")[:200_000]


def _name_present(name: str | None, text: str, alnum: str) -> bool:
    """Whether a business name (company or brand) appears on the page."""
    tokens, slug = business_key(name)
    return bool(
        (slug and len(slug) >= 5 and slug in alnum)
        or (tokens and len(tokens) >= 2 and all(t in text for t in tokens))
        or (len(tokens) == 1 and next(iter(tokens)) in text and len(next(iter(tokens))) >= 5)
    )


def verify_ownership(
    lead: LeadToQualify,
    fetch: FetchResult,
    host: str,
    source: str,
    *,
    brand: Any | None = None,
) -> tuple[float, list[str]]:
    """Score how confidently this page belongs to *this* business.

    Returns ``(confidence, matched)``. A CVR-number match is definitive; a
    name match (the company name **or** the production unit's trading name) is
    the required anchor for everything else, corroborated by phone / email /
    geo / street address / trusted-source provenance. ``brand`` is an optional
    :class:`~leadmachine.cvr.penhed.PenhedInfo`-shaped object (``.name`` /
    ``.phone`` / ``.email`` / ``.address``) so a differently-branded storefront
    site verifies even though it never names the operating company.
    """
    text = _page_text(fetch)
    digits = _digits(text)
    spaced = _NON_ALNUM_RE.sub(" ", text)
    alnum = spaced.replace(" ", "")
    matched: list[str] = []

    # CVR number in the footer is the strongest signal Danish sites give us.
    cvr = _digits(lead.cvr_number or "")
    cvr_hit = len(cvr) == 8 and cvr in digits
    if cvr_hit:
        matched.append("cvr")

    if _name_present(lead.company_name, text, alnum):
        matched.append("name")
    brand_name = getattr(brand, "name", None)
    if brand_name and _name_present(brand_name, text, alnum):
        matched.append("brand")
    # A registered secondary name (binavn) is a real trading name — the site may
    # only ever say "Restaurant MellemRum", never "Thygesen & Thallaug".
    hit_binavn = next(
        (bn for bn in (lead.binavne or []) if _name_present(bn, text, alnum)), None
    )
    if hit_binavn:
        matched.append("binavn")
    name_hit = bool({"name", "brand", "binavn"} & set(matched))

    phones = list(lead.phone or [])
    if brand is not None:
        phones += list(getattr(brand, "phone", None) or [])
    phone_hit = any(len(_digits(p)) >= 8 and _digits(p) in digits for p in phones)
    if phone_hit:
        matched.append("phone")

    emails = [lead.email, getattr(brand, "email", None) if brand is not None else None]
    email_hit = any(e and e.lower() in text for e in emails)
    if email_hit:
        matched.append("email")

    geo_hit = bool(
        lead.postal_code
        and lead.postal_code in text
        and lead.city
        and _normalize(lead.city) in text
    )
    if geo_hit:
        matched.append("geo")

    addresses = [lead.address, getattr(brand, "address", None) if brand is not None else None]
    addr_exact_hit = any(_exact_address_match(a, spaced) for a in addresses)
    addr_hit = addr_exact_hit or any(_street_match(a, spaced) for a in addresses)
    if addr_exact_hit:
        matched.append("address_exact")
    elif addr_hit:
        matched.append("address")

    # The owner's personal name ("v/ Bjarke Bilde") on the page is a distinctive
    # anchor in its own right — sole-trader sites often never repeat the generic
    # legal name ("Klinik for Fysioterapi") but do credit the owner.
    owner = owner_name(lead.company_name)
    owner_tokens = [t for t in _TOKEN_RE.findall(_normalize(owner)) if len(t) >= 3]
    owner_hit = (
        len(owner_tokens) >= 2 and f" {' '.join(owner_tokens)} " in f" {spaced} "
    )
    if owner_hit:
        matched.append("owner")

    if cvr_hit:
        return 0.99, matched

    # Phone/email/exact-address pin one business; postal code, city and bare
    # street name are shared with every competitor on the same street, so they
    # only corroborate when the name itself already narrows it to one business.
    hard = phone_hit or email_hit or addr_exact_hit
    soft = geo_hit or addr_hit
    trusted = source in _TRUSTED_SOURCES
    if name_hit or owner_hit:
        if trusted:
            # Domain came from their own registered email / production unit.
            return (0.9 if (hard or soft) else 0.85), matched
        hit_names = [
            nm
            for key, nm in (
                ("name", lead.company_name),
                ("brand", brand_name),
                ("binavn", hit_binavn),
            )
            if key in matched
        ]
        # The owner's personal name is always distinctive — "v/ Bjarke Bilde"
        # on the page identifies the business even when the legal name doesn't.
        if not owner_hit and not any(is_distinctive(nm) for nm in hit_names):
            # A generic category+place name ("København Frisør", "Klinik for
            # Fysioterapi") matches any competitor's site — and geo/street match
            # the whole street — so only a hard identity signal can corroborate.
            return (0.9, matched) if hard else (0.0, matched)
        if hard or soft:
            return 0.9, matched
        # Name-only from here: require a distinctive *business* name. An owner
        # hit alone (or with generic trade tokens) and nothing else on the page
        # could be a different person with the same common name.
        distinctive_hits = [nm for nm in hit_names if is_distinctive(nm)]
        if not distinctive_hits:
            return 0.0, matched
        # A guessed domain is circular evidence when the guess came from the
        # stripped slug: any site living at the dictionary-word domain
        # "mellemrum.dk" says "mellemrum" somewhere. Only a host that spells out
        # the full name (restaurantmellemrum.dk) is self-evidencing.
        if source == "name_guess" and not _host_carries_full_name(distinctive_hits, host):
            return 0.0, matched
        return 0.6, matched
    # No name and no CVR — only trust a self-registered host with corroboration.
    if trusted and (hard or soft):
        return 0.7, matched
    return 0.0, matched


class WebsiteDiscoverer:
    """Finds + verifies a real site for a lead, cheapest source first."""

    def __init__(
        self,
        fetcher: WebsiteFetcher,
        resolver: Resolver,
        *,
        brave: BraveSearchClient | None = None,
        penhed_client: Any | None = None,
    ) -> None:
        self._fetcher = fetcher
        self._resolver = resolver
        self._brave = brave
        self._penhed_client = penhed_client

    @classmethod
    def from_settings(
        cls, settings: Any, fetcher: WebsiteFetcher, resolver: Resolver, **kwargs: Any
    ) -> "WebsiteDiscoverer":
        from ..cvr.penhed import EsPenhedClient  # local: keep cvr import lazy

        return cls(
            fetcher,
            resolver,
            brave=BraveSearchClient.from_settings(settings),
            penhed_client=EsPenhedClient.from_settings(settings),
            **kwargs,
        )

    def close(self) -> None:
        if self._brave is not None:
            self._brave.close()
        close = getattr(self._penhed_client, "close", None)
        if callable(close):
            close()

    def discover(self, lead: LeadToQualify) -> DiscoveryResult | None:
        seen: set[str] = set()

        # Tier 0 — email domain (free, strongest).
        email_host = email_domain_candidate(lead.email)
        if email_host and email_host not in seen:
            seen.add(email_host)
            found = self._try(lead, email_host, "email_domain")
            if found:
                return found

        # Tier 1 — name → domain guesses (free, DNS + fetch only).
        for host in name_domain_candidates(lead.company_name):
            if host in seen:
                continue
            seen.add(host)
            found = self._try(lead, host, "name_guess")
            if found:
                return found

        # Tier 1a — the same, from each registered secondary name (binavn). The
        # storefront often trades under it (THYGESEN & THALLAUG → "Restaurant
        # MellemRum" → restaurantmellemrum.dk), and it's free to guess.
        for binavn in lead.binavne or []:
            for host in name_domain_candidates(binavn):
                if host in seen:
                    continue
                seen.add(host)
                found = self._try(lead, host, "name_guess")
                if found:
                    return found

        # Tier 1.5 — production unit (P-enhed): the storefront trading name +
        # its own registered site/contact, which the company record lacks.
        penhed = self._lookup_penhed(lead)
        if penhed is not None:
            # (a) the P-enhed's own registered site — the strongest brand signal.
            penhed_host = _host_from_website(penhed.website)
            if penhed_host and penhed_host not in seen:
                seen.add(penhed_host)
                found = self._try(lead, penhed_host, "penhed", brand=penhed)
                if found:
                    return found
            # P-enhed's own email domain.
            penhed_email_host = email_domain_candidate(penhed.email)
            if penhed_email_host and penhed_email_host not in seen:
                seen.add(penhed_email_host)
                found = self._try(lead, penhed_email_host, "penhed", brand=penhed)
                if found:
                    return found
            # (b) trading-name → domain guesses (verified via the brand name).
            for host in name_domain_candidates(penhed.name):
                if host in seen:
                    continue
                seen.add(host)
                found = self._try(lead, host, "penhed", brand=penhed)
                if found:
                    return found

        # Tier 2 — Brave web search (paid; only when configured). Search the
        # trading names first (P-enhed brand, then binavne) — that's what the
        # storefront ranks under — then fall back to the legal name. Cleaned of
        # owner suffix / legal form: the full legal string tanks recall.
        if self._brave is not None:
            city = lead.city or (penhed.city if penhed is not None else None)
            owner = owner_name(lead.company_name)
            query_names: list[str] = []
            for candidate in (
                penhed.name if penhed is not None else None,
                *(lead.binavne or []),
                lead.company_name,
            ):
                cleaned = search_name(candidate)
                if not cleaned:
                    continue
                # A generic trade name ("Klinik for Fysioterapi") ranks every
                # competitor above the actual business — the owner's name is
                # the distinctive part, so search with it ("… Bjarke Bilde").
                if owner and not is_distinctive(candidate):
                    cleaned = f"{cleaned} {owner}"
                if cleaned not in query_names:
                    query_names.append(cleaned)

            for query_name in query_names[:_MAX_SEARCH_QUERIES]:
                query = f"{query_name} {city}" if city else query_name
                hosts = self._brave.candidate_hosts(query)[:_MAX_SEARCH_CANDIDATES]
                for host in hosts:
                    if host in seen:
                        continue
                    seen.add(host)
                    found = self._try(lead, host, "search", brand=penhed)
                    if found:
                        return found
        return None

    def _lookup_penhed(self, lead: LeadToQualify) -> Any | None:
        """Best-effort production-unit fetch (never raises into discovery)."""
        if self._penhed_client is None or not lead.pnummer:
            return None
        try:
            return self._penhed_client.fetch_by_pnummer(lead.pnummer)
        except Exception:
            return None

    def _try(
        self, lead: LeadToQualify, host: str, source: str, *, brand: Any | None = None
    ) -> DiscoveryResult | None:
        """DNS → fetch → screen → verify one candidate host."""
        host = _strip_www(host.lower().strip("."))
        if _is_directory(host):
            return None
        # Resolve the apex, then fall back to www — plenty of Danish sites
        # publish an A record only on www (roskildesvaneapotek.dk has none;
        # www.roskildesvaneapotek.dk does). Without this we'd call them dead.
        resolved: str | None = None
        for candidate in (host, f"www.{host}"):
            try:
                if self._resolver.addresses(candidate):
                    resolved = candidate
                    break
            except Exception:
                continue
        if resolved is None:
            return None

        url = f"https://{resolved}/"
        try:
            fetch = self._fetcher.fetch(url)
        except Exception:
            return None
        if fetch is None or fetch.failed or classify_from_fetch(fetch) is not None:
            return None  # dead / parked / marketplace

        final_host = _strip_www(
            fetch.final_url.split("://", 1)[-1].split("/", 1)[0].split(":")[0].lower()
        )
        if _is_directory(final_host):
            return None
        # A candidate that redirects onto a shared "group" platform isn't their
        # own independent site — leave it for the qualifier's normal path.
        if is_not_independent(final_host, fetch.final_url, lead.company_name):
            return None

        confidence, matched = verify_ownership(lead, fetch, final_host, source, brand=brand)
        if confidence < _ACCEPT_THRESHOLD:
            return None
        # Record the trading name that actually verified, if any.
        trading_name: str | None = None
        if "brand" in matched:
            trading_name = getattr(brand, "name", None)
        elif "binavn" in matched:
            trading_name = next(iter(lead.binavne or []), None)
        return DiscoveryResult(
            url=fetch.final_url or url,
            host=final_host or host,
            source=source,
            confidence=confidence,
            matched=matched,
            fetch=fetch,
            brand_name=trading_name,
        )
