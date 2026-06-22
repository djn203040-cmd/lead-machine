import httpx

from leadmachine.cvr.client import EsCvrClient, _is_retryable, _scroll_endpoint

from .conftest import make_scroll_transport

URL = "http://distribution.virk.dk/cvr-permanent/virksomhed/_search"


def test_scroll_endpoint_is_index_less() -> None:
    assert _scroll_endpoint(URL) == "http://distribution.virk.dk/_search/scroll"


def test_is_retryable_predicate() -> None:
    req = httpx.Request("POST", URL)
    assert _is_retryable(httpx.ConnectError("boom")) is True
    assert _is_retryable(httpx.HTTPStatusError("", request=req, response=httpx.Response(503, request=req))) is True
    assert _is_retryable(httpx.HTTPStatusError("", request=req, response=httpx.Response(404, request=req))) is False
    assert _is_retryable(ValueError("nope")) is False


def test_search_scrolls_all_pages(sources) -> None:
    transport, captured = make_scroll_transport(sources, page_size=2)
    http = httpx.Client(transport=transport)
    client = EsCvrClient(url=URL, http_client=http, page_size=2)

    records = list(client._scroll({"match_all": {}}))

    assert len(records) == len(sources)
    assert [r["cvrNummer"] for r in records] == [s["Vrvirksomhed"]["cvrNummer"] for s in sources]

    # first call hits the search URL with ?scroll; later calls hit /_search/scroll
    assert captured[0].method == "POST"
    assert "scroll=" in str(captured[0].url)
    assert any(str(r.url).endswith("/_search/scroll") for r in captured)
    # scroll context is released
    assert any(r.method == "DELETE" for r in captured)


def test_search_uses_query_builder(sources) -> None:
    from leadmachine.cvr.query import SearchParameters

    transport, captured = make_scroll_transport(sources, page_size=10)
    http = httpx.Client(transport=transport)
    client = EsCvrClient(url=URL, http_client=http)

    list(client.search(SearchParameters(branchekoder=["960210"], statuses=[])))

    import json

    body = json.loads(captured[0].content)
    assert body["query"] == {"bool": {"filter": [{"terms": {
        "Vrvirksomhed.virksomhedMetadata.nyesteHovedbranche.branchekode": ["960210"]
    }}]}}
    assert body["size"] == client.page_size


def test_empty_result_set_yields_nothing() -> None:
    transport, _ = make_scroll_transport([], page_size=2)
    http = httpx.Client(transport=transport)
    client = EsCvrClient(url=URL, http_client=http)
    assert list(client._scroll({"match_all": {}})) == []
