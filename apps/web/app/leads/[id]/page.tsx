import Link from "next/link";
import { notFound } from "next/navigation";
import type { Tables } from "@/lib/database.types";
import { createClient } from "@/lib/supabase/server";
import { groupLabel } from "@/lib/branchekoder";
import {
  employeesLabel,
  formatDate,
  formatDKK,
  websiteNeedMeta,
  websiteQualityMeta,
  websiteSourceLabel,
} from "@/lib/leadmeta";
import {
  type AngleObjection,
  type ContactEnrichment,
  type FinancialEnrichment,
  type SocialEnrichment,
  type WebsiteEvidence,
  isEmpty,
  objections,
  view,
} from "@/lib/enrichment";
import {
  FACTOR_LABELS_DA,
  FACTOR_ORDER,
  formatDetail,
  parseBreakdown,
} from "@/lib/score-breakdown";
import { buildVoicemail, voicemailFirstName } from "@/lib/voicemail";
import { PipelineBadge, ScoreChip, WebsiteNeedBadge } from "../_components/Badge";
import PipelinePanel, {
  type FollowupView,
  type NoteView,
} from "./_components/PipelinePanel";

export const dynamic = "force-dynamic";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card card-pad">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-faint">{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  const empty = value === null || value === undefined || value === "";
  return (
    <div className="flex justify-between gap-4 border-b border-line/60 py-2 text-sm last:border-0">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-ink">{empty ? "—" : value}</dd>
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
    <div className="mt-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{label}</p>
      <p className="mt-0.5 whitespace-pre-wrap text-sm text-ink">{text}</p>
    </div>
  );
}

