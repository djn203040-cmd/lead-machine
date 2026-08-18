"use server";

import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import type { Tables, TablesInsert, TablesUpdate } from "@/lib/database.types";
import { type WebsiteEvidence, view } from "@/lib/enrichment";
import { employeesLabel } from "@/lib/leadmeta";
import { enqueueMail } from "@/lib/mail/enqueue";
import { MAX_LETTER_CHARS, buildLetter, isMailArm, type MailArm } from "@/lib/mail/letter";
import { draftObservation } from "@/lib/mail/observation";

type ActionResult = { error?: string; warning?: string; info?: string };

// supabase-js 2.108's typed client infers insert/update params as `never` with
// our generated types (same reason the list queries use `.returns<>()`). The
// `satisfies` keeps the payload checked; the `as never` bridges that inference.

const PATHS = ["/leads/mail", "/leads/dialer", "/leads"];
function revalidate() {
  for (const p of PATHS) revalidatePath(p);
}

async function ctx() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return { supabase, userId: user?.id ?? null };
}

/** Arm C picker (and the lead page's "Send brev"): queue one or many leads. */
export async function enqueueLeads(leadIds: string[], arm: string): Promise<ActionResult> {
  if (!isMailArm(arm)) return { error: "Ugyldig arm" };
  if (!leadIds.length) return { error: "Vælg mindst ét lead" };
  const { supabase, userId } = await ctx();
  let drafts = 0,
    rejected = 0,
    exists = 0;
  const errors: string[] = [];
  for (const id of leadIds) {
    const r = await enqueueMail(supabase, id, arm as MailArm, userId);
    if (r.status === "draft") drafts++;
    else if (r.status === "rejected") rejected++;
    else if (r.status === "exists") exists++;
    else errors.push(r.error);
  }
  revalidate();
  revalidatePath(`/leads/${leadIds[0]}`);
  const parts = [`${drafts} i kø`];
  if (rejected) parts.push(`${rejected} afvist af filtre`);
  if (exists) parts.push(`${exists} havde allerede et brev`);
  return errors.length ? { error: errors.join("; "), info: parts.join(" · ") } : { info: parts.join(" · ") };
}

export type MailPatch = {
  recipient_name?: string | null;
  first_name?: string | null;
  address_line?: string | null;
  postal_code?: string | null;
  city?: string | null;
  observation_text?: string | null;
  focus_text?: string | null;
  landing_video_url?: string | null;
  landing_headline?: string | null;
  arm?: string;
};

export async function updateMail(mailId: string, patch: MailPatch): Promise<ActionResult> {
  const { supabase } = await ctx();
  if (patch.arm !== undefined && !isMailArm(patch.arm)) return { error: "Ugyldig arm" };
  const clean = Object.fromEntries(
    Object.entries(patch).map(([k, v]) => [k, typeof v === "string" ? v.trim() || null : v]),
  );
  // Editing invalidates a frozen letter — back to draft so it is re-approved.
  const { error } = await supabase
    .from("lead_mail")
    .update(
      ({
        ...clean,
        status: "draft",
        letter_text: null,
        letter_chars: null,
        observation_approved_at: null,
        observation_approved_by: null,
      } satisfies TablesUpdate<"lead_mail">) as never,
    )
    .eq("id", mailId)
    .in("status", ["draft", "approved"]);
  if (error) return { error: error.message };
  revalidate();
  return {};
}

