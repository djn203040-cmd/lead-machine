"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import type { TablesUpdate } from "@/lib/database.types";

export type EnrichmentActionResult = { error?: string; count?: number };

// Supabase caps a single request's URL length; chunk large id lists.
const CHUNK = 400;

// `satisfies … as never` mirrors leads/[id]/actions.ts — keeps the payload
// type-checked while bridging supabase-js 2.108's broken param inference.
async function transition(
  ids: string[],
  to: "queued" | "skipped",
  from: string[],
): Promise<EnrichmentActionResult> {
  const unique = [...new Set(ids)];
  if (!unique.length) return { count: 0 };

  const supabase = await createClient();
  let count = 0;
  for (let i = 0; i < unique.length; i += CHUNK) {
    const chunk = unique.slice(i, i + CHUNK);
    const { data, error } = await supabase
      .from("leads")
      .update(({ enrichment_status: to } satisfies TablesUpdate<"leads">) as never)
      .in("id", chunk)
      .in("enrichment_status", from) // never override an in-flight/enriched lead
      .select("id")
      .returns<{ id: string }[]>();
    if (error) return { error: error.message };
    count += data?.length ?? 0;
  }
  revalidatePath("/leads");
  return { count };
}

/** Opt leads into enrichment. Re-queues skipped/failed leads too. */
export async function enqueueEnrichment(ids: string[]): Promise<EnrichmentActionResult> {
  return transition(ids, "queued", ["pending", "skipped", "failed"]);
}

/** Decline enrichment for newly discovered (still-pending) leads. */
export async function skipEnrichment(ids: string[]): Promise<EnrichmentActionResult> {
  return transition(ids, "skipped", ["pending"]);
}
