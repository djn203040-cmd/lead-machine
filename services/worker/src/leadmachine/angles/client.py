"""Claude client for sales-angle generation (M6).

Wraps the Anthropic Messages API with a JSON-schema structured-output contract
and returns the parsed payload. The ``anthropic`` import is deferred to
:meth:`from_settings` so the package (and its tests, which use a fake client)
never require the SDK or an API key.
"""

from __future__ import annotations

import json
from typing import Any

# Cheap, high-quality default. Per the claude-api guidance we don't downgrade
# for cost on our own — change only if the operator explicitly wants another model.
ANGLES_MODEL = "claude-opus-4-8"
MAX_TOKENS = 2048

# Structured-output schema (mirrors lead_angles content columns). Structured
# outputs require additionalProperties:false and an explicit `required` list.
ANGLE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary_da": {"type": "string"},
        "weaknesses_da": {"type": "string"},
        "angle_da": {"type": "string"},
        "opening_line_da": {"type": "string"},
        "cta_da": {"type": "string"},
        "objections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "objection_da": {"type": "string"},
                    "response_da": {"type": "string"},
                },
                "required": ["objection_da", "response_da"],
            },
        },
        "competitor_name": {"type": "string"},
        "competitor_angle_type": {"type": "string", "enum": ["fomo", "first_mover", "none"]},
    },
    "required": [
        "summary_da",
        "weaknesses_da",
        "angle_da",
        "opening_line_da",
        "cta_da",
        "objections",
        "competitor_name",
        "competitor_angle_type",
    ],
}


def _first_text(response: Any) -> str:
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            return block.text
    raise ValueError("Claude response contained no text block")


class ClaudeAnglesClient:
    """Generates a structured Danish angle from a (system, user) prompt pair."""

    def __init__(self, client: Any, model: str = ANGLES_MODEL) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls, settings: Any) -> "ClaudeAnglesClient":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY must be set (see .env.example)")
        from anthropic import Anthropic  # lazy: keep the SDK off the import/test path

        return cls(Anthropic(api_key=settings.anthropic_api_key))

    def generate(self, system: str, user: str) -> dict[str, Any]:
        """Call Claude with structured output and return the parsed JSON payload."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": ANGLE_SCHEMA}},
        )
        return json.loads(_first_text(response))

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "ClaudeAnglesClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
