"""Resolve a lead's CVR website field into a candidate URL + bucket (M2).

Classifies the registered ``Hjemmeside`` per research §1.5: no site, a
social-media-only presence, a free builder/placeholder subdomain, or a real
custom-domain site worth fetching. The first three are already "no real
website" — the hottest leads — and skip fetching entirely.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from .models import ResolveResult

# Hosts that mean "social-media-only presence" (no real website).
SOCIAL_HOSTS: frozenset[str] = frozenset(
    {
        "facebook.com",
        "m.facebook.com",
        "fb.me",
        "fb.com",
        "instagram.com",
        "linktr.ee",
        "linktree.com",
        "beacons.ai",
        "linkin.bio",
        "taplink.cc",
        "linkedin.com",
    }
)

# Free builder subdomains / placeholders = "no real website".
FREE_SUBDOMAIN_SUFFIXES: tuple[str, ...] = (
    ".wixsite.com",
    ".weebly.com",
    ".godaddysites.com",
    ".business.site",
    ".blogspot.com",
    ".wordpress.com",
    ".jimdosite.com",
    ".webnode.com",
    ".simplesite.com",
    ".one.com",
)
FREE_SUBDOMAIN_HOSTS: frozenset[str] = frozenset({"sites.google.com", "business.site"})


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def resolve_website(raw: str | None) -> ResolveResult:
    """Bucket a raw website value into none / social / free_subdomain / url."""
    if not raw or not raw.strip():
        return ResolveResult(kind="none", raw=raw)

    candidate = raw.strip()
    if "://" not in candidate:
        candidate = "https://" + candidate

    parts = urlsplit(candidate)
    netloc = parts.netloc.split("@")[-1]
    host = netloc.split(":")[0].lower().strip(".")
    if not host or "." not in host:
        return ResolveResult(kind="none", raw=raw)

    bare = _strip_www(host)

    if bare in SOCIAL_HOSTS:
        return ResolveResult(kind="social", url=candidate, host=bare, raw=raw)

    if bare in FREE_SUBDOMAIN_HOSTS or any(host.endswith(s) for s in FREE_SUBDOMAIN_SUFFIXES):
        return ResolveResult(kind="free_subdomain", url=candidate, host=bare, raw=raw)

    # Real custom-domain site: normalize to a clean https URL to fetch.
    clean = urlunsplit(("https", host, parts.path or "/", "", ""))
    return ResolveResult(kind="url", url=clean, host=bare, raw=raw)
