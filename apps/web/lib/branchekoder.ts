// Branchekode catalog for the leads discovery filter.
//
// Generated from the official Dansk Branchekode DB25 classification
// (Danmarks Statistik, effective 2025-01-01 — the scheme the live CVR register
// now uses). Each entry is a 6-digit DB25 code in the CVR form (no dots), a
// friendly Danish label, and a category group. Mirrors
// services/worker/src/leadmachine/cvr/branchekoder.py — keep the two in sync
// (both are generated from scripts/catalog/gen_catalog.js).

export type BranchekodeGroup =
  | "food_drink"
  | "beauty_wellness"
  | "health"
  | "trades"
  | "cleaning"
  | "auto"
  | "transport"
  | "retail"
  | "professional"
  | "finance"
  | "realestate"
  | "it_media"
  | "education"
  | "hospitality"
  | "leisure"
  | "business_services";

export const GROUPS: Record<BranchekodeGroup, string> = {
  food_drink: "Mad & drikke",
  beauty_wellness: "Skønhed & velvære",
  health: "Sundhed & klinik",
  trades: "Håndværk & bygge",
  cleaning: "Rengøring & ejendomsservice",
  auto: "Auto & køretøjer",
  transport: "Transport & logistik",
  retail: "Detailhandel",
  professional: "Rådgivning & liberale erhverv",
  finance: "Finans & forsikring",
  realestate: "Ejendom & bolig",
  it_media: "IT, web & medier",
  education: "Undervisning & kurser",
  hospitality: "Hotel, event & turisme",
  leisure: "Sport, fritid & kultur",
  business_services: "Erhvervsservice & bemanding",
};

export type Branche = { code: string; label: string; group: BranchekodeGroup };