/** Ask Claude for a first draft of the observation + focus. Human still approves. */
export async function suggestObservation(mailId: string): Promise<ActionResult> {
  const { supabase } = await ctx();
  const { data: mailData } = await supabase
    .from("lead_mail")
    .select("id, lead_id, arm, company_name")
    .eq("id", mailId)
    .maybeSingle();
  const mail = mailData as Pick<Tables<"lead_mail">, "id" | "lead_id" | "arm" | "company_name"> | null;
  if (!mail) return { error: "Brev ikke fundet" };

  const [leadRes, angleRes, enrichRes, notesRes] = await Promise.all([
    supabase
      .from("leads")
      .select("branche_text, city, website, website_need, employees_band, employees_exact, founded_at")
      .eq("id", mail.lead_id)
      .maybeSingle(),
    supabase.from("lead_angles").select("summary_da, weaknesses_da").eq("lead_id", mail.lead_id).maybeSingle(),
    supabase.from("lead_enrichment").select("website").eq("lead_id", mail.lead_id).maybeSingle(),
    supabase
      .from("lead_notes")
      .select("body")
      .eq("lead_id", mail.lead_id)
      .order("created_at", { ascending: false })
      .limit(5),
  ]);
  const lead = leadRes.data as Pick<
    Tables<"leads">,
    "branche_text" | "city" | "website" | "website_need" | "employees_band" | "employees_exact" | "founded_at"
  > | null;
  const angle = angleRes.data as Pick<Tables<"lead_angles">, "summary_da" | "weaknesses_da"> | null;
  const enrich = enrichRes.data as Pick<Tables<"lead_enrichment">, "website"> | null;
  const notes = ((notesRes.data ?? []) as { body: string }[]).map((n) => n.body);

  const web = view<WebsiteEvidence>(enrich?.website);
  const res = await draftObservation({
    arm: mail.arm as MailArm,
    company_name: mail.company_name,
    branche_text: lead?.branche_text ?? null,
    city: lead?.city ?? null,
    website: lead?.website ?? null,
    website_need: lead?.website_need ?? "unknown",
    employees: lead ? employeesLabel(lead.employees_band, lead.employees_exact) : null,
    founded_at: lead?.founded_at ?? null,
    angle_summary: angle?.summary_da ?? null,
    angle_notes: angle?.weaknesses_da ?? null,
    website_evidence: { signals: web.signals, quality: web.quality, reasons: web.reasons },
    call_notes: notes,
  });
  if (res.error || !res.draft) return { error: res.error ?? "Intet udkast" };

  const { error } = await supabase
    .from("lead_mail")
    .update(
      ({
        observation_text: res.draft.observation,
        focus_text: res.draft.focus,
        status: "draft",
        letter_text: null,
        letter_chars: null,
        observation_approved_at: null,
        observation_approved_by: null,
      } satisfies TablesUpdate<"lead_mail">) as never,
    )
    .eq("id", mailId);
  if (error) return { error: error.message };
  revalidate();
  return {
    info: `Udkast (${res.draft.confidence} sikkerhed) — belæg: ${res.draft.evidence}`,
    warning: res.draft.confidence === "lav" ? "Lav sikkerhed — tjek observationen mod virkeligheden før du godkender." : undefined,
  };
}

/** Freeze the letter text and mark the observation human-approved. */
export async function approveMail(mailId: string): Promise<ActionResult> {
  const { supabase, userId } = await ctx();
  const { data } = await supabase.from("lead_mail").select("*").eq("id", mailId).maybeSingle();
  const m = data as Tables<"lead_mail"> | null;
  if (!m) return { error: "Brev ikke fundet" };
  if (m.status !== "draft") return { error: "Kun breve til gennemsyn kan godkendes" };
  if (!m.address_line || !m.postal_code || !m.city) return { error: "Adressen er ufuldstændig" };

  const letter = buildLetter({
    arm: m.arm as MailArm,
    firstName: m.first_name,
    companyName: m.company_name,
    observation: m.observation_text,
    focus: m.focus_text,
    slug: m.slug,
  });
  if (letter.missing.length) return { error: `Mangler: ${letter.missing.join(", ")}` };
  if (letter.chars > MAX_LETTER_CHARS)
    return { error: `Brevet er ${letter.chars} tegn — max ${MAX_LETTER_CHARS}. Kort observationen ned.` };

  const { error } = await supabase
    .from("lead_mail")
    .update(
      ({
        status: "approved",
        letter_text: letter.text,
        letter_chars: letter.chars,
        observation_approved_at: new Date().toISOString(),
        observation_approved_by: userId,
      } satisfies TablesUpdate<"lead_mail">) as never,
    )
    .eq("id", mailId);
  if (error) return { error: error.message };
  revalidate();
  return {};
}

