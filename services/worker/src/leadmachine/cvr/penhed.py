"""Production-unit (produktionsenhed / P-enhed) lookup.

A lead like **Kakurega ApS** (the operating company) often runs a differently
branded storefront — **Noribar** — and the website + public contact details
live under the *brand*, not the company name. That brand is a separate CVR
object: the **produktionsenhed** (P-enhed), keyed by its ``pNummer``. The
company (``Vrvirksomhed``) record only carries a bare ``pNummer`` under
``penheder``; the trading name, ``hjemmeside``, ``elektroniskPost``,
``telefonNummer`` and ``beliggenhedsadresse`` sit on the P-enhed record in the
``cvr-permanent/produktionsenhed`` index (same host + credentials as the company
index).

This module fetches a P-enhed by pNummer and flattens the parts website
discovery needs (trading name + its own site/contact), reusing the same
period-stamped parsers as the company mapper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from .._http import DEFAULT_HEADERS, request_json
from .mapper import (
    _format_address,
    _is_current,
    _latest_named,
    _pick_current,
    _pick_current_all,
    _unwrap,
)

# The pNummer field in the produktionsenhed ES mapping. NB: the root document
# key is "VrproduktionsEnhed" with a capital E (ES field names are
# case-sensitive) — confirmed against the Erhvervsstyrelsen ES docs.
PENHED_ROOT = "VrproduktionsEnhed"
PNUMMER_FIELD = f"{PENHED_ROOT}.pNummer"

__all__ = [
    "PenhedInfo",
    "PenhedClient",
    "EsPenhedClient",
    "map_penhed",
    "current_pnummer",
    "current_binavne",
]


@dataclass(slots=True)
class PenhedInfo:
    """The parts of a P-enhed website discovery cares about."""

    pnummer: str
    name: str | None = None  # the storefront / trading name ("Noribar")
    website: str | None = None
    email: str | None = None
    phone: list[str] = field(default_factory=list)
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    branchekode: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "pnummer": self.pnummer,
            "name": self.name,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
        }


def current_pnummer(cvr_record: dict[str, Any] | None) -> str | None:
    """The current (or latest) pNummer from a company blob's ``penheder`` list."""
    if not cvr_record:
        return None
    v = _unwrap(cvr_record)
    penheder = v.get("penheder") or []
    if not penheder:
        return None
    current = [p for p in penheder if _is_current(p)]
    chosen = current[-1] if current else penheder[-1]
    pn = chosen.get("pNummer")
    return str(pn) if pn not in (None, "") else None


def current_binavne(cvr_record: dict[str, Any] | None) -> list[str]:
    """Current secondary company names (``binavne``) from a company blob.

    A Danish company can register secondary names, and the storefront often
    trades under one: THYGESEN & THALLAUG ApS has binavn "RESTAURANT MELLEMRUM
    ApS" — and the site lives at restaurantmellemrum.dk, not under the legal
    name. Only currently-valid entries (``periode.gyldigTil`` null) are returned.
    """
    if not cvr_record:
        return []
    v = _unwrap(cvr_record)
    out: list[str] = []
    for item in v.get("binavne") or []:
        if not _is_current(item):
            continue
        navn = item.get("navn")
        if navn and navn not in out:
            out.append(str(navn))
    return out


def _unwrap_penhed(record: dict[str, Any]) -> dict[str, Any]:
    """Accept a full ``_source`` ({"VrproduktionsEnhed": {...}}) or the object."""
    inner = record.get(PENHED_ROOT)
    return inner if isinstance(inner, dict) else record


def map_penhed(record: dict[str, Any]) -> PenhedInfo:
    """Flatten a raw ``Vrproduktionsenhed`` record into a :class:`PenhedInfo`."""
    p = _unwrap_penhed(record)
    meta = p.get("produktionsEnhedMetadata") or {}

    pnummer = str(p.get("pNummer") or "").strip()

    name = (meta.get("nyesteNavn") or {}).get("navn")
    if not name:
        name = _latest_named(p.get("navne"))

    addr = meta.get("nyesteBeliggenhedsadresse") or {}
    postnummer = addr.get("postnummer")

    return PenhedInfo(
        pnummer=pnummer,
        name=name,
        website=_pick_current(p.get("hjemmeside")),
        email=_pick_current(p.get("elektroniskPost")),
        phone=_pick_current_all(p.get("telefonNummer")),
        address=_format_address(addr),
        postal_code=str(postnummer) if postnummer not in (None, "") else None,
        city=addr.get("postdistrikt"),
        branchekode=(meta.get("nyesteHovedbranche") or {}).get("branchekode"),
    )


class PenhedClient(Protocol):
    def fetch_by_pnummer(self, pnummer: str | int) -> PenhedInfo | None:
        """Return the production unit for ``pNummer``, or ``None`` if absent."""
        ...


class EsPenhedClient:
    """Single-shot reader over the CVR production-unit index (fetch by pNummer)."""

    def __init__(
        self,
        *,
        url: str,
        user: str = "",
        password: str = "",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.search_url = url
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            auth=(user, password) if user or password else None,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers=DEFAULT_HEADERS,
        )

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> "EsPenhedClient | None":
        """Build from the worker :class:`Settings`, or ``None`` without creds."""
        if not (settings.cvr_es_user or settings.cvr_es_password):
            return None
        return cls(
            url=settings.cvr_es_penhed_url,
            user=settings.cvr_es_user,
            password=settings.cvr_es_password,
            **kwargs,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "EsPenhedClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def fetch_by_pnummer(self, pnummer: str | int) -> PenhedInfo | None:
        """Look up one production unit by its pNummer (best-effort → ``None``).

        The pNummer is queried as a string, matching the Erhvervsstyrelsen ES
        docs (``{"term": {"VrproduktionsEnhed.pNummer": "1028076343"}}``).
        """
        body = {"size": 1, "query": {"term": {PNUMMER_FIELD: str(pnummer)}}}
        try:
            data = request_json(self._client, "POST", self.search_url, body)
        except Exception:
            return None
        hits = ((data.get("hits") or {}).get("hits")) or []
        if not hits:
            return None
        source = hits[0].get("_source") or {}
        return map_penhed(source)
