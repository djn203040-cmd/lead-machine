// Map a raw CVR `Vrvirksomhed` record to a `leads` row — TypeScript port of the
// relevant parts of services/worker/src/leadmachine/cvr/mapper.py. Defensive:
// every CVR field is optional and deeply nested.

import type { TablesInsert } from "@/lib/database.types";

// Personally owned businesses (natural persons): enkeltmandsvirksomhed = 10,
// PMV = 81. These are personal data and need Robinson screening before outreach.
const SOLE_TRADER_FORM_CODES = new Set([10, 81]);
const ACTIVE_STATUSES = new Set(["NORMAL", "AKTIV"]);

export const SUPPRESS_REKLAME = "reklamebeskyttet";
export const SUPPRESS_INACTIVE = "inactive";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;

export type MappedLead = {
  row: TablesInsert<"leads">;
  raw: Json;
  suppression: typeof SUPPRESS_REKLAME | typeof SUPPRESS_INACTIVE | null;
};

function unwrap(record: Json): Json {
  if (record?.Vrvirksomhed && typeof record.Vrvirksomhed === "object") {
    return record.Vrvirksomhed;
  }
  return record;
}

function isCurrent(item: Json): boolean {
  return (item?.periode?.gyldigTil ?? null) === null;
}

function pickCurrent(items: Json[] | undefined, key = "kontaktoplysning"): string | null {
  if (!items?.length) return null;
  const visible = items.filter((i) => !i?.hemmelig);
  if (!visible.length) return null;
  const current = visible.filter(isCurrent);
  const chosen = (current.length ? current : visible).at(-1);
  const value = chosen?.[key];
  return value !== null && value !== undefined && value !== "" ? String(value) : null;
}

function pickCurrentAll(items: Json[] | undefined, key = "kontaktoplysning"): string[] {
  const out: string[] = [];
  for (const i of items ?? []) {
    if (i?.hemmelig || !isCurrent(i)) continue;
    const value = i?.[key];
    if (value !== null && value !== undefined && value !== "" && !out.includes(String(value))) {
      out.push(String(value));
    }
  }
  return out;
}

function latestEmployment(meta: Json): Json {
  for (const key of [
    "nyesteMaanedsbeskaeftigelse",
    "nyesteKvartalsbeskaeftigelse",
    "nyesteAarsbeskaeftigelse",
  ]) {
    if (meta?.[key]) return meta[key];
  }
  return {};
}

function formatAddress(addr: Json): string | null {
  const street = addr?.vejnavn;
  if (!street) return null;
  let house = "";
  if (addr.husnummerFra !== null && addr.husnummerFra !== undefined) {
    house = String(addr.husnummerFra);
    if (addr.husnummerTil && addr.husnummerTil !== addr.husnummerFra) house += `-${addr.husnummerTil}`;
    if (addr.bogstavFra) house += String(addr.bogstavFra);
  }
  let line = `${street} ${house}`.trim();
  const extras = ["etage", "sidedoer"].filter((k) => addr[k]).map((k) => String(addr[k]));
  if (extras.length) line += `, ${extras.join(" ")}`;
  return line;
}

function status(meta: Json, v: Json): string | null {
  if (meta?.sammensatStatus) return String(meta.sammensatStatus);
  const history = v?.virksomhedsstatus ?? [];
  return history.length ? history.at(-1)?.status ?? null : null;
}

export function mapCompany(record: Json): MappedLead {
  const v = unwrap(record);
  const meta = v?.virksomhedMetadata ?? {};

  const cvrNumber = String(v?.cvrNummer ?? "").trim();
  if (!cvrNumber) throw new Error("CVR record has no cvrNummer");

  let name: string | null = meta?.nyesteNavn?.navn ?? null;
  if (!name) {
    const navne = v?.navne ?? [];
    name = navne.length ? navne.at(-1)?.navn ?? null : null;
  }

  const hovedbranche = meta?.nyesteHovedbranche ?? {};
  const addr = meta?.nyesteBeliggenhedsadresse ?? {};
  const form = meta?.nyesteVirksomhedsform ?? {};
  const formCode = form?.virksomhedsformkode;
  const emp = latestEmployment(meta);
  const postnummer = addr?.postnummer;

  const website = pickCurrent(v?.hjemmeside);
  const cvrStatus = status(meta, v);
  const reklamebeskyttet = Boolean(v?.reklamebeskyttet ?? false);
  const isActive = ACTIVE_STATUSES.has((cvrStatus ?? "").trim().toUpperCase());

  const suppression = reklamebeskyttet
    ? SUPPRESS_REKLAME
    : !isActive
      ? SUPPRESS_INACTIVE
      : null;

  const row: TablesInsert<"leads"> = {
    cvr_number: cvrNumber,
    company_name: name || `CVR ${cvrNumber}`,
    address: formatAddress(addr),
    postal_code: postnummer !== null && postnummer !== undefined && postnummer !== "" ? String(postnummer) : null,
    city: addr?.postdistrikt ?? null,
    kommune: addr?.kommune?.kommuneNavn ?? null,
    phone: pickCurrentAll(v?.telefonNummer),
    email: pickCurrent(v?.elektroniskPost),
    website,
    branchekode: hovedbranche?.branchekode ?? null,
    branche_text: hovedbranche?.branchetekst ?? null,
    company_form: form?.langBeskrivelse ?? form?.kortBeskrivelse ?? null,
    cvr_status: cvrStatus,
    employees_band: emp?.intervalKodeAntalAnsatte ?? null,
    employees_exact: emp?.antalAnsatte ?? null,
    founded_at: meta?.stiftelsesDato ?? null,
    reklamebeskyttet,
    is_sole_trader: SOLE_TRADER_FORM_CODES.has(formCode),
    // Always `unknown`: the worker's qualifier only processes `unknown` leads,
    // and a missing CVR `hjemmeside` must still go through website *discovery*
    // (most Danish SMBs never fill that field in) before concluding `none`.
    website_need: "unknown",
  };

  return { row, raw: unwrap(record), suppression };
}
