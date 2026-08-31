"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import type { Tables, TablesInsert, TablesUpdate } from "@/lib/database.types";
import { isPipelineStatus } from "@/lib/leadmeta";
import { enqueueMail } from "@/lib/mail/enqueue";
import { syncOutcomeToPm } from "@/lib/pm";

// `warning` = outcome logged locally, but a side effect (PM sync) failed.
// `info` = a side effect worth telling the caller (e.g. a letter was queued).
type ActionResult = { error?: string; warning?: string; info?: string };

// Direct-mail arm triggers (see docs/DIRECT-MAIL.md): a "no answer" queues an
// arm-A letter, a "not interested" queues arm B. Best-effort — the call outcome
// is already logged; the letter still needs human review before it is sent.
async function queueLetter(
  supabase: Awaited<ReturnType<typeof createClient>>,
  leadId: string,
  arm: "A" | "B",
  userId: string | null,
): Promise<string | undefined> {
  try {
    const r = await enqueueMail(supabase, leadId, arm, userId);
    if (r.status === "draft") return `Brev (arm ${arm}) lagt til gennemsyn`;
    if (r.status === "rejected") return `Brev ikke muligt: ${r.reason}`;
    if (r.status === "exists") return "Lead har allerede et brev i kø";
    return undefined;
  } catch {
    return undefined;
  }
}

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

  // Fetched up front — the PM sync needs the lead's identity + existing link.
  const { data: lead } = await supabase
    .from("leads")
    .select("company_name, email, branchekode, branche_text, pm_lead_id")
    .eq("id", leadId)
    .single<
      Pick<Tables<"leads">, "company_name" | "email" | "branchekode" | "branche_text" | "pm_lead_id">
    >();

  const { error } = await supabase
    .from("leads")
    .update(({ pipeline_status: status } satisfies TablesUpdate<"leads">) as never)
    .eq("id", leadId);
  if (error) return { error: error.message };

  // Every dial attempt is a lead_calls row — the mail arms hang off these.
  await supabase
    .from("lead_calls")
    .insert(({ lead_id: leadId, outcome: status, user_id: user?.id ?? null } satisfies TablesInsert<"lead_calls">) as never);

  const text = note?.trim();
  if (text) {
    const { error: noteErr } = await supabase
      .from("lead_notes")
      .insert(
        ({ lead_id: leadId, body: text, user_id: user?.id ?? null } satisfies TablesInsert<"lead_notes">) as never,
      );
    if (noteErr) return { error: noteErr.message };
  }

  // Mirror the outcome into Sonorous OS (best-effort — never blocks the log).
  let warning: string | undefined;
  if (lead) {
    const sync = await syncOutcomeToPm(status, lead);
    warning = sync.warning;
    if (sync.pmLeadId) {
      await supabase
        .from("leads")
        .update(
          ({
            pm_lead_id: sync.pmLeadId,
            pm_synced_at: new Date().toISOString(),
          } satisfies TablesUpdate<"leads">) as never,
        )
        .eq("id", leadId);
    }
  }

  // "Ikke interesseret" → arm B letter (acknowledges the no, drops the pitch).
  const info = status === "lost" ? await queueLetter(supabase, leadId, "B", user?.id ?? null) : undefined;

  revalidatePath("/leads/dialer");
  revalidatePath("/leads");
  revalidatePath("/leads/mail");
  revalidatePath("/leads/stats");
  return { ...(warning ? { warning } : {}), ...(info ? { info } : {}) };
}

/**
 * "Intet svar" — logs the attempt without moving pipeline_status (the lead
 * stays in the ring list) and queues an arm-A letter for review.
 */
export async function logNoAnswer(leadId: string, note?: string): Promise<ActionResult> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const { error } = await supabase
    .from("lead_calls")
    .insert(({ lead_id: leadId, outcome: "no_answer", user_id: user?.id ?? null } satisfies TablesInsert<"lead_calls">) as never);
  if (error) return { error: error.message };

  const text = note?.trim();
  if (text) {
    await supabase
      .from("lead_notes")
      .insert(({ lead_id: leadId, body: text, user_id: user?.id ?? null } satisfies TablesInsert<"lead_notes">) as never);
  }
  const info = await queueLetter(supabase, leadId, "A", user?.id ?? null);
  revalidatePath("/leads/dialer");
  revalidatePath("/leads/mail");
  revalidatePath("/leads/stats");
  return info ? { info } : {};
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
