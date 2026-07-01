"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import {
  ALL_CODES,
  GROUPS,
  groupForCode,
  normalizeCode,
} from "@/lib/branchekoder";
import { cvrCredsFromEnv } from "@/lib/cvr/client";
import { runDiscovery } from "@/lib/cvr/discover";
import type { SearchParameters } from "@/lib/cvr/query";

export type DiscoverState = {
  ok?: boolean;
  error?: string;
  stats?: { seen: number; upserted: number; suppressed: number };
  // New/undecided leads from this run, offered for enrichment via the prompt.
  pendingLeadIds?: string[];
};

const EMPLOYEE_BANDS = new Set([
  "ANTAL_0_0", "ANTAL_1_1", "ANTAL_2_4", "ANTAL_5_9", "ANTAL_10_19",
  "ANTAL_20_49", "ANTAL_50_99", "ANTAL_100_199", "ANTAL_200_499",
  "ANTAL_500_999", "ANTAL_1000_999999",
]);

function parseInts(values: FormDataEntryValue[], lo: number, hi: number): number[] {
  const out = new Set<number>();
  for (const v of values) {
    const n = Number(String(v).trim());
    if (Number.isInteger(n) && n >= lo && n <= hi) out.add(n);
  }
  return [...out];
}

/** Human-readable search name from the selected branches + areas. */
function searchName(codes: string[], postnumre: number[], kommunekoder: number[]): string {
  const groups = [...new Set(codes.map((c) => groupForCode(c)).filter(Boolean))] as string[];
  const brancheLabel =
    groups.length === 0
      ? `${codes.length} brancher`
      : groups.length <= 2
        ? groups.map((g) => GROUPS[g as keyof typeof GROUPS]).join(", ")
        : `${codes.length} brancher`;

  const areaBits: string[] = [];
  if (postnumre.length) areaBits.push(`${postnumre.length} postnr.`);
  if (kommunekoder.length) areaBits.push(`${kommunekoder.length} kommune(r)`);
  const area = areaBits.join(" + ") || "hele landet";

  return `${brancheLabel} · ${area}`;
}

export async function discoverAction(
  _prev: DiscoverState,
  formData: FormData,
): Promise<DiscoverState> {
  const codes = [
    ...new Set(
      formData.getAll("codes").map((c) => normalizeCode(String(c))).filter((c) => ALL_CODES.has(c)),
    ),
  ];
  const postnumre = parseInts(formData.getAll("postnumre"), 1000, 9999);
  const kommunekoder = parseInts(formData.getAll("kommunekoder"), 1, 999);
  const bands = formData.getAll("bands").map(String).filter((b) => EMPLOYEE_BANDS.has(b));

  if (!codes.length) return { error: "Vælg mindst én branche." };
  if (!postnumre.length && !kommunekoder.length)
    return { error: "Vælg mindst ét område (by, kommune eller postnummer)." };

  const creds = cvrCredsFromEnv();
  if (!creds) {
    return {
      error:
        "CVR-adgang er ikke konfigureret endnu. Tilføj CVR_ES_USER og CVR_ES_PASSWORD i miljøet (gratis login fra cvrselvbetjening@erst.dk).",
    };
  }

  const params: SearchParameters = {
    branchekoder: codes,
    postnumre,
    kommunekoder,
    employeeBands: bands,
  };
  const name = searchName(codes, postnumre, kommunekoder);

  try {
    const supabase = await createClient();
    const stats = await runDiscovery(supabase, params, name, undefined, creds);
    revalidatePath("/leads");
    return {
      ok: true,
      stats: {
        seen: stats.seen,
        upserted: stats.upserted,
        suppressed: stats.suppressedReklame + stats.suppressedInactive,
      },
      pendingLeadIds: stats.pendingLeadIds,
    };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "Discovery mislykkedes." };
  }
}