export async function setMailStatus(
  mailId: string,
  status: "draft" | "cancelled",
): Promise<ActionResult> {
  const { supabase } = await ctx();
  const { error } = await supabase
    .from("lead_mail")
    .update(
      ({
        status,
        ...(status === "draft"
          ? { batch_id: null, letter_text: null, letter_chars: null, observation_approved_at: null, observation_approved_by: null }
          : {}),
      } satisfies TablesUpdate<"lead_mail">) as never,
    )
    .eq("id", mailId)
    .in("status", ["draft", "approved", "batched", "rejected"]);
  if (error) return { error: error.message };
  revalidate();
  return {};
}

/** Re-run the filters on a rejected letter (e.g. after Robinson screening). */
export async function retryRejected(mailId: string): Promise<ActionResult> {
  const { supabase, userId } = await ctx();
  const { data } = await supabase.from("lead_mail").select("lead_id, arm").eq("id", mailId).maybeSingle();
  const m = data as Pick<Tables<"lead_mail">, "lead_id" | "arm"> | null;
  if (!m) return { error: "Brev ikke fundet" };
  await supabase.from("lead_mail").update(({ status: "cancelled" } satisfies TablesUpdate<"lead_mail">) as never).eq("id", mailId);
  const r = await enqueueMail(supabase, m.lead_id, m.arm as MailArm, userId);
  revalidate();
  if (r.status === "error") return { error: r.error };
  if (r.status === "rejected") return { warning: `Stadig afvist: ${r.reason}` };
  return { info: "Filtrene er nu bestået — brevet er til gennemsyn." };
}

// --- batches -----------------------------------------------------------------

/** Move every approved letter into a new batch. MOQ is 10 — warn under that. */
export async function createBatch(name: string, seedIncluded: boolean, mailIds?: string[]): Promise<ActionResult> {
  const { supabase, userId } = await ctx();
  let q = supabase.from("lead_mail").select("id").eq("status", "approved");
  if (mailIds?.length) q = q.in("id", mailIds);
  const { data: approved } = await q;
  const ids = ((approved ?? []) as { id: string }[]).map((r) => r.id);
  if (!ids.length) return { error: "Ingen godkendte breve at batche" };

  const { data: batchData, error: bErr } = await supabase
    .from("mail_batches")
    .insert(
      ({
        name: name.trim() || `Batch ${new Date().toISOString().slice(0, 10)}`,
        seed_included: seedIncluded,
        created_by: userId,
      } satisfies TablesInsert<"mail_batches">) as never,
    )
    .select("id")
    .single();
  if (bErr || !batchData) return { error: bErr?.message ?? "Kunne ikke oprette batch" };
  const batchId = (batchData as { id: string }).id;

  const { error } = await supabase
    .from("lead_mail")
    .update(({ status: "batched", batch_id: batchId } satisfies TablesUpdate<"lead_mail">) as never)
    .in("id", ids);
  if (error) return { error: error.message };
  revalidate();
  return ids.length < 10
    ? { warning: `${ids.length} breve — Pensaki fakturerer minimum 10 stk. pr. ordre.` }
    : { info: `${ids.length} breve i batchen` };
}

export async function removeFromBatch(mailId: string): Promise<ActionResult> {
  const { supabase } = await ctx();
  const { error } = await supabase
    .from("lead_mail")
    .update(({ status: "approved", batch_id: null } satisfies TablesUpdate<"lead_mail">) as never)
    .eq("id", mailId)
    .eq("status", "batched");
  if (error) return { error: error.message };
  revalidate();
  return {};
}

