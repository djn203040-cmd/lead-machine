"""Robinson-list screening.

The Robinson list (*Robinsonlisten*) is Denmark's official opt-out register for
addressed marketing, maintained under the Databeskyttelsesloven and distributed
on subscription (via Bisnode / Dun & Bradstreet). People on it must not receive
marketing approaches. For a sole trader the natural person *is* the business, so
their CVR contact data is personal data — we must screen sole-trader leads
against the list before any outreach. Limited companies (ApS/A/S) are out of
scope: they are legal persons, not natural persons.

The register itself is licensed data we cannot redistribute, so this module is
deliberately *source-agnostic*: it loads entries from a local file provisioned
out-of-band on the worker host (``ROBINSON_LIST_PATH``) and matches on a
normalized ``name + postal_code`` key. Matching is intentionally conservative —
a false positive only costs us one lead, which is the safe direction for a
compliance gate.

File format (one entry per line, JSON or ``name;postal_code`` CSV)::

    {"name": "Jens Hansen", "postal_code": "2200"}
    Jens Hansen;2200
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

# Tokens that are noise for person matching (sole-trader CVR names often carry a
# trade suffix like "v/Jens Hansen" or "Jens Hansen Tømrer").
_STRIP_PREFIXES = ("v/", "v /", "ved ")


def normalize_name(name: str | None) -> str:
    """Fold a person/company name to a stable match token.

    Lowercases, strips a leading ``v/`` (``ved``) trade marker, drops accents
    and punctuation, and collapses whitespace. Danish æ/ø/å are preserved as
    distinct letters (they are not folded to ae/oe/aa) so they still compare
    equal to themselves.
    """
    if not name:
        return ""
    text = name.strip().lower()
    for prefix in _STRIP_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    # Drop combining accents but keep base letters and æ/ø/å.
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )
    cleaned = "".join(ch if (ch.isalnum() or ch.isspace()) else " " for ch in text)
    return " ".join(cleaned.split())


def _normalize_postal(postal_code: str | None) -> str:
    return "".join(ch for ch in (postal_code or "") if ch.isdigit())


def robinson_key(name: str | None, postal_code: str | None) -> str:
    """The lookup key for a (name, postal_code) pair."""
    return f"{normalize_name(name)}|{_normalize_postal(postal_code)}"


class RobinsonList:
    """An in-memory set of suppressed (name, postal_code) keys."""

    def __init__(self, keys: set[str] | None = None) -> None:
        self._keys = keys or set()

    def __len__(self) -> int:
        return len(self._keys)

    @property
    def is_empty(self) -> bool:
        return not self._keys

    def contains(self, name: str | None, postal_code: str | None) -> bool:
        """True if this person+area is on the Robinson list."""
        key = robinson_key(name, postal_code)
        # An entry needs at least a name to be a real match.
        return bool(normalize_name(name)) and key in self._keys

    @classmethod
    def from_entries(cls, entries: list[tuple[str, str]]) -> "RobinsonList":
        """Build from ``(name, postal_code)`` pairs."""
        return cls({robinson_key(name, postal) for name, postal in entries})

    @classmethod
    def load(cls, path: str | Path | None) -> "RobinsonList":
        """Load the list from ``path`` (JSON-lines or ``name;postal`` CSV).

        A missing or unset path yields an **empty** list: screening then runs but
        suppresses nothing. The caller should treat an empty list as "not yet
        provisioned" and avoid live outreach until the real register is in place
        (the ``screen`` CLI warns about this).
        """
        if not path:
            return cls()
        p = Path(path)
        if not p.exists():
            return cls()

        entries: list[tuple[str, str]] = []
        for raw in p.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line[0] in "{[":
                obj = json.loads(line)
                entries.append((obj.get("name", ""), str(obj.get("postal_code", ""))))
            else:
                parts = line.split(";")
                name = parts[0]
                postal = parts[1] if len(parts) > 1 else ""
                entries.append((name, postal))
        return cls.from_entries(entries)
