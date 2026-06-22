"""Shared HTTP helpers: retrying JSON/bytes requests over httpx.

Retries transport errors and 5xx responses with exponential backoff; never
retries 4xx (auth / bad query). Used by both the CVR and financial clients.
"""

from __future__ import annotations

from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

USER_AGENT = "lead-machine/0.1 (+https://github.com/djn203040-cmd/lead-machine)"
DEFAULT_HEADERS = {"Content-Type": "application/json", "User-Agent": USER_AGENT}


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


_RETRY = dict(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=16),
    retry=retry_if_exception(is_retryable),
)


@retry(**_RETRY)
def request_json(
    client: httpx.Client, method: str, url: str, json_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    resp = client.request(method, url, json=json_body)
    resp.raise_for_status()
    return resp.json()


@retry(**_RETRY)
def request_bytes(client: httpx.Client, method: str, url: str) -> bytes:
    resp = client.request(method, url)
    resp.raise_for_status()
    return resp.content
