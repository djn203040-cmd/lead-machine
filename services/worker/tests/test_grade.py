"""Tests for the LLM website-quality grader (Haiku)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from leadmachine.website.grade import ClaudeGrader, _text_excerpt
from leadmachine.website.models import FetchResult, WebsiteSignals


class _FakeAnthropic:
    """Stand-in for anthropic.Anthropic — echoes a canned JSON payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[dict[str, Any]] = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        text = json.dumps(self._payload)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _fetch() -> FetchResult:
    return FetchResult(
        final_url="https://minsalon.dk/",
        status=200,
        html="<html><body><h1>Velkommen</h1><p>Book tid online.</p></body></html>",
    )


def test_grade_returns_quality_tier() -> None:
    client = _FakeAnthropic(
        {"tier": "modern", "reasons": ["responsive", "https"], "justification_da": "Tidssvarende."}
    )
    grader = ClaudeGrader(client, model="claude-haiku-4-5")
    q = grader.grade(signals=WebsiteSignals(has_viewport=True), fetch=_fetch(), psi=None, url="https://minsalon.dk/")

    assert q.tier == "modern"
    assert q.reasons == ["responsive", "https"]
    assert q.model == "claude-haiku-4-5"
    # Uses structured output against the model we configured.
    call = client.calls[0]
    assert call["model"] == "claude-haiku-4-5"
    assert call["output_config"]["format"]["type"] == "json_schema"


def test_grade_rejects_invalid_tier() -> None:
    grader = ClaudeGrader(_FakeAnthropic({"tier": "amazing", "reasons": [], "justification_da": ""}))
    with pytest.raises(ValueError):
        grader.grade(signals=WebsiteSignals(), fetch=_fetch(), psi=None, url="https://x.dk/")


def test_text_excerpt_strips_markup_and_scripts() -> None:
    fetch = FetchResult(
        final_url="https://x.dk/",
        status=200,
        html="<html><head><style>a{}</style><script>var x=1</script></head>"
        "<body><h1>Hej</h1> verden</body></html>",
    )
    text = _text_excerpt(fetch)
    assert "Hej" in text and "verden" in text
    assert "var x" not in text and "a{}" not in text
