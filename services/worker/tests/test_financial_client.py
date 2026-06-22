import httpx

from leadmachine.financial.client import FinancialClient, _to_report

SEARCH_URL = "http://distribution.virk.dk/offentliggoerelser/_search"


def test_to_report_extracts_documents() -> None:
    report = _to_report(
        {
            "cvrNummer": 12345678,
            "offentliggoerelsesTidspunkt": "2024-05-15T10:00:00+02:00",
            "regnskab": {"regnskabsperiode": {"startDato": "2023-01-01", "slutDato": "2023-12-31"}},
            "dokumenter": [
                {"dokumentMimeType": "application/xml", "dokumentUrl": "x.xml"},
                {"dokumentMimeType": "application/pdf", "dokumentUrl": "x.pdf"},
            ],
        }
    )
    assert report is not None
    assert report.cvr_number == "12345678"
    assert report.period_end == "2023-12-31"
    assert report.xbrl_url == "x.xml"
    assert report.pdf_url == "x.pdf"


def test_fetch_latest_report_picks_newest_with_xbrl(offentliggoerelser_response) -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=offentliggoerelser_response)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = FinancialClient(url=SEARCH_URL, http_client=http)

    report = client.fetch_latest_report("12345678")

    assert report is not None
    assert report.period_end == "2023-12-31"  # 2023 newer than 2022
    assert report.xbrl_url == "https://regnskaber.virk.dk/rep-2023.xml"

    import json

    body = json.loads(captured[0].content)
    assert body["query"] == {"bool": {"filter": [{"term": {"cvrNummer": 12345678}}]}}


def test_fetch_returns_none_when_no_xbrl() -> None:
    resp = {"hits": {"hits": [{"_source": {
        "cvrNummer": 1,
        "dokumenter": [{"dokumentMimeType": "application/pdf", "dokumentUrl": "only.pdf"}],
    }}]}}
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=resp)))
    client = FinancialClient(url=SEARCH_URL, http_client=http)
    assert client.fetch_latest_report(1) is None


def test_download_xbrl_gets_document_bytes() -> None:
    from leadmachine.financial.models import Report

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://regnskaber.virk.dk/rep-2023.xml"
        return httpx.Response(200, content=b"<xbrl/>")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = FinancialClient(url=SEARCH_URL, http_client=http)
    report = Report("1", "2023-01-01", "2023-12-31", None, "https://regnskaber.virk.dk/rep-2023.xml")
    assert client.download_xbrl(report) == b"<xbrl/>"
