import Link from "next/link";
import { notFound } from "next/navigation";
import type { Tables } from "@/lib/database.types";
import { createClient } from "@/lib/supabase/server";
import { groupLabel } from "@/lib/branchekoder";
import { employeesLabel, formatDate, formatDKK, websiteNeedMeta } from "@/lib/leadmeta";
import {
  type ContactEnrichment,
  type FinancialEnrichment,
  type SocialEnrichment,
  type WebsiteEvidence,
  isEmpty,
  view,
} from "@/lib/enrichment";
import {
  FACTOR_LABELS_DA,
  FACTOR_ORDER,
  formatDetail,
  parseBreakdown,
} from "@/lib/score-breakdown";
import { PipelineBadge, ScoreChip, WebsiteNeedBadge } from "../_components/Badge";
import PipelinePanel, {
  type FollowupView,
  type NoteView,
} from "./_components/PipelinePanel";

export const dynamic = "force-dynamic";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded border bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold text-gray-700">{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  const empty = value === null || value === undefined || value === "";
  return (
    <div className="flex justify-between gap-4 py-1 text-sm">
      <dt className="text-gray-500">{label}</dt>
      <dd className="text-right text-gray-900">{empty ? "—" : value}</dd>
    </div>
  );
}

function yesNo(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "Ja" : "Nej";
}

const COMPETITOR_ANGLE_DA: Record<string, string> = {
  fomo: "FOMO — konkurrenter er mere synlige",
  first_mover: "First mover — vær først/bedst lokalt",
};

