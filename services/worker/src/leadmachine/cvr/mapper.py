"""Map raw CVR ``Vrvirksomhed`` records to normalized leads.

Supports the discovery job (issue #17): turns a deeply-nested CVR company
document into a flat row for the ``leads`` table and computes whether the
company must be suppressed from the pipeline (marketing-protected, or not
active / bankrupt / dissolved).

Everything here is defensive: CVR documents have many optional, deeply-nested
fields and any of them can be missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .query import ACTIVE_STATUSES

# Company-form codes for personally owned businesses (natural persons).
# Enkeltmandsvirksomhed = 10, Personligt ejet mindre virksomhed (PMV) = 81.
# These need Robinson-list screening and are treated as personal data.
SOLE_TRADER_FORM_CODES: frozenset[int] = frozenset({10, 81})

# Reasons a company is kept out of the pipeline.
SUPPRESS_REKLAME = "reklamebeskyttet"
SUPPRESS_INACTIVE = "inactive"


@dataclass(slots=True)
class MappedLead:
    """A normalized lead, ready to upsert into ``leads``."""

    cvr_number: str
    company_name: str
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    kommune: str | None = None
    phone: list[str] = field(default_factory=list)
    email: str | None = None
    website: str | None = None
    branchekode: str | None = None
    branche_text: str | None = None
    company_form: str | None = None
    cvr_status: str | None = None
    employees_band: str | None = None
    employees_exact: int | None = None
    founded_at: str | None = None  # ISO date, "YYYY-MM-DD"
    reklamebeskyttet: bool = False
    is_sole_trader: bool = False

    @property
    def is_active(self) -> bool:
        return (self.cvr_status or "").strip().upper() in ACTIVE_STATUSES

    @property
    def suppression_reason(self) -> str | None:
        """Why this lead must not enter the pipeline, or ``None`` if it may."""
        if self.reklamebeskyttet:
            return SUPPRESS_REKLAME
        if not self.is_active:
            return SUPPRESS_INACTIVE
        return None

    def to_lead_row(self) -> dict[str, Any]:
        """Column dict for an upsert into ``leads`` (omits server defaults)."""
        return {
            "cvr_number": self.cvr_number,
            "company_name": self.company_name,
            "address": self.address,
            "postal_code": self.postal_code,
            "city": self.city,
            "kommune": self.kommune,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "branchekode": self.branchekode,
            "branche_text": self.branche_text,
            "company_form": self.company_form,
            "cvr_status": self.cvr_status,
            "employees_band": self.employees_band,
            "employees_exact": self.employees_exact,
            "founded_at": self.founded_at,
            "reklamebeskyttet": self.reklamebeskyttet,
            "is_sole_trader": self.is_sole_trader,
        }


def _unwrap(record: dict[str, Any]) -> dict[str, Any]:
    """Accept either a full ``_source`` ({"Vrvirksomhed": {...}}) or the
    ``Vrvirksomhed`` object directly."""
    if "Vrvirksomhed" in record and isinstance(record["Vrvirksomhed"], dict):
        return record["Vrvirksomhed"]
    return record


def _is_current(item: dict[str, Any]) -> bool:
    """A CVR period entry is current when ``periode.gyldigTil`` is null."""
    periode = item.get("periode") or {}
    return periode.get("gyldigTil") is None


def _pick_current(items: list[dict[str, Any]] | None, key: str = "kontaktoplysning") -> str | None:
    """Pick the current, non-secret value from a CVR period-stamped list.

    Prefers an entry whose period is still open; otherwise falls back to the
    last entry. Skips entries flagged ``hemmelig`` (secret/unlisted)."""
    if not items:
        return None
    visible = [i for i in items if not i.get("hemmelig")]
    if not visible:
        return None
    current = [i for i in visible if _is_current(i)]
    chosen = current[-1] if current else visible[-1]
    value = chosen.get(key)
    return str(value) if value not in (None, "") else None


def _pick_current_all(items: list[dict[str, Any]] | None, key: str = "kontaktoplysning") -> list[str]:
    """All current, non-secret values from a period-stamped list (e.g. phones)."""
    if not items:
        return []
    out: list[str] = []
    for i in items:
        if i.get("hemmelig") or not _is_current(i):
            continue
        value = i.get(key)
        if value not in (None, "") and str(value) not in out:
            out.append(str(value))
    return out


def _latest_employment(meta: dict[str, Any]) -> dict[str, Any]:
    """Most current employment figure: monthly, then quarterly, then yearly."""
    for key in (
        "nyesteMaanedsbeskaeftigelse",
        "nyesteKvartalsbeskaeftigelse",
        "nyesteAarsbeskaeftigelse",
    ):
        emp = meta.get(key)
        if emp:
            return emp
    return {}


def _format_address(addr: dict[str, Any]) -> str | None:
    """Compose a one-line address from a CVR beliggenhedsadresse."""
    if not addr:
        return None
    street = addr.get("vejnavn")
    if not street:
        return None
    house = ""
    if addr.get("husnummerFra") is not None:
        house = str(addr["husnummerFra"])
        if addr.get("husnummerTil") and addr["husnummerTil"] != addr["husnummerFra"]:
            house += f"-{addr['husnummerTil']}"
        if addr.get("bogstavFra"):
            house += str(addr["bogstavFra"])
    line = f"{street} {house}".strip()
    extras = [str(addr[k]) for k in ("etage", "sidedoer") if addr.get(k)]
    if extras:
        line += ", " + " ".join(extras)
    return line


def _status(meta: dict[str, Any], v: dict[str, Any]) -> str | None:
    """Composite status, falling back to the latest virksomhedsstatus entry."""
    status = meta.get("sammensatStatus")
    if status:
        return str(status)
    history = v.get("virksomhedsstatus") or []
    if history:
        return history[-1].get("status")
    return None


def map_company(record: dict[str, Any]) -> MappedLead:
    """Map a raw CVR company record to a :class:`MappedLead`."""
    v = _unwrap(record)
    meta = v.get("virksomhedMetadata") or {}

    cvr_number = str(v.get("cvrNummer") or "").strip()
    if not cvr_number:
        raise ValueError("CVR record has no cvrNummer")

    name = (meta.get("nyesteNavn") or {}).get("navn")
    if not name:
        navne = v.get("navne") or []
        name = navne[-1].get("navn") if navne else None

    hovedbranche = meta.get("nyesteHovedbranche") or {}
    addr = meta.get("nyesteBeliggenhedsadresse") or {}
    form = meta.get("nyesteVirksomhedsform") or {}
    form_code = form.get("virksomhedsformkode")
    emp = _latest_employment(meta)

    postnummer = addr.get("postnummer")

    return MappedLead(
        cvr_number=cvr_number,
        company_name=name or f"CVR {cvr_number}",
        address=_format_address(addr),
        postal_code=str(postnummer) if postnummer not in (None, "") else None,
        city=addr.get("postdistrikt"),
        kommune=(addr.get("kommune") or {}).get("kommuneNavn"),
        phone=_pick_current_all(v.get("telefonNummer")),
        email=_pick_current(v.get("elektroniskPost")),
        website=_pick_current(v.get("hjemmeside")),
        branchekode=hovedbranche.get("branchekode"),
        branche_text=hovedbranche.get("branchetekst"),
        company_form=form.get("langBeskrivelse") or form.get("kortBeskrivelse"),
        cvr_status=_status(meta, v),
        employees_band=emp.get("intervalKodeAntalAnsatte"),
        employees_exact=emp.get("antalAnsatte"),
        founded_at=meta.get("stiftelsesDato"),
        reklamebeskyttet=bool(v.get("reklamebeskyttet", False)),
        is_sole_trader=form_code in SOLE_TRADER_FORM_CODES,
    )


# Management/ownership organisations we treat as decision-makers.
_MGMT_ORG_TYPES = {"LEDELSESORGAN"}
_MGMT_ORG_NAMES = {
    "DIREKTION",
    "BESTYRELSE",
    "REELLE EJERE",
    "EJERREGISTER",
    "FULDT ANSVARLIG DELTAGERE",
}


def _latest_named(items: list[dict[str, Any]] | None) -> str | None:
    """Current (or latest) ``navn`` from a period-stamped name list."""
    if not items:
        return None
    current = [i for i in items if _is_current(i)]
    chosen = current[-1] if current else items[-1]
    return chosen.get("navn")


def _org_current_function(org: dict[str, Any]) -> tuple[bool, str | None]:
    """Whether a person currently holds this organisation role, and the title."""
    is_current = False
    function: str | None = None
    medlemsdata = org.get("medlemsData") or []
    for md in medlemsdata:
        for attr in md.get("attributter") or []:
            for val in attr.get("vaerdier") or []:
                if _is_current(val):
                    is_current = True
                    if attr.get("type") == "FUNKTION" and not function:
                        function = val.get("vaerdi")
    if not medlemsdata:
        # No membership detail — fall back to the org-name period.
        for name in org.get("organisationsNavn") or []:
            if _is_current(name):
                is_current = True
    return is_current, function


def extract_management(record: dict[str, Any]) -> list[dict[str, str]]:
    """Best-effort current decision-makers (direktion/bestyrelse/owners) from CVR.

    Returns ``[{"name": ..., "role": ...}]``; empty when no current management
    relations are present. Best-effort — CVR ``deltagerRelation`` is sparse and
    varied, so this favours precision (only clearly-current memberships)."""
    v = _unwrap(record)
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for rel in v.get("deltagerRelation") or []:
        name = _latest_named((rel.get("deltager") or {}).get("navne"))
        if not name:
            continue
        for org in rel.get("organisationer") or []:
            org_name = _latest_named(org.get("organisationsNavn"))
            hovedtype = org.get("hovedtype")
            is_mgmt = hovedtype in _MGMT_ORG_TYPES or (
                org_name is not None and org_name.upper() in _MGMT_ORG_NAMES
            )
            if not is_mgmt:
                continue
            is_current, function = _org_current_function(org)
            if not is_current:
                continue
            role = function or org_name or hovedtype or "ledelse"
            key = (name, role)
            if key in seen:
                continue
            seen.add(key)
            out.append({"name": name, "role": role})

    return out
