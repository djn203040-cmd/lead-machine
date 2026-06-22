// Typed view over lead_scores.breakdown (written by the worker's
// scoring.score_lead().as_dict()). Parsed defensively — the column is jsonb.

export type FactorScore = {
  points: number;
  max: number;
  detail?: Record<string, unknown>;
};

export type ScoreBreakdown = {
  version?: number;
  total: number;
  gated: boolean;
  gate_reason?: string;
  factors: Record<string, FactorScore>;
};

// Factor keys (and display order) emitted by the rubric.
export const FACTOR_ORDER = [
  "website_need",
  "budget",
  "presence",
  "industry",
  "recency",
] as const;

export const FACTOR_LABELS_DA: Record<string, string> = {
  website_need: "Hjemmesidebehov",
  budget: "Budget",
  presence: "Online tilstedeværelse",
  industry: "Brancheegnethed",
  recency: "Aktualitet",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseBreakdown(json: unknown): ScoreBreakdown | null {
  if (!isRecord(json)) return null;
  const total = typeof json.total === "number" ? json.total : null;
  if (total === null) return null;

  const factors: Record<string, FactorScore> = {};
  if (isRecord(json.factors)) {
    for (const [key, raw] of Object.entries(json.factors)) {
      if (!isRecord(raw)) continue;
      if (typeof raw.points !== "number" || typeof raw.max !== "number") continue;
      factors[key] = {
        points: raw.points,
        max: raw.max,
        detail: isRecord(raw.detail) ? raw.detail : undefined,
      };
    }
  }

  return {
    version: typeof json.version === "number" ? json.version : undefined,
    total,
    gated: json.gated === true,
    gate_reason: typeof json.gate_reason === "string" ? json.gate_reason : undefined,
    factors,
  };
}

// Stable, readable rendering of a factor's detail payload (e.g.
// {"tier":"local_service","branchekode":"960210"}).
export function formatDetail(detail: Record<string, unknown> | undefined): string {
  if (!detail) return "";
  return Object.entries(detail)
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(" · ");
}
