import { enrichmentMeta, pipelineMeta, websiteNeedMeta } from "@/lib/leadmeta";

function Badge({ label, className }: { label: string; className: string }) {
  return <span className={`chip ${className}`}>{label}</span>;
}

export function WebsiteNeedBadge({ need }: { need: string | null | undefined }) {
  const meta = websiteNeedMeta(need);
  return <Badge label={meta.label} className={meta.className} />;
}

export function PipelineBadge({ status }: { status: string | null | undefined }) {
  const meta = pipelineMeta(status);
  return <Badge label={meta.label} className={meta.className} />;
}

export function EnrichmentBadge({ status }: { status: string | null | undefined }) {
  const meta = enrichmentMeta(status);
  return <Badge label={meta.label} className={meta.className} />;
}

// 0–100 score pill, tinted by strength. Strong leads get the solid forest tone.
export function ScoreChip({ score }: { score: number | null | undefined }) {
  if (typeof score !== "number") {
    return <span className="text-faint">—</span>;
  }
  const tone =
    score >= 75
      ? "bg-gradient-to-b from-brand-700 to-brand text-white shadow-sm"
      : score >= 50
        ? "bg-brand-100 text-brand-800"
        : score >= 25
          ? "bg-amber-bg text-amber-fg"
          : "bg-[#edece6] text-muted";
  return (
    <span
      className={`inline-flex min-w-9 items-center justify-center rounded-lg px-2 py-1 font-mono text-sm font-semibold tabular-nums ${tone}`}
    >
      {score}
    </span>
  );
}
