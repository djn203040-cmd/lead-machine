import Link from "next/link";
import type { Tables } from "@/lib/database.types";
import { createClient } from "@/lib/supabase/server";
import { codesInGroup, groupLabel } from "@/lib/branchekoder";
import { employeesLabel } from "@/lib/leadmeta";
import { PipelineBadge, ScoreChip, WebsiteNeedBadge } from "./_components/Badge";
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
  const filters: LeadFilters = {
    q: first(sp.q),
    group: first(sp.group),
    need: first(sp.need),
    status: first(sp.status),
    minScore: first(sp.minScore),
  };
  const page = Math.max(1, Number.parseInt(first(sp.page), 10) || 1);
  const from = (page - 1) * PAGE_SIZE;

  const supabase = await createClient();
  let query = supabase
    .from("leads")
    .select(
      "id, company_name, city, branche_text, branchekode, employees_band, employees_exact, website_need, score, pipeline_status, phone",
      { count: "exact" },
    )
    .eq("is_archived", false)
    .eq("suppressed", false); // Robinson-listed / suppressed leads are never shown for outreach

  if (filters.q) query = query.ilike("company_name", `%${filters.q}%`);
  if (filters.need) query = query.eq("website_need", filters.need);
  if (filters.status) query = query.eq("pipeline_status", filters.status);
  if (filters.group) query = query.in("branchekode", codesInGroup(filters.group));
  const min = Number.parseInt(filters.minScore, 10);
  if (!Number.isNaN(min)) query = query.gte("score", min);

  const { data, count } = await query
    .order("score", { ascending: false, nullsFirst: false })
    .range(from, from + PAGE_SIZE - 1)
    .returns<LeadRow[]>();

  const leads = data ?? [];
  const total = count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const baseParams = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value) baseParams.set(key, value);
  const pageHref = (p: number) => {
    const params = new URLSearchParams(baseParams);
    if (p > 1) params.set("page", String(p));
    const qs = params.toString();
    return qs ? `/leads?${qs}` : "/leads";
  };

  return (
    <div>
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="text-xl font-semibold">Leads</h1>
        <span className="text-sm text-gray-500">{total} virksomheder</span>
      </div>

      <FilterBar filters={filters} />

      {leads.length === 0 ? (
        <div className="rounded border border-dashed p-12 text-center text-gray-500">
          Ingen leads matcher filtrene. Kør en søgning for at finde danske virksomheder.
        </div>
      ) : (
        <div className="overflow-x-auto rounded border bg-white">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-gray-500">
                <th className="px-3 py-2 font-medium">Virksomhed</th>
                <th className="px-3 py-2 font-medium">Branche</th>
                <th className="px-3 py-2 font-medium">By</th>
                <th className="px-3 py-2 font-medium">Ansatte</th>
                <th className="px-3 py-2 font-medium">Hjemmeside</th>
                <th className="px-3 py-2 text-right font-medium">Score</th>
                <th className="px-3 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => (
                <tr key={l.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <Link
                      href={`/leads/${l.id}`}
                      className="font-medium text-gray-900 hover:underline"
                    >
                      {l.company_name}
                    </Link>
                    {l.phone?.[0] ? (
                      <div className="text-xs text-gray-400">{l.phone[0]}</div>
                    ) : null}
                  </td>
                  <td className="px-3 py-2 text-gray-600">
                    {l.branche_text ?? groupLabel(l.branchekode) ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-gray-600">{l.city ?? "—"}</td>
                  <td className="px-3 py-2 text-gray-600">
                    {employeesLabel(l.employees_band, l.employees_exact)}
                  </td>
                  <td className="px-3 py-2">
                    <WebsiteNeedBadge need={l.website_need} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <ScoreChip score={l.score} />
                  </td>
                  <td className="px-3 py-2">
                    <PipelineBadge status={l.pipeline_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-gray-500">
            Side {page} af {totalPages}
          </span>
          <div className="flex gap-2">
            {page > 1 ? (
              <Link href={pageHref(page - 1)} className="rounded border px-3 py-1.5 hover:bg-gray-50">
                Forrige
              </Link>
            ) : (
              <span className="rounded border px-3 py-1.5 text-gray-300">Forrige</span>
            )}
            {page < totalPages ? (
              <Link href={pageHref(page + 1)} className="rounded border px-3 py-1.5 hover:bg-gray-50">
                Næste
              </Link>
            ) : (
              <span className="rounded border px-3 py-1.5 text-gray-300">Næste</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
