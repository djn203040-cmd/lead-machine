// The three mandatory legal filters (+ data sanity) applied at enqueue time.
// Built into the pipeline, not bolted on: a lead that fails lands in lead_mail
// as `rejected` with the reason, so attrition is measurable (spec §4, §11.7).
//
//  1. Reklamebeskyttelse (CVR-loven §19) — flag in CVR data → never mail.
//     Discovery already drops these, but a lead can be flagged later.
//  2. Robinsonlisten (MFL §10 stk. 4) — applies to natural persons and
//     personally-run sole traders at a home address. `suppressed` is the
//     worker's Robinson verdict; a sole trader that was never screened is
//     held back rather than mailed.
//  3. Adressebeskyttelse — owner records come back blank; we always mail the
//     COMPANY address (att. named person), so this only bites when the
//     company itself has no usable address.

export type EligibilityLead = {
  is_archived: boolean;
  suppressed: boolean;
  suppression_reason: string | null;
  reklamebeskyttet: boolean;
  is_sole_trader: boolean;
  robinson_screened_at: string | null;
  address: string | null;
  postal_code: string | null;
  city: string | null;
};

export type RejectReason =
  | "reklamebeskyttelse"
  | "robinson"
  | "robinson_unscreened"
  | "adressebeskyttelse"
  | "no_address"
  | "suppressed"
  | "duplicate"
  | "archived";

export type Eligibility = { ok: true } | { ok: false; reason: RejectReason };

export type EligibilityOptions = {
  /**
   * The worker stamps robinson_screened_at on every sole trader — even when
   * ROBINSON_LIST_PATH is unset and the list is empty (screening "ran" but
   * suppressed nothing). Until the real list is provisioned, that stamp is not
   * evidence. Set MAIL_ROBINSON_PROVISIONED=1 in the web env once it is.
   */
  robinsonProvisioned: boolean;
};

export function robinsonProvisionedFromEnv(): boolean {
  return process.env.MAIL_ROBINSON_PROVISIONED === "1";
}

export function checkEligibility(
  lead: EligibilityLead,
  opts: EligibilityOptions = { robinsonProvisioned: robinsonProvisionedFromEnv() },
): Eligibility {
  if (lead.is_archived) return { ok: false, reason: "archived" };
  if (lead.reklamebeskyttet) return { ok: false, reason: "reklamebeskyttelse" };
  if (lead.suppressed) {
    const r = (lead.suppression_reason ?? "").toLowerCase();
    return { ok: false, reason: r.includes("robinson") ? "robinson" : "suppressed" };
  }
  // A sole trader's CVR address is a private address → Robinson applies.
  if (lead.is_sole_trader && (!lead.robinson_screened_at || !opts.robinsonProvisioned)) {
    return { ok: false, reason: "robinson_unscreened" };
  }
  const hasStreet = Boolean(lead.address?.trim());
  const hasTown = Boolean(lead.postal_code?.trim()) && Boolean(lead.city?.trim());
  if (!hasStreet || !hasTown) return { ok: false, reason: "no_address" };
  return { ok: true };
}
