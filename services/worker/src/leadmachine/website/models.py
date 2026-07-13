"""Dataclasses for website qualification (M2)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


class DomainStatus(str, Enum):
    LIVE = "live"
    DEAD = "dead"
    PARKED = "parked"


@dataclass(slots=True)
class ResolveResult:
    """Outcome of resolving a lead's website field to a candidate URL.

    ``kind`` ∈ {none, social, free_subdomain, url}.
    """

    kind: str
    url: str | None = None
    host: str | None = None
    raw: str | None = None
    confidence: str = "high"

    def as_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(slots=True)
class FetchResult:
    final_url: str
    status: int
    html: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    redirects: list[str] = field(default_factory=list)
    tls_ok: bool = True
    fetcher: str = "httpx"
    failed: bool = False
    error: str | None = None

    @property
    def has_https(self) -> bool:
        return self.final_url.lower().startswith("https://") and self.tls_ok


@dataclass(slots=True)
class WebsiteSignals:
    has_viewport: bool = False
    has_https: bool = False
    legacy_markup: bool = False
    legacy_reasons: list[str] = field(default_factory=list)
    cms: str | None = None
    cms_version: str | None = None
    copyright_year: int | None = None
    is_one_page: bool = False
    has_fb_link: bool = False
    fb_url: str | None = None
    has_meta_pixel: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PageSpeedResult:
    performance: int | None = None
    seo: int | None = None
    accessibility: int | None = None
    best_practices: int | None = None
    failed_audits: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _drop_none(asdict(self))


@dataclass(slots=True)
class WebsiteAssessment:
    website_need: str
    evidence: dict[str, Any] = field(default_factory=dict)
    social: dict[str, Any] = field(default_factory=dict)
    # Where the graded site came from: ``cvr`` (registered), or one of the
    # discovery tiers (``email_domain`` / ``name_guess`` / ``search``). ``None``
    # when there is no site (need = none/dead/parked/…).
    website_source: str | None = None
    discovered_url: str | None = None
    # LLM quality tier of a live site ∈ {dated, basic, modern, premium}.
    website_quality: str | None = None


@dataclass(slots=True)
class LeadToQualify:
    lead_id: str
    website: str | None = None
    company_name: str | None = None
    # Corroborating signals used to discover + verify a site when CVR has none.
    email: str | None = None
    phone: list[str] = field(default_factory=list)
    city: str | None = None
    postal_code: str | None = None
    cvr_number: str | None = None
    address: str | None = None  # street line, for address-match verification
    # Production-unit number: unlocks the storefront trading name + its own site.
    pnummer: str | None = None
    # Registered secondary names (CVR ``binavne``) — often the trading name the
    # storefront + its website actually use (THYGESEN & THALLAUG → MellemRum).
    binavne: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DiscoveryResult:
    """A verified, live website found for a lead that had none in CVR."""

    url: str
    host: str
    source: str  # email_domain | name_guess | penhed | search
    confidence: float  # 0..1 ownership confidence
    matched: list[str] = field(default_factory=list)  # which signals matched
    fetch: "FetchResult | None" = None  # the page we verified (reused for analysis)
    brand_name: str | None = None  # storefront/trading name, when verified via a P-enhed

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "url": self.url,
            "host": self.host,
            "source": self.source,
            "confidence": round(self.confidence, 2),
            "matched": self.matched,
        }
        if self.brand_name:
            d["brand_name"] = self.brand_name
        return d


@dataclass(slots=True)
class WebsiteQuality:
    """LLM grade of a live site's design/age."""

    tier: str  # dated | basic | modern | premium
    reasons: list[str] = field(default_factory=list)
    justification_da: str = ""
    model: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
