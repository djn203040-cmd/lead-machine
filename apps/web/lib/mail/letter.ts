// Handwritten direct-mail copy — the three arms, the slug and the letter
// builder. Pure functions, shared by the server actions, the mail page and
// the landing page. See docs/DIRECT-MAIL.md.
//
// Hard rules from the spec:
//  - A4 650: ≤ 650 characters incl. spaces (≈110 Danish words). Longer reads
//    like a sales letter.
//  - Never "jeg har undersøgt din virksomhed" — the observation IS the proof.
//  - Never a timestamp ("jeg ringede tirsdag") — two weeks pass in transit.
//  - The handwritten URL is the company slug: sonorous.dk/<firma>.

export type MailArm = "A" | "B" | "C";

export const MAIL_ARMS: readonly MailArm[] = ["A", "B", "C"];

export const MAIL_ARM_META: Record<MailArm, { label: string; trigger: string; className: string }> = {
  A: { label: "A · Intet svar", trigger: "Ringet, ikke svaret", className: "chip-info" },
  B: { label: "B · Ikke interesseret", trigger: "Talt sammen, sagde nej", className: "chip-rose" },
  C: { label: "C · Kold", trigger: "Aldrig kontaktet", className: "chip-violet" },
};

export function isMailArm(value: string): value is MailArm {
  return (MAIL_ARMS as readonly string[]).includes(value);
}

export const MAIL_STATUS_META: Record<string, { label: string; className: string }> = {
  rejected: { label: "Afvist (filter)", className: "chip-neutral" },
  draft: { label: "Til gennemsyn", className: "chip-amber" },
  approved: { label: "Godkendt", className: "chip-teal" },
  batched: { label: "I batch", className: "chip-violet" },
  ordered: { label: "Bestilt", className: "chip-cyan" },
  sent: { label: "Sendt", className: "chip-brand" },
  cancelled: { label: "Annulleret", className: "chip-neutral" },
};

export function mailStatusMeta(status: string | null | undefined) {
  return MAIL_STATUS_META[status ?? "draft"] ?? MAIL_STATUS_META.draft;
}

export const REJECT_REASON_DA: Record<string, string> = {
  reklamebeskyttelse: "Reklamebeskyttet i CVR (CVR-loven §19)",
  robinson: "På Robinsonlisten (MFL §10 stk. 4)",
  robinson_unscreened: "Enkeltmandsvirksomhed — Robinsonlisten er ikke provisioneret/screenet endnu",
  adressebeskyttelse: "Adressebeskyttelse — ingen brugbar adresse",
  no_address: "Ingen postadresse i CVR",
  suppressed: "Undertrykt (frameldt / suppressed)",
  duplicate: "Har allerede et aktivt brev",
  archived: "Lead er arkiveret",
};

/** Pensaki A4 650 — the format we use. */
export const MAX_LETTER_CHARS = 650;
/** Envelope addressing gets its own allowance on top of the message. */
export const MAX_ADDRESS_CHARS = 200;

export const SENDER_NAME = process.env.NEXT_PUBLIC_MAIL_SENDER_NAME || "Daniel";
export const SENDER_COMPANY = "Sonorous Digital";

/**
 * The public host the letter carries in handwriting. Keep it short — it is
 * written with a fountain pen and typed by the recipient. The lead-machine
 * deployment must answer on it (see docs/DIRECT-MAIL.md → domain).
 */
export const MAIL_PUBLIC_BASE = (process.env.NEXT_PUBLIC_MAIL_PUBLIC_BASE || "sonorous.dk")
  .replace(/^https?:\/\//, "")
  .replace(/\/+$/, "");

export function publicUrl(slug: string): string {
  return `${MAIL_PUBLIC_BASE}/${slug}`;
}

// --- slug -----------------------------------------------------------------

const LEGAL_FORMS =
  /\b(aps|a\/s|as|ivs|i\/s|is|k\/s|ks|p\/s|smba|amba|fmba|v\/|holding|invest|ejendomme|enkeltmandsvirksomhed|pmv)\b/gi;

/**
 * Company name → handwriting-safe slug. Lowercase a–z0–9 only, no hyphens
 * where avoidable (a hyphen in cursive is ambiguous), legal-form suffixes
 * stripped, Danish letters transliterated. "Flamia ApS" → "flamia".
 */
export function slugify(companyName: string): string {
  const cleaned = companyName
    .replace(LEGAL_FORMS, " ")
    .replace(/[æÆ]/g, "ae")
    .replace(/[øØ]/g, "oe")
    .replace(/[åÅ]/g, "aa")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " og ")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  const words = cleaned.split(/\s+/).filter(Boolean);
  // Prefer the first two words joined; a single-word brand stays as-is.
  let slug = words.slice(0, 2).join("");
  if (slug.length < 3 && words.length > 2) slug = words.slice(0, 3).join("");
  if (slug.length > 24) slug = slug.slice(0, 24);
  return slug || "firma";
}

