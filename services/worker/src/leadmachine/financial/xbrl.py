"""Parse Danish FSA-taxonomy XBRL annual reports (M3).

Annual reports published on Virk's ``offentliggoerelser`` channel ship as XBRL
instance documents (``application/xml``). We extract a small set of ``fsa:``
facts for the **primary reporting period** only — ignoring the prior-year
comparatives and any dimensional (segment/scenario) breakdowns.

Stdlib ``xml.etree.ElementTree`` is used deliberately: no native build
dependency (lxml), keeping the worker free-first and CI-light.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .models import Financials

XBRLI_NS = "http://www.xbrl.org/2003/instance"

# fsa local-name -> Financials field. fsa namespace URIs vary by taxonomy year
# (e.g. http://xbrl.dcca.dk/fsa) so we match on the "/fsa" namespace suffix.
_FSA_FACTS: dict[str, str] = {
    "GrossProfitLoss": "gross_profit",
    "ProfitLoss": "profit_loss",
    "Equity": "equity",
    "Assets": "assets",
    "Revenue": "revenue",
    "EmployeeBenefitsExpense": "employee_expense",
    "AverageNumberOfEmployees": "avg_employees",
}


@dataclass(slots=True)
class _Context:
    end: str | None  # endDate (duration) or instant
    has_dimensions: bool


def _split(tag: str) -> tuple[str, str]:
    if tag.startswith("{"):
        uri, local = tag[1:].split("}", 1)
        return uri, local
    return "", tag


def _is_fsa(uri: str) -> bool:
    return uri.endswith("/fsa") or uri.endswith("/fsa/")


def _num(el: ET.Element) -> float | None:
    text = (el.text or "").strip().replace(",", "")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if el.get("sign") == "-":
        value = -value
    return value


def _parse_contexts(root: ET.Element) -> dict[str, _Context]:
    contexts: dict[str, _Context] = {}
    for el in root.iter():
        uri, local = _split(el.tag)
        if uri != XBRLI_NS or local != "context":
            continue
        cid = el.get("id")
        if not cid:
            continue
        end: str | None = None
        has_dims = False
        for child in el.iter():
            curi, clocal = _split(child.tag)
            if curi == XBRLI_NS and clocal == "endDate":
                end = (child.text or "").strip() or end
            elif curi == XBRLI_NS and clocal == "instant":
                end = (child.text or "").strip() or end
            elif clocal in ("explicitMember", "typedMember"):
                has_dims = True
        contexts[cid] = _Context(end=end, has_dimensions=has_dims)
    return contexts


def _primary_end(contexts: dict[str, _Context]) -> str | None:
    """The latest period end among non-dimensional contexts."""
    ends = [c.end for c in contexts.values() if c.end and not c.has_dimensions]
    return max(ends) if ends else None


def parse_xbrl(data: bytes | str) -> Financials:
    """Extract primary-period financials from an XBRL instance document."""
    root = ET.fromstring(data)
    contexts = _parse_contexts(root)
    primary_end = _primary_end(contexts)
    if primary_end is None:
        return Financials()

    out: dict[str, float] = {}
    for el in root.iter():
        uri, local = _split(el.tag)
        if not _is_fsa(uri):
            continue
        field = _FSA_FACTS.get(local)
        if field is None or field in out:
            continue
        ctx = contexts.get(el.get("contextRef", ""))
        if ctx is None or ctx.has_dimensions or ctx.end != primary_end:
            continue
        value = _num(el)
        if value is not None:
            out[field] = value

    return Financials(**out)
