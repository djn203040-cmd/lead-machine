"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import type { TablesInsert, TablesUpdate } from "@/lib/database.types";
import { isPipelineStatus } from "@/lib/leadmeta";

type ActionResult = { error?: string };

// supabase-js 2.108's typed client infers insert/update params as `never` with
// our generated types (same reason the list query uses `.returns<>()`). The
// `satisfies` keeps the payload checked; the `as never` bridges that inference.

// One call-outcome: move the lead's pipeline status and, optionally, attach the
// note the caller jotted during the call. Used by the outcome buttons.
export async function logOutcome(
  leadId: string,
  status: string,
  note?: string,
): Promise<ActionResult> {
  if (!isPipelineStatus(status)) return { error: "Ugyldig status" };
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { error } = await supabase
    .from("leads")
    .update(({ pipeline_status: status } satisfies TablesUpdate<"leads">) as never)
    .eq("id", leadId);
  if (error) return { error: error.message };

  const text = note?.trim();
  if (text) {
    const { error: noteErr } = await supabase
      .from("lead_notes")
      .insert(
        ({ lead_id: leadId, body: text, user_id: user?.id ?? null } satisfies TablesInsert<"lead_notes">) as never,
      );
    if (noteErr) return { error: noteErr.message };
  }

  revalidatePath("/leads/dialer");
  revalidatePath("/leads");
  return {};
}

export async function saveNote(leadId: string, body: string): Promise<ActionResult> {
  const text = body.trim();
  if (!text) return { error: "Noten er tom" };
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const { error } = await supabase
    .from("lead_notes")
    .insert(
      ({ lead_id: leadId, body: text, user_id: user?.id ?? null } satisfies TablesInsert<"lead_notes">) as never,
    );
  if (error) return { error: error.message };
  revalidatePath("/leads/dialer");
  return {};
}

export async function scheduleFollowup(leadId: string, date: string): Promise<ActionResult> {
  if (!date) return { error: "Vælg en dato" };
  const ts = new Date(`${date}T09:00:00`);
  if (Number.isNaN(ts.getTime())) return { error: "Ugyldig dato" };
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const { error } = await supabase
    .from("lead_followups")
    .insert(
      ({
        lead_id: leadId,
        follow_up_date: ts.toISOString(),
        user_id: user?.id ?? null,
      } satisfies TablesInsert<"lead_followups">) as never,
    );
  if (error) return { error: error.message };
  revalidatePath("/leads/dialer");
  return {};
}
