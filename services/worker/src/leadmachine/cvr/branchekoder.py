"""Branchekode catalog (issue #15).

Maps our target local-business verticals to Danish DB07/NACE *branchekoder*.

Codes are stored in the **6-digit form used by the CVR index** (no dots,
leading zeros preserved as strings) — e.g. DB07 ``96.02.10`` → ``"960210"``.
Each entry carries a Danish UI label and an English hint, grouped by a
high-level category so the dashboard (M5) can render a grouped filter.

This is the initial seed covering the verticals in PLAN.md §5 (local service
businesses that live or die on local search). Extend it as new ICPs appear;
verify any added code against the official DB07 list from Danmarks Statistik.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Branche:
    """A single branchekode in our catalog."""

    code: str  # 6-digit CVR form, e.g. "960210"
    label_da: str
    label_en: str
    group: str

    @property
    def code_db07(self) -> str:
        """DB07 dotted form, e.g. "960210" -> "96.02.10"."""
        c = self.code
        return f"{c[0:2]}.{c[2:4]}.{c[4:6]}" if len(c) == 6 else c


# Category groups (keys are stable; labels are Danish for the UI).
GROUPS: dict[str, str] = {
    "food_drink": "Mad & drikke",
    "beauty_wellness": "Skønhed & velvære",
    "health": "Sundhed",
    "trades": "Håndværk & bygge",
    "auto": "Auto",
    "retail": "Detailhandel",
    "professional": "Liberale erhverv",
    "leisure": "Sport & fritid",
}


# The catalog. Only codes we are confident map to the DB07 standard are listed.
CATALOG: tuple[Branche, ...] = (
    # --- Mad & drikke -------------------------------------------------------
    Branche("561010", "Restauranter", "Restaurants", "food_drink"),
    Branche("561020", "Pizzeriaer, grillbarer, isbarer mv.", "Pizza/grill/takeaway", "food_drink"),
    Branche("563000", "Cafeer, værtshuse, diskoteker mv.", "Cafés, bars, clubs", "food_drink"),
    Branche("562100", "Event catering", "Event catering", "food_drink"),
    Branche("562900", "Anden restaurationsvirksomhed", "Other food service", "food_drink"),
    Branche("107100", "Fremstilling af friske bagerivarer", "Bakeries", "food_drink"),
    # --- Skønhed & velvære --------------------------------------------------
    Branche("960210", "Frisørsaloner", "Hairdressers", "beauty_wellness"),
    Branche("960220", "Skønheds- og hudpleje", "Beauty & skin care", "beauty_wellness"),
    Branche("960400", "Aktiviteter vedr. fysisk velvære", "Physical wellbeing (spa, massage)", "beauty_wellness"),
    Branche("960900", "Anden personlig service", "Other personal service", "beauty_wellness"),
    # --- Sundhed ------------------------------------------------------------
    Branche("862300", "Praktiserende tandlæger", "Dentists", "health"),
    Branche("862100", "Alment praktiserende læger", "GPs", "health"),
    Branche("862200", "Praktiserende speciallæger", "Medical specialists", "health"),
    Branche("869010", "Fysioterapeutisk behandling", "Physiotherapists", "health"),
    Branche("869090", "Sundhedsvæsen i øvrigt", "Other health practitioners", "health"),
    Branche("750000", "Dyrlæger", "Veterinarians", "health"),
    # --- Håndværk & bygge ---------------------------------------------------
    Branche("432200", "VVS- og blikkenslagerforretninger", "Plumbers", "trades"),
    Branche("432100", "El-installatører", "Electricians", "trades"),
    Branche("433200", "Tømrer- og bygningssnedkervirksomhed", "Carpenters/joiners", "trades"),
    Branche("433410", "Malerforretninger", "Painters", "trades"),
    Branche("433420", "Glarmesterforretninger", "Glaziers", "trades"),
    Branche("439100", "Tagdækningsvirksomhed", "Roofers", "trades"),
    Branche("813000", "Landskabspleje", "Landscaping/gardening", "trades"),
    Branche("812100", "Almindelig rengøring i bygninger", "Cleaning", "trades"),
    # --- Auto ---------------------------------------------------------------
    Branche("452010", "Almindelige autoreparationsværksteder", "Auto repair", "auto"),
    Branche("451110", "Detailhandel med personbiler mv.", "Car dealers", "auto"),
    # --- Detailhandel -------------------------------------------------------
    Branche("477810", "Detailhandel med optiske artikler", "Opticians", "retail"),
    Branche("477620", "Detailhandel med blomster og planter", "Florists", "retail"),
    Branche("472200", "Detailhandel med kød og kødprodukter", "Butchers", "retail"),
    Branche("477100", "Detailhandel med beklædning", "Clothing retail", "retail"),
    Branche("477700", "Detailhandel med ure og smykker", "Jewellery", "retail"),
    # --- Liberale erhverv ---------------------------------------------------
    Branche("683110", "Ejendomsmæglere mv.", "Real estate agents", "professional"),
    Branche("691010", "Advokatvirksomhed", "Law firms", "professional"),
    Branche("692020", "Bogføring og revision; skatterådgivning", "Bookkeeping/accounting", "professional"),
    Branche("742000", "Fotografisk virksomhed", "Photographers", "professional"),
    Branche("855300", "Køreskoler", "Driving schools", "professional"),
    # --- Sport & fritid -----------------------------------------------------
    Branche("931300", "Fitnesscentre", "Gyms / fitness", "leisure"),
    Branche("931200", "Sportsklubber", "Sports clubs", "leisure"),
)


# Lookups -------------------------------------------------------------------
_BY_CODE: dict[str, Branche] = {b.code: b for b in CATALOG}


def all_branches() -> tuple[Branche, ...]:
    """The full catalog."""
    return CATALOG


def by_code(code: str) -> Branche | None:
    """Look up a branche by its 6-digit (or dotted DB07) code."""
    return _BY_CODE.get(normalize_code(code))


def codes_in_group(group: str) -> list[str]:
    """All branchekoder belonging to a category group."""
    return [b.code for b in CATALOG if b.group == group]


def normalize_code(code: str) -> str:
    """Coerce a branchekode to the 6-digit CVR form ("96.02.10" -> "960210")."""
    return code.replace(".", "").replace(" ", "").strip()


def grouped() -> dict[str, list[Branche]]:
    """Catalog grouped by category, for building grouped UI filters."""
    out: dict[str, list[Branche]] = {g: [] for g in GROUPS}
    for b in CATALOG:
        out.setdefault(b.group, []).append(b)
    return out
