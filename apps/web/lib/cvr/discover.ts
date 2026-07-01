// In-app discovery orchestration (server-only): fetch CVR companies, map them,
// drop suppressed entities, and upsert the rest into `leads` + raw payloads into
// `lead_enrichment.cvr`. Mirrors the worker's run_discovery, but persists with
// the authenticated SSR client (RLS "authenticated full access" covers writes).

import "server-only";
import type { Database, TablesInsert } from "@/lib/database.types";
import { fetchCvrCompanies, type CvrCreds, MAX_RESULTS } from "./client";
import { mapCompany, SUPPRESS_REKLAME } from "./mapper";
import type { SearchParameters } from "./query";

// The exact client type the SSR helper returns (its schema generics differ from
// a bare SupabaseClient<Database>).
type DbClient = Awaited<ReturnType<(typeof import("@/lib/supabase/server"))["createClient"]>>;

export type DiscoveryStats = {
  seen: number;
  upserted: number;
  suppressedReklame: number;
  suppressedInactive: number;
  errors: number;
  // Leads from this run still awaiting an enrich? decision (brand-new inserts +
  // any re-seen leads never decided on). Drives the post-discovery prompt.
  pendingLeadIds: string[];
};

export async function runDiscovery(
  supabase: DbClient,
  params: SearchParameters,
  searchName: string,
  maxResults: number = MAX_RESULTS,
  creds?: CvrCreds | null,
): Promise<DiscoveryStats> {
  const stats: DiscoveryStats = {
    seen: 0,
    upserted: 0,
    suppressedReklame: 0,
    suppressedInactive: 0,
    errors: 0,
    pendingLeadIds: [],
  };
  if (!creds) throw new Error("CVR credentials are not configured.");

  // Record the run so it shows in history (best-effort).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const { data: searchRow } = await supabase
    .from("searches")
    .insert(
      ({
        name: searchName,
        type: "cvr",
        parameters: params as unknown as Database["public"]["Tables"]["searches"]["Insert"]["parameters"],
        status: "running",
        created_by: user?.id ?? null,
      } satisfies TablesInsert<"searches">) as never,
    )
    .select("id")
    .single<{ id: string }>();
  const searchId = searchRow?.id ?? null;

  const records = await fetchCvrCompanies(params, creds, maxResults);

  // Map + de-duplicate by CVR number, dropping suppressed entities.
  const byCvr = new Map<string, { row: TablesInsert<"leads">; raw: unknown }>();
  for (const record of records) {
    stats.seen += 1;
    try {
      const { row, raw, suppression } = mapCompany(record);
      if (suppression === SUPPRESS_REKLAME) {
        stats.suppressedReklame += 1;
        continue;
      }
      if (suppression) {
        stats.suppressedInactive += 1;
        continue;
      }
      if (searchId) row.search_id = searchId;
      if (row.cvr_number) byCvr.set(row.cvr_number, { row, raw });
    } catch {
      stats.errors += 1;
    }
  }

  if (byCvr.size > 0) {
    const rows = [...byCvr.values()].map((x) => x.row);
    const { data: upserted, error } = await supabase
      .from("leads")
      .upsert(rows as never, { onConflict: "cvr_number" })
      .select("id, cvr_number, enrichment_status")
      .returns<{ id: string; cvr_number: string; enrichment_status: string }[]>();
    if (error) throw new Error(error.message);

    stats.upserted = upserted?.length ?? 0;
    // `enrichment_status` is only defaulted on insert; re-seen leads keep their
    // prior decision, so "still pending" == new/undecided leads to prompt about.
    stats.pendingLeadIds = (upserted ?? [])
      .filter((u) => u.enrichment_status === "pending")
      .map((u) => u.id);

    // Mirror the raw CVR payload into lead_enrichment.cvr (batch upsert).
    const enrichRows: TablesInsert<"lead_enrichment">[] = [];
    for (const lead of upserted ?? []) {
      const match = byCvr.get(lead.cvr_number);
      if (!match) continue;
      enrichRows.push({
        lead_id: lead.id,
        cvr: match.raw as Database["public"]["Tables"]["lead_enrichment"]["Insert"]["cvr"],
        last_enriched_at: new Date().toISOString(),
      });
    }
    if (enrichRows.length) {
      await supabase.from("lead_enrichment").upsert(enrichRows as never, { onConflict: "lead_id" });
    }
  }

  if (searchId) {
    await supabase
      .from("searches")
      .update(({ status: "completed", stats } as unknown as Database["public"]["Tables"]["searches"]["Update"]) as never)
      .eq("id", searchId);
  }

  return stats;
}
