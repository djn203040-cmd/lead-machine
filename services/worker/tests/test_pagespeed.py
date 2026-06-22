import httpx

from leadmachine.website.pagespeed import PageSpeedClient, parse_pagespeed

PSI_JSON = {
    "lighthouseResult": {
        "categories": {
            "performance": {"score": 0.45},
            "seo": {"score": 0.9},
            "accessibility": {"score": 0.8},
            "best-practices": {"score": 0.75},
        },
        "audits": {
            "is-on-https": {"score": 1},
            "viewport": {"score": 0},
            "font-size": {"score": 0},
            "tap-targets": {"score": 1},
        },
    }
}


def test_parse_pagespeed_scores_and_failed_audits() -> None:
    res = parse_pagespeed(PSI_JSON)
    assert res.performance == 45
    assert res.seo == 90
    assert res.accessibility == 80
    assert res.best_practices == 75
    assert set(res.failed_audits) == {"viewport", "font-size"}


def test_parse_pagespeed_handles_missing_fields() -> None:
    res = parse_pagespeed({})
    assert res.performance is None
    assert res.failed_audits == []


def test_client_sends_mobile_strategy() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=PSI_JSON)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = PageSpeedClient(api_key="k", http_client=http)
    res = client.analyze("https://eksempel.dk/")

    assert res.performance == 45
    q = str(captured[0].url)
    assert "strategy=mobile" in q
    assert "key=k" in q
    assert "locale=da" in q
