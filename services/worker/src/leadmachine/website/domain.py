"""Dead / parked domain detection (M2, issue #19).

Cheap checks that short-circuit before a full fetch:
- **DNS** — no A/AAAA record (NXDOMAIN / no-address) ⇒ DEAD.
- **Parking nameservers** — NS on the apex matches a known parking provider ⇒ PARKED.
- **HTTP/redirect/TLS** (post-fetch) — 4xx/5xx or failure ⇒ DEAD; redirect to a
  domain marketplace, or parked-page content ⇒ PARKED.

DNS is behind a :class:`Resolver` Protocol so it is testable without network.
"""

from __future__ import annotations

from typing import Protocol

from .models import DomainStatus, FetchResult

# Nameserver bases used by domain-parking / for-sale providers.
PARKING_NAMESERVERS: tuple[str, ...] = (
    "sedoparking.com",
    "bodis.com",
    "parkingcrew.net",
    "above.com",
    "dan.com",
    "hugedomains.com",
    "afternic.com",
    "fabulous.com",
    "voodoo.com",
    "parklogic.com",
    "namecheaphosting.com",
    "registrar-servers.com",
    "uniregistrymarket.link",
    "domaincontrol.com",
)

# Hosts a parked/for-sale domain commonly redirects to.
MARKETPLACE_HOSTS: frozenset[str] = frozenset(
    {
        "dan.com",
        "sedo.com",
        "hugedomains.com",
        "afternic.com",
        "undeveloped.com",
        "buydomains.com",
        "uniregistry.com",
    }
)

# Phrases on a parked landing page.
PARKED_CONTENT_MARKERS: tuple[str, ...] = (
    "this domain is for sale",
    "domain is for sale",
    "buy this domain",
    "domain parking",
    "parked free, courtesy of",
    "the domain you requested",
    "domænet er til salg",
    "dette domæne er til salg",
    "købe dette domæne",
)


class Resolver(Protocol):
    def addresses(self, domain: str) -> list[str]: ...
    def nameservers(self, domain: str) -> list[str]: ...


def _apex(host: str) -> str:
    """Naive registrable domain (good enough for single-level TLDs like .dk)."""
    labels = host.strip(".").split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _matches_parking(nameservers: list[str]) -> bool:
    return any(
        any(ns.rstrip(".").endswith(base) for base in PARKING_NAMESERVERS) for ns in nameservers
    )


def classify_domain(host: str, resolver: Resolver) -> DomainStatus:
    """DNS-only classification (run before fetching)."""
    if not resolver.addresses(host):
        return DomainStatus.DEAD
    if _matches_parking(resolver.nameservers(_apex(host))):
        return DomainStatus.PARKED
    return DomainStatus.LIVE


def classify_from_fetch(result: FetchResult) -> DomainStatus | None:
    """Refine status from an HTTP fetch; ``None`` means 'looks live'."""
    if result.failed:
        return DomainStatus.DEAD
    if result.status >= 400:
        return DomainStatus.DEAD
    final_host = result.final_url.split("://", 1)[-1].split("/", 1)[0].lower()
    final_host = final_host[4:] if final_host.startswith("www.") else final_host
    if final_host in MARKETPLACE_HOSTS:
        return DomainStatus.PARKED
    haystack = result.html[:5000].lower()
    if any(marker in haystack for marker in PARKED_CONTENT_MARKERS):
        return DomainStatus.PARKED
    return None


class DnsResolver:
    """dnspython-backed resolver (the production default)."""

    def __init__(self, timeout: float = 5.0) -> None:
        import dns.resolver

        self._resolver = dns.resolver.Resolver()
        self._resolver.timeout = timeout
        self._resolver.lifetime = timeout

    def _query(self, domain: str, rrtype: str) -> list[str]:
        import dns.exception
        import dns.resolver

        try:
            answer = self._resolver.resolve(domain, rrtype)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            return []
        except dns.exception.DNSException:
            return []
        return [r.to_text() for r in answer]

    def addresses(self, domain: str) -> list[str]:
        return self._query(domain, "A") + self._query(domain, "AAAA")

    def nameservers(self, domain: str) -> list[str]:
        return [ns.lower() for ns in self._query(domain, "NS")]