/** Slug candidates in order of preference — caller checks uniqueness. */
export function slugCandidates(companyName: string, city?: string | null): string[] {
  const base = slugify(companyName);
  const out = [base];
  if (city) {
    const c = slugify(city);
    if (c && c !== base) out.push(`${base}${c}`.slice(0, 28));
  }
  for (let i = 2; i <= 9; i++) out.push(`${base}${i}`);
  return out;
}

// --- first name -----------------------------------------------------------

/** Given a full name, the part we open the letter with. */
export function firstNameOf(fullName: string | null | undefined): string | null {
  const n = fullName?.trim();
  if (!n) return null;
  return n.split(/\s+/)[0] ?? null;
}

// --- letter ---------------------------------------------------------------

export type LetterInput = {
  arm: MailArm;
  firstName: string | null;
  companyName: string;
  /** "[konkret observation]" — one specific, checkable thing. */
  observation: string | null;
  /** "[X]" — what we looked at (jeres booking, jeres tilbudsflow …). */
  focus: string | null;
  slug: string;
};

export type Letter = { text: string; chars: number; ok: boolean; missing: string[] };

const OPENERS: Record<MailArm, (i: LetterInput) => string> = {
  // No timestamp — the letter lands ~2 weeks after the call.
  A: () => "Jeg forsøgte at fange dig på telefonen — det er nemmere bare at skrive.",
  // Acknowledge the no first, drop the pitch.
  B: (i) =>
    `Vi talte kort sammen, og det var ikke relevant lige nu. Helt fair. Jeg havde alligevel kigget på ${i.focus ?? "jeres hverdag"}, så du får det jeg fandt — brug det som du vil.`,
  C: (i) =>
    `Jeg faldt over ${i.companyName} og blev hængende ved ${i.observation ?? "[konkret observation]"}.`,
};

/**
 * Render the letter for an arm. Deterministic; the only per-lead variables are
 * first name, company, the observation line, the focus and the slug.
 */
export function buildLetter(i: LetterInput): Letter {
  const missing: string[] = [];
  if (!i.firstName) missing.push("fornavn");
  if (i.arm !== "B" && !i.observation) missing.push("observation");
  if (!i.focus) missing.push("fokus ([X])");

  const hello = i.firstName ? `Hej ${i.firstName},` : "Hej,";
  const focus = i.focus ?? "[X]";
  const opener = OPENERS[i.arm](i);

  const paras: string[] = [hello, opener];

  if (i.arm === "A") {
    // Arm A carries the observation in the second paragraph, since the opener
    // is spent on the call reference.
    paras.push(
      `Jeg blev hængende ved ${i.observation ?? "[konkret observation]"}. Jeg bygger små automatiseringer for danske virksomheder — typisk noget der fjerner 5–10 timers manuelt arbejde om ugen. Da jeg kiggede på ${focus}, kunne jeg se to steder hvor det ville kunne lade sig gøre.`,
    );
  } else if (i.arm === "C") {
    paras.push(
      `Jeg bygger små automatiseringer for danske virksomheder — typisk noget der fjerner 5–10 timers manuelt arbejde om ugen. Da jeg kiggede på ${focus}, kunne jeg se to steder hvor det ville kunne lade sig gøre.`,
    );
  } else {
    // Arm B — no pitch; the value is the finding itself.
    paras.push(
      `Det er to steder hvor der ligger 5–10 timers manuelt arbejde om ugen, som kunne køre af sig selv.`,
    );
  }

  paras.push(`Jeg har samlet det her: ${publicUrl(i.slug)}`);
  paras.push("Ingen tilmelding. Bare en side jeg har lavet til jer.");
  paras.push(`${SENDER_NAME}, ${SENDER_COMPANY}`);

  const text = paras.join("\n\n");
  const chars = text.length;
  return { text, chars, ok: chars <= MAX_LETTER_CHARS && missing.length === 0, missing };
}

/** The address block as Pensaki hand-writes it on the envelope. */
export function addressBlock(m: {
  recipient_name: string | null;
  company_name: string;
  address_line: string | null;
  postal_code: string | null;
  city: string | null;
  country: string;
}): string {
  const lines = [
    m.recipient_name ? `${m.recipient_name}` : null,
    m.recipient_name ? `${m.company_name}` : m.company_name,
    m.address_line,
    [m.postal_code, m.city].filter(Boolean).join(" ") || null,
    m.country,
  ].filter((l): l is string => Boolean(l && l.trim()));
  return lines.join("\n");
}
