"""Extract Danish phone numbers from a business's own web page.

A phone number is the single most important qualifier — outreach is phone-first,
so a lead we can't call is disqualified. Roughly half of CVR records carry no
public number, so when a lead has none we scrape one off its own site.

Precision matters more than recall here: attaching a *wrong* number is worse than
attaching none (we'd call a stranger). So we only trust high-signal sources:

    1. ``tel:`` links          — an explicit, machine-readable phone link
    2. ``+45``-prefixed numbers — unambiguously a Danish phone
    3. numbers next to a phone cue (``tlf``/``telefon``/``ring``/☎)

A bare 8-digit run with no phone context is ignored — it's just as likely a CVR
number, price, or postal code. Numbers are normalised to 8 digits and validated
against Danish numbering (8 digits, first digit 2–9).
"""

from __future__ import annotations

import re

__all__ = ["extract_phones", "normalize_phone"]

_TEL_HREF = re.compile(r"tel:([+\d\s\-()]+)", re.I)
_EIGHT = r"(?:\d[\s\-.]*){8}"
_PLUS45 = re.compile(r"\+\s*45[\s\-.]*(" + _EIGHT + r")")
_CUE = re.compile(
    r"(?:tlf|telefon|telefonnr|tel|ring(?:\s+til)?|phone|call|mobil|☎|📞)[\s.:nr/]*"
    r"((?:\+45[\s\-.]*)?" + _EIGHT + r")",
    re.I,
)


def normalize_phone(raw: str | None) -> str | None:
    """Normalise a raw number to a valid Danish 8-digit string, or ``None``."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 12 and digits.startswith("0045"):
        digits = digits[4:]  # strip the 0045 international prefix
    elif len(digits) == 10 and digits.startswith("45"):
        digits = digits[2:]  # strip the +45 country code
    if len(digits) == 8 and digits[0] in "23456789":
        return digits
    return None


def extract_phones(html: str | None, *, exclude: object = ()) -> list[str]:
    """Danish phone numbers found on the page, most-trusted source first.

    ``exclude`` is any iterable of numbers to drop (e.g. the lead's CVR number,
    which is also 8 digits) so we never mistake it for a phone.
    """
    if not html:
        return []
    ex = {re.sub(r"\D", "", str(x)) for x in exclude if x}
    found: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        n = normalize_phone(raw)
        if n and n not in seen and n not in ex:
            seen.add(n)
            found.append(n)

    for m in _TEL_HREF.finditer(html):
        add(m.group(1))
    for rx in (_PLUS45, _CUE):
        for m in rx.finditer(html):
            add(m.group(1))
    return found
