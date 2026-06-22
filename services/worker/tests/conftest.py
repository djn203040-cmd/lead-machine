"""Shared test fixtures + fakes for the CVR discovery engine."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_sources() -> list[dict[str, Any]]:
    """The mocked CVR ES ``_source`` documents ({"Vrvirksomhed": {...}})."""
    return json.loads((FIXTURES / "cvr_companies.json").read_text(encoding="utf-8"))


@pytest.fixture
def sources() -> list[dict[str, Any]]:
    return load_sources()


@pytest.fixture
def companies(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unwrapped ``Vrvirksomhed`` records, as a CvrClient yields them."""
    return [s["Vrvirksomhed"] for s in sources]


# --- fakes -----------------------------------------------------------------
class MockCvrClient:
    """In-memory CvrClient yielding pre-canned Vrvirksomhed records."""

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self.records = records
        self.last_params: Any = None

    def search(self, params: Any) -> Iterator[dict[str, Any]]:
        self.last_params = params
        yield from self.records


class FakeLeadWriter:
    """Records upserts keyed by CVR number (so dedup is observable)."""

    def __init__(self) -> None:
        self.store: dict[str, tuple[Any, dict[str, Any], str | None]] = {}
        self.calls = 0

    def upsert(self, lead: Any, raw_cvr: dict[str, Any], search_id: str | None) -> None:
        self.calls += 1
        self.store[lead.cvr_number] = (lead, raw_cvr, search_id)

    @property
    def count(self) -> int:
        return len(self.store)


class _FakeTable:
    def __init__(self, name: str, log: list[Any]) -> None:
        self.name = name
        self.log = log
        self._row: Any = None
        self._on_conflict: str | None = None

    def upsert(self, row: Any, on_conflict: str | None = None) -> "_FakeTable":
        self._row = row
        self._on_conflict = on_conflict
        return self

    def update(self, row: Any) -> "_FakeTable":
        self._row = row
        return self

    def eq(self, *args: Any) -> "_FakeTable":
        return self

    def execute(self) -> SimpleNamespace:
        self.log.append((self.name, self._row, self._on_conflict))
        if self.name == "leads":
            return SimpleNamespace(data=[{"id": "lead-uuid-1"}])
        return SimpleNamespace(data=[{"lead_id": "lead-uuid-1"}])


class FakeSupabase:
    """Minimal stand-in for the supabase client (table().upsert().execute())."""

    def __init__(self) -> None:
        self.log: list[Any] = []

    def table(self, name: str) -> _FakeTable:
        return _FakeTable(name, self.log)


@pytest.fixture
def fake_writer() -> FakeLeadWriter:
    return FakeLeadWriter()


# --- httpx scroll transport ------------------------------------------------
def make_scroll_transport(
    sources: list[dict[str, Any]], page_size: int = 2
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """Build a MockTransport that emulates ES scroll over ``sources``.

    Returns the transport and a list that captures every request made.
    """
    pages = [sources[i : i + page_size] for i in range(0, len(sources), page_size)] or [[]]
    captured: list[httpx.Request] = []
    state = {"page": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"succeeded": True})
        page = state["page"]
        hits = pages[page] if page < len(pages) else []
        state["page"] = page + 1
        body = {
            "_scroll_id": f"scroll-{state['page']}",
            "hits": {"hits": [{"_id": str(i), "_source": s} for i, s in enumerate(hits)]},
        }
        return httpx.Response(200, json=body)

    return httpx.MockTransport(handler), captured


# --- financial enrichment (M3) ---------------------------------------------
def load_xbrl() -> bytes:
    return (FIXTURES / "xbrl_sample.xml").read_bytes()


@pytest.fixture
def xbrl_bytes() -> bytes:
    return load_xbrl()


@pytest.fixture
def offentliggoerelser_response() -> dict[str, Any]:
    return json.loads((FIXTURES / "offentliggoerelser_sample.json").read_text(encoding="utf-8"))


@pytest.fixture
def deltager_record() -> dict[str, Any]:
    return json.loads((FIXTURES / "cvr_deltager.json").read_text(encoding="utf-8"))


class MockFinancialClient:
    """In-memory FinancialClient returning a canned report + XBRL bytes."""

    def __init__(self, report: Any, xbrl: bytes | None) -> None:
        self.report = report
        self.xbrl = xbrl
        self.requested: list[str] = []

    def fetch_latest_report(self, cvr_number: Any) -> Any:
        self.requested.append(str(cvr_number))
        return self.report

    def download_xbrl(self, report: Any) -> bytes | None:
        return self.xbrl


class FakeFinancialWriter:
    """Records financial/contact writes keyed by lead_id."""

    def __init__(self) -> None:
        self.writes: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}

    def write(self, lead_id: str, financial: dict[str, Any], contact: dict[str, Any]) -> None:
        self.writes[lead_id] = (financial, contact)


# --- website qualification (M2) --------------------------------------------
class FakeResolver:
    """Configurable DNS resolver. Defaults to a live, non-parked domain."""

    def __init__(
        self, addr_map: dict[str, list[str]] | None = None, ns_map: dict[str, list[str]] | None = None
    ) -> None:
        self.addr_map = addr_map or {}
        self.ns_map = ns_map or {}

    def addresses(self, domain: str) -> list[str]:
        return self.addr_map.get(domain, ["1.2.3.4"])

    def nameservers(self, domain: str) -> list[str]:
        return self.ns_map.get(domain, ["ns1.hosting.dk", "ns2.hosting.dk"])


class StubFetcher:
    """Returns canned FetchResults; ``results`` is a {url: FetchResult} map or a
    single FetchResult used for any URL."""

    def __init__(self, results: Any) -> None:
        self.results = results
        self.fetched: list[str] = []

    def fetch(self, url: str) -> Any:
        self.fetched.append(url)
        if isinstance(self.results, dict):
            return self.results.get(url) or self.results.get("*")
        return self.results


class MockPageSpeed:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[str] = []

    def analyze(self, url: str) -> Any:
        self.calls.append(url)
        return self.result


class FakeWebsiteWriter:
    def __init__(self) -> None:
        self.writes: dict[str, tuple[str, dict[str, Any], dict[str, Any]]] = {}

    def write(
        self, lead_id: str, website_need: str, evidence: dict[str, Any], social: dict[str, Any]
    ) -> None:
        self.writes[lead_id] = (website_need, evidence, social)


# --- scoring (M4) ----------------------------------------------------------
class FakeScoreWriter:
    """Records score writes keyed by lead_id."""

    def __init__(self) -> None:
        self.writes: dict[str, tuple[int, dict[str, Any]]] = {}

    def write(self, lead_id: str, total: int, breakdown: dict[str, Any]) -> None:
        self.writes[lead_id] = (total, breakdown)
