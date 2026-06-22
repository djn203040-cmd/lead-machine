"""Website fetch layer (M2, issue #18).

A :class:`WebsiteFetcher` Protocol with a free, dependency-light
:class:`HttpxFetcher` default that handles the vast majority of small Danish
business sites (light anti-bot). It tries HTTPS first and falls back to HTTP so
the "no HTTPS" signal is captured (``tls_ok``).

The Scrapling escalation (fast ``Fetcher`` → ``StealthyFetcher``/Camoufox for
JS-heavy or blocked targets, per the plan) plugs in behind this same Protocol on
a worker host that has a real browser; it is intentionally not a dependency here
so the worker stays installable and CI stays browser-free.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from .._http import USER_AGENT
from .models import FetchResult

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "da,en;q=0.8",
    "From": USER_AGENT,
}

MAX_HTML_BYTES = 2_000_000


class WebsiteFetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


class HttpxFetcher:
    """Fast HTTP(S) fetch with an HTTPS→HTTP fallback."""

    def __init__(
        self, *, timeout: float = 20.0, http_client: httpx.Client | None = None
    ) -> None:
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers=BROWSER_HEADERS,
            follow_redirects=True,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "HttpxFetcher":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def fetch(self, url: str) -> FetchResult:
        try:
            return self._get(url, tls_ok=True)
        except httpx.HTTPError as exc:
            # HTTPS handshake/connection failed — retry plain HTTP to tell
            # "no HTTPS" (tls_ok=False) apart from "dead".
            if url.lower().startswith("https://"):
                http_url = "http://" + url[len("https://") :]
                try:
                    return self._get(http_url, tls_ok=False)
                except httpx.HTTPError as exc2:
                    return self._fail(http_url, exc2)
            return self._fail(url, exc)

    def _get(self, url: str, *, tls_ok: bool) -> FetchResult:
        resp = self._client.get(url)
        html = "" if resp.is_error else resp.text[:MAX_HTML_BYTES]
        redirects = [str(r.url) for r in resp.history]
        return FetchResult(
            final_url=str(resp.url),
            status=resp.status_code,
            html=html,
            headers={k.lower(): v for k, v in resp.headers.items()},
            redirects=redirects,
            tls_ok=tls_ok and str(resp.url).lower().startswith("https://"),
            fetcher="httpx",
        )

    @staticmethod
    def _fail(url: str, exc: Exception) -> FetchResult:
        return FetchResult(
            final_url=url,
            status=0,
            failed=True,
            tls_ok=False,
            error=f"{type(exc).__name__}: {exc}",
            fetcher="httpx",
        )
