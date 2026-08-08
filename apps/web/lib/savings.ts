// The number the whole call rests on: what we can realistically save this
// business per year, and the 20% of it we get paid.
//
// The worker computes it (services/worker/.../financial/savings.py) and parks
// it in the score breakdown's "savings" factor detail, so there is exactly one
// source of truth — the UI never re-derives the math, it only reads it.

import { parseBreakdown } from "./score-breakdown";

/** Our cut of what is actually saved. Mirrors FEE_SHARE in the worker. */
export const FEE_SHARE = 0.2;

export type SavingsView = {
  annualLow: number;
  annualHigh: number;
  feeLow: number;
  feeHigh: number;
  /**
   * "accounts" = derived from their own filed bruttofortjeneste/resultat, which
   * the caller may quote back to them. "benchmark" = nothing usable was filed,
   * so it's an outside guess from sector and size.
   */
  basis: "accounts" | "benchmark";
  /** What the rate was applied to: operating cost base, or estimated revenue. */
  pool: number | null;
  /** Share of the pool used, e.g. 0.10. */
  rate: number | null;
  /** 'høj' | 'middel' | 'lav' — inherited from the revenue estimate. */
  confidence: string | null;
  /** Trimmed because they don't earn that much (gross profit) or a ceiling. */
  cappedBy: string | null;
};

function num(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** Read the savings band off a lead_scores.breakdown payload, if it has one. */
export function savingsFromBreakdown(json: unknown): SavingsView | null {
  const breakdown = parseBreakdown(json);
  const detail = breakdown?.factors.savings?.detail;
  if (!detail) return null;

  const annualLow = num(detail.annual_low);
  const annualHigh = num(detail.annual_high);
  if (annualLow === null || annualHigh === null) return null;

  return {
    annualLow,
    annualHigh,
    feeLow: num(detail.fee_low) ?? Math.round(annualLow * FEE_SHARE),
    feeHigh: num(detail.fee_high) ?? Math.round(annualHigh * FEE_SHARE),
    // Breakdowns written before the accounts-first basis have no `basis` key.
    basis: detail.basis === "accounts" ? "accounts" : "benchmark",
    pool: num(detail.pool),
    rate: num(detail.rate),
    confidence: typeof detail.confidence === "string" ? detail.confidence : null,
    cappedBy: typeof detail.capped_by === "string" ? detail.capped_by : null,
  };
}
