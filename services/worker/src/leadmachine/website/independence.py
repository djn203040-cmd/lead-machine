"""Detect a web presence that isn't really the business's own (M2 follow-up).

Some leads *have* a live site, but it lives as a sub-page on a shared "group"
platform — e.g. ``foodfamilygroup.dk/bistrosolera/`` — instead of their own
domain. That's a strong lead, not a weak one: they don't own their domain, share
SEO authority with siblings/competitors, and can't freely control the site. We
treat it like having no real site of their own (``not_independent``).

The footprint test, per lead: does the registered website's *domain* represent
THIS business? If the domain doesn't carry the business name but the *path* does
(a tenant page), or the host is a known shared platform, it's not independent.
Conservative by design — when the domain is unrelated to the name and the name
isn't in the path, we leave it as a normal site to grade on quality.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

# Known shared/group platforms that host many separate businesses under one
# domain (each business is a sub-page, not the owner). Extend as we find more.
KNOWN_PLATFORM_HOSTS: frozenset[str] = frozenset(
    {
        "foodfamilygroup.dk",
    }
)

# Company-form / generic tokens that never identify a business by name.
_STOP_TOKENS: frozenset[str] = frozenset(
    {
        "aps", "as", "a", "s", "ivs", "ihs", "ks", "is", "pmv", "smba", "amba",
        "fmba", "ltd", "gmbh", "inc", "co", "holding", "group", "gruppe",
        "gruppen", "danmark", "denmark", "dk", "the", "og", "and",
        "restaurant", "restauranten", "cafe", "café", "bar", "bistro", "kro",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MIN_SLUG_LEN = 5  # below this we can't match a name confidently


def _normalize(text: str) -> str:
    """Lowercase + fold Danish/diacritic letters to their ASCII web spelling."""
    text = text.lower()
    for src, dst in (("æ", "ae"), ("ø", "oe"), ("å", "aa"), ("é", "e"), ("ü", "u")):
        text = text.replace(src, dst)
    return text


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def business_key(company_name: str | None) -> tuple[set[str], str]:
    """Return (significant name tokens, concatenated slug) for matching.

    Drops company-form and generic words. The slug is every *significant* token
    joined; we also keep individual long tokens for partial matches.
    """
    if not company_name:
        return set(), ""
    tokens = [t for t in _TOKEN_RE.findall(_normalize(company_name)) if t not in _STOP_TOKENS]
    significant = {t for t in tokens if len(t) >= 3}
    slug = "".join(tokens)
    return significant, slug


def _alnum(text: str) -> str:
    return "".join(_TOKEN_RE.findall(_normalize(text)))


def _host_carries_name(host: str, tokens: set[str], slug: str) -> bool:
    """Does the domain itself represent the business (their own site)?"""
    host_alnum = _alnum(host)
    if slug and len(slug) >= _MIN_SLUG_LEN and slug in host_alnum:
        return True
    return any(len(t) >= 4 and t in host_alnum for t in tokens)


def _path_carries_name(path: str, tokens: set[str], slug: str) -> bool:
    """Is the business identified by the URL *path* (a tenant sub-page)?"""
    path_alnum = _alnum(path)
    if not path_alnum:
        return False
    if slug and len(slug) >= _MIN_SLUG_LEN and slug in path_alnum:
        return True
    return bool(tokens) and all(t in path_alnum for t in tokens)


def is_not_independent(host: str | None, url: str | None, company_name: str | None) -> bool:
    """True when the live site isn't the business's own independent domain."""
    if not host:
        return False
    host_l = _strip_www(host.lower().strip("."))
    if host_l in KNOWN_PLATFORM_HOSTS or any(
        host_l.endswith("." + p) for p in KNOWN_PLATFORM_HOSTS
    ):
        return True

    tokens, slug = business_key(company_name)
    if len(slug) < _MIN_SLUG_LEN:
        return False  # name too short/generic to judge confidently
    if _host_carries_name(host_l, tokens, slug):
        return False  # their own domain — grade it on quality instead

    path = urlsplit(url).path if url else ""
    return _path_carries_name(path, tokens, slug)
