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


@dataclass(slots=True)
class LeadToQualify:
    lead_id: str
    website: str | None = None
