// Dialer-outcome sync into Sonorous OS (the self-built PM system, separate
// Supabase project) — its CRM "Leads" module. Server-only.
//
// Policy: only a booked meeting CREATES a PM lead (cold-call misses stay out
// of the CRM). Once a lead is linked (pm_lead_id), every outcome UPDATES the
// PM lead's status. Note the PM leads table has no phone column by design
// (Notion is its schema source of truth) — name/email/niche is what fits.
//
// Requires PM_SUPABASE_URL + PM_SUPABASE_SECRET_KEY in the web app's server
// env. Without them the sync no-ops and the dialer works as before.

import "server-only";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { groupLabel } from "@/lib/branchekoder";

// Lead Machine pipeline_status → Sonorous OS lead_status enum.
const PM_STATUS: Record<string, string> = {
  contacted: "contacted",
  meeting_booked: "meeting_booked",
  lost: "lost",
  discarded: "archived",
};

export type PmSyncLead = {
  pm_lead_id: string | null;
  company_name: string;
  email: string | null;
  branchekode: string | null;
  branche_text: string | null;
};

export type PmSyncResult = {
  /** id of the (possibly just-created) PM lead — caller persists it as pm_lead_id */
  pmLeadId?: string;
  /** sync failed — the outcome is still logged locally, but tell the caller */
  warning?: string;
};

function pmClient(): SupabaseClient | null {
  const url = process.env.PM_SUPABASE_URL;
  const key = process.env.PM_SUPABASE_SECRET_KEY;
  if (!url || !key) return null;
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

/** Push a dialer outcome to the PM system. Never throws. */
export async function syncOutcomeToPm(status: string, lead: PmSyncLead): Promise<PmSyncResult> {
  const pmStatus = PM_STATUS[status];
  if (!pmStatus) return {};
  const pm = pmClient();
  if (!pm) return {};

  try {
    if (lead.pm_lead_id) {
      const { error } = await pm
        .from("leads")
        .update({ status: pmStatus })
        .eq("id", lead.pm_lead_id);
      if (error) return { warning: `Udfald gemt, men PM-sync fejlede: ${error.message}` };
      return { pmLeadId: lead.pm_lead_id };
    }

    if (pmStatus !== "meeting_booked") return {};

    const niche = groupLabel(lead.branchekode) ?? lead.branche_text;
    const { data, error } = await pm
      .from("leads")
      .insert({
        name: lead.company_name,
        status: pmStatus,
        email: lead.email,
        niche: niche ? [niche] : [],
      })
      .select("id")
      .single<{ id: string }>();
    if (error || !data) {
      return { warning: `Udfald gemt, men PM-sync fejlede: ${error?.message ?? "ukendt fejl"}` };
    }
    return { pmLeadId: data.id };
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { warning: `Udfald gemt, men PM-sync fejlede: ${msg}` };
  }
}
