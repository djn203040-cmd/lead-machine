"""Branchekode catalog (issue #15).

Maps our target local-business verticals to Danish DB07/NACE *branchekoder*.

Codes are stored in the **6-digit form used by the CVR index** (no dots,
leading zeros preserved as strings) — e.g. DB07 ``96.02.10`` → ``"960210"``.
Each entry carries a Danish UI label and an English hint, grouped by a
high-level category so the dashboard (M5) can render a grouped filter.

This is the initial seed covering the verticals in PLAN.md §5 (local service
businesses that live or die on local search). Extend it as new ICPs appear;
verify any added code against the official DB07 list from Danmarks Statistik.

Regenerated 2026-06-30 against the live CVR register (``distribution.virk.dk``).
Denmark migrated active companies to revised branchekoder, so several of the
original DB07-2007 codes (e.g. ``960210`` frisør, ``561010`` restaurant,
``691010`` advokat) now match *only ceased* companies — their live equivalents
(``962100`` / ``561110`` / ``741100`` …) are used here. Each ``label_da`` is the
current official ``branchetekst``. A handful of niches (pizza/grill ``561020``,
car dealers ``451120``, opticians ``477810``, other food service ``562900``)
keep their canonical code but had few/no ``NORMAL``/``Aktiv`` rows in the
snapshot — discovery may return thin results for those verticals.
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


# The catalog. Codes verified against the live CVR register (active = NORMAL /
# Aktiv count noted) on 2026-06-30. ``label_da`` is the current branchetekst.
CATALOG: tuple[Branche, ...] = (
    # --- Mad & drikke -------------------------------------------------------
    Branche("561110", "Servering af mad i restauranter og caféer", "Restaurants", "food_drink"),
    Branche("561020", "Pizzeriaer, grillbarer, isbarer mv.", "Pizza/grill/takeaway", "food_drink"),
    Branche("563020", "Udskænkning af alkoholiske drikkevarer (barer, værtshuse)", "Bars & pubs", "food_drink"),
    Branche("562100", "Event catering", "Event catering", "food_drink"),
    Branche("562900", "Anden restaurationsvirksomhed", "Other food service", "food_drink"),
    Branche("107120", "Fremstilling af friske bageriprodukter", "Bakeries", "food_drink"),
    # --- Skønhed & velvære --------------------------------------------------
    Branche("962100", "Drift af frisør- og barbersaloner", "Hairdressers", "beauty_wellness"),
    Branche("962200", "Skønhedspleje og anden skønhedsbehandling", "Beauty & skin care", "beauty_wellness"),
    Branche("962300", "Drift af dagspa, saunaer og dampbade", "Spa & physical wellbeing", "beauty_wellness"),
    Branche("969900", "Andre personlige serviceydelser i.a.n.", "Other personal service", "beauty_wellness"),
    # --- Sundhed ------------------------------------------------------------
    Branche("862300", "Praktiserende tandlæger", "Dentists", "health"),
    Branche("862100", "Alment praktiserende læger", "GPs", "health"),
    Branche("862200", "Praktiserende speciallæger", "Medical specialists", "health"),
    Branche("869900", "Sundhedsvæsen i øvrigt (klinikker, fysioterapi mv.)", "Other health practitioners", "health"),
    Branche("750000", "Dyrlæger", "Veterinarians", "health"),
    # --- Håndværk & bygge ---------------------------------------------------
    Branche("432200", "VVS- og blikkenslagerforretninger", "Plumbers", "trades"),
    Branche("432100", "El-installation", "Electricians", "trades"),
    Branche("433200", "Tømrer- og bygningssnedkervirksomhed", "Carpenters/joiners", "trades"),
    Branche("433410", "Malerforretninger", "Painters", "trades"),
    Branche("433420", "Glarmestervirksomhed", "Glaziers", "trades"),
    Branche("439100", "Tagdækningsvirksomhed", "Roofers", "trades"),
    Branche("813000", "Landskabspleje", "Landscaping/gardening", "trades"),
    Branche("812100", "Almindelig rengøring i bygninger", "Cleaning", "trades"),
    # --- Auto ---------------------------------------------------------------
    Branche("953190", "Reparation og vedligeholdelse af motorkøretøjer i.a.n.", "Auto repair", "auto"),
    Branche("451120", "Detailhandel med personbiler, varebiler og minibusser", "Car dealers", "auto"),
    # --- Detailhandel -------------------------------------------------------
    Branche("477810", "Optikere", "Opticians", "retail"),
    Branche("477620", "Planteforhandlere og havecentre", "Florists & garden centres", "retail"),
    Branche("472200", "Slagter- og viktualieforretninger", "Butchers", "retail"),
    Branche("477110", "Tøjforretninger", "Clothing retail", "retail"),
    Branche("477700", "Detailhandel med ure, smykker og guld- og sølvvarer", "Jewellery", "retail"),
    # --- Liberale erhverv ---------------------------------------------------
    Branche("683110", "Ejendomsmæglere mv.", "Real estate agents", "professional"),
    Branche("741100", "Advokatvirksomhed", "Law firms", "professional"),
    Branche("692000", "Bogføring og revision; skatterådgivning", "Bookkeeping/accounting", "professional"),
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
