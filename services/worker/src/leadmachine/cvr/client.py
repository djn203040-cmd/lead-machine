"""CVR Elasticsearch client (issue #14).

Talks to the Erhvervsstyrelsen bulk distribution
(``distribution.virk.dk/cvr-permanent/virksomhed/_search``) over HTTP Basic
auth, scrolling through the full result set with retries on transient errors.

Free system-to-system credentials are requested from ``cvrselvbetjening@erst.dk``.
The whole client sits behind the :class:`leadmachine.cvr.CvrClient` Protocol so
the Datafordeler **GraphQL** service can replace it when the REST/ES channel
sunsets (Q2 2026) without touching callers.
"""

from __future__ import annotations

from typing import Any, Iterator
from urllib.parse import urlsplit, urlunsplit

import httpx

from .._http import DEFAULT_HEADERS, request_json
from .query import SearchParameters, build_es_query

DEFAULT_PAGE_SIZE = 1000
DEFAULT_SCROLL_TTL = "2m"

__all__ = ["EsCvrClient", "DEFAULT_PAGE_SIZE", "DEFAULT_SCROLL_TTL"]


def _scroll_endpoint(search_url: str) -> str:
    """Derive the index-less ``/_search/scroll`` endpoint from a search URL."""
    parts = urlsplit(search_url)
    return urlunsplit((parts.scheme, parts.netloc, "/_search/scroll", "", ""))


class EsCvrClient:
    """Scroll-based reader over the CVR company index."""

    def __init__(
        self,
        *,
        url: str,
        user: str = "",
        password: str = "",
        page_size: int = DEFAULT_PAGE_SIZE,
        scroll_ttl: str = DEFAULT_SCROLL_TTL,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.search_url = url
        self.scroll_url = _scroll_endpoint(url)
        self.page_size = page_size
        self.scroll_ttl = scroll_ttl
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            auth=(user, password) if user or password else None,
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers=DEFAULT_HEADERS,
        )

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> "EsCvrClient":
        """Build from the worker :class:`Settings`."""
        return cls(
            url=settings.cvr_es_url,
            user=settings.cvr_es_user,
            password=settings.cvr_es_password,
            **kwargs,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "EsCvrClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- CvrClient protocol --------------------------------------------------
    def search(self, params: SearchParameters) -> Iterator[dict[str, Any]]:
        """Yield raw ``Vrvirksomhed`` records matching the search parameters."""
        yield from self._scroll(build_es_query(params))

    # -- internals -----------------------------------------------------------
    def _scroll(self, query: dict[str, Any]) -> Iterator[dict[str, Any]]:
        body = {"size": self.page_size, "query": query}
        data = request_json(
            self._client, "POST", f"{self.search_url}?scroll={self.scroll_ttl}", body
        )
        scroll_id = data.get("_scroll_id")
        try:
            while True:
                hits = (data.get("hits") or {}).get("hits") or []
                if not hits:
                    break
                for hit in hits:
                    source = hit.get("_source") or {}
                    yield source.get("Vrvirksomhed", source)
                if not scroll_id:
                    break
                data = request_json(
                    self._client,
                    "POST",
                    self.scroll_url,
                    {"scroll": self.scroll_ttl, "scroll_id": scroll_id},
                )
                scroll_id = data.get("_scroll_id", scroll_id)
        finally:
            if scroll_id:
                self._clear_scroll(scroll_id)

    def _clear_scroll(self, scroll_id: str) -> None:
        """Best-effort release of the server-side scroll context."""
        try:
            self._client.request(
                "DELETE", self.scroll_url, json={"scroll_id": [scroll_id]}
            )
        except httpx.HTTPError:
            pass
