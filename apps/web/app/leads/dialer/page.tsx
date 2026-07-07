import Link from "next/link";
import type { Tables } from "@/lib/database.types";
import { createClient } from "@/lib/supabase/server";
import Dialer, { type DialerLead } from "./_components/Dialer";

export const dynamic = "force-dynamic";

// Cap the ring list — a calling session never gets through hundreds anyway, and
// this keeps the up-front fetch light while enabling instant client navigation.
const QUEUE_LIMIT = 150;

type LeadRow = Pick<
  Tables<"leads">,
  | "id"
  | "company_name"
  | "phone"
  | "website"
  | "email"
  | "address"
  | "postal_code"
  | "city"
  | "kommune"
  | "cvr_number"
  | "branche_text"
  | "branchekode"
  | "employees_band"
  | "employees_exact"
  | "company_form"
  | "founded_at"
  | "is_sole_trader"
  | "website_need"
  | "pipeline_status"
  | "score"
>;

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

export default async function DialerPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  // Default ring list = leads not yet worked (new/enriched/qualified). The "all"
  // scope also re-surfaces contacted leads for a second attempt.
  const scope = first(sp.scope) === "all" ? "all" : "fresh";

  const supabase = await createClient();
  let query = supabase
    .from("leads")
    .select(
      "id, company_name, phone, website, email, address, postal_code, city, kommune, cvr_number, branche_text, branchekode, employees_band, employees_exact, company_form, founded_at, is_sole_trader, website_need, pipeline_status, score",
    )
    .eq("is_archived", false)
    .eq("suppressed", false) // Robinson-listed / suppressed leads are never called
    .eq("enrichment_status", "enriched");

  query =
    scope === "all"
      ? query.not("pipeline_status", "in", "(won,lost,discarded)")
      : query.in("pipeline_status", ["new", "enriched", "qualified"]);

  const { data } = await query
    .order("score", { ascending: false, nullsFirst: false })
    .limit(QUEUE_LIMIT)
    .returns<LeadRow[]>();

  // Only leads we can actually dial belong in a power dialer.
  const rows = (data ?? []).filter((l) => Array.isArray(l.phone) && l.phone.length > 0);
  const ids = rows.map((l) => l.id);

  // Side tables — batch-fetched for the whole queue, then stitched in by lead_id.
  const [anglesRes, enrichRes, scoresRes] = ids.length
    ? await Promise.all([
        supabase
          .from("lead_angles")
          .select(
            "lead_id, opening_line_da, summary_da, angle_da, weaknesses_da, competitor_angle_type, competitor_name",
          )
          .in("lead_id", ids),
        supabase.from("lead_enrichment").select("lead_id, financial, contact").in("lead_id", ids),
        supabase.from("lead_scores").select("lead_id, total").in("lead_id", ids),
      ])
    : [{ data: [] }, { data: [] }, { data: [] }];

  const angleBy = new Map(
    ((anglesRes.data ?? []) as Tables<"lead_angles">[]).map((a) => [a.lead_id, a]),
  );
  const enrichBy = new Map(
    ((enrichRes.data ?? []) as Tables<"lead_enrichment">[]).map((e) => [e.lead_id, e]),
  );
  const scoreBy = new Map(
    ((scoresRes.data ?? []) as Tables<"lead_scores">[]).map((s) => [s.lead_id, s.total]),
  );

  const queue: DialerLead[] = rows.map((l) => {
    const a = angleBy.get(l.id);
    const e = enrichBy.get(l.id);
    return {
      ...l,
      score: scoreBy.get(l.id) ?? l.score,
      angle: a
        ? {
            opening_line_da: a.opening_line_da,
            summary_da: a.summary_da,
            angle_da: a.angle_da,
            weaknesses_da: a.weaknesses_da,
            competitor_angle_type: a.competitor_angle_type,
            competitor_name: a.competitor_name,
          }
        : null,
      financial: e?.financial ?? null,
      contact: e?.contact ?? null,
    };
  });

  const scopeHref = (s: "fresh" | "all") => (s === "all" ? "/leads/dialer?scope=all" : "/leads/dialer");
  const tabClass = (active: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
      active ? "bg-brand-600 text-white shadow-sm" : "text-muted hover:text-ink"
    }`;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Powerdialer</h1>
          <p className="mt-1 text-sm text-muted">
            Ét lead ad gangen — nummer, salgsvinkel og virksomhedsdata klar til opkald.
          </p>
        </div>
        <div className="inline-flex gap-1 rounded-xl border border-line bg-card p-1">
          <Link href={scopeHref("fresh")} className={tabClass(scope === "fresh")}>
            Ikke ringet
          </Link>
          <Link href={scopeHref("all")} className={tabClass(scope === "all")}>
            Alle aktive
          </Link>
        </div>
      </div>

      <Dialer queue={queue} />
    </div>
  );
}
