// CVR Elasticsearch query builder — TypeScript port of
// services/worker/src/leadmachine/cvr/query.py. Keep the two in sync.
//
// Translates a search definition (branchekoder + postnumre + employee bands +
// statuses) into the `query` body for the CVR company index. A single
// `bool.filter` keeps it a non-scoring, cacheable filter context.

import { normalizeCode } from "@/lib/branchekoder";

// Statuses we treat as "active"; everything else is discovery-suppressed.
export const ACTIVE_STATUSES = ["NORMAL", "AKTIV"] as const;

export type SearchParameters = {
  branchekoder?: string[];
  postnumre?: number[];
  postnummerRanges?: [number, number][];
  kommunekoder?: number[];
  employeeBands?: string[];
  statuses?: string[];
};

const META = "Vrvirksomhed.virksomhedMetadata";
const PATH_BRANCHEKODE = `${META}.nyesteHovedbranche.branchekode`;
const PATH_POSTNUMMER = `${META}.nyesteBeliggenhedsadresse.postnummer`;
const PATH_KOMMUNEKODE = `${META}.nyesteBeliggenhedsadresse.kommune.kommuneKode`;
const PATH_STATUS = `${META}.sammensatStatus`;
// Employee band is published over three cadences; match any of them.
const PATHS_EMPLOYEE_BAND = [
  `${META}.nyesteMaanedsbeskaeftigelse.intervalKodeAntalAnsatte`,
  `${META}.nyesteKvartalsbeskaeftigelse.intervalKodeAntalAnsatte`,
  `${META}.nyesteAarsbeskaeftigelse.intervalKodeAntalAnsatte`,
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type EsClause = Record<string, any>;

function geoClause(p: SearchParameters): EsClause | null {
  const should: EsClause[] = [];
  if (p.postnumre?.length) {
    should.push({ terms: { [PATH_POSTNUMMER]: p.postnumre.map(Number) } });
  }
  for (const [lo, hi] of p.postnummerRanges ?? []) {
    should.push({ range: { [PATH_POSTNUMMER]: { gte: Number(lo), lte: Number(hi) } } });
  }
  if (p.kommunekoder?.length) {
    should.push({ terms: { [PATH_KOMMUNEKODE]: p.kommunekoder.map(Number) } });
  }
  if (should.length === 0) return null;
  if (should.length === 1) return should[0];
  return { bool: { should, minimum_should_match: 1 } };
}

function employeeClause(bands?: string[]): EsClause | null {
  if (!bands?.length) return null;
  return {
    bool: {
      should: PATHS_EMPLOYEE_BAND.map((path) => ({ terms: { [path]: bands } })),
      minimum_should_match: 1,
    },
  };
}

export function buildEsQuery(params: SearchParameters): EsClause {
  const filters: EsClause[] = [];

  const branchekoder = (params.branchekoder ?? []).map((c) => normalizeCode(String(c)));
  if (branchekoder.length) filters.push({ terms: { [PATH_BRANCHEKODE]: branchekoder } });

  const geo = geoClause(params);
  if (geo) filters.push(geo);

  const emp = employeeClause(params.employeeBands);
  if (emp) filters.push(emp);

  const statuses = (params.statuses ?? [...ACTIVE_STATUSES]).map((s) => s.trim().toUpperCase());
  if (statuses.length) filters.push({ terms: { [PATH_STATUS]: statuses } });

  if (filters.length === 0) return { match_all: {} };
  return { bool: { filter: filters } };
}
