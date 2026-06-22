"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { codesInGroup, GROUPS, type BranchekodeGroup } from "@/lib/branchekoder";
import { cvrCredsFromEnv } from "@/lib/cvr/client";
import { runDiscovery } from "@/lib/cvr/discover";
import type { SearchParameters } from "@/lib/cvr/query";

export type DiscoverState = {
  ok?: boolean;
  error?: string;
  stats?: { seen: number; upserted: number; suppressed: number };
};

const EMPLOYEE_BANDS = new Set([
  "ANTAL_0_0", "ANTAL_1_1", "ANTAL_2_4", "ANTAL_5_9", "ANTAL_10_19",
  "ANTAL_20_49", "ANTAL_50_99", "ANTAL_100_199", "ANTAL_200_499",
  "ANTAL_500_999", "ANTAL_1000_999999",
]);

function parsePostnumre(raw: string): number[] {
  return raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n >= 1000 && n <= 9999);
}

export async function discoverAction(
  _prev: DiscoverState,
  formData: FormData,
): Promise<DiscoverState> {
  const group = String(formData.get("group") ?? "") as BranchekodeGroup;
  const postnrRaw = String(formData.get("postnumre") ?? "");
  const bands = formData.getAll("bands").map(String).filter((b) => EMPLOYEE_BANDS.has(b));

  if (!group || !(group in GROUPS)) return { error: "Vælg en branche." };
  const branchekoder = codesInGroup(group);
  if (!branchekoder.length) return { error: "Ingen branchekoder for den gruppe." };

  const postnumre = parsePostnumre(postnrRaw);
  if (!postnumre.length) return { error: "Indtast mindst ét gyldigt postnummer (1000–9999)." };

  const creds = cvrCredsFromEnv();
  if (!creds) {
    return {
      error:
        "CVR-adgang er ikke konfigureret endnu. Tilføj CVR_ES_USER og CVR_ES_PASSWORD i miljøet (gratis login fra cvrselvbetjening@erst.dk).",
    };
  }

  const params: SearchParameters = { branchekoder, postnumre, employeeBands: bands };
  const name = `${GROUPS[group]} · ${postnumre.join(", ")}`;

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
    };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "Discovery mislykkedes." };
  }
}