function AnglePart({ label, text }: { label: string; text: string | null }) {
  if (!text) return null;
  return (
    <div className="mt-2">
      <p className="text-xs font-medium uppercase tracking-wide text-emerald-800">{label}</p>
      <p className="text-sm whitespace-pre-wrap text-gray-800">{text}</p>
    </div>
  );
}

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const [leadRes, enrichRes, scoreRes, angleRes, notesRes, followupsRes] = await Promise.all([
    supabase.from("leads").select("*").eq("id", id).maybeSingle(),
    supabase.from("lead_enrichment").select("*").eq("lead_id", id).maybeSingle(),
    supabase.from("lead_scores").select("*").eq("lead_id", id).maybeSingle(),
    supabase.from("lead_angles").select("*").eq("lead_id", id).maybeSingle(),
    supabase
      .from("lead_notes")
      .select("id, body, created_at")
      .eq("lead_id", id)
      .order("created_at", { ascending: false }),
    supabase
      .from("lead_followups")
      .select("id, follow_up_date, reminder_sent")
      .eq("lead_id", id)
      .order("follow_up_date", { ascending: true }),
  ]);

  // supabase-js 2.108 infers these typed-client results as `never`; assert the
  // generated Row types (same reason the list query uses `.returns<>()`).
  const lead = leadRes.data as Tables<"leads"> | null;
  if (!lead) notFound();

  const enrichment = enrichRes.data as Tables<"lead_enrichment"> | null;
  const scoreRow = scoreRes.data as Tables<"lead_scores"> | null;
  const angle = angleRes.data as Tables<"lead_angles"> | null;
  const breakdown = parseBreakdown(scoreRow?.breakdown);
  const notes = (notesRes.data ?? []) as NoteView[];
  const followups = (followupsRes.data ?? []) as FollowupView[];

  const web = view<WebsiteEvidence>(enrichment?.website);
  const fin = view<FinancialEnrichment>(enrichment?.financial);
  const social = view<SocialEnrichment>(enrichment?.social);
  const contact = view<ContactEnrichment>(enrichment?.contact);

  const address = [lead.address, [lead.postal_code, lead.city].filter(Boolean).join(" ")]
    .filter(Boolean)
    .join(", ");

  return (
    <div>
      <Link href="/leads" className="text-sm text-gray-500 hover:underline">
        ← Tilbage til leads
      </Link>

      <div className="mb-6 mt-2 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{lead.company_name}</h1>
        <ScoreChip score={scoreRow?.total ?? lead.score} />
        <WebsiteNeedBadge need={lead.website_need} />
        <PipelineBadge status={lead.pipeline_status} />
      </div>

      {lead.suppressed && (
        <div className="mb-6 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          <span className="font-semibold">Undertrykt — må ikke kontaktes.</span>{" "}
          {lead.suppression_reason === "robinson"
            ? "Indehaveren står på Robinsonlisten (frabedt sig markedsføring)."
            : "Dette lead er markeret som undertrykt."}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {angle && (
            <section className="rounded border border-emerald-200 bg-emerald-50 p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-emerald-900">Salgsvinkel</h2>
                <span className="text-xs text-emerald-700">
                  {COMPETITOR_ANGLE_DA[angle.competitor_angle_type ?? ""] ?? ""}
                  {angle.competitor_name ? ` · ${angle.competitor_name}` : ""}
                  {angle.generated_at ? ` · ${formatDate(angle.generated_at)}` : ""}
                </span>
              </div>
              {angle.opening_line_da && (
                <blockquote className="border-l-2 border-emerald-400 pl-3 text-base font-medium text-gray-900">
                  «{angle.opening_line_da}»
                </blockquote>
              )}
              <AnglePart label="Resumé" text={angle.summary_da} />
              <AnglePart label="Vinkel" text={angle.angle_da} />
              <AnglePart label="Svagheder" text={angle.weaknesses_da} />
            </section>
          )}

          <Section title="Virksomhedsdata">
            <dl>
              <Field label="CVR-nummer" value={lead.cvr_number} />
              <Field label="Adresse" value={address} />
              <Field label="Kommune" value={lead.kommune} />
              <Field label="Branche" value={lead.branche_text ?? groupLabel(lead.branchekode)} />
              <Field label="Branchekode" value={lead.branchekode} />
              <Field label="Ansatte" value={employeesLabel(lead.employees_band, lead.employees_exact)} />
              <Field label="Stiftet" value={formatDate(lead.founded_at)} />
              <Field label="Virksomhedsform" value={lead.company_form} />
              <Field label="CVR-status" value={lead.cvr_status} />
              {lead.is_sole_trader && <Field label="Type" value="Enkeltmandsvirksomhed" />}
            </dl>
          </Section>

          {breakdown && (
            <Section title="Score-forklaring">
              {breakdown.gated ? (
                <p className="text-sm text-rose-700">
                  Udelukket fra scoring{breakdown.gate_reason ? ` (${breakdown.gate_reason})` : ""}.
                </p>
              ) : (
                <ul className="space-y-3">
                  {FACTOR_ORDER.filter((k) => breakdown.factors[k]).map((k) => {
                    const f = breakdown.factors[k];
                    const pct = f.max ? Math.round((f.points / f.max) * 100) : 0;
                    return (
                      <li key={k}>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-700">{FACTOR_LABELS_DA[k] ?? k}</span>
                          <span className="tabular-nums text-gray-500">
                            {f.points}/{f.max}
                          </span>
                        </div>
                        <div className="mt-1 h-2 rounded bg-gray-100">
                          <div
                            className="h-2 rounded bg-emerald-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        {f.detail && (
                          <p className="mt-0.5 text-xs text-gray-400">{formatDetail(f.detail)}</p>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </Section>
          )}

          {!isEmpty(enrichment?.website) && (
            <Section title="Hjemmesidevurdering">
              <dl>
                <Field label="Vurdering" value={websiteNeedMeta(lead.website_need).label} />
                {web.resolved?.url && (
                  <Field
                    label="URL"
                    value={
                      <a
                        href={web.resolved.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        {web.resolved.url}
                      </a>
                    }
                  />
                )}
                {web.signals && (
                  <>
                    <Field label="Mobilvenlig (viewport)" value={yesNo(web.signals.has_viewport)} />
                    <Field label="HTTPS" value={yesNo(web.signals.has_https)} />
                    <Field label="Forældet markup" value={yesNo(web.signals.legacy_markup)} />
                    {web.signals.cms && <Field label="CMS" value={web.signals.cms} />}
                    {web.signals.copyright_year && (
                      <Field label="Copyright-år" value={web.signals.copyright_year} />
                    )}
                  </>
                )}
                {typeof web.pagespeed?.performance === "number" && (
                  <Field label="PageSpeed (mobil)" value={web.pagespeed.performance} />
                )}
                {web.reasons && web.reasons.length > 0 && (
                  <Field label="Signaler" value={web.reasons.join(", ")} />
                )}
              </dl>
            </Section>
          )}

          {!isEmpty(enrichment?.financial) && (
            <Section title="Økonomi">
              <dl>
                <Field label="Bruttofortjeneste" value={formatDKK(fin.gross_profit)} />
                <Field label="Årets resultat" value={formatDKK(fin.profit_loss)} />
                <Field label="Egenkapital" value={formatDKK(fin.equity)} />
                {fin.revenue_estimate?.value !== undefined && (
                  <Field
                    label="Omsætning (est.)"
                    value={`${formatDKK(fin.revenue_estimate.value)}${
                      fin.revenue_estimate.confidence ? ` · ${fin.revenue_estimate.confidence}` : ""
                    }`}
                  />
                )}
                {fin.period?.end && <Field label="Regnskabsperiode" value={fin.period.end} />}
              </dl>
            </Section>
          )}

          {!isEmpty(enrichment?.social) && (
            <Section title="Online tilstedeværelse">
              <dl>
                <Field label="Facebook-side" value={yesNo(social.has_fb_page)} />
                {social.fb_url && (
                  <Field
                    label="Facebook"
                    value={
                      <a
                        href={social.fb_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Profil
                      </a>
                    }
                  />
                )}
                <Field label="Meta Pixel" value={yesNo(social.has_meta_pixel)} />
              </dl>
            </Section>
          )}

          {contact.decision_makers && contact.decision_makers.length > 0 && (
            <Section title="Beslutningstagere">
              <ul className="space-y-1 text-sm">
                {contact.decision_makers.map((dm, i) => (
                  <li key={`${dm.name}-${i}`} className="flex justify-between gap-4">
                    <span className="text-gray-900">{dm.name}</span>
                    <span className="text-gray-500">{dm.role}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        <div className="space-y-6">
          <Section title="Kontakt">
            {lead.phone.length > 0 ? (
              <div className="space-y-1">
                {lead.phone.map((p) => (
                  <a
                    key={p}
                    href={`tel:${p.replace(/\s/g, "")}`}
                    className="block text-lg font-semibold text-emerald-700 hover:underline"
                  >
                    {p}
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">Intet telefonnummer</p>
            )}
            {lead.website && (
              <a
                href={lead.website}
                target="_blank"
                rel="noreferrer"
                className="mt-2 block break-all text-sm text-blue-600 hover:underline"
              >
                {lead.website}
              </a>
            )}
            {lead.email && <p className="mt-1 break-all text-sm text-gray-500">{lead.email}</p>}
            <p className="mt-3 text-xs text-gray-400">
              Telefon-først — Markedsføringsloven §10 forbyder kold B2B-email uden samtykke.
            </p>
          </Section>

          <Section title="Pipeline">
            <PipelinePanel
              leadId={lead.id}
              status={lead.pipeline_status}
              notes={notes}
              followups={followups}
            />
          </Section>
        </div>
      </div>
    </div>
  );
}