/**
 * Batch ordered at the vendor: mark letters ordered, note it on each lead and
 * schedule the follow-up call (arms A + C) at +offset days. Arm B gets no call
 * (spec §8) — it is judged on scan rate alone.
 */
export async function markBatchOrdered(
  batchId: string,
  vendorOrderId: string,
  followupOffsetDays: number,
): Promise<ActionResult> {
  const { supabase, userId } = await ctx();
  const offset = Number.isFinite(followupOffsetDays) && followupOffsetDays > 0 ? Math.round(followupOffsetDays) : 12;
  const now = new Date();
  const { error: bErr } = await supabase
    .from("mail_batches")
    .update(
      ({
        status: "ordered",
        vendor_order_id: vendorOrderId.trim() || null,
        ordered_at: now.toISOString(),
        followup_offset_days: offset,
      } satisfies TablesUpdate<"mail_batches">) as never,
    )
    .eq("id", batchId);
  if (bErr) return { error: bErr.message };

  const { data } = await supabase.from("lead_mail").select("id, lead_id, arm, slug").eq("batch_id", batchId);
  const rows = (data ?? []) as Pick<Tables<"lead_mail">, "id" | "lead_id" | "arm" | "slug">[];
  const followupDate = new Date(now.getTime() + offset * 86_400_000);
  followupDate.setHours(9, 0, 0, 0);

  for (const m of rows) {
    let followupId: string | null = null;
    if (m.arm !== "B") {
      const { data: f } = await supabase
        .from("lead_followups")
        .insert(
          ({ lead_id: m.lead_id, follow_up_date: followupDate.toISOString(), user_id: userId } satisfies TablesInsert<"lead_followups">) as never,
        )
        .select("id")
        .single();
      followupId = (f as { id: string } | null)?.id ?? null;
    }
    await supabase.from("lead_notes").insert(
      ({
        lead_id: m.lead_id,
        user_id: userId,
        body: `Håndskrevet brev bestilt (arm ${m.arm}) — ${vendorOrderId.trim() || "ordre"} · side: /${m.slug}${m.arm !== "B" ? ` · opfølgningsopkald +${offset} dage` : ""}`,
      } satisfies TablesInsert<"lead_notes">) as never,
    );
    await supabase
      .from("lead_mail")
      .update(({ status: "ordered", followup_id: followupId } satisfies TablesUpdate<"lead_mail">) as never)
      .eq("id", m.id);
  }
  revalidate();
  return { info: `${rows.length} breve bestilt · opfølgning ${followupDate.toLocaleDateString("da-DK")}` };
}

export async function markBatchSent(batchId: string): Promise<ActionResult> {
  const { supabase } = await ctx();
  const now = new Date().toISOString();
  const { error } = await supabase
    .from("mail_batches")
    .update(({ status: "sent", sent_at: now } satisfies TablesUpdate<"mail_batches">) as never)
    .eq("id", batchId);
  if (error) return { error: error.message };
  await supabase
    .from("lead_mail")
    .update(({ status: "sent" } satisfies TablesUpdate<"lead_mail">) as never)
    .eq("batch_id", batchId)
    .eq("status", "ordered");
  revalidate();
  return {};
}

export async function markSeedReceived(batchId: string): Promise<ActionResult> {
  const { supabase } = await ctx();
  const { error } = await supabase
    .from("mail_batches")
    .update(({ seed_received_at: new Date().toISOString(), status: "done" } satisfies TablesUpdate<"mail_batches">) as never)
    .eq("id", batchId);
  if (error) return { error: error.message };
  revalidate();
  return {};
}

export async function updateBatchNotes(batchId: string, notes: string): Promise<ActionResult> {
  const { supabase } = await ctx();
  const { error } = await supabase
    .from("mail_batches")
    .update(({ notes: notes.trim() || null } satisfies TablesUpdate<"mail_batches">) as never)
    .eq("id", batchId);
  if (error) return { error: error.message };
  revalidate();
  return {};
}
