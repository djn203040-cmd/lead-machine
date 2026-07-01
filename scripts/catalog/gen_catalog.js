// Generate the branchekode catalog (TS + Python) from a curated DB25 selection.
// Validates every code against the official DB25 leaf list, then writes both the
// web (TS) and worker (Python) catalogs so they stay in sync.
//
//   node scripts/catalog/gen_catalog.js
//
// db25_leaf_codes.json is the 738 leaf (6-digit) codes of the official Dansk
// Branchekode DB25, extracted from Danmarks Statistik's CSV (see README.md).
const fs = require("fs");
const path = require("path");
const REPO = path.join(__dirname, "..", "..");
const DB25 = new Map(
  require("./db25_leaf_codes.json").map((d) => [d.code, d.titel]),
);

// Groups: key -> Danish label (shown in UI). Order defines UI order.
const GROUPS = [
  ["food_drink", "Mad & drikke"],
  ["beauty_wellness", "Skønhed & velvære"],
  ["health", "Sundhed & klinik"],
  ["trades", "Håndværk & bygge"],
  ["cleaning", "Rengøring & ejendomsservice"],
  ["auto", "Auto & køretøjer"],
  ["transport", "Transport & logistik"],
  ["retail", "Detailhandel"],
  ["professional", "Rådgivning & liberale erhverv"],
  ["finance", "Finans & forsikring"],
  ["realestate", "Ejendom & bolig"],
  ["it_media", "IT, web & medier"],
  ["education", "Undervisning & kurser"],
  ["hospitality", "Hotel, event & turisme"],
  ["leisure", "Sport, fritid & kultur"],
  ["business_services", "Erhvervsservice & bemanding"],
];

