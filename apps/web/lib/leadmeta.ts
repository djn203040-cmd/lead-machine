// UI metadata + formatters for lead fields. Danish labels; Tailwind badge tones.

type BadgeMeta = { label: string; className: string };

// website_need ladder. For a website agency, "no/dead/parked/facebook-only/bad"
// = the best leads, so those get the strong (emerald) tone; modern is muted.
export const WEBSITE_NEED_META: Record<string, BadgeMeta> = {
  none: { label: "Ingen hjemmeside", className: "bg-emerald-100 text-emerald-800" },
  dead: { label: "Dødt domæne", className: "bg-emerald-100 text-emerald-800" },
  parked: { label: "Parkeret domæne", className: "bg-emerald-100 text-emerald-800" },
  facebook_only: { label: "Kun Facebook", className: "bg-emerald-100 text-emerald-800" },
  bad: { label: "Dårlig hjemmeside", className: "bg-amber-100 text-amber-800" },
  outdated: { label: "Forældet", className: "bg-amber-100 text-amber-800" },
  modern: { label: "Moderne", className: "bg-gray-100 text-gray-600" },
  unknown: { label: "Ikke vurderet", className: "bg-gray-100 text-gray-500" },
};

export function websiteNeedMeta(need: string | null | undefined): BadgeMeta {
  return WEBSITE_NEED_META[need ?? "unknown"] ?? WEBSITE_NEED_META.unknown;
}

export const WEBSITE_NEED_OPTIONS = Object.entries(WEBSITE_NEED_META).map(
  ([value, meta]) => ({ value, label: meta.label }),
);

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
  new: { label: "Ny", className: "bg-blue-100 text-blue-800" },
  enriched: { label: "Beriget", className: "bg-indigo-100 text-indigo-800" },
  qualified: { label: "Kvalificeret", className: "bg-violet-100 text-violet-800" },
  contacted: { label: "Kontaktet", className: "bg-cyan-100 text-cyan-800" },
  meeting_booked: { label: "Møde booket", className: "bg-teal-100 text-teal-800" },
  won: { label: "Vundet", className: "bg-emerald-100 text-emerald-800" },
  lost: { label: "Tabt", className: "bg-rose-100 text-rose-700" },
  discarded: { label: "Kasseret", className: "bg-gray-100 text-gray-500" },
};

export function pipelineMeta(status: string | null | undefined): BadgeMeta {
  return PIPELINE_META[(status ?? "new") as PipelineStatus] ?? PIPELINE_META.new;
}

export function isPipelineStatus(value: string): value is PipelineStatus {
  return (PIPELINE_STATUSES as readonly string[]).includes(value);
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
