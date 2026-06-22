"""PageSpeed Insights client (M2, issue #21).

Free PSI v5 API (25k/day): ``strategy=mobile``, lab category scores +
red-flag binary audits (research §1.3). CrUX field data is absent for small DK
sites, so we read only ``lighthouseResult`` lab scores. Callers gate this behind
static screens to conserve quota.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from .._http import request_json
from .models import PageSpeedResult

ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
CATEGORIES = ("performance", "seo", "accessibility", "best-practices")
# Binary (0/1) audits that make concrete sales hooks when failed.
RED_FLAG_AUDITS = (
    "is-on-https",
    "viewport",
    "font-size",
    "tap-targets",
    "document-title",
    "meta-description",
)


def _score(categories: dict[str, Any], key: str) -> int | None:
    raw = (categories.get(key) or {}).get("score")
    return round(raw * 100) if isinstance(raw, (int, float)) else None


def parse_pagespeed(data: dict[str, Any]) -> PageSpeedResult:
    lighthouse = data.get("lighthouseResult") or {}
    categories = lighthouse.get("categories") or {}
    audits = lighthouse.get("audits") or {}
    failed = [a for a in RED_FLAG_AUDITS if (audits.get(a) or {}).get("score") == 0]
    return PageSpeedResult(
        performance=_score(categories, "performance"),
        seo=_score(categories, "seo"),
        accessibility=_score(categories, "accessibility"),
        best_practices=_score(categories, "best-practices"),
        failed_audits=failed,
    )


class PageSpeedClient:
    def __init__(self, *, api_key: str = "", http_client: httpx.Client | None = None) -> None:
        self.api_key = api_key
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> "PageSpeedClient":
        return cls(api_key=settings.pagespeed_api_key, **kwargs)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "PageSpeedClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def analyze(self, url: str) -> PageSpeedResult:
        params = [("url", url), ("strategy", "mobile"), ("locale", "da")]
        params += [("category", c) for c in CATEGORIES]
        if self.api_key:
            params.append(("key", self.api_key))
        data = request_json(self._client, "GET", f"{ENDPOINT}?{urlencode(params)}")
        return parse_pagespeed(data)
