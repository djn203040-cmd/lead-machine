import httpx

from leadmachine.website.fetch import HttpxFetcher

URL = "https://eksempel.dk/"


def test_successful_https_fetch() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, html="<html><body>hej</body></html>")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = HttpxFetcher(http_client=http).fetch(URL)

    assert result.status == 200
    assert result.has_https is True
    assert "hej" in result.html
    assert result.failed is False


def test_https_failure_falls_back_to_http() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.scheme == "https":
            raise httpx.ConnectError("tls boom")
        return httpx.Response(200, text="<html>plain</html>")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = HttpxFetcher(http_client=http).fetch(URL)

    assert result.status == 200
    assert result.final_url.startswith("http://")
    assert result.tls_ok is False
    assert result.has_https is False


def test_total_failure_is_marked_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dead")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = HttpxFetcher(http_client=http).fetch(URL)

    assert result.failed is True
    assert result.status == 0
    assert result.has_https is False


def test_error_status_yields_empty_html() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="oops")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    result = HttpxFetcher(http_client=http).fetch(URL)
    assert result.status == 503
    assert result.html == ""
