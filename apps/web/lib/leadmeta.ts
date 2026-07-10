// UI metadata + formatters for lead fields. Danish labels; Tailwind badge tones.

type BadgeMeta = { label: string; className: string };

// website_need ladder. For a website agency, "no/dead/parked/facebook-only/
// not-independent" = the best leads, so those get the strong (brand) tone;
// bad/outdated are amber, modern is muted.
export const WEBSITE_NEED_META: Record<string, BadgeMeta> = {
  none: { label: "Ingen hjemmeside", className: "chip-brand" },
  dead: { label: "Dødt domæne", className: "chip-brand" },
  parked: { label: "Parkeret domæne", className: "chip-brand" },
  facebook_only: { label: "Kun Facebook", className: "chip-brand" },
  not_independent: { label: "Ej selvstændig side", className: "chip-brand" },
  bad: { label: "Dårlig hjemmeside", className: "chip-amber" },
  outdated: { label: "Forældet", className: "chip-amber" },
  modern: { label: "Moderne", className: "chip-neutral" },
  unknown: { label: "Ikke vurderet", className: "chip-neutral" },
};

export function websiteNeedMeta(need: string | null | undefined): BadgeMeta {
  return WEBSITE_NEED_META[need ?? "unknown"] ?? WEBSITE_NEED_META.unknown;
}

export const WEBSITE_NEED_OPTIONS = Object.entries(WEBSITE_NEED_META).map(
  ([value, meta]) => ({ value, label: meta.label }),
);

// website_quality — the LLM design/age grade of a live site (dated → premium).
export const WEBSITE_QUALITY_META: Record<string, BadgeMeta> = {
  dated: { label: "Forældet", className: "chip-brand" },
  basic: { label: "Simpel", className: "chip-amber" },
  modern: { label: "Moderne", className: "chip-neutral" },
  premium: { label: "High-end", className: "chip-neutral" },
};

export function websiteQualityMeta(
  quality: string | null | undefined,
): BadgeMeta | null {
  return quality ? (WEBSITE_QUALITY_META[quality] ?? null) : null;
}

// website_source — how we found the site (registered vs discovered).
export const WEBSITE_SOURCE_META: Record<string, string> = {
  cvr: "CVR-registreret",
  email_domain: "Fundet via e-mail-domæne",
  name_guess: "Fundet via firmanavn",
  penhed: "Fundet via P-enhed (butiksnavn)",
  search: "Fundet via websøgning",
};

export function websiteSourceLabel(source: string | null | undefined): string {
  return source ? (WEBSITE_SOURCE_META[source] ?? source) : "—";
}

// pipeline_status, in lifecycle order (matches the leads CHECK constraint).
export const PIPELINE_STATUSES = [
  "new",
  "enriched",
  "qualified",
  "contacted",
  "meeting_booked",
  "won",
  "lost",
  "discarded",
] as const;

export type PipelineStatus = (typeof PIPELINE_STATUSES)[number];

export const PIPELINE_META: Record<PipelineStatus, BadgeMeta> = {
  new: { label: "Ny", className: "chip-info" },
  enriched: { label: "Beriget", className: "chip-violet" },
  qualified: { label: "Kvalificeret", className: "chip-violet" },
  contacted: { label: "Kontaktet", className: "chip-cyan" },
  meeting_booked: { label: "Møde booket", className: "chip-teal" },
  won: { label: "Vundet", className: "chip-brand" },
  lost: { label: "Tabt", className: "chip-rose" },
  discarded: { label: "Kasseret", className: "chip-neutral" },
};

export function pipelineMeta(status: string | null | undefined): BadgeMeta {
  return PIPELINE_META[(status ?? "new") as PipelineStatus] ?? PIPELINE_META.new;
}

export function isPipelineStatus(value: string): value is PipelineStatus {
  return (PIPELINE_STATUSES as readonly string[]).includes(value);
}

// enrichment_status (matches the leads CHECK constraint). Drives the
// "Beriget / Ikke beriget" split on the leads list.
export const ENRICHMENT_STATUSES = [
  "pending",
  "queued",
  "enriching",
  "enriched",
  "skipped",
  "failed",
] as const;

export type EnrichmentStatus = (typeof ENRICHMENT_STATUSES)[number];

export const ENRICHMENT_META: Record<EnrichmentStatus, BadgeMeta> = {
  pending: { label: "Afventer", className: "chip-neutral" },
  queued: { label: "I kø", className: "chip-info" },
  enriching: { label: "Beriger…", className: "chip-cyan" },
  enriched: { label: "Beriget", className: "chip-brand" },
  skipped: { label: "Fravalgt", className: "chip-neutral" },
  failed: { label: "Fejlede", className: "chip-rose" },
};

export function enrichmentMeta(status: string | null | undefined): BadgeMeta {
  return ENRICHMENT_META[(status ?? "pending") as EnrichmentStatus] ?? ENRICHMENT_META.pending;
}

// --- formatters ------------------------------------------------------------
const DKK = new Intl.NumberFormat("da-DK", {
  style: "currency",
  currency: "DKK",
  maximumFractionDigits: 0,
});

export function formatDKK(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return DKK.format(value);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("da-DK", { year: "numeric", month: "short", day: "numeric" });
}

export function employeesLabel(
  band: string | null | undefined,
  exact: number | null | undefined,
): string {
  if (typeof exact === "number") return String(exact);
  if (!band) return "—";
  // CVR band tokens look like "ANTAL_2_4" / "ANTAL_1000_999999".
  const m = band.match(/ANTAL_(\d+)_(\d+)/);
  if (!m) return band;
  const [, lo, hi] = m;
  if (hi === "999999") return `${lo}+`;
  return lo === hi ? lo : `${lo}–${hi}`;
}
