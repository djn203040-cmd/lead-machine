// Danish phone-type classification — who is likely to answer the call?
//
// Danish numbers are assigned by range (Energistyrelsens nummerplan), so the
// first digits reveal the service type: mobile ranges are a personal handset
// (for a small business: the owner directly), geographic landlines are the
// shop's main line (staff/gatekeeper likely), and 70/80/90-numbers are
// corporate switchboard/service lines. Prefix heuristic — mirrors
// classify_phone()/best_phone_type() in worker website/phones.py and the
// dk_phone_class()/dk_phone_type() SQL functions (migration 0009).

export type PhoneType = "mobile" | "landline" | "service";

const MOBILE_PREFIXES = [
  "2", // all of 20–29
  "30", "31", "40", "41", "42", "50", "51", "52", "53",
  "60", "61", "71", "81", "91", "92", "93",
];
const SERVICE_PREFIXES = ["70", "80", "90"];

/** Normalise to a Danish 8-digit string (strip +45/0045), or null. */
export function normalizePhone(raw: string | null | undefined): string | null {
  let digits = (raw ?? "").replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("0045")) digits = digits.slice(4);
  else if (digits.length === 10 && digits.startsWith("45")) digits = digits.slice(2);
  return /^[2-9]\d{7}$/.test(digits) ? digits : null;
}

export function classifyPhone(raw: string | null | undefined): PhoneType | null {
  const n = normalizePhone(raw);
  if (!n) return null;
  if (SERVICE_PREFIXES.some((p) => n.startsWith(p))) return "service";
  if (MOBILE_PREFIXES.some((p) => n.startsWith(p))) return "mobile";
  return "landline";
}

export type PhoneTypeMeta = {
  label: string;
  /** Existing .chip color class from globals.css */
  className: string;
  /** One-line dialer hint: who picks up and how to open. */
  hint: string;
};

const PHONE_TYPE_META: Record<PhoneType, PhoneTypeMeta> = {
  mobile: {
    label: "Mobil — direkte",
    className: "chip-teal",
    hint: "Sandsynligvis ejerens egen telefon — gå direkte på åbningsreplikken.",
  },
  landline: {
    label: "Fastnet — hovednummer",
    className: "chip-amber",
    hint: "Butikkens hovedtelefon — en medarbejder kan tage den. Nævn demoen kort og spørg efter ejeren.",
  },
  service: {
    label: "70-nummer — omstilling",
    className: "chip-rose",
    hint: "Virksomhedens omstilling — aldrig ejeren direkte. Nævn demoen kort og bed om den rigtige person.",
  },
};

export function phoneTypeMeta(type: string | null | undefined): PhoneTypeMeta | null {
  return type && type in PHONE_TYPE_META ? PHONE_TYPE_META[type as PhoneType] : null;
}

/** Options for the lead-list filter (values match leads.phone_type). */
export const PHONE_TYPE_OPTIONS = [
  { value: "mobile", label: "Mobil (direkte til ejer)" },
  { value: "landline", label: "Fastnet (hovednummer)" },
  { value: "service", label: "70-nummer (omstilling)" },
];
