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

__all__ = ["best_phone_type", "classify_phone", "extract_phones", "normalize_phone"]

# Danish numbering-plan prefixes (Energistyrelsen). Number ranges are assigned by
# service type, so the first digits reveal who likely answers: a mobile range is
# near-always someone's own handset (for a small business: the owner), geographic
# landline ranges are the shop's main line (staff/reception can pick up), and
# 70/80/90-numbers are corporate switchboard/service lines — never a person.
# Heuristic: Denmark allows porting across service types, but in practice ranges
# hold; a wrong guess here only softens the call angle, it never blocks a call.
_MOBILE_PREFIXES = (
    "2",  # all of 20–29
    "30", "31", "40", "41", "42", "50", "51", "52", "53",
    "60", "61", "71", "81", "91", "92", "93",
)
_SERVICE_PREFIXES = ("70", "80", "90")  # non-geo business, freephone, premium

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


def classify_phone(raw: str | None) -> str | None:
    """``'mobile'`` | ``'landline'`` | ``'service'`` for a Danish number, else ``None``.

    mobile   → likely a personal handset (small business: the owner directly)
    landline → geographic number, likely the shop's main line
    service  → 70/80/90 non-geographic corporate line (switchboard, never a person)
    """
    n = normalize_phone(raw)
    if n is None:
        return None
    if n.startswith(_SERVICE_PREFIXES):
        return "service"
    if n.startswith(_MOBILE_PREFIXES):
        return "mobile"
    return "landline"


def best_phone_type(phones: object) -> str | None:
    """Lead-level rollup: the most *personal* class across the lead's numbers.

    A lead with any mobile number is 'mobile' — that's the number to dial first.
    """
    classes = {classify_phone(str(p)) for p in (phones or ()) if p}
    for cls in ("mobile", "landline", "service"):
        if cls in classes:
            return cls
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
