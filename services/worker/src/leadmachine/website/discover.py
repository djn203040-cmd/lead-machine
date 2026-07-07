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
from .independence import business_key, is_not_independent
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
    }
)

_TLDS = (".dk", ".com")
_DIGITS_RE = re.compile(r"\d+")
_ACCEPT_THRESHOLD = 0.6  # minimum ownership confidence to attach a discovered site
_MAX_NAME_CANDIDATES = 4
_MAX_SEARCH_CANDIDATES = 6


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
        t for t in _TOKEN_RE.findall(_normalize(company_name or "")) if t not in _STOP_TOKENS
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
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(15.0, connect=8.0))

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
        try:
            data = request_json_get(self._client, self.ENDPOINT, params=params, headers=headers)
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


def request_json_get(client: Any, url: str, *, params: dict, headers: dict) -> dict:
    """GET JSON with the shared retry policy (params/headers on the request)."""
    from .._http import _RETRY  # reuse the retry config
    from tenacity import retry

    @retry(**_RETRY)
    def _do() -> dict:
        resp = client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()

    return _do()


# --- ownership verification ------------------------------------------------
def _page_text(fetch: FetchResult) -> str:
    """Normalized haystack for name/geo matching (title + body, capped)."""
    return _normalize(fetch.html or "")[:200_000]


def verify_ownership(lead: LeadToQualify, fetch: FetchResult, host: str, source: str) -> tuple[float, list[str]]:
    """Score how confidently this page belongs to *this* business.

    Returns ``(confidence, matched)``. A CVR-number match is definitive; a
    company-name match is the required anchor for everything else, corroborated
    by phone / email / geo / the email-domain provenance.
    """
    text = _page_text(fetch)
    digits = _digits(text)
    matched: list[str] = []

    # CVR number in the footer is the strongest signal Danish sites give us.
    cvr = _digits(lead.cvr_number or "")
    cvr_hit = len(cvr) == 8 and cvr in digits
    if cvr_hit:
        matched.append("cvr")

    tokens, slug = business_key(lead.company_name)
    alnum = re.sub(r"[^a-z0-9]", "", text)
    name_hit = bool(
        (slug and len(slug) >= 5 and slug in alnum)
        or (tokens and len(tokens) >= 2 and all(t in text for t in tokens))
        or (len(tokens) == 1 and next(iter(tokens)) in text and len(next(iter(tokens))) >= 5)
    )
    if name_hit:
        matched.append("name")

    phone_hit = any(len(_digits(p)) >= 8 and _digits(p) in digits for p in (lead.phone or []))
    if phone_hit:
        matched.append("phone")

    email_hit = bool(lead.email and lead.email.lower() in text)
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

    if cvr_hit:
        return 0.99, matched

    corroborated = phone_hit or email_hit or geo_hit
    if name_hit:
        if corroborated:
            return 0.9, matched
        if source == "email_domain":
            return 0.85, matched  # domain came from their own email
        return 0.6, matched  # name-only: accept at the threshold
    # No name and no CVR — only trust an email-domain host with corroboration.
    if source == "email_domain" and corroborated:
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
    ) -> None:
        self._fetcher = fetcher
        self._resolver = resolver
        self._brave = brave

    @classmethod
    def from_settings(
        cls, settings: Any, fetcher: WebsiteFetcher, resolver: Resolver, **kwargs: Any
    ) -> "WebsiteDiscoverer":
        return cls(fetcher, resolver, brave=BraveSearchClient.from_settings(settings), **kwargs)

    def close(self) -> None:
        if self._brave is not None:
            self._brave.close()

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

        # Tier 2 — Brave web search (paid; only when configured).
        if self._brave is not None and lead.company_name:
            query = f'"{lead.company_name}"'
            if lead.city:
                query += f" {lead.city}"
            hosts = self._brave.candidate_hosts(query)[:_MAX_SEARCH_CANDIDATES]
            for host in hosts:
                if host in seen:
                    continue
                seen.add(host)
                found = self._try(lead, host, "search")
                if found:
                    return found
        return None

    def _try(self, lead: LeadToQualify, host: str, source: str) -> DiscoveryResult | None:
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
        if fetch.failed or classify_from_fetch(fetch) is not None:
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

        confidence, matched = verify_ownership(lead, fetch, final_host, source)
        if confidence < _ACCEPT_THRESHOLD:
            return None
        return DiscoveryResult(
            url=fetch.final_url or url,
            host=final_host or host,
            source=source,
            confidence=confidence,
            matched=matched,
            fetch=fetch,
        )