// The catalog — order defines display order within a group.
export const BRANCHER: Branche[] = [
  { code: "561110", label: "Restauranter & caféer", group: "food_drink" },
  { code: "561190", label: "Øvrige spisesteder", group: "food_drink" },
  { code: "561200", label: "Food trucks & madboder", group: "food_drink" },
  { code: "562100", label: "Event catering", group: "food_drink" },
  { code: "562200", label: "Kontraktcatering & kantiner", group: "food_drink" },
  { code: "563010", label: "Juice- & kaffebarer", group: "food_drink" },
  { code: "563020", label: "Barer & værtshuse", group: "food_drink" },
  { code: "107120", label: "Bagerier", group: "food_drink" },
  { code: "107110", label: "Industribagerier", group: "food_drink" },
  { code: "108200", label: "Chokolade & konfekture", group: "food_drink" },
  { code: "110500", label: "Bryggerier", group: "food_drink" },
  { code: "110200", label: "Vinproducenter", group: "food_drink" },
  { code: "110700", label: "Læskedrik & vand", group: "food_drink" },
  { code: "962100", label: "Frisører & barbere", group: "beauty_wellness" },
  { code: "962200", label: "Skønheds- & hudpleje", group: "beauty_wellness" },
  { code: "962300", label: "Dagspa, sauna & wellness", group: "beauty_wellness" },
  { code: "969100", label: "Personlig service i hjemmet", group: "beauty_wellness" },
  { code: "969900", label: "Andre personlige serviceydelser", group: "beauty_wellness" },
  { code: "862100", label: "Alment praktiserende læger", group: "health" },
  { code: "862200", label: "Speciallæger", group: "health" },
  { code: "862300", label: "Tandlæger", group: "health" },
  { code: "869300", label: "Psykolog & psykoterapi", group: "health" },
  { code: "869400", label: "Sundhedspleje & jordemødre", group: "health" },
  { code: "869500", label: "Fysio- & ergoterapi", group: "health" },
  { code: "869600", label: "Alternativ behandling", group: "health" },
  { code: "869100", label: "Billeddiagnostik & laboratorier", group: "health" },
  { code: "869900", label: "Klinikker & sundhed i øvrigt", group: "health" },
  { code: "477300", label: "Apoteker", group: "health" },
  { code: "750000", label: "Dyrlæger", group: "health" },
  { code: "431100", label: "Nedrivning", group: "trades" },
  { code: "431200", label: "Byggepladsarbejde", group: "trades" },
  { code: "432100", label: "El-installatører", group: "trades" },
  { code: "432200", label: "VVS & blikkenslagere", group: "trades" },
  { code: "432300", label: "Isolering", group: "trades" },
  { code: "432400", label: "Andre bygningsinstallationer", group: "trades" },
  { code: "433100", label: "Stukkatører", group: "trades" },
  { code: "433200", label: "Tømrer & snedkere", group: "trades" },
  { code: "433300", label: "Gulv & vægbeklædning", group: "trades" },
  { code: "433410", label: "Malere", group: "trades" },
  { code: "433420", label: "Glarmestre", group: "trades" },
  { code: "433500", label: "Bygningsfærdiggørelse", group: "trades" },
  { code: "434100", label: "Tagdækkere", group: "trades" },
  { code: "434200", label: "Specialiserede bygningsarbejder", group: "trades" },
  { code: "435000", label: "Anlægsarbejde", group: "trades" },
  { code: "439100", label: "Murere", group: "trades" },
  { code: "439900", label: "Andre byggeaktiviteter", group: "trades" },
  { code: "811000", label: "Ejendomsservice (facility)", group: "cleaning" },
  { code: "812100", label: "Rengøring", group: "cleaning" },
  { code: "812210", label: "Vinduespudsning", group: "cleaning" },
  { code: "812220", label: "Skorstensfejere", group: "cleaning" },
  { code: "812290", label: "Erhvervsrengøring", group: "cleaning" },
  { code: "812300", label: "Anden rengøring", group: "cleaning" },
  { code: "813000", label: "Anlægsgartnere & landskabspleje", group: "cleaning" },
  { code: "961010", label: "Erhvervsvaskerier", group: "cleaning" },
  { code: "961020", label: "Renserier & vaskerier", group: "cleaning" },
  { code: "953190", label: "Autoværksteder", group: "auto" },
  { code: "953110", label: "Dæk & dækservice", group: "auto" },
  { code: "953120", label: "Autolakering & karrosseri", group: "auto" },
  { code: "953200", label: "MC-værksteder", group: "auto" },
  { code: "478100", label: "Bilforhandlere", group: "auto" },
  { code: "478200", label: "Autoreservedele & tilbehør", group: "auto" },
  { code: "478300", label: "MC-forhandlere", group: "auto" },
  { code: "473000", label: "Tankstationer", group: "auto" },
  { code: "494100", label: "Vognmænd (vejgods)", group: "transport" },
  { code: "494200", label: "Flyttefirmaer", group: "transport" },
  { code: "493200", label: "Bus- & turkørsel", group: "transport" },
  { code: "493300", label: "Taxi & vognmandskørsel", group: "transport" },
  { code: "532000", label: "Kurér & pakketransport", group: "transport" },
  { code: "521000", label: "Lager & oplagring", group: "transport" },
  { code: "522120", label: "Parkering & vejhjælp", group: "transport" },
  { code: "471110", label: "Kiosker", group: "retail" },
  { code: "471120", label: "Supermarkeder & købmænd", group: "retail" },
  { code: "471130", label: "Discountbutikker", group: "retail" },
  { code: "472100", label: "Frugt & grønt", group: "retail" },
  { code: "472200", label: "Slagtere", group: "retail" },
  { code: "472300", label: "Fiskehandlere", group: "retail" },
  { code: "472400", label: "Bager- & kagebutikker", group: "retail" },
  { code: "472500", label: "Vinhandlere", group: "retail" },
  { code: "472700", label: "Specialfødevarer", group: "retail" },
  { code: "474000", label: "Elektronik & telebutikker", group: "retail" },
  { code: "475210", label: "Farve- & tapetbutikker", group: "retail" },
  { code: "475220", label: "Byggemarkeder & værktøj", group: "retail" },
  { code: "475400", label: "Hvidevarer", group: "retail" },
  { code: "475510", label: "Møbelbutikker", group: "retail" },
  { code: "475530", label: "Isenkram & køkkenudstyr", group: "retail" },
  { code: "475590", label: "Bolig & belysning", group: "retail" },
  { code: "476100", label: "Boghandlere", group: "retail" },
  { code: "476310", label: "Sportsudstyr", group: "retail" },
  { code: "476320", label: "Cykelhandlere", group: "retail" },
  { code: "476400", label: "Legetøj & spil", group: "retail" },
  { code: "476910", label: "Musikinstrumenter", group: "retail" },
  { code: "477110", label: "Tøjbutikker", group: "retail" },
  { code: "477120", label: "Børnetøj", group: "retail" },
  { code: "477210", label: "Skobutikker", group: "retail" },
  { code: "477220", label: "Lædervarer & tasker", group: "retail" },
  { code: "477410", label: "Optikere", group: "retail" },
  { code: "477500", label: "Kosmetik & parfumeri", group: "retail" },
  { code: "477610", label: "Blomster & planter", group: "retail" },
  { code: "477620", label: "Dyrehandlere", group: "retail" },
  { code: "477700", label: "Ure & smykker", group: "retail" },
  { code: "477900", label: "Genbrug & brugte varer", group: "retail" },
  { code: "691000", label: "Advokater", group: "professional" },
  { code: "692000", label: "Revisorer & bogføring", group: "professional" },
  { code: "702000", label: "Virksomhedsrådgivning", group: "professional" },
  { code: "711100", label: "Arkitekter", group: "professional" },
  { code: "711210", label: "Rådgivende ingeniører", group: "professional" },
  { code: "711290", label: "Teknisk rådgivning", group: "professional" },
  { code: "712020", label: "Teknisk afprøvning & kontrol", group: "professional" },
  { code: "741100", label: "Industri- & modedesign", group: "professional" },
  { code: "741200", label: "Grafisk design", group: "professional" },
  { code: "741300", label: "Indretningsarkitekter", group: "professional" },
  { code: "742000", label: "Fotografer", group: "professional" },
  { code: "731110", label: "Reklamebureauer", group: "professional" },
  { code: "733000", label: "PR & kommunikation", group: "professional" },
  { code: "732000", label: "Markedsanalyse", group: "professional" },
  { code: "743000", label: "Oversættelse & tolkning", group: "professional" },
  { code: "749990", label: "Andre liberale erhverv", group: "professional" },
  { code: "641900", label: "Pengeinstitutter", group: "finance" },
  { code: "649100", label: "Finansiel leasing", group: "finance" },
  { code: "649210", label: "Realkredit", group: "finance" },
  { code: "662200", label: "Forsikringsmæglere & -agenter", group: "finance" },
  { code: "663000", label: "Formueforvaltning", group: "finance" },
  { code: "661200", label: "Værdipapirmægling", group: "finance" },
  { code: "661900", label: "Finansiel service i øvrigt", group: "finance" },
  { code: "681100", label: "Ejendomshandel (køb/salg)", group: "realestate" },
  { code: "681200", label: "Projektudvikling (bolig)", group: "realestate" },
  { code: "682030", label: "Boligudlejning", group: "realestate" },
  { code: "682040", label: "Erhvervsudlejning", group: "realestate" },
  { code: "683110", label: "Ejendomsmæglere", group: "realestate" },
  { code: "683120", label: "Boliganvisning", group: "realestate" },
  { code: "683210", label: "Ejendomsadministration", group: "realestate" },
  { code: "683220", label: "Ejerforeninger", group: "realestate" },
  { code: "621000", label: "Softwareudvikling", group: "it_media" },
  { code: "622000", label: "IT-konsulenter", group: "it_media" },
  { code: "629000", label: "Andre IT-services", group: "it_media" },
  { code: "631000", label: "Hosting & datacentre", group: "it_media" },
  { code: "639100", label: "Webportaler", group: "it_media" },
  { code: "582900", label: "Softwareudgivelse", group: "it_media" },
  { code: "582100", label: "Spiludvikling", group: "it_media" },
  { code: "591100", label: "Film- & videoproduktion", group: "it_media" },
  { code: "592000", label: "Musik & lydproduktion", group: "it_media" },
  { code: "581900", label: "Forlag & udgivelse", group: "it_media" },
  { code: "855100", label: "Sport & fritidsundervisning", group: "education" },
  { code: "855200", label: "Musik- & danseskoler", group: "education" },
  { code: "855300", label: "Køreskoler", group: "education" },
  { code: "855900", label: "Kurser & anden undervisning", group: "education" },
  { code: "851000", label: "Førskole & privat pasning", group: "education" },
  { code: "551000", label: "Hoteller", group: "hospitality" },
  { code: "552000", label: "Ferieboliger & B&B", group: "hospitality" },
  { code: "553000", label: "Campingpladser", group: "hospitality" },
  { code: "791100", label: "Rejsebureauer", group: "hospitality" },
  { code: "791200", label: "Rejsearrangører", group: "hospitality" },
  { code: "823000", label: "Messer & konferencer", group: "hospitality" },
  { code: "931100", label: "Sportsanlæg", group: "leisure" },
  { code: "931200", label: "Sportsklubber", group: "leisure" },
  { code: "931300", label: "Fitnesscentre", group: "leisure" },
  { code: "931900", label: "Andre sportsaktiviteter", group: "leisure" },
  { code: "932100", label: "Forlystelsesparker", group: "leisure" },
  { code: "932910", label: "Lystbådehavne", group: "leisure" },
  { code: "932990", label: "Forlystelser & fritid", group: "leisure" },
  { code: "591400", label: "Biografer", group: "leisure" },
  { code: "903910", label: "Eventteknik & scene", group: "leisure" },
  { code: "782000", label: "Vikarbureauer", group: "business_services" },
  { code: "781000", label: "Rekruttering & jobformidling", group: "business_services" },
  { code: "800100", label: "Vagt & sikkerhed", group: "business_services" },
  { code: "800900", label: "Sikkerhedstjenester", group: "business_services" },
  { code: "822000", label: "Callcentre", group: "business_services" },
  { code: "821000", label: "Kontor- & administrationsservice", group: "business_services" },
  { code: "829100", label: "Inkasso & kreditoplysning", group: "business_services" },
  { code: "829900", label: "Anden erhvervsservice", group: "business_services" },
];

const BY_CODE: Record<string, Branche> = Object.fromEntries(
  BRANCHER.map((b) => [b.code, b]),
);

export function normalizeCode(code: string): string {
  return code.replace(/[.\s]/g, "").trim();
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
