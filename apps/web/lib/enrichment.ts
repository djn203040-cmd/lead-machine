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

export function isEmpty(json: unknown): boolean {
  return !json || (typeof json === "object" && Object.keys(json as object).length === 0);
}
