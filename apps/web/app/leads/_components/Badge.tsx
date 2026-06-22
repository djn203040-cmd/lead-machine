import { pipelineMeta, websiteNeedMeta } from "@/lib/leadmeta";

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${className}`}
    >
      {label}
    </span>
  );
}

export function WebsiteNeedBadge({ need }: { need: string | null | undefined }) {
  const meta = websiteNeedMeta(need);
  return <Badge label={meta.label} className={meta.className} />;
}

export function PipelineBadge({ status }: { status: string | null | undefined }) {
  const meta = pipelineMeta(status);
  return <Badge label={meta.label} className={meta.className} />;
}

// 0–100 score chip, tinted by strength.
export function ScoreChip({ score }: { score: number | null | undefined }) {
  if (typeof score !== "number") {
    return <span className="text-gray-400">—</span>;
  }
  const tone =
    score >= 75
      ? "bg-emerald-600 text-white"
      : score >= 50
        ? "bg-emerald-100 text-emerald-800"
        : score >= 25
          ? "bg-amber-100 text-amber-800"
          : "bg-gray-100 text-gray-600";
  return (
    <span className={`inline-block min-w-9 rounded px-2 py-0.5 text-center text-sm font-semibold ${tone}`}>
      {score}
    </span>
  );
}
