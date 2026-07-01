// Danish geography (regions → kommuner → postnumre/byer) for the discovery
// location picker. Source data: DAWA / dataforsyningen.dk (denmark.geo.json),
// compacted to [kode/nr, navn, …] tuples to keep the client bundle small.
//
// CVR's Elasticsearch index can filter on `postnummer` and `kommuneKode` but NOT
// on city name. So a city selection resolves to its postnumre, and a kommune /
// region selection resolves to kommunekoder — see resolveLocations().

import raw from "@/lib/geo/denmark.geo.json";

type RegionTuple = [kode: number, navn: string];
type KommuneTuple = [kode: number, navn: string, regionskode: number];
type PostnummerTuple = [nr: number, navn: string, kommunekoder: number[]];

const DATA = raw as {
  regions: RegionTuple[];
  kommuner: KommuneTuple[];
  postnumre: PostnummerTuple[];
};

export type LocationKind = "by" | "kommune" | "region";

export type LocationOption = {
  /** Stable id, e.g. "by:8000" / "kommune:101" / "region:1084". */
  id: string;
  kind: LocationKind;
  label: string;
  sublabel: string;
  /** Postal codes this selection contributes to the CVR query. */
  postnumre: number[];
  /** Kommune codes this selection contributes to the CVR query. */
  kommunekoder: number[];
  /** Lowercased haystack for matching (name + codes). */
  haystack: string;
};

const REGION_BY_KODE = new Map(DATA.regions.map((r) => [r[0], r[1]]));
const KOMMUNE_BY_KODE = new Map(DATA.kommuner.map((k) => [k[0], k[1]]));

function fold(s: string): string {
  // Lowercase + treat the Danish vowels as their base letters so "aarhus"
  // matches "Århus" and "noerre" matches "Nørre".
  return s
    .toLowerCase()
    .replace(/å/g, "a")
    .replace(/æ/g, "ae")
    .replace(/ø/g, "oe");
}

// --- Build the searchable option list once (module-level, ~1200 entries) ----

function buildOptions(): LocationOption[] {
  const options: LocationOption[] = [];

  // Regions → all kommunekoder in the region.
  for (const [kode, navn] of DATA.regions) {
    const kommunekoder = DATA.kommuner.filter((k) => k[2] === kode).map((k) => k[0]);
    options.push({
      id: `region:${kode}`,
      kind: "region",
      label: `Region ${navn}`,
      sublabel: `${kommunekoder.length} kommuner`,
      postnumre: [],
      kommunekoder,
      haystack: fold(`region ${navn}`),
    });
  }

  // Kommuner → the kommunekode itself.
  for (const [kode, navn, regionskode] of DATA.kommuner) {
    options.push({
      id: `kommune:${kode}`,
      kind: "kommune",
      label: `${navn} Kommune`,
      sublabel: `Region ${REGION_BY_KODE.get(regionskode) ?? ""}`.trim(),
      postnumre: [],
      kommunekoder: [kode],
      haystack: fold(`${navn} kommune`),
    });
  }

  // Byer (postdistrikter) grouped by name → all postnumre with that name.
  const byName = new Map<string, { nrs: number[]; kommunekoder: Set<number> }>();
  for (const [nr, navn, kommunekoder] of DATA.postnumre) {
    let entry = byName.get(navn);
    if (!entry) {
      entry = { nrs: [], kommunekoder: new Set() };
      byName.set(navn, entry);
    }
    entry.nrs.push(nr);
    kommunekoder.forEach((k) => entry!.kommunekoder.add(k));
  }
  for (const [navn, { nrs, kommunekoder }] of byName) {
    nrs.sort((a, b) => a - b);
    const kk = [...kommunekoder];
    const kommuneNavn = kk.map((k) => KOMMUNE_BY_KODE.get(k)).filter(Boolean).join(", ");
    options.push({
      id: `by:${nrs[0]}`,
      kind: "by",
      label: navn,
      sublabel:
        nrs.length === 1
          ? `${nrs[0]}${kommuneNavn ? ` · ${kommuneNavn}` : ""}`
          : `${nrs[0]}–${nrs[nrs.length - 1]} · ${nrs.length} postnr.`,
      postnumre: nrs,
      kommunekoder: [],
      haystack: fold(`${navn} ${nrs.join(" ")}`),
    });
  }

  return options;
}

export const LOCATION_OPTIONS: LocationOption[] = buildOptions();
const OPTION_BY_ID = new Map(LOCATION_OPTIONS.map((o) => [o.id, o]));

const KIND_RANK: Record<LocationKind, number> = { region: 0, kommune: 1, by: 2 };

/** Rank-and-filter the option list for the autocomplete. */
export function searchLocations(query: string, limit = 12): LocationOption[] {
  const q = fold(query.trim());
  if (!q) return [];
  const scored: { o: LocationOption; score: number }[] = [];
  for (const o of LOCATION_OPTIONS) {
    const idx = o.haystack.indexOf(q);
    if (idx === -1) continue;
    // Prefix matches rank highest; then by selection breadth (region→by).
    const score = (idx === 0 ? 0 : 100) + idx + KIND_RANK[o.kind] * 3;
    scored.push({ o, score });
  }
  scored.sort((a, b) => a.score - b.score || a.o.label.localeCompare(b.o.label, "da"));
  return scored.slice(0, limit).map((s) => s.o);
}

export function locationById(id: string): LocationOption | undefined {
  return OPTION_BY_ID.get(id);
}

/** Merge selected options into a deduped {postnumre, kommunekoder} filter. */
export function resolveLocations(ids: string[]): {
  postnumre: number[];
  kommunekoder: number[];
} {
  const postnumre = new Set<number>();
  const kommunekoder = new Set<number>();
  for (const id of ids) {
    const o = OPTION_BY_ID.get(id);
    if (!o) continue;
    o.postnumre.forEach((n) => postnumre.add(n));
    o.kommunekoder.forEach((k) => kommunekoder.add(k));
  }
  return { postnumre: [...postnumre], kommunekoder: [...kommunekoder] };
}