function Objections({ items }: { items: AngleObjection[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">Indvendinger</p>
      <dl className="mt-1.5 space-y-2">
        {items.map((o, i) => (
          <div
            key={`${o.objection_da}-${i}`}
            className="rounded-lg border border-brand-100 bg-white/60 p-2.5"
          >
            <dt className="text-sm font-medium text-ink">{o.objection_da}</dt>
            <dd className="mt-0.5 whitespace-pre-wrap text-sm text-muted">→ {o.response_da}</dd>
          </div>
        ))}
      </dl>
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
      <Link
        href="/leads"
        className="inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-brand-700"
      >
        ← Tilbage til leads
      </Link>

      <div className="mb-6 mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-semibold tracking-tight text-ink">{lead.company_name}</h1>
        <ScoreChip score={scoreRow?.total ?? lead.score} />
        <WebsiteNeedBadge need={lead.website_need} />
        <PipelineBadge status={lead.pipeline_status} />
      </div>

      {lead.suppressed && (
        <div className="mb-6 rounded-xl border border-rose-fg/30 bg-rose-bg p-4 text-sm text-rose-fg">
          <span className="font-semibold">Undertrykt — må ikke kontaktes.</span>{" "}
          {lead.suppression_reason === "robinson"
            ? "Indehaveren står på Robinsonlisten (frabedt sig markedsføring)."
            : "Dette lead er markeret som undertrykt."}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {angle && (
            <section className="overflow-hidden rounded-xl border border-brand-100 bg-gradient-to-br from-brand-50 to-brand-100/50 p-5 shadow-[var(--shadow-card)]">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-brand-800">
                  <span className="grid h-6 w-6 place-items-center rounded-md bg-brand-700 text-white">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
                      <path d="m13 2-9 11h6l-1 9 9-11h-6z" fill="currentColor" />
                    </svg>
                  </span>
                  Salgsvinkel
                </h2>
                <span className="text-xs text-brand-700">
                  {COMPETITOR_ANGLE_DA[angle.competitor_angle_type ?? ""] ?? ""}
                  {angle.competitor_name ? ` · ${angle.competitor_name}` : ""}
                  {angle.generated_at ? ` · ${formatDate(angle.generated_at)}` : ""}
                </span>
              </div>
              {angle.opening_line_da && (
                <blockquote className="border-l-2 border-brand-500 pl-3 text-base font-medium text-ink">
                  «{angle.opening_line_da}»
                </blockquote>
              )}
              <AnglePart label="Vinkel" text={angle.angle_da} />
              {angle.cta_da && (
                <div className="mt-4 rounded-lg border border-brand-200 bg-white/70 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                    Book mødet
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm font-medium text-ink">
                    «{angle.cta_da}»
                  </p>
                </div>
              )}
              <Objections items={objections(angle.objections)} />
              <AnglePart label="Resumé" text={angle.summary_da} />
              <AnglePart label="Svagheder" text={angle.weaknesses_da} />
            </section>
          )}

          <Section title="Telefonsvarer — ved intet svar">
            <blockquote className="whitespace-pre-wrap border-l-2 border-brand-500 pl-3 text-sm text-ink">
              {buildVoicemail({
                firstName: voicemailFirstName(contact.decision_makers ?? []),
                companyName: lead.company_name,
                websiteNeed: lead.website_need,
              })}
            </blockquote>
            <p className="mt-2 text-xs text-faint">
              Fast script — kun fornavn og årsag skifter. Et «JA» på SMS er deres egen
              henvendelse, så du må ringe (og skrive) tilbage.
            </p>
          </Section>

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
                <p className="text-sm text-rose-fg">
                  Udelukket fra scoring{breakdown.gate_reason ? ` (${breakdown.gate_reason})` : ""}.
                </p>
              ) : (
                <ul className="space-y-3.5">
                  {FACTOR_ORDER.filter((k) => breakdown.factors[k]).map((k) => {
                    const f = breakdown.factors[k];
                    const pct = f.max ? Math.round((f.points / f.max) * 100) : 0;
                    return (
                      <li key={k}>
                        <div className="flex justify-between text-sm">
                          <span className="text-ink">{FACTOR_LABELS_DA[k] ?? k}</span>
                          <span className="font-mono tabular-nums text-muted">
                            {f.points}/{f.max}
                          </span>
                        </div>
                        <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#edece6]">
                          <div
                            className="h-2 rounded-full bg-gradient-to-r from-brand-600 to-brand-500 transition-[width] duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        {f.detail && (
                          <p className="mt-1 text-xs text-faint">{formatDetail(f.detail)}</p>
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
                {lead.website_quality && (
                  <Field
                    label="Kvalitet"
                    value={
                      websiteQualityMeta(lead.website_quality)?.label ?? lead.website_quality
                    }
                  />
                )}
                {lead.website_source && (
                  <Field label="Kilde" value={websiteSourceLabel(lead.website_source)} />
                )}
                {web.discovery?.brand_name && (
                  <Field label="Butiksnavn" value={web.discovery.brand_name} />
                )}
                {lead.discovered_url && (
                  <Field
                    label="Fundet URL"
                    value={
                      <a
                        href={lead.discovered_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-brand-700 hover:underline"
                      >
                        {lead.discovered_url}
                      </a>
                    }
                  />
                )}
                {web.quality?.justification_da && (
                  <Field label="Kvalitetsnote" value={web.quality.justification_da} />
                )}
                {web.resolved?.url && (
                  <Field
                    label="URL"
                    value={
                      <a
                        href={web.resolved.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-brand-700 hover:underline"
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
                        className="text-brand-700 hover:underline"
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
              <ul className="space-y-2 text-sm">
                {contact.decision_makers.map((dm, i) => (
                  <li
                    key={`${dm.name}-${i}`}
                    className="flex justify-between gap-4 border-b border-line/60 pb-2 last:border-0 last:pb-0"
                  >
                    <span className="font-medium text-ink">{dm.name}</span>
                    <span className="text-muted">{dm.role}</span>
                  </li>
                ))}
              </ul>
            </Section>
          )}
        </div>

        <div className="space-y-6">
          <Section title="Kontakt">
            {lead.phone.length > 0 ? (
              <div className="space-y-2">
                {lead.phone.map((p) => (
                  <a
                    key={p}
                    href={`tel:${p.replace(/\s/g, "")}`}
                    className="flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-lg font-semibold text-brand-700 transition-colors hover:bg-brand-100"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                      <path
                        d="M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24 11.4 11.4 0 0 0 3.6.58 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.58 3.6a1 1 0 0 1-.24 1z"
                        fill="currentColor"
                      />
                    </svg>
                    {p}
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-sm text-faint">Intet telefonnummer</p>
            )}
            {lead.website && (
              <a
                href={lead.website}
                target="_blank"
                rel="noreferrer"
                className="mt-2 block break-all text-sm text-brand-700 hover:underline"
              >
                {lead.website}
              </a>
            )}
            {lead.email && <p className="mt-1 break-all text-sm text-muted">{lead.email}</p>}
            <p className="mt-3 text-xs text-faint">
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
