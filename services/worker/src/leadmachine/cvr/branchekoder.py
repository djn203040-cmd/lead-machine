"""Branchekode catalog (issue #15).

Maps our target local-business verticals to Danish **DB25** branchekoder — the
classification the live CVR register migrated to (Danmarks Statistik, effective
2025-01-01). Codes are the 6-digit CVR form (no dots), e.g. DB25 ``96.21.00``
-> ``"962100"``. Each entry carries a friendly Danish label, an English hint,
and a high-level category group for the dashboard filter.

Generated from the official DB25 CSV via scripts/catalog/gen_catalog.js and validated
against the full leaf-code list — keep in sync with
apps/web/lib/branchekoder.ts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Branche:
    """A single branchekode in our catalog."""

    code: str  # 6-digit CVR form, e.g. "962100"
    label_da: str
    label_en: str
    group: str

    @property
    def code_db07(self) -> str:
        """Dotted form, e.g. "962100" -> "96.21.00"."""
        c = self.code
        return f"{c[0:2]}.{c[2:4]}.{c[4:6]}" if len(c) == 6 else c


# Category groups (keys are stable; labels are Danish for the UI).
GROUPS: dict[str, str] = {
    "food_drink": "Mad & drikke",
    "beauty_wellness": "Skønhed & velvære",
    "health": "Sundhed & klinik",
    "trades": "Håndværk & bygge",
    "cleaning": "Rengøring & ejendomsservice",
    "auto": "Auto & køretøjer",
    "transport": "Transport & logistik",
    "retail": "Detailhandel",
    "professional": "Rådgivning & liberale erhverv",
    "finance": "Finans & forsikring",
    "realestate": "Ejendom & bolig",
    "it_media": "IT, web & medier",
    "education": "Undervisning & kurser",
    "hospitality": "Hotel, event & turisme",
    "leisure": "Sport, fritid & kultur",
    "business_services": "Erhvervsservice & bemanding",
}


# The catalog. Every code verified to exist in the official DB25 leaf list.
CATALOG: tuple[Branche, ...] = (
    Branche("561110", "Restauranter & caféer", "Restaurants & cafés", "food_drink"),
    Branche("561190", "Øvrige spisesteder", "Other eateries", "food_drink"),
    Branche("561200", "Food trucks & madboder", "Food trucks & stalls", "food_drink"),
    Branche("562100", "Event catering", "Event catering", "food_drink"),
    Branche("562200", "Kontraktcatering & kantiner", "Contract catering", "food_drink"),
    Branche("563010", "Juice- & kaffebarer", "Juice & coffee bars", "food_drink"),
    Branche("563020", "Barer & værtshuse", "Bars & pubs", "food_drink"),
    Branche("107120", "Bagerier", "Bakeries", "food_drink"),
    Branche("107110", "Industribagerier", "Industrial bakeries", "food_drink"),
    Branche("108200", "Chokolade & konfekture", "Chocolate & confectionery", "food_drink"),
    Branche("110500", "Bryggerier", "Breweries", "food_drink"),
    Branche("110200", "Vinproducenter", "Wine producers", "food_drink"),
    Branche("110700", "Læskedrik & vand", "Soft drinks & water", "food_drink"),
    Branche("962100", "Frisører & barbere", "Hairdressers & barbers", "beauty_wellness"),
    Branche("962200", "Skønheds- & hudpleje", "Beauty & skin care", "beauty_wellness"),
    Branche("962300", "Dagspa, sauna & wellness", "Spa & wellness", "beauty_wellness"),
    Branche("969100", "Personlig service i hjemmet", "Personal home services", "beauty_wellness"),
    Branche("969900", "Andre personlige serviceydelser", "Other personal services", "beauty_wellness"),
    Branche("862100", "Alment praktiserende læger", "GPs", "health"),
    Branche("862200", "Speciallæger", "Medical specialists", "health"),
    Branche("862300", "Tandlæger", "Dentists", "health"),
    Branche("869300", "Psykolog & psykoterapi", "Psychology & therapy", "health"),
    Branche("869400", "Sundhedspleje & jordemødre", "Nursing & midwives", "health"),
    Branche("869500", "Fysio- & ergoterapi", "Physio & occupational therapy", "health"),
    Branche("869600", "Alternativ behandling", "Alternative treatment", "health"),
    Branche("869100", "Billeddiagnostik & laboratorier", "Imaging & labs", "health"),
    Branche("869900", "Klinikker & sundhed i øvrigt", "Other health practitioners", "health"),
    Branche("477300", "Apoteker", "Pharmacies", "health"),
    Branche("750000", "Dyrlæger", "Veterinarians", "health"),
    Branche("431100", "Nedrivning", "Demolition", "trades"),
    Branche("431200", "Byggepladsarbejde", "Site preparation", "trades"),
    Branche("432100", "El-installatører", "Electricians", "trades"),
    Branche("432200", "VVS & blikkenslagere", "Plumbers & HVAC", "trades"),
    Branche("432300", "Isolering", "Insulation", "trades"),
    Branche("432400", "Andre bygningsinstallationer", "Other building installation", "trades"),
    Branche("433100", "Stukkatører", "Plasterers", "trades"),
    Branche("433200", "Tømrer & snedkere", "Carpenters & joiners", "trades"),
    Branche("433300", "Gulv & vægbeklædning", "Floor & wall covering", "trades"),
    Branche("433410", "Malere", "Painters", "trades"),
    Branche("433420", "Glarmestre", "Glaziers", "trades"),
    Branche("433500", "Bygningsfærdiggørelse", "Building completion", "trades"),
    Branche("434100", "Tagdækkere", "Roofers", "trades"),
    Branche("434200", "Specialiserede bygningsarbejder", "Specialised building work", "trades"),
    Branche("435000", "Anlægsarbejde", "Civil engineering works", "trades"),
    Branche("439100", "Murere", "Bricklayers", "trades"),
    Branche("439900", "Andre byggeaktiviteter", "Other construction", "trades"),
    Branche("811000", "Ejendomsservice (facility)", "Facility management", "cleaning"),
    Branche("812100", "Rengøring", "General cleaning", "cleaning"),
    Branche("812210", "Vinduespudsning", "Window cleaning", "cleaning"),
    Branche("812220", "Skorstensfejere", "Chimney sweeps", "cleaning"),
    Branche("812290", "Erhvervsrengøring", "Commercial cleaning", "cleaning"),
    Branche("812300", "Anden rengøring", "Other cleaning", "cleaning"),
    Branche("813000", "Anlægsgartnere & landskabspleje", "Landscaping & gardening", "cleaning"),
    Branche("961010", "Erhvervsvaskerier", "Industrial laundries", "cleaning"),
    Branche("961020", "Renserier & vaskerier", "Dry cleaners & laundromats", "cleaning"),
    Branche("953190", "Autoværksteder", "Auto repair", "auto"),
    Branche("953110", "Dæk & dækservice", "Tyre service", "auto"),
    Branche("953120", "Autolakering & karrosseri", "Body & paint shops", "auto"),
    Branche("953200", "MC-værksteder", "Motorcycle repair", "auto"),
    Branche("478100", "Bilforhandlere", "Car dealers", "auto"),
    Branche("478200", "Autoreservedele & tilbehør", "Auto parts", "auto"),
    Branche("478300", "MC-forhandlere", "Motorcycle dealers", "auto"),
    Branche("473000", "Tankstationer", "Petrol stations", "auto"),
    Branche("494100", "Vognmænd (vejgods)", "Road freight", "transport"),
    Branche("494200", "Flyttefirmaer", "Movers", "transport"),
    Branche("493200", "Bus- & turkørsel", "Bus & coach", "transport"),
    Branche("493300", "Taxi & vognmandskørsel", "Taxi", "transport"),
    Branche("532000", "Kurér & pakketransport", "Courier & parcel", "transport"),
    Branche("521000", "Lager & oplagring", "Warehousing", "transport"),
    Branche("522120", "Parkering & vejhjælp", "Parking & roadside assistance", "transport"),
    Branche("471110", "Kiosker", "Kiosks", "retail"),
    Branche("471120", "Supermarkeder & købmænd", "Supermarkets & grocers", "retail"),
    Branche("471130", "Discountbutikker", "Discount stores", "retail"),
    Branche("472100", "Frugt & grønt", "Greengrocers", "retail"),
    Branche("472200", "Slagtere", "Butchers", "retail"),
    Branche("472300", "Fiskehandlere", "Fishmongers", "retail"),
    Branche("472400", "Bager- & kagebutikker", "Bakery shops", "retail"),
    Branche("472500", "Vinhandlere", "Wine shops", "retail"),
    Branche("472700", "Specialfødevarer", "Specialty food", "retail"),
    Branche("474000", "Elektronik & telebutikker", "Electronics & telecom", "retail"),
    Branche("475210", "Farve- & tapetbutikker", "Paint & wallpaper", "retail"),
    Branche("475220", "Byggemarkeder & værktøj", "Hardware & DIY", "retail"),
    Branche("475400", "Hvidevarer", "Home appliances", "retail"),
    Branche("475510", "Møbelbutikker", "Furniture stores", "retail"),
    Branche("475530", "Isenkram & køkkenudstyr", "Kitchenware & hardware", "retail"),
    Branche("475590", "Bolig & belysning", "Home & lighting", "retail"),
    Branche("476100", "Boghandlere", "Bookshops", "retail"),
    Branche("476310", "Sportsudstyr", "Sporting goods", "retail"),
    Branche("476320", "Cykelhandlere", "Bicycle shops", "retail"),
    Branche("476400", "Legetøj & spil", "Toys & games", "retail"),
    Branche("476910", "Musikinstrumenter", "Musical instruments", "retail"),
    Branche("477110", "Tøjbutikker", "Clothing stores", "retail"),
    Branche("477120", "Børnetøj", "Children's clothing", "retail"),
    Branche("477210", "Skobutikker", "Shoe shops", "retail"),
    Branche("477220", "Lædervarer & tasker", "Leather goods & bags", "retail"),
    Branche("477410", "Optikere", "Opticians", "retail"),
    Branche("477500", "Kosmetik & parfumeri", "Cosmetics & perfume", "retail"),
    Branche("477610", "Blomster & planter", "Florists & plants", "retail"),
    Branche("477620", "Dyrehandlere", "Pet shops", "retail"),
    Branche("477700", "Ure & smykker", "Watches & jewellery", "retail"),
    Branche("477900", "Genbrug & brugte varer", "Second-hand goods", "retail"),
    Branche("691000", "Advokater", "Law firms", "professional"),
    Branche("692000", "Revisorer & bogføring", "Accountants & bookkeeping", "professional"),
    Branche("702000", "Virksomhedsrådgivning", "Management consulting", "professional"),
    Branche("711100", "Arkitekter", "Architects", "professional"),
    Branche("711210", "Rådgivende ingeniører", "Consulting engineers", "professional"),
    Branche("711290", "Teknisk rådgivning", "Technical consulting", "professional"),
    Branche("712020", "Teknisk afprøvning & kontrol", "Technical testing", "professional"),
    Branche("741100", "Industri- & modedesign", "Industrial & fashion design", "professional"),
    Branche("741200", "Grafisk design", "Graphic design", "professional"),
    Branche("741300", "Indretningsarkitekter", "Interior design", "professional"),
    Branche("742000", "Fotografer", "Photographers", "professional"),
    Branche("731110", "Reklamebureauer", "Advertising agencies", "professional"),
    Branche("733000", "PR & kommunikation", "PR & communications", "professional"),
    Branche("732000", "Markedsanalyse", "Market research", "professional"),
    Branche("743000", "Oversættelse & tolkning", "Translation & interpreting", "professional"),
    Branche("749990", "Andre liberale erhverv", "Other professional services", "professional"),
    Branche("641900", "Pengeinstitutter", "Banks", "finance"),
    Branche("649100", "Finansiel leasing", "Financial leasing", "finance"),
    Branche("649210", "Realkredit", "Mortgage credit", "finance"),
    Branche("662200", "Forsikringsmæglere & -agenter", "Insurance brokers", "finance"),
    Branche("663000", "Formueforvaltning", "Asset management", "finance"),
    Branche("661200", "Værdipapirmægling", "Securities broking", "finance"),
    Branche("661900", "Finansiel service i øvrigt", "Other financial services", "finance"),
    Branche("681100", "Ejendomshandel (køb/salg)", "Real estate trading", "realestate"),
    Branche("681200", "Projektudvikling (bolig)", "Property development", "realestate"),
    Branche("682030", "Boligudlejning", "Residential letting", "realestate"),
    Branche("682040", "Erhvervsudlejning", "Commercial letting", "realestate"),
    Branche("683110", "Ejendomsmæglere", "Estate agents", "realestate"),
    Branche("683120", "Boliganvisning", "Housing agencies", "realestate"),
    Branche("683210", "Ejendomsadministration", "Property management", "realestate"),
    Branche("683220", "Ejerforeninger", "Owners' associations", "realestate"),
    Branche("621000", "Softwareudvikling", "Software development", "it_media"),
    Branche("622000", "IT-konsulenter", "IT consultants", "it_media"),
    Branche("629000", "Andre IT-services", "Other IT services", "it_media"),
    Branche("631000", "Hosting & datacentre", "Hosting & data centres", "it_media"),
    Branche("639100", "Webportaler", "Web portals", "it_media"),
    Branche("582900", "Softwareudgivelse", "Software publishing", "it_media"),
    Branche("582100", "Spiludvikling", "Game publishing", "it_media"),
    Branche("591100", "Film- & videoproduktion", "Film & video production", "it_media"),
    Branche("592000", "Musik & lydproduktion", "Music & audio production", "it_media"),
    Branche("581900", "Forlag & udgivelse", "Publishing", "it_media"),
    Branche("855100", "Sport & fritidsundervisning", "Sports & leisure teaching", "education"),
    Branche("855200", "Musik- & danseskoler", "Music & dance schools", "education"),
    Branche("855300", "Køreskoler", "Driving schools", "education"),
    Branche("855900", "Kurser & anden undervisning", "Courses & other education", "education"),
    Branche("851000", "Førskole & privat pasning", "Preschool & childcare", "education"),
    Branche("551000", "Hoteller", "Hotels", "hospitality"),
    Branche("552000", "Ferieboliger & B&B", "Holiday homes & B&B", "hospitality"),
    Branche("553000", "Campingpladser", "Campsites", "hospitality"),
    Branche("791100", "Rejsebureauer", "Travel agencies", "hospitality"),
    Branche("791200", "Rejsearrangører", "Tour operators", "hospitality"),
    Branche("823000", "Messer & konferencer", "Trade fairs & conferences", "hospitality"),
    Branche("931100", "Sportsanlæg", "Sports facilities", "leisure"),
    Branche("931200", "Sportsklubber", "Sports clubs", "leisure"),
    Branche("931300", "Fitnesscentre", "Gyms & fitness", "leisure"),
    Branche("931900", "Andre sportsaktiviteter", "Other sports activities", "leisure"),
    Branche("932100", "Forlystelsesparker", "Amusement parks", "leisure"),
    Branche("932910", "Lystbådehavne", "Marinas", "leisure"),
    Branche("932990", "Forlystelser & fritid", "Recreation & leisure", "leisure"),
    Branche("591400", "Biografer", "Cinemas", "leisure"),
    Branche("903910", "Eventteknik & scene", "Event & stage services", "leisure"),
    Branche("782000", "Vikarbureauer", "Temp agencies", "business_services"),
    Branche("781000", "Rekruttering & jobformidling", "Recruitment", "business_services"),
    Branche("800100", "Vagt & sikkerhed", "Guard & security", "business_services"),
    Branche("800900", "Sikkerhedstjenester", "Security services", "business_services"),
    Branche("822000", "Callcentre", "Call centres", "business_services"),
    Branche("821000", "Kontor- & administrationsservice", "Office & admin services", "business_services"),
    Branche("829100", "Inkasso & kreditoplysning", "Debt collection & credit", "business_services"),
    Branche("829900", "Anden erhvervsservice", "Other business services", "business_services"),
)


# Lookups -------------------------------------------------------------------
_BY_CODE: dict[str, Branche] = {b.code: b for b in CATALOG}


def all_branches() -> tuple[Branche, ...]:
    """The full catalog."""
    return CATALOG


def by_code(code: str) -> Branche | None:
    """Look up a branche by its 6-digit (or dotted) code."""
    return _BY_CODE.get(normalize_code(code))


def codes_in_group(group: str) -> list[str]:
    """All branchekoder belonging to a category group."""
    return [b.code for b in CATALOG if b.group == group]


def normalize_code(code: str) -> str:
    """Coerce a branchekode to the 6-digit CVR form ("96.21.00" -> "962100")."""
    return code.replace(".", "").replace(" ", "").strip()


def grouped() -> dict[str, list[Branche]]:
    """Catalog grouped by category, for building grouped UI filters."""
    out: dict[str, list[Branche]] = {g: [] for g in GROUPS}
    for b in CATALOG:
        out.setdefault(b.group, []).append(b)
    return out
