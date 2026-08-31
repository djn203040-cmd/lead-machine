import Link from "next/link";
import { GROUP_OPTIONS, codesInGroup, displayBranche, groupLabel } from "@/lib/branchekoder";
import type { Tables } from "@/lib/database.types";
import { formatDate } from "@/lib/leadmeta";
import { pickRecipient } from "@/lib/mail/enqueue";
import { MAIL_ARM_META, MAIL_PUBLIC_BASE, type MailArm } from "@/lib/mail/letter";
import { createClient } from "@/lib/supabase/server";
import BatchPanel, { type BatchView } from "./_components/BatchPanel";
import CandidatePicker, { type Candidate } from "./_components/CandidatePicker";
import CreateBatchForm from "./_components/CreateBatchForm";
import MailCard, { type MailView } from "./_components/MailCard";

export const dynamic = "force-dynamic";

const TABS = [
  { key: "queue", label: "Til gennemsyn" },
  { key: "ready", label: "Klar til batch" },
  { key: "batches", label: "Batches" },
  { key: "scans", label: "Scanninger" },
  { key: "candidates", label: "Find modtagere" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

function first(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

type MailRow = Tables<"lead_mail"> & { leads: { pipeline_status: string; branchekode: string | null; website: string | null } | null };
type ScanRow = Tables<"mail_scans"> & { lead_mail: { company_name: string; arm: string; lead_id: string } | null };

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="card px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-faint">{label}</p>
      <p className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${tone ?? "text-ink"}`}>{value}</p>
    </div>
  );
}

export default async function MailPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await searchParams;
  const tabParam = first(sp.tab);
  const tab: TabKey = (TABS.some((t) => t.key === tabParam) ? tabParam : "queue") as TabKey;
  const group = first(sp.group);
  const candArm = (["A", "B", "C"].includes(first(sp.arm)) ? first(sp.arm) : "C") as MailArm;

  const supabase = await createClient();

  // Counts for the header — cheap, one round trip each.
  const statuses = ["draft", "approved", "batched", "ordered", "sent", "rejected"] as const;
  const countRes = await Promise.all(
    statuses.map((s) =>
      supabase.from("lead_mail").select("id", { count: "exact", head: true }).eq("status", s),
    ),
  );
  const counts = Object.fromEntries(statuses.map((s, i) => [s, countRes[i].count ?? 0])) as Record<
    (typeof statuses)[number],
    number
  >;
  const { count: scannedCount } = await supabase
    .from("lead_mail")
    .select("id", { count: "exact", head: true })
    .gt("scan_count", 0);
  const outCount = counts.ordered + counts.sent;

  const mailSelect = "*, leads(pipeline_status, branchekode, website)";

  let queue: MailView[] = [];
  let ready: MailView[] = [];
  let batches: BatchView[] = [];
  let scans: ScanRow[] = [];
  let candidates: Candidate[] = [];

  const toView = (m: MailRow): MailView => ({
    id: m.id,
    lead_id: m.lead_id,
    arm: m.arm as MailArm,
    status: m.status,
    slug: m.slug,
    recipient_name: m.recipient_name,
    first_name: m.first_name,
    company_name: m.company_name,
    address_line: m.address_line,
    postal_code: m.postal_code,
    city: m.city,
    country: m.country,
    observation_text: m.observation_text,
    focus_text: m.focus_text,
    letter_text: m.letter_text,
    letter_chars: m.letter_chars,
    reject_reason: m.reject_reason,
    landing_video_url: m.landing_video_url,
    landing_headline: m.landing_headline,
    scan_count: m.scan_count,
    first_scanned_at: m.first_scanned_at,
    opted_out_at: m.opted_out_at,
    created_at: m.created_at,
    website: m.leads?.website ?? null,
    branche: groupLabel(m.leads?.branchekode ?? null),
  });

  if (tab === "queue") {
    const { data } = await supabase
      .from("lead_mail")
      .select(mailSelect)
      .in("status", ["draft", "rejected"])
      .order("status", { ascending: false }) // draft before rejected
      .order("created_at", { ascending: true })
      .returns<MailRow[]>();
    queue = (data ?? []).map(toView);
  } else if (tab === "ready") {
    const { data } = await supabase
      .from("lead_mail")
      .select(mailSelect)
      .eq("status", "approved")
      .order("created_at", { ascending: true })
      .returns<MailRow[]>();
    ready = (data ?? []).map(toView);
  } else if (tab === "batches") {
    const [bRes, mRes] = await Promise.all([
      supabase.from("mail_batches").select("*").order("created_at", { ascending: false }),
      supabase.from("lead_mail").select(mailSelect).not("batch_id", "is", null).order("company_name"),
    ]);
    const b = (bRes.data ?? []) as Tables<"mail_batches">[];
    const m = (mRes.data ?? []) as unknown as MailRow[];
    const byBatch = new Map<string, MailView[]>();
    for (const row of m) {
      if (!row.batch_id) continue;
      const list = byBatch.get(row.batch_id) ?? [];
      list.push(toView(row));
      byBatch.set(row.batch_id, list);
    }
    batches = b.map((bt) => ({ ...bt, letters: byBatch.get(bt.id) ?? [] }));
  } else if (tab === "scans") {
    const { data } = await supabase
      .from("mail_scans")
      .select("*, lead_mail(company_name, arm, lead_id)")
      .order("scanned_at", { ascending: false })
      .limit(200)
      .returns<ScanRow[]>();
    scans = data ?? [];
  } else if (tab === "candidates") {
    // Arm C pool: enriched, mailable-looking leads never contacted, without a
    // live letter. The hard legal filters run again at enqueue — this list is
    // just a pre-filter so the picker isn't full of obvious rejects.
    let q = supabase
      .from("leads")
      .select(
        "id, company_name, address, postal_code, city, branchekode, branche_text, employees_band, employees_exact, score, pipeline_status, is_sole_trader, website, website_need",
      )
      .eq("is_archived", false)
      .eq("suppressed", false)
      .eq("reklamebeskyttet", false)
      .eq("enrichment_status", "enriched")
      .not("address", "is", null)
      .not("postal_code", "is", null);
    if (candArm === "C") q = q.in("pipeline_status", ["new", "enriched", "qualified"]);
    else if (candArm === "B") q = q.eq("pipeline_status", "lost");
    if (group) q = q.in("branchekode", codesInGroup(group));
    const { data: leadsData } = await q.order("score", { ascending: false, nullsFirst: false }).limit(200);
    const leads = (leadsData ?? []) as unknown as Pick<
      Tables<"leads">,
      | "id" | "company_name" | "address" | "postal_code" | "city" | "branchekode" | "branche_text"
      | "employees_band" | "employees_exact" | "score" | "pipeline_status" | "is_sole_trader" | "website" | "website_need"
    >[];
    const ids = leads.map((l) => l.id);
    const [{ data: existing }, { data: calls }, { data: contacts }] = ids.length
      ? await Promise.all([
          supabase.from("lead_mail").select("lead_id, status").in("lead_id", ids).not("status", "in", "(rejected,cancelled)"),
          supabase.from("lead_calls").select("lead_id, outcome").in("lead_id", ids),
          supabase.from("lead_enrichment").select("lead_id, contact").in("lead_id", ids),
        ])
      : [{ data: [] }, { data: [] }, { data: [] }];
    const hasMail = new Set(((existing ?? []) as { lead_id: string }[]).map((r) => r.lead_id));
    const callsBy = new Map<string, string[]>();
    for (const c of (calls ?? []) as { lead_id: string; outcome: string }[]) {
      callsBy.set(c.lead_id, [...(callsBy.get(c.lead_id) ?? []), c.outcome]);
    }
    const contactBy = new Map(
      ((contacts ?? []) as { lead_id: string; contact: unknown }[]).map((c) => [c.lead_id, c.contact]),
    );
    candidates = leads
      .filter((l) => !hasMail.has(l.id))
      .filter((l) => {
        const outcomes = callsBy.get(l.id) ?? [];
        if (candArm === "C") return outcomes.length === 0;
        if (candArm === "A") return outcomes.includes("no_answer") && !outcomes.some((o) => o !== "no_answer");
        return true;
      })
      .map((l) => ({
        id: l.id,
        company_name: l.company_name,
        address: [l.address, [l.postal_code, l.city].filter(Boolean).join(" ")].filter(Boolean).join(", "),
        branche: displayBranche(l.branchekode, l.branche_text),
        score: l.score,
        recipient: pickRecipient(contactBy.get(l.id)),
        is_sole_trader: l.is_sole_trader,
        website: l.website,
        website_need: l.website_need,
      }));
  }

  const tabHref = (t: TabKey) => (t === "queue" ? "/leads/mail" : `/leads/mail?tab=${t}`);
  const tabClass = (active: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
      active ? "bg-brand-600 text-white shadow-sm" : "text-muted hover:text-ink"
    }`;
  const badge = (n: number) =>
    n > 0 ? <span className="ml-1.5 rounded-full bg-black/10 px-1.5 text-[11px] tabular-nums">{n}</span> : null;

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Breve</h1>
          <p className="mt-1 text-sm text-muted">
            Håndskrevne breve (Pensaki) til beslutningstagere — udløst af opkald eller valgt koldt.
            Hvert brev bærer sin egen side: <span className="font-mono">{MAIL_PUBLIC_BASE}/&lt;firma&gt;</span>.
          </p>
        </div>
        <Link href="/leads/mail?tab=candidates" className="btn btn-primary">
          + Find modtagere
        </Link>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Til gennemsyn" value={counts.draft} tone={counts.draft ? "text-amber-fg" : undefined} />
        <Stat label="Godkendt" value={counts.approved} tone={counts.approved >= 10 ? "text-teal-fg" : undefined} />
        <Stat label="I batch" value={counts.batched} />
        <Stat label="Sendt / bestilt" value={outCount} />
        <Stat
          label="Scannet"
          value={outCount ? `${scannedCount ?? 0} · ${Math.round(((scannedCount ?? 0) / outCount) * 100)}%` : scannedCount ?? 0}
          tone={(scannedCount ?? 0) > 0 ? "text-brand-700" : undefined}
        />
        <Stat label="Afvist (filter)" value={counts.rejected} tone="text-muted" />
      </div>

      <div className="mb-5 inline-flex flex-wrap gap-1 rounded-xl border border-line bg-card p-1">
        {TABS.map((t) => (
          <Link key={t.key} href={tabHref(t.key)} className={tabClass(tab === t.key)}>
            {t.label}
            {t.key === "queue" ? badge(counts.draft) : t.key === "ready" ? badge(counts.approved) : null}
          </Link>
        ))}
      </div>

      {tab === "queue" && (
        <section className="space-y-3">
          {queue.length === 0 ? (
            <div className="card card-pad text-sm text-muted">
              Ingen breve til gennemsyn. Breve kommer hertil fra powerdialeren (Intet svar → arm A, Ikke interesseret →
              arm B) eller fra <Link href="/leads/mail?tab=candidates" className="text-brand-700 underline">Find modtagere</Link>.
            </div>
          ) : (
            <>
              <p className="text-xs text-muted">
                Gennemlæs observationen mod virkeligheden før du godkender — en forkert observation er værre end ingen.
                Godkendelse fryser brevteksten.
              </p>
              {queue.map((m) => (
                <MailCard key={m.id} mail={m} />
              ))}
            </>
          )}
        </section>
      )}

      {tab === "ready" && (
        <section className="space-y-3">
          <CreateBatchForm approvedCount={ready.length} />
          {ready.map((m) => (
            <MailCard key={m.id} mail={m} compact />
          ))}
          {ready.length === 0 && (
            <div className="card card-pad text-sm text-muted">Ingen godkendte breve endnu.</div>
          )}
        </section>
      )}

      {tab === "batches" && (
        <section className="space-y-4">
          {batches.length === 0 ? (
            <div className="card card-pad text-sm text-muted">Ingen batches endnu — opret én fra „Klar til batch“ når der ligger 10+ godkendte breve.</div>
          ) : (
            batches.map((b) => <BatchPanel key={b.id} batch={b} />)
          )}
        </section>
      )}

      {tab === "scans" && (
        <section className="card overflow-hidden">
          {scans.length === 0 ? (
            <div className="card-pad text-sm text-muted">Ingen scanninger endnu. Hver åbning af en brev-side logges her — det er kanalens primære måling.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-canvas text-left text-xs uppercase tracking-wide text-faint">
                  <tr>
                    <th className="px-4 py-2">Tidspunkt</th>
                    <th className="px-4 py-2">Virksomhed</th>
                    <th className="px-4 py-2">Arm</th>
                    <th className="px-4 py-2">Side</th>
                    <th className="px-4 py-2">Enhed</th>
                    <th className="px-4 py-2">Referrer</th>
                  </tr>
                </thead>
                <tbody>
                  {scans.map((s) => (
                    <tr key={s.id} className="border-t border-line/60">
                      <td className="px-4 py-2 tabular-nums text-muted">
                        {new Date(s.scanned_at).toLocaleString("da-DK", { dateStyle: "short", timeStyle: "short" })}
                      </td>
                      <td className="px-4 py-2 font-medium text-ink">
                        {s.lead_mail ? (
                          <Link href={`/leads/${s.lead_mail.lead_id}`} className="hover:underline">
                            {s.lead_mail.company_name}
                          </Link>
                        ) : "—"}
                      </td>
                      <td className="px-4 py-2">
                        {s.lead_mail ? <span className={`chip ${MAIL_ARM_META[s.lead_mail.arm as MailArm]?.className}`}>{s.lead_mail.arm}</span> : "—"}
                      </td>
                      <td className="px-4 py-2 font-mono text-xs">/{s.slug}</td>
                      <td className="px-4 py-2 text-muted">{s.device ?? "—"}</td>
                      <td className="max-w-[16rem] truncate px-4 py-2 text-muted">{s.referrer ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === "candidates" && (
        <section className="space-y-3">
          <div className="card card-pad flex flex-wrap items-end gap-3">
            <form className="flex flex-wrap items-end gap-3" method="get">
              <input type="hidden" name="tab" value="candidates" />
              <label className="text-xs text-muted">
                Arm
                <select name="arm" defaultValue={candArm} className="select mt-1 block">
                  {(["C", "A", "B"] as const).map((a) => (
                    <option key={a} value={a}>{MAIL_ARM_META[a].label} — {MAIL_ARM_META[a].trigger}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-muted">
                Branche
                <select name="group" defaultValue={group} className="select mt-1 block">
                  <option value="">Alle brancher</option>
                  {GROUP_OPTIONS.map((g) => (
                    <option key={g.value} value={g.value}>{g.label}</option>
                  ))}
                </select>
              </label>
              <button className="btn btn-secondary" type="submit">Vis</button>
            </form>
            <p className="ml-auto max-w-md text-xs text-muted">
              Listen er forfiltreret (beriget, adresse, ikke reklamebeskyttet, ikke undertrykt, intet aktivt brev). De tre
              lovpligtige filtre kører igen når du sætter i kø — afviste får en årsag.
            </p>
          </div>
          <CandidatePicker candidates={candidates} arm={candArm} />
        </section>
      )}

      <p className="mt-8 text-xs text-faint">
        Sidst opdateret {formatDate(new Date().toISOString())} · A4 650 tegn · min. 10 breve pr. ordre · ~2 uger fra ordre til postkasse.
      </p>
    </div>
  );
}
