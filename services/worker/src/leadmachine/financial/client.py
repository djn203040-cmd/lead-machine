"""Client for Virk's annual-report channel (M3).

``distribution.virk.dk/offentliggoerelser/_search`` is a **free, unauthenticated**
Elasticsearch index of published company documents. We query it by CVR number,
pick the most recent annual report that ships an XBRL instance, and download
that document for parsing.
"""

from __future__ import annotations

from typing import Any

import httpx

from .._http import DEFAULT_HEADERS, request_bytes, request_json
from .models import Report

DEFAULT_FETCH_SIZE = 30


def _to_report(source: dict[str, Any]) -> Report | None:
    cvr = source.get("cvrNummer")
    if cvr is None:
        return None
    periode = (source.get("regnskab") or {}).get("regnskabsperiode") or {}
    docs = source.get("dokumenter") or []
    xbrl_url = next(
        (d.get("dokumentUrl") for d in docs if d.get("dokumentMimeType") == "application/xml"),
        None,
    )
    pdf_url = next(
        (d.get("dokumentUrl") for d in docs if d.get("dokumentMimeType") == "application/pdf"),
        None,
    )
    return Report(
        cvr_number=str(cvr),
        period_start=periode.get("startDato"),
        period_end=periode.get("slutDato"),
        published_at=source.get("offentliggoerelsesTidspunkt"),
        xbrl_url=xbrl_url,
        pdf_url=pdf_url,
    )


class FinancialClient:
    """Reads annual reports for a CVR number from the offentliggørelser index."""

    def __init__(
        self,
        *,
        url: str,
        http_client: httpx.Client | None = None,
        fetch_size: int = DEFAULT_FETCH_SIZE,
    ) -> None:
        self.search_url = url
        self.fetch_size = fetch_size
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        )

    @classmethod
    def from_settings(cls, settings: Any, **kwargs: Any) -> "FinancialClient":
        return cls(url=settings.cvr_offentliggoerelser_url, **kwargs)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "FinancialClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def fetch_latest_report(self, cvr_number: str | int) -> Report | None:
        """Most recent annual report (with an XBRL document) for a CVR number."""
        query = {
            "size": self.fetch_size,
            "query": {"bool": {"filter": [{"term": {"cvrNummer": int(cvr_number)}}]}},
        }
        data = request_json(self._client, "POST", self.search_url, query)
        hits = (data.get("hits") or {}).get("hits") or []
        reports = [
            r
            for r in (_to_report(h.get("_source") or {}) for h in hits)
            if r is not None and r.xbrl_url
        ]
        if not reports:
            return None
        reports.sort(key=lambda r: (r.period_end or "", r.published_at or ""), reverse=True)
        return reports[0]

    def download_xbrl(self, report: Report) -> bytes | None:
        if not report.xbrl_url:
            return None
        return request_bytes(self._client, "GET", report.xbrl_url)