// [code, Danish label (friendly, shortened), English hint, group]
const C = [
  // --- Mad & drikke ---
  ["561110", "Restauranter & caféer", "Restaurants & cafés", "food_drink"],
  ["561190", "Øvrige spisesteder", "Other eateries", "food_drink"],
  ["561200", "Food trucks & madboder", "Food trucks & stalls", "food_drink"],
  ["562100", "Event catering", "Event catering", "food_drink"],
  ["562200", "Kontraktcatering & kantiner", "Contract catering", "food_drink"],
  ["563010", "Juice- & kaffebarer", "Juice & coffee bars", "food_drink"],
  ["563020", "Barer & værtshuse", "Bars & pubs", "food_drink"],
  ["107120", "Bagerier", "Bakeries", "food_drink"],
  ["107110", "Industribagerier", "Industrial bakeries", "food_drink"],
  ["108200", "Chokolade & konfekture", "Chocolate & confectionery", "food_drink"],
  ["110500", "Bryggerier", "Breweries", "food_drink"],
  ["110200", "Vinproducenter", "Wine producers", "food_drink"],
  ["110700", "Læskedrik & vand", "Soft drinks & water", "food_drink"],
  // --- Skønhed & velvære ---
  ["962100", "Frisører & barbere", "Hairdressers & barbers", "beauty_wellness"],
  ["962200", "Skønheds- & hudpleje", "Beauty & skin care", "beauty_wellness"],
  ["962300", "Dagspa, sauna & wellness", "Spa & wellness", "beauty_wellness"],
  ["969100", "Personlig service i hjemmet", "Personal home services", "beauty_wellness"],
  ["969900", "Andre personlige serviceydelser", "Other personal services", "beauty_wellness"],
  // --- Sundhed & klinik ---
  ["862100", "Alment praktiserende læger", "GPs", "health"],
  ["862200", "Speciallæger", "Medical specialists", "health"],
  ["862300", "Tandlæger", "Dentists", "health"],
  ["869300", "Psykolog & psykoterapi", "Psychology & therapy", "health"],
  ["869400", "Sundhedspleje & jordemødre", "Nursing & midwives", "health"],
  ["869500", "Fysio- & ergoterapi", "Physio & occupational therapy", "health"],
  ["869600", "Alternativ behandling", "Alternative treatment", "health"],
  ["869100", "Billeddiagnostik & laboratorier", "Imaging & labs", "health"],
  ["869900", "Klinikker & sundhed i øvrigt", "Other health practitioners", "health"],
  ["477300", "Apoteker", "Pharmacies", "health"],
  ["750000", "Dyrlæger", "Veterinarians", "health"],
  // --- Håndværk & bygge ---
  ["431100", "Nedrivning", "Demolition", "trades"],
  ["431200", "Byggepladsarbejde", "Site preparation", "trades"],
  ["432100", "El-installatører", "Electricians", "trades"],
  ["432200", "VVS & blikkenslagere", "Plumbers & HVAC", "trades"],
  ["432300", "Isolering", "Insulation", "trades"],
  ["432400", "Andre bygningsinstallationer", "Other building installation", "trades"],
  ["433100", "Stukkatører", "Plasterers", "trades"],
  ["433200", "Tømrer & snedkere", "Carpenters & joiners", "trades"],
  ["433300", "Gulv & vægbeklædning", "Floor & wall covering", "trades"],
  ["433410", "Malere", "Painters", "trades"],
  ["433420", "Glarmestre", "Glaziers", "trades"],
  ["433500", "Bygningsfærdiggørelse", "Building completion", "trades"],
  ["434100", "Tagdækkere", "Roofers", "trades"],
  ["434200", "Specialiserede bygningsarbejder", "Specialised building work", "trades"],
  ["435000", "Anlægsarbejde", "Civil engineering works", "trades"],
  ["439100", "Murere", "Bricklayers", "trades"],
  ["439900", "Andre byggeaktiviteter", "Other construction", "trades"],
  // --- Rengøring & ejendomsservice ---
  ["811000", "Ejendomsservice (facility)", "Facility management", "cleaning"],
  ["812100", "Rengøring", "General cleaning", "cleaning"],
  ["812210", "Vinduespudsning", "Window cleaning", "cleaning"],
  ["812220", "Skorstensfejere", "Chimney sweeps", "cleaning"],
  ["812290", "Erhvervsrengøring", "Commercial cleaning", "cleaning"],
  ["812300", "Anden rengøring", "Other cleaning", "cleaning"],
  ["813000", "Anlægsgartnere & landskabspleje", "Landscaping & gardening", "cleaning"],
  ["961010", "Erhvervsvaskerier", "Industrial laundries", "cleaning"],
  ["961020", "Renserier & vaskerier", "Dry cleaners & laundromats", "cleaning"],
  // --- Auto & køretøjer ---
  ["953190", "Autoværksteder", "Auto repair", "auto"],
  ["953110", "Dæk & dækservice", "Tyre service", "auto"],
  ["953120", "Autolakering & karrosseri", "Body & paint shops", "auto"],
  ["953200", "MC-værksteder", "Motorcycle repair", "auto"],
  ["478100", "Bilforhandlere", "Car dealers", "auto"],
  ["478200", "Autoreservedele & tilbehør", "Auto parts", "auto"],
  ["478300", "MC-forhandlere", "Motorcycle dealers", "auto"],
  ["473000", "Tankstationer", "Petrol stations", "auto"],
  // --- Transport & logistik ---
  ["494100", "Vognmænd (vejgods)", "Road freight", "transport"],
  ["494200", "Flyttefirmaer", "Movers", "transport"],
  ["493200", "Bus- & turkørsel", "Bus & coach", "transport"],
  ["493300", "Taxi & vognmandskørsel", "Taxi", "transport"],
  ["532000", "Kurér & pakketransport", "Courier & parcel", "transport"],
  ["521000", "Lager & oplagring", "Warehousing", "transport"],
  ["522120", "Parkering & vejhjælp", "Parking & roadside assistance", "transport"],
  // --- Detailhandel ---
  ["471110", "Kiosker", "Kiosks", "retail"],
  ["471120", "Supermarkeder & købmænd", "Supermarkets & grocers", "retail"],
  ["471130", "Discountbutikker", "Discount stores", "retail"],
  ["472100", "Frugt & grønt", "Greengrocers", "retail"],
  ["472200", "Slagtere", "Butchers", "retail"],
  ["472300", "Fiskehandlere", "Fishmongers", "retail"],
  ["472400", "Bager- & kagebutikker", "Bakery shops", "retail"],
  ["472500", "Vinhandlere", "Wine shops", "retail"],
  ["472700", "Specialfødevarer", "Specialty food", "retail"],
  ["474000", "Elektronik & telebutikker", "Electronics & telecom", "retail"],
  ["475210", "Farve- & tapetbutikker", "Paint & wallpaper", "retail"],
  ["475220", "Byggemarkeder & værktøj", "Hardware & DIY", "retail"],
  ["475400", "Hvidevarer", "Home appliances", "retail"],
  ["475510", "Møbelbutikker", "Furniture stores", "retail"],
  ["475530", "Isenkram & køkkenudstyr", "Kitchenware & hardware", "retail"],
  ["475590", "Bolig & belysning", "Home & lighting", "retail"],
  ["476100", "Boghandlere", "Bookshops", "retail"],
  ["476310", "Sportsudstyr", "Sporting goods", "retail"],
  ["476320", "Cykelhandlere", "Bicycle shops", "retail"],
  ["476400", "Legetøj & spil", "Toys & games", "retail"],
  ["476910", "Musikinstrumenter", "Musical instruments", "retail"],
  ["477110", "Tøjbutikker", "Clothing stores", "retail"],
  ["477120", "Børnetøj", "Children's clothing", "retail"],
  ["477210", "Skobutikker", "Shoe shops", "retail"],
  ["477220", "Lædervarer & tasker", "Leather goods & bags", "retail"],
  ["477410", "Optikere", "Opticians", "retail"],
  ["477500", "Kosmetik & parfumeri", "Cosmetics & perfume", "retail"],
  ["477610", "Blomster & planter", "Florists & plants", "retail"],
  ["477620", "Dyrehandlere", "Pet shops", "retail"],
  ["477700", "Ure & smykker", "Watches & jewellery", "retail"],
  ["477900", "Genbrug & brugte varer", "Second-hand goods", "retail"],
  // --- Rådgivning & liberale erhverv ---
  ["691000", "Advokater", "Law firms", "professional"],
  ["692000", "Revisorer & bogføring", "Accountants & bookkeeping", "professional"],
  ["702000", "Virksomhedsrådgivning", "Management consulting", "professional"],
  ["711100", "Arkitekter", "Architects", "professional"],
  ["711210", "Rådgivende ingeniører", "Consulting engineers", "professional"],
  ["711290", "Teknisk rådgivning", "Technical consulting", "professional"],
  ["712020", "Teknisk afprøvning & kontrol", "Technical testing", "professional"],
  ["741100", "Industri- & modedesign", "Industrial & fashion design", "professional"],
  ["741200", "Grafisk design", "Graphic design", "professional"],
  ["741300", "Indretningsarkitekter", "Interior design", "professional"],
  ["742000", "Fotografer", "Photographers", "professional"],
  ["731110", "Reklamebureauer", "Advertising agencies", "professional"],
  ["733000", "PR & kommunikation", "PR & communications", "professional"],
  ["732000", "Markedsanalyse", "Market research", "professional"],
  ["743000", "Oversættelse & tolkning", "Translation & interpreting", "professional"],
  ["749990", "Andre liberale erhverv", "Other professional services", "professional"],
  // --- Finans & forsikring ---
  ["641900", "Pengeinstitutter", "Banks", "finance"],
  ["649100", "Finansiel leasing", "Financial leasing", "finance"],
  ["649210", "Realkredit", "Mortgage credit", "finance"],
  ["662200", "Forsikringsmæglere & -agenter", "Insurance brokers", "finance"],
  ["663000", "Formueforvaltning", "Asset management", "finance"],
  ["661200", "Værdipapirmægling", "Securities broking", "finance"],
  ["661900", "Finansiel service i øvrigt", "Other financial services", "finance"],
  // --- Ejendom & bolig ---
  ["681100", "Ejendomshandel (køb/salg)", "Real estate trading", "realestate"],
  ["681200", "Projektudvikling (bolig)", "Property development", "realestate"],
  ["682030", "Boligudlejning", "Residential letting", "realestate"],
  ["682040", "Erhvervsudlejning", "Commercial letting", "realestate"],
  ["683110", "Ejendomsmæglere", "Estate agents", "realestate"],
  ["683120", "Boliganvisning", "Housing agencies", "realestate"],
  ["683210", "Ejendomsadministration", "Property management", "realestate"],
  ["683220", "Ejerforeninger", "Owners' associations", "realestate"],
  // --- IT, web & medier ---
  ["621000", "Softwareudvikling", "Software development", "it_media"],
  ["622000", "IT-konsulenter", "IT consultants", "it_media"],
  ["629000", "Andre IT-services", "Other IT services", "it_media"],
  ["631000", "Hosting & datacentre", "Hosting & data centres", "it_media"],
  ["639100", "Webportaler", "Web portals", "it_media"],
  ["582900", "Softwareudgivelse", "Software publishing", "it_media"],
  ["582100", "Spiludvikling", "Game publishing", "it_media"],
  ["591100", "Film- & videoproduktion", "Film & video production", "it_media"],
  ["592000", "Musik & lydproduktion", "Music & audio production", "it_media"],
  ["581900", "Forlag & udgivelse", "Publishing", "it_media"],
  // --- Undervisning & kurser ---
  ["855100", "Sport & fritidsundervisning", "Sports & leisure teaching", "education"],
  ["855200", "Musik- & danseskoler", "Music & dance schools", "education"],
  ["855300", "Køreskoler", "Driving schools", "education"],
  ["855900", "Kurser & anden undervisning", "Courses & other education", "education"],
  ["851000", "Førskole & privat pasning", "Preschool & childcare", "education"],
  // --- Hotel, event & turisme ---
  ["551000", "Hoteller", "Hotels", "hospitality"],
  ["552000", "Ferieboliger & B&B", "Holiday homes & B&B", "hospitality"],
  ["553000", "Campingpladser", "Campsites", "hospitality"],
  ["791100", "Rejsebureauer", "Travel agencies", "hospitality"],
  ["791200", "Rejsearrangører", "Tour operators", "hospitality"],
  ["823000", "Messer & konferencer", "Trade fairs & conferences", "hospitality"],
  // --- Sport, fritid & kultur ---
  ["931100", "Sportsanlæg", "Sports facilities", "leisure"],
  ["931200", "Sportsklubber", "Sports clubs", "leisure"],
  ["931300", "Fitnesscentre", "Gyms & fitness", "leisure"],
  ["931900", "Andre sportsaktiviteter", "Other sports activities", "leisure"],
  ["932100", "Forlystelsesparker", "Amusement parks", "leisure"],
  ["932910", "Lystbådehavne", "Marinas", "leisure"],
  ["932990", "Forlystelser & fritid", "Recreation & leisure", "leisure"],
  ["591400", "Biografer", "Cinemas", "leisure"],
  ["903910", "Eventteknik & scene", "Event & stage services", "leisure"],
  // --- Erhvervsservice & bemanding ---
  ["782000", "Vikarbureauer", "Temp agencies", "business_services"],
  ["781000", "Rekruttering & jobformidling", "Recruitment", "business_services"],
  ["800100", "Vagt & sikkerhed", "Guard & security", "business_services"],
  ["800900", "Sikkerhedstjenester", "Security services", "business_services"],
  ["822000", "Callcentre", "Call centres", "business_services"],
  ["821000", "Kontor- & administrationsservice", "Office & admin services", "business_services"],
  ["829100", "Inkasso & kreditoplysning", "Debt collection & credit", "business_services"],
  ["829900", "Anden erhvervsservice", "Other business services", "business_services"],
];

