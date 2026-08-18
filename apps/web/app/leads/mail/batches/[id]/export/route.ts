import { NextResponse, type NextRequest } from "next/server";
import type { Tables } from "@/lib/database.types";
import { batchToCsv, type ExportRow } from "@/lib/mail/export";
import { MAIL_PUBLIC_BASE } from "@/lib/mail/letter";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

// CSV of one batch for the vendor's import template. Authenticated (the
// middleware bounces anonymous requests to /login). Adds our own seed row when
// the batch has seed_included and MAIL_SEED_* are set — that letter is how we
// measure real DE→DK transit before trusting the follow-up offset.
export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const [{ data: batchData }, { data: rowsData }] = await Promise.all([
    supabase.from("mail_batches").select("*").eq("id", id).maybeSingle(),
    supabase
      .from("lead_mail")
      .select("slug, recipient_name, company_name, address_line, postal_code, city, country, letter_text, is_seed")
      .eq("batch_id", id)
      .order("company_name"),
  ]);
  const batch = batchData as Tables<"mail_batches"> | null;
  if (!batch) return new NextResponse("Batch ikke fundet", { status: 404 });

  const rows: ExportRow[] = ((rowsData ?? []) as ExportRow[]).slice();

  const seedStreet = process.env.MAIL_SEED_STREET;
  const seedZip = process.env.MAIL_SEED_ZIP;
  const seedCity = process.env.MAIL_SEED_CITY;
  if (batch.seed_included && seedStreet && seedZip && seedCity) {
    rows.push({
      slug: `seed-${batch.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 20)}`,
      recipient_name: process.env.MAIL_SEED_NAME ?? null,
      company_name: process.env.MAIL_SEED_COMPANY ?? "Sonorous Digital",
      address_line: seedStreet,
      postal_code: seedZip,
      city: seedCity,
      country: "Danmark",
      letter_text: `Seed-brev — måler leveringstid DE→DK.\n\nBatch: ${batch.name}\nBestilt: ${new Date().toLocaleDateString("da-DK")}\n\n${MAIL_PUBLIC_BASE}\n\nSonorous Digital`,
      is_seed: true,
    });
  } else if (batch.seed_included) {
    // Make the gap visible in the file instead of silently dropping the seed.
    rows.push({
      slug: "seed-MISSING-ENV",
      recipient_name: "SÆT MAIL_SEED_NAME/STREET/ZIP/CITY",
      company_name: "Sonorous Digital",
      address_line: null,
      postal_code: null,
      city: null,
      country: "Danmark",
      letter_text: "Seed-adresse mangler i miljøvariablerne — udfyld rækken manuelt.",
      is_seed: true,
    });
  }

  const csv = batchToCsv(rows);
  const filename = `pensaki-${batch.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.csv`;
  return new NextResponse(csv, {
    headers: {
      "content-type": "text/csv; charset=utf-8",
      "content-disposition": `attachment; filename="${filename}"`,
      "cache-control": "no-store",
    },
  });
}
