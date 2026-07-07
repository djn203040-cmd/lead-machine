"""Grade a live site's design/age with a cheap LLM pass (Haiku).

The static signals in :mod:`analyze` already yield a coarse ``website_need``
tier (bad / outdated / modern). This adds a sharper, human-legible quality
grade — **dated / basic / modern / premium** — that maps to the sales question
"does this site look old, simple, modern, or high-end?".

We keep it cheap on purpose: one Haiku call per live site, fed the extracted
signals plus a short text excerpt (no screenshots, no browser). The ``anthropic``
import is deferred so the package and its tests never require the SDK or a key,
and grading is best-effort — the qualifier swallows any error rather than fail.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .models import FetchResult, PageSpeedResult, WebsiteQuality, WebsiteSignals

DEFAULT_GRADER_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 512
_TEXT_EXCERPT_CHARS = 2500

QUALITY_TIERS = ("dated", "basic", "modern", "premium")

QUALITY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "tier": {"type": "string", "enum": list(QUALITY_TIERS)},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "justification_da": {"type": "string"},
    },
    "required": ["tier", "reasons", "justification_da"],
}

SYSTEM_PROMPT = (
    "Du vurderer kvaliteten og alderen på en dansk virksomheds hjemmeside ud fra "
    "tekniske signaler og et tekstuddrag. Klassificér siden i én af fire tiers:\n"
    "- dated: gammel, forældet, hjemmelavet (tabel-layout, ingen mobilvenlighed, "
    "gammelt copyright-år, forældet CMS).\n"
    "- basic: simpel men fungerende (skabelon/builder, lidt indhold, få sider).\n"
    "- modern: tidssvarende, responsivt design, moderne CMS/rammer.\n"
    "- premium: gennemført, high-end, professionelt custom-design.\n"
    "Svar kun via det strukturerede skema. 'reasons' er korte engelske stikord; "
    "'justification_da' er én kort dansk sætning."
)

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _text_excerpt(fetch: FetchResult) -> str:
    html = _SCRIPT_STYLE_RE.sub(" ", fetch.html or "")
    text = _TAG_RE.sub(" ", html)
    return _WS_RE.sub(" ", text).strip()[:_TEXT_EXCERPT_CHARS]


def _build_user_prompt(
    signals: WebsiteSignals, fetch: FetchResult, psi: PageSpeedResult | None, url: str
) -> str:
    payload = {
        "url": url,
        "signals": signals.as_dict(),
        "pagespeed": psi.as_dict() if psi is not None else None,
        "text_excerpt": _text_excerpt(fetch),
    }
    return "Vurdér denne hjemmeside:\n" + json.dumps(payload, ensure_ascii=False)


def _first_text(response: Any) -> str:
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            return block.text
    raise ValueError("Claude response contained no text block")


class ClaudeGrader:
    """Grades a live site's quality tier via one structured Haiku call."""

    def __init__(self, client: Any, model: str = DEFAULT_GRADER_MODEL) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Any) -> "ClaudeGrader":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set (see .env.example)")
        from anthropic import Anthropic  # lazy: keep the SDK off the import/test path

        model = getattr(settings, "website_grader_model", "") or DEFAULT_GRADER_MODEL
        return cls(Anthropic(api_key=settings.anthropic_api_key), model=model)

    def grade(
        self,
        *,
        signals: WebsiteSignals,
        fetch: FetchResult,
        psi: PageSpeedResult | None,
        url: str,
    ) -> WebsiteQuality:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(signals, fetch, psi, url)}],
            output_config={"format": {"type": "json_schema", "schema": QUALITY_SCHEMA}},
        )
        data = json.loads(_first_text(response))
        tier = data.get("tier")
        if tier not in QUALITY_TIERS:
            raise ValueError(f"grader returned invalid tier: {tier!r}")
        return WebsiteQuality(
            tier=tier,
            reasons=list(data.get("reasons") or []),
            justification_da=data.get("justification_da") or "",
            model=self._model,
        )

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "ClaudeGrader":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
