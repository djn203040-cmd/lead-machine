// Batch export for the vendor. Pensaki's API v4 is beta and undocumented on
// our side (open question §11.3), so the reliable path is their XLS/CSV
// import template: one row per letter, {{segment}}-style columns for the
// personalised lines. Columns are named for their template; adjust the header
// row if their importer wants different names — the data is what matters.

export type ExportRow = {
  slug: string;
  recipient_name: string | null;
  company_name: string;
  address_line: string | null;
  postal_code: string | null;
  city: string | null;
  country: string;
  letter_text: string | null;
  is_seed: boolean;
};

function cell(v: string | null | undefined): string {
  const s = (v ?? "").replace(/\r?\n/g, "\n");
  return `"${s.replace(/"/g, '""')}"`;
}

/** Semicolon-separated (Excel/da-DK default), UTF-8 with BOM, CRLF rows. */
export function batchToCsv(rows: ExportRow[]): string {
  const header = [
    "reference",
    "salutation_name",
    "company",
    "street",
    "zip",
    "city",
    "country",
    "message",
    "is_seed",
  ];
  const lines = [header.join(";")];
  for (const r of rows) {
    lines.push(
      [
        cell(r.slug),
        cell(r.recipient_name),
        cell(r.company_name),
        cell(r.address_line),
        cell(r.postal_code),
        cell(r.city),
        cell(r.country),
        cell(r.letter_text),
        r.is_seed ? "1" : "0",
      ].join(";"),
    );
  }
  return "﻿" + lines.join("\r\n") + "\r\n";
}
