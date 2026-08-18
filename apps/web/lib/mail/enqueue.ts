// Put a lead into the letter queue: run the legal filters, snapshot the
// recipient block from CVR data, mint a unique slug, insert a lead_mail row.
// Shared by the dialer (arm A/B triggers) and the mail page (arm C picker).
// Server-only — needs the caller's Supabase session.

import "server-only";

import type { Tables, TablesInsert } from "@/lib/database.types";
import type { createClient } from "@/lib/supabase/server";
import { type ContactEnrichment, view } from "@/lib/enrichment";
import { voicemailFirstName } from "@/lib/voicemail";
import { checkEligibility, type RejectReason } from "./eligibility";
import { type MailArm, firstNameOf, slugCandidates } from "./letter";

type Db = Awaited<ReturnType<typeof createClient>>;

export type EnqueueResult =
  | { status: "draft"; mailId: string; slug: string }
  | { status: "rejected"; mailId: string; reason: RejectReason }
  | { status: "exists"; mailId: string }
  | { status: "error"; error: string };

type LeadRow = Pick<
  Tables<"leads">,
  | "id"
  | "company_name"
  | "address"
  | "postal_code"
  | "city"
  | "is_archived"
  | "suppressed"
  | "suppression_reason"
  | "reklamebeskyttet"
  | "is_sole_trader"
  | "robinson_screened_at"
>;

/** Pick the decision maker we address: owner/director first, else first listed. */
export function pickRecipient(contact: unknown): string | null {
  const dms = view<ContactEnrichment>(contact).decision_makers ?? [];
  const preferred = dms.find((dm) => /indehaver|ejer|direktør|adm/i.test(dm.role ?? ""));
  return (preferred ?? dms[0])?.name?.trim() || null;
}

async function uniqueSlug(supabase: Db, companyName: string, city: string | null): Promise<string> {
  const candidates = slugCandidates(companyName, city);
  const { data } = await supabase.from("lead_mail").select("slug").in("slug", candidates);
  const taken = new Set(((data ?? []) as { slug: string }[]).map((r) => r.slug));
  const free = candidates.find((c) => !taken.has(c));
  // Astronomically unlikely to exhaust; fall back to a short random suffix.
  return free ?? `${candidates[0]}${Math.random().toString(36).slice(2, 5)}`;
}

export async function enqueueMail(
  supabase: Db,
  leadId: string,
  arm: MailArm,
  userId: string | null,
): Promise<EnqueueResult> {
  // One live letter per lead — surface the existing one instead of duplicating.
  const { data: existing } = await supabase
    .from("lead_mail")
    .select("id")
    .eq("lead_id", leadId)
    .not("status", "in", "(rejected,cancelled)")
    .maybeSingle();
  if (existing) return { status: "exists", mailId: (existing as { id: string }).id };

  const [{ data: leadData, error: leadErr }, { data: enrich }] = await Promise.all([
    supabase
      .from("leads")
      .select(
        "id, company_name, address, postal_code, city, is_archived, suppressed, suppression_reason, reklamebeskyttet, is_sole_trader, robinson_screened_at",
      )
      .eq("id", leadId)
      .maybeSingle(),
    supabase.from("lead_enrichment").select("contact").eq("lead_id", leadId).maybeSingle(),
  ]);
  const lead = leadData as LeadRow | null;
  if (leadErr || !lead) return { status: "error", error: leadErr?.message ?? "Lead ikke fundet" };

  const contact = (enrich as { contact: unknown } | null)?.contact;
  const recipient = pickRecipient(contact);
  // Sole trader: the person IS the business; the CVR name usually carries it.
  const firstName =
    firstNameOf(recipient) ??
    (lead.is_sole_trader ? firstNameOf(lead.company_name.replace(/\bv\/.*$/i, "")) : null) ??
    // voicemail helper is the same rule, kept for parity with the dialer
    voicemailFirstName(view<ContactEnrichment>(contact).decision_makers ?? []);

  const slug = await uniqueSlug(supabase, lead.company_name, lead.city);
  const verdict = checkEligibility(lead);

  const row = {
    lead_id: lead.id,
    arm,
    status: verdict.ok ? "draft" : "rejected",
    reject_reason: verdict.ok ? null : verdict.reason,
    slug,
    recipient_name: recipient,
    first_name: firstName,
    company_name: lead.company_name,
    address_line: lead.address,
    postal_code: lead.postal_code,
    city: lead.city,
    created_by: userId,
  } satisfies TablesInsert<"lead_mail">;

  const { data: inserted, error } = await supabase
    .from("lead_mail")
    .insert(row as never)
    .select("id")
    .single();
  if (error || !inserted) return { status: "error", error: error?.message ?? "Kunne ikke oprette brev" };
  const mailId = (inserted as { id: string }).id;
  return verdict.ok
    ? { status: "draft", mailId, slug }
    : { status: "rejected", mailId, reason: verdict.reason };
}
