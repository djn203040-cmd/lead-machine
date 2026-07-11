import Link from "next/link";
import type { Tables } from "@/lib/database.types";
import { createClient } from "@/lib/supabase/server";
import { codesInGroup, groupLabel } from "@/lib/branchekoder";
import { employeesLabel } from "@/lib/leadmeta";
import { EnrichmentBadge, PipelineBadge, ScoreChip, WebsiteNeedBadge } from "./_components/Badge";
import EnrichButton from "./_components/EnrichButton";
import FilterBar, { type LeadFilters } from "./_components/FilterBar";

export const dynamic = "force-dynamic";

const PAGE_SIZE = 25;

type LeadRow = Pick<
  Tables<"leads">,
  | "id"
  | "company_name"
  | "city"
  | "branche_text"
  | "branchekode"
  | "employees_band"
  | "employees_exact"
  | "website_need"
  | "score"
  | "pipeline_status"
  | "enrichment_status"
  | "phone"
>;

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

export default async function LeadsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const view = first(sp.view) === "not_enriched" ? "not_enriched" : "enriched";
  const filters: LeadFilters = {
    q: first(sp.q),
    group: first(sp.group),
    need: first(sp.need),
    status: first(sp.status),
    minScore: first(sp.minScore),
    view,
  };
  const page = Math.max(1, Number.parseInt(first(sp.page), 10) || 1);
  const from = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();
  let query = supabase
    .from("leads")
    .select(
      "id, company_name, city, branche_text, branchekode, employees_band, employees_exact, website_need, score, pipeline_status, enrichment_status, phone",
      { count: "exact" },
    )
    .eq("is_archived", false)
    .eq("suppressed", false); // Robinson-listed / suppressed leads are never shown for outreach

  // Split enriched leads (default, outreach-ready) from everything else. An
  // enriched lead with no phone is disqualified (phone-first outreach) and
  // hidden from the working list — we've already tried CVR → P-enhed → website.
  query =
    view === "enriched"
      ? query.eq("enrichment_status", "enriched").eq("has_phone", true)
      : query.neq("enrichment_status", "enriched");

  if (filters.q) query = query.ilike("company_name", `%${filters.q}%`);
  if (filters.need) query = query.eq("website_need", filters.need);
  if (filters.status) query = query.eq("pipeline_status", filters.status);
  if (filters.group) query = query.in("branchekode", codesInGroup(filters.group));
  const min = Number.parseInt(filters.minScore, 10);
  if (!Number.isNaN(min)) query = query.gte("score", min);

  // Enriched leads rank by score; un-enriched have none, so show newest first.
  query =
    view === "enriched"
      ? query.order("score", { ascending: false, nullsFirst: false })
      : query.order("created_at", { ascending: false });

  const { data, count } = await query.range(from, from + PAGE_SIZE - 1).returns<LeadRow[]>();

  const leads = data ?? [];
  const total = count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // Filter/pagination params, keeping `view` only when it's the non-default tab.
  const baseParams = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (!value || (key === "view" && value === "enriched")) continue;
    baseParams.set(key, value);
  }
  const pageHref = (p: number) => {
    const params = new URLSearchParams(baseParams);
    if (p > 1) params.set("page", String(p));
    const qs = params.toString();
    return qs ? `/leads?${qs}` : "/leads";
  };
  const viewHref = (v: "enriched" | "not_enriched") => {
    const params = new URLSearchParams(baseParams);
    params.delete("page");
    if (v === "not_enriched") params.set("view", v);
    else params.delete("view");
    const qs = params.toString();
    return qs ? `/leads?${qs}` : "/leads";
  };
  const tabClass = (active: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
      active ? "bg-brand-600 text-white shadow-sm" : "text-muted hover:text-ink"
    }`;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Leads</h1>
          <p className="mt-1 text-sm text-muted">
            Danske virksomheder, scoret og klar til outreach.
          </p>
        </div>
        <span className="chip chip-brand text-[0.8rem]">
          {total} virksomheder
        </span>
      </div>

      <div className="mb-5 inline-flex gap-1 rounded-xl border border-line bg-card p-1">
        <Link href={viewHref("enriched")} className={tabClass(view === "enriched")}>
          Beriget
        </Link>
        <Link href={viewHref("not_enriched")} className={tabClass(view === "not_enriched")}>
          Ikke beriget
        </Link>
      </div>

      <FilterBar filters={filters} />

      {leads.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
          <span className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-700">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
              <path d="m20 20-3.2-3.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
          <h2 className="text-lg font-semibold text-ink">Ingen leads endnu</h2>
          <p className="max-w-sm text-sm text-muted">
            Ingen virksomheder matcher filtrene. Kør en søgning for at finde danske
            virksomheder, der mangler en ordentlig hjemmeside.
          </p>
          <Link href="/leads/new" className="btn btn-primary mt-1">
            <span className="text-base leading-none">+</span> Find virksomheder
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-line bg-canvas/60 text-left text-xs uppercase tracking-wide text-faint">
                  <th className="px-4 py-3 font-semibold">Virksomhed</th>
                  <th className="px-4 py-3 font-semibold">Branche</th>
                  <th className="px-4 py-3 font-semibold">By</th>
                  <th className="px-4 py-3 font-semibold">Ansatte</th>
                  <th className="px-4 py-3 font-semibold">Hjemmeside</th>
                  <th className="px-4 py-3 text-right font-semibold">Score</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => (
                  <tr
                    key={l.id}
                    className="relative cursor-pointer border-b border-line/70 transition-colors last:border-0 hover:bg-brand-50/60"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/leads/${l.id}`}
                        className="font-medium text-ink after:absolute after:inset-0 hover:text-brand-700"
                      >
                        {l.company_name}
                      </Link>
                      {l.phone?.[0] ? (
                        <div className="text-xs text-faint">{l.phone[0]}</div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3 text-muted">
                      {l.branche_text ?? groupLabel(l.branchekode) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted">{l.city ?? "—"}</td>
                    <td className="px-4 py-3 text-muted">
                      {employeesLabel(l.employees_band, l.employees_exact)}
                    </td>
                    <td className="px-4 py-3">
                      <WebsiteNeedBadge need={l.website_need} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <ScoreChip score={l.score} />
                    </td>
                    <td className="px-4 py-3">
                      {view === "enriched" ? (
                        <PipelineBadge status={l.pipeline_status} />
                      ) : (
                        <div className="flex items-center gap-2">
                          <EnrichmentBadge status={l.enrichment_status} />
                          <EnrichButton leadId={l.id} status={l.enrichment_status} />
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-5 flex items-center justify-between text-sm">
          <span className="text-muted">
            Side {page} af {totalPages}
          </span>
          <div className="flex gap-2">
            {page > 1 ? (
              <Link href={pageHref(page - 1)} className="btn btn-secondary">
                Forrige
              </Link>
            ) : (
              <span className="btn btn-secondary pointer-events-none opacity-45">Forrige</span>
            )}
            {page < totalPages ? (
              <Link href={pageHref(page + 1)} className="btn btn-secondary">
                Næste
              </Link>
            ) : (
              <span className="btn btn-secondary pointer-events-none opacity-45">Næste</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
