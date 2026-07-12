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
    business_key,
    is_distinctive,
    is_not_independent,
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
_MAX_NAME_CANDIDATES = 4
_MAX_SEARCH_CANDIDATES = 4
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
    return host in DIRECTORY_HOSTS or any(
        host.endswith("." + d) for d in DIRECTORY_HOSTS
    )


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
    independence tokenizer), so we only guess from the distinctive words.
    """
    tokens_set, slug = business_key(company_name)
    if not slug or len(slug) < 4:
        return []
    # Keep name order for the hyphenated variant (business_key returns a set).
    from .independence import _TOKEN_RE, _STOP_TOKENS  # local: internal helpers

    ordered = [
        t for t in _TOKEN_RE.findall(_normalize(strip_owner_suffix(company_name)))
        if t not in _STOP_TOKENS
    ]
    bases: list[str] = []
    if slug:
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
    name_hit = "name" in matched or "brand" in matched

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
    addr_hit = any(_street_match(a, spaced) for a in addresses)
    if addr_hit:
        matched.append("address")

    if cvr_hit:
        return 0.99, matched

    corroborated = phone_hit or email_hit or geo_hit or addr_hit
    trusted = source in _TRUSTED_SOURCES
    if name_hit:
        if corroborated:
            return 0.9, matched
        if trusted:
            return 0.85, matched  # domain came from their own email / production unit
        # Name-only, untrusted source (search / name-guess): only accept when the
        # name is distinctive. A generic category+place name ("København Frisør")
        # matches any competitor's site, so require a hard corroborator instead.
        if is_distinctive(lead.company_name) or (brand_name and is_distinctive(brand_name)):
            return 0.6, matched
        return 0.0, matched
    # No name and no CVR — only trust a self-registered host with corroboration.
    if trusted and corroborated:
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

        # Tier 2 — Brave web search (paid; only when configured). Search on the
        # trading name when we have one — that's what the storefront ranks under.
        if self._brave is not None:
            brand_name = penhed.name if penhed is not None else None
            # Search the cleaned name (no owner suffix / legal form) — the full
            # legal string ("… V/Lars Weltzer ApS") tanks web-search recall.
            query_name = brand_name or search_name(lead.company_name)
            if query_name:
                query = query_name
                city = lead.city or (penhed.city if penhed is not None else None)
                if city:
                    query += f" {city}"
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
        try:
            if not self._resolver.addresses(host):
                return None
        except Exception:
            return None

        url = f"https://{host}/"
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
        return DiscoveryResult(
            url=fetch.final_url or url,
            host=final_host or host,
            source=source,
            confidence=confidence,
            matched=matched,
            fetch=fetch,
            brand_name=getattr(brand, "name", None) if "brand" in matched else None,
        )
