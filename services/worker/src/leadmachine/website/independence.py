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

# Legal-form / corporate tokens — never part of a domain or a business identity.
_LEGAL_TOKENS: frozenset[str] = frozenset(
    {
        "aps", "as", "a", "s", "ivs", "ihs", "ks", "is", "pmv", "smba", "amba",
        "fmba", "ltd", "gmbh", "inc", "co", "holding", "group", "gruppe",
        "gruppen", "danmark", "denmark", "dk", "the", "og", "and",
    }
)
# Trade words dropped when *matching* a name (too generic to identify a firm) —
# but businesses often DO put them in their domain (restaurantmellemrum.dk), so
# `full_slug` keeps them for domain guessing.
_TRADE_TOKENS: frozenset[str] = frozenset(
    {"restaurant", "restauranten", "cafe", "café", "bar", "bistro", "kro"}
)
# Company-form / generic tokens that never identify a business by name.
_STOP_TOKENS: frozenset[str] = _LEGAL_TOKENS | _TRADE_TOKENS

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MIN_SLUG_LEN = 5  # below this we can't match a name confidently

# Non-distinctive tokens: trade words + Danish city/place names. A name made up
# ONLY of these ("København Frisør", "Tandlægerne i Centrum") identifies a
# *category*, not a *business* — any competitor's site matches it — so a bare
# name-match from web search on such a name isn't trustworthy without a hard
# corroborator (CVR/phone/address). Kept separate from _STOP_TOKENS because
# these ARE worth guessing/searching on, just not verifying on alone.
_GENERIC_TOKENS: frozenset[str] = frozenset(
    {
        # trades
        "frisoer", "frisor", "frisoersalon", "salon", "salonen", "barber", "klip",
        "tandlaege", "tandlaegen", "tandlaegerne", "tandlaegeselskabet", "tandklinik",
        "laege", "laegen", "laegerne", "laegehus", "laegehuset", "laegeklinik",
        "laegeklinikken", "klinik", "klinikken", "speciallaege", "fysioterapi",
        "kiropraktor", "kiropraktik", "kiropraktisk", "apotek", "apoteket", "optik",
        "optiker", "dyreklinik", "dyrehospital", "dyrlaege", "oejenklinik", "oejenlaege",
        "restauration", "restaurationen", "cafeen", "cafeteria", "pizza", "pizzeria",
        "grill", "grillen", "grillbar", "sushi", "kebab", "shawarma", "burger",
        "bageri", "bageren", "konditori", "kroen", "bodega", "pub", "vinbar",
        "spisested", "spisestedet", "smoerrebroed", "slagter", "slagteren", "blomster",
        "kiosk", "kiosken", "cut", "hair", "beauty", "wellness", "massage",
        # cities / places
        "koebenhavn", "kobenhavn", "cph", "frederiksberg", "aarhus", "arhus", "odense",
        "aalborg", "esbjerg", "randers", "kolding", "horsens", "vejle", "roskilde",
        "herning", "hoersholm", "silkeborg", "naestved", "fredericia", "viborg",
        "koege", "holstebro", "taastrup", "slagelse", "hilleroed", "helsingoer",
        "soenderborg", "svendborg", "hjoerring", "holbaek", "soroe", "ringsted",
        "glostrup", "ballerup", "gladsaxe", "hvidovre", "greve", "vejen",
        # geographic generics
        "centrum", "city", "midtby", "bymidten", "torv", "torvet", "hovedgaden",
        "noerrebro", "oesterbro", "vesterbro", "amager", "sydhavn", "sydhavnen",
    }
)

# Danish CVR names often append the owner: "Frisør X v/Anna Hansen",
# "Tandlægerne i Centrum V/Lars Weltzer", "KJ Minh /Vu Nguyen". The storefront
# site rarely repeats the owner's personal name, so we strip that suffix before
# matching/guessing — otherwise the extra name tokens block an otherwise-clean
# match. Only the unambiguous "v/", "v." and " /Owner" markers are cut.
_OWNER_SUFFIX_RE = re.compile(r"(?i)\s+v[/.].*$|\s+/\s*\S.*$")
# Legal-form suffix, dropped from a name used as a web-search query.
_LEGAL_FORM_RE = re.compile(r"(?i)\s+(?:aps|a/s|i/s|ivs|k/s|p/s|s/i|smba|amba|fmba|g/s)\b\.?")


def strip_owner_suffix(name: str | None) -> str:
    """Drop a trailing ``v/<owner>`` (or ``/<owner>``) personal-name suffix."""
    return _OWNER_SUFFIX_RE.sub("", name or "").strip()


def search_name(company_name: str | None) -> str:
    """A cleaned business name for a web search — no owner suffix, no legal form."""
    return _LEGAL_FORM_RE.sub("", strip_owner_suffix(company_name)).strip()


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
    company_name = strip_owner_suffix(company_name)
    tokens = [t for t in _TOKEN_RE.findall(_normalize(company_name)) if t not in _STOP_TOKENS]
    significant = {t for t in tokens if len(t) >= 3}
    slug = "".join(tokens)
    return significant, slug


def full_slug(company_name: str | None) -> str:
    """Slug keeping trade words — businesses put them in the domain.

    ``"RESTAURANT MELLEMRUM ApS"`` → ``"restaurantmellemrum"`` (whereas
    :func:`business_key`'s slug drops "restaurant" → ``"mellemrum"``). Only the
    legal form is stripped.
    """
    if not company_name:
        return ""
    name = strip_owner_suffix(company_name)
    return "".join(
        t for t in _TOKEN_RE.findall(_normalize(name)) if t not in _LEGAL_TOKENS
    )


def is_distinctive(company_name: str | None) -> bool:
    """Whether a name identifies *a business*, not just a category+place.

    ``"København Frisør"`` / ``"Tandlægerne i Centrum"`` are only generic trade +
    city words → any competitor's site matches them, so a bare web-search
    name-match isn't trustworthy. ``"Noribar"`` / ``"La Cabra"`` / ``"Det Glade
    Vanvid"`` keep a distinctive token → trustworthy.
    """
    tokens, _ = business_key(company_name)
    return any(t not in _GENERIC_TOKENS for t in tokens)


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