// --- Validate ---------------------------------------------------------------
const groupKeys = new Set(GROUPS.map((g) => g[0]));
const errors = [];
const seen = new Set();
for (const [code, , , group] of C) {
  if (!DB25.has(code)) errors.push(`code ${code} not in DB25`);
  if (!groupKeys.has(group)) errors.push(`code ${code} bad group ${group}`);
  if (seen.has(code)) errors.push(`duplicate code ${code}`);
  seen.add(code);
}
if (errors.length) {
  console.error("VALIDATION FAILED:\n" + errors.join("\n"));
  process.exit(1);
}
console.log(`Validated ${C.length} codes across ${GROUPS.length} groups. All exist in DB25.`);
const counts = {};
for (const [, , , g] of C) counts[g] = (counts[g] || 0) + 1;
console.log("per group:", JSON.stringify(counts));

// --- Emit TypeScript --------------------------------------------------------
const esc = (s) => s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
let ts = `// Branchekode catalog for the leads discovery filter.
//
// Generated from the official Dansk Branchekode DB25 classification
// (Danmarks Statistik, effective 2025-01-01 — the scheme the live CVR register
// now uses). Each entry is a 6-digit DB25 code in the CVR form (no dots), a
// friendly Danish label, and a category group. Mirrors
// services/worker/src/leadmachine/cvr/branchekoder.py — keep the two in sync
// (both are generated from scripts/catalog/gen_catalog.js).

export type BranchekodeGroup =
${GROUPS.map((g) => `  | "${g[0]}"`).join("\n")};

export const GROUPS: Record<BranchekodeGroup, string> = {
${GROUPS.map((g) => `  ${g[0]}: "${esc(g[1])}",`).join("\n")}
};

export type Branche = { code: string; label: string; group: BranchekodeGroup };

// The catalog — order defines display order within a group.
export const BRANCHER: Branche[] = [
${C.map(([code, da, , group]) => `  { code: "${code}", label: "${esc(da)}", group: "${group}" },`).join("\n")}
];

const BY_CODE: Record<string, Branche> = Object.fromEntries(
  BRANCHER.map((b) => [b.code, b]),
);

export function normalizeCode(code: string): string {
  return code.replace(/[.\\s]/g, "").trim();
}

export function brancheForCode(code: string | null | undefined): Branche | null {
  if (!code) return null;
  return BY_CODE[normalizeCode(code)] ?? null;
}

export function labelForCode(code: string | null | undefined): string | null {
  return brancheForCode(code)?.label ?? null;
}

export function groupForCode(code: string | null | undefined): BranchekodeGroup | null {
  return brancheForCode(code)?.group ?? null;
}

export function groupLabel(code: string | null | undefined): string | null {
  const group = groupForCode(code);
  return group ? GROUPS[group] : null;
}

export function codesInGroup(group: string): string[] {
  return BRANCHER.filter((b) => b.group === group).map((b) => b.code);
}

export const GROUP_OPTIONS: { value: BranchekodeGroup; label: string }[] = (
  Object.keys(GROUPS) as BranchekodeGroup[]
).map((value) => ({ value, label: GROUPS[value] }));

/** All catalogued codes, as a Set, for fast validation. */
export const ALL_CODES: Set<string> = new Set(BRANCHER.map((b) => b.code));
`;
fs.writeFileSync(path.join(REPO, "apps/web/lib/branchekoder.ts"), ts);

// --- Emit Python ------------------------------------------------------------
const pyGroups = GROUPS.map((g) => `    "${g[0]}": "${g[1]}",`).join("\n");
const pyRows = C.map(
  ([code, da, en, group]) => `    Branche("${code}", "${da}", "${en}", "${group}"),`,
).join("\n");
let py = `"""Branchekode catalog (issue #15).

Maps our target local-business verticals to Danish **DB25** branchekoder — the
classification the live CVR register migrated to (Danmarks Statistik, effective
2025-01-01). Codes are the 6-digit CVR form (no dots), e.g. DB25 \`\`96.21.00\`\`
-> \`\`"962100"\`\`. Each entry carries a friendly Danish label, an English hint,
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
${pyGroups}
}


# The catalog. Every code verified to exist in the official DB25 leaf list.
CATALOG: tuple[Branche, ...] = (
${pyRows}
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
`;
fs.writeFileSync(path.join(REPO, "services/worker/src/leadmachine/cvr/branchekoder.py"), py);
console.log("wrote apps/web/lib/branchekoder.ts and services/worker/src/leadmachine/cvr/branchekoder.py");
