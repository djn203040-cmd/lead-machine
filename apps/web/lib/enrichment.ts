// Typed views over the lead_enrichment jsonb columns (written by the worker:
// cvr / website / financial / social / contact). Read defensively — every
// field is optional. Use `view<T>()` to coerce a Json column to its shape.

export type WebsiteEvidence = {
  resolved?: { kind?: string; url?: string; host?: string };
  signals?: {
    has_viewport?: boolean;
    has_https?: boolean;
    legacy_markup?: boolean;
    legacy_reasons?: string[];
    cms?: string | null;
    copyright_year?: number | null;
    is_one_page?: boolean;
  };
  pagespeed?: {
    performance?: number | null;
    seo?: number | null;
    accessibility?: number | null;
    best_practices?: number | null;
  };
  reasons?: string[];
  note?: string;
  // Present when the site was found by discovery (CVR had none).
  discovery?: {
    source?: string;
    host?: string;
    confidence?: number;
    matched?: string[];
    // Storefront/trading name, when the site was verified via a production unit.
    brand_name?: string;
  };
  // LLM design/age grade of a live site.
  quality?: {
    tier?: string;
    reasons?: string[];
    justification_da?: string;
    model?: string;
  };
};

export type RevenueEstimate = {
  value?: number;
  method?: string;
  confidence?: string;
};

export type FinancialEnrichment = {
  source?: string;
  currency?: string;
  period?: { start?: string; end?: string };
  gross_profit?: number;
  profit_loss?: number;
  equity?: number;
  assets?: number;
  revenue?: number;
  avg_employees?: number;
  revenue_estimate?: RevenueEstimate | null;
};

export type SocialEnrichment = {
  has_fb_page?: boolean;
  fb_url?: string;
  has_meta_pixel?: boolean;
};

export type DecisionMaker = { name?: string; role?: string };
export type ContactEnrichment = {
  source?: string;
  decision_makers?: DecisionMaker[];
};

// jsonb (Json) -> a typed view. The column defaults to {} so the cast is safe.
export function view<T>(json: unknown): T {
  return (json ?? {}) as T;
}

// One cold-call objection + its rebuttal (lead_angles.objections jsonb array).
export type AngleObjection = { objection_da: string; response_da: string };

// Coerce the lead_angles.objections jsonb into a clean, render-safe array.
export function objections(json: unknown): AngleObjection[] {
  if (!Array.isArray(json)) return [];
  return json.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const o = (item as Record<string, unknown>).objection_da;
    const r = (item as Record<string, unknown>).response_da;
    return typeof o === "string" && typeof r === "string" && o && r
      ? [{ objection_da: o, response_da: r }]
      : [];
  });
}

export function isEmpty(json: unknown): boolean {
  return !json || (typeof json === "object" && Object.keys(json as object).length === 0);
}
