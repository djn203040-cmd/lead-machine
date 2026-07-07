"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { groupLabel } from "@/lib/branchekoder";
import {
  type ContactEnrichment,
  type FinancialEnrichment,
  view,
} from "@/lib/enrichment";
import { employeesLabel, formatDKK, pipelineMeta, websiteNeedMeta } from "@/lib/leadmeta";
import { logOutcome, saveNote, scheduleFollowup } from "../actions";

export type DialerAngle = {
  opening_line_da: string | null;
  summary_da: string | null;
  angle_da: string | null;
  weaknesses_da: string | null;
  competitor_angle_type: string | null;
  competitor_name: string | null;
};

export type DialerLead = {
  id: string;
  company_name: string;
  phone: string[];
  website: string | null;
  email: string | null;
  address: string | null;
  postal_code: string | null;
  city: string | null;
  kommune: string | null;
  cvr_number: string | null;
  branche_text: string | null;
  branchekode: string | null;
  employees_band: string | null;
  employees_exact: number | null;
  company_form: string | null;
  founded_at: string | null;
  is_sole_trader: boolean;
  website_need: string;
  pipeline_status: string;
  score: number | null;
  angle: DialerAngle | null;
  financial: unknown;
  contact: unknown;
};

const COMPETITOR_ANGLE_DA: Record<string, string> = {
  fomo: "FOMO — konkurrenter er mere synlige",
  first_mover: "First mover — vær først/bedst lokalt",
};

// Outcome buttons — each moves the pipeline forward and advances to the next lead.
const OUTCOMES = [
  { status: "contacted", label: "Kontaktet", tone: "cyan" },
  { status: "meeting_booked", label: "Møde booket", tone: "teal" },
  { status: "lost", label: "Ikke interesseret", tone: "rose" },
  { status: "discarded", label: "Kassér", tone: "neutral" },
] as const;

const OUTCOME_BTN: Record<string, string> = {
  cyan: "border-cyan-fg/25 bg-cyan-bg text-cyan-fg hover:border-cyan-fg/50",
  teal: "border-teal-fg/25 bg-teal-bg text-teal-fg hover:border-teal-fg/50",
  rose: "border-rose-fg/25 bg-rose-bg text-rose-fg hover:border-rose-fg/50",
  neutral: "border-line-strong bg-canvas text-muted hover:border-faint",
};

function telHref(p: string) {
  return `tel:${p.replace(/[^\d+]/g, "")}`;
}

function AnglePart({ label, text }: { label: string; text: string | null | undefined }) {
  if (!text) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{label}</p>
      <p className="mt-0.5 whitespace-pre-wrap text-sm text-ink">{text}</p>
    </div>
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

export default function Dialer({ queue }: { queue: DialerLead[] }) {
  const [index, setIndex] = useState(0);
  // Leads handled this session — greyed out in the rail, skipped by "next unhandled".
  const [handled, setHandled] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [date, setDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const total = queue.length;
  const lead = queue[index] as DialerLead | undefined;

  const go = useCallback(
    (dir: 1 | -1) => {
      setError(null);
      setNote("");
      setDate("");
      setIndex((i) => Math.min(total - 1, Math.max(0, i + dir)));
    },
    [total],
  );

  const run = useCallback(
    (action: () => Promise<{ error?: string }>, onOk?: () => void) => {
      setError(null);
      startTransition(async () => {
        const res = await action();
        if (res.error) setError(res.error);
        else onOk?.();
      });
    },
    [],
  );

  // Record an outcome, then jump to the next not-yet-handled lead.
  const recordOutcome = useCallback(
    (status: string, statusLabel: string) => {
      if (!lead) return;
      const leadId = lead.id;
      const noteText = note;
      run(
        () => logOutcome(leadId, status, noteText),
        () => {
          setHandled((h) => ({ ...h, [leadId]: statusLabel }));
          setNote("");
          setDate("");
          // Advance to the next lead in the queue after logging the outcome.
          setIndex((i) => Math.min(total - 1, i + 1));
        },
      );
    },
    [lead, note, run, total],
  );

  // Handled-lead ids, for the ✓ badge on already-actioned leads.
  const handledRef = useMemo(() => new Set(Object.keys(handled)), [handled]);

  // Keyboard: ←/→ navigate. Ignore while typing in a field.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement | null;
      if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        go(-1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go]);

  if (!lead) {
    return (
      <div className="card flex flex-col items-center gap-3 px-6 py-16 text-center">
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-700">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
            <path
              d="M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24 11.4 11.4 0 0 0 3.6.58 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.58 3.6a1 1 0 0 1-.24 1z"
              fill="currentColor"
            />
          </svg>
        </span>
        <h2 className="text-lg font-semibold text-ink">Ingen leads i ringelisten</h2>
        <p className="max-w-sm text-sm text-muted">
          Ingen berigede virksomheder med telefonnummer matcher filtret. Find flere
          virksomheder eller berig eksisterende leads.
        </p>
        <Link href="/leads" className="btn btn-primary mt-1">
          Til leads
        </Link>
      </div>
    );
  }

  const fin = view<FinancialEnrichment>(lead.financial);
  const contact = view<ContactEnrichment>(lead.contact);
  const decisionMakers = contact.decision_makers ?? [];
  const angle = lead.angle;
  const branche = lead.branche_text ?? groupLabel(lead.branchekode) ?? "—";
  const address = [lead.address, [lead.postal_code, lead.city].filter(Boolean).join(" ")]
    .filter(Boolean)
    .join(", ");
  const need = websiteNeedMeta(lead.website_need);
  const currentStatus = handled[lead.id] ?? pipelineMeta(lead.pipeline_status).label;
  const hasFinancial =
    typeof fin.gross_profit === "number" ||
    typeof fin.profit_loss === "number" ||
    typeof fin.equity === "number" ||
    fin.revenue_estimate?.value !== undefined;

  return (
    <div>
      {/* Progress + navigation */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="chip chip-brand text-[0.8rem]">
            Lead {index + 1} / {total}
          </span>
          {handledRef.has(lead.id) && (
            <span className="chip chip-teal text-[0.8rem]">✓ {handled[lead.id]}</span>
          )}
          <span className="hidden text-xs text-faint sm:inline">
            Brug ← → for at skifte lead
          </span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={index === 0}
            className="btn btn-secondary"
          >
            ← Forrige
          </button>
          <button
            type="button"
            onClick={() => go(1)}
            disabled={index >= total - 1}
            className="btn btn-secondary"
          >
            Spring over →
          </button>
        </div>
      </div>

      <div className="mb-6 h-1.5 overflow-hidden rounded-full bg-[#edece6]">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-600 to-brand-500 transition-[width] duration-300"
          style={{ width: `${((index + 1) / total) * 100}%` }}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: who + why (the pitch) */}
        <div className="space-y-6 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight text-ink">
              {lead.company_name}
            </h1>
            {typeof lead.score === "number" && (
              <span className="inline-flex min-w-9 items-center justify-center rounded-lg bg-gradient-to-b from-brand-700 to-brand px-2.5 py-1 font-mono text-sm font-semibold tabular-nums text-white shadow-sm">
                {lead.score}
              </span>
            )}
            <span className={`chip ${need.className}`}>{need.label}</span>
          </div>
          <p className="-mt-3 text-sm text-muted">
            {branche} · {lead.city ?? lead.kommune ?? "—"} ·{" "}
            {employeesLabel(lead.employees_band, lead.employees_exact)} ansatte
          </p>

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
                </span>
              </div>
              {angle.opening_line_da && (
                <blockquote className="border-l-2 border-brand-500 pl-3 text-base font-medium text-ink">
                  «{angle.opening_line_da}»
                </blockquote>
              )}
              <AnglePart label="Resumé" text={angle.summary_da} />
              <AnglePart label="Vinkel" text={angle.angle_da} />
              <AnglePart label="Svagheder" text={angle.weaknesses_da} />
            </section>
          )}

          <section className="card card-pad">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-faint">
              Virksomhedsdata
            </h2>
            <dl>
              <Field label="CVR-nummer" value={lead.cvr_number} />
              <Field label="Adresse" value={address} />
              <Field label="Kommune" value={lead.kommune} />
              <Field label="Branche" value={branche} />
              <Field
                label="Ansatte"
                value={employeesLabel(lead.employees_band, lead.employees_exact)}
              />
              <Field label="Virksomhedsform" value={lead.company_form} />
              {lead.is_sole_trader && <Field label="Type" value="Enkeltmandsvirksomhed" />}
            </dl>
          </section>

          {hasFinancial && (
            <section className="card card-pad">
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-faint">
                Økonomi
              </h2>
              <dl>
                <Field label="Bruttofortjeneste" value={formatDKK(fin.gross_profit)} />
                <Field label="Årets resultat" value={formatDKK(fin.profit_loss)} />
                <Field label="Egenkapital" value={formatDKK(fin.equity)} />
                {fin.revenue_estimate?.value !== undefined && (
                  <Field
                    label="Omsætning (est.)"
                    value={formatDKK(fin.revenue_estimate.value)}
                  />
                )}
              </dl>
            </section>
          )}

          {decisionMakers.length > 0 && (
            <section className="card card-pad">
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-faint">
                Beslutningstagere
              </h2>
              <ul className="space-y-2 text-sm">
                {decisionMakers.map((dm, i) => (
                  <li
                    key={`${dm.name}-${i}`}
                    className="flex justify-between gap-4 border-b border-line/60 pb-2 last:border-0 last:pb-0"
                  >
                    <span className="font-medium text-ink">{dm.name}</span>
                    <span className="text-muted">{dm.role}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        {/* Right: the call panel (sticky) */}
        <div className="space-y-6">
          <div className="lg:sticky lg:top-24 space-y-6">
            <section className="card card-pad">
              <h2 className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-faint">
                Ring nu
                <span className="chip chip-neutral normal-case">{currentStatus}</span>
              </h2>
              {lead.phone.length > 0 ? (
                <div className="space-y-2">
                  {lead.phone.map((p) => (
                    <a
                      key={p}
                      href={telHref(p)}
                      className="flex items-center justify-center gap-2.5 rounded-xl bg-gradient-to-b from-brand-700 to-brand px-4 py-3.5 text-2xl font-semibold tabular-nums tracking-tight text-white shadow-[var(--shadow-card)] transition-transform hover:-translate-y-0.5"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
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
                  className="mt-3 block break-all text-sm text-brand-700 hover:underline"
                >
                  {lead.website}
                </a>
              )}
              {lead.email && (
                <p className="mt-1 break-all text-sm text-muted">{lead.email}</p>
              )}
              <p className="mt-3 text-xs text-faint">
                Telefon-først — Markedsføringsloven §10 forbyder kold B2B-email uden samtykke.
              </p>
            </section>

            <section className="card card-pad">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">
                Note fra samtalen
              </h2>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Hvad blev sagt?"
                rows={2}
                className="textarea"
              />
              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  disabled={pending || !note.trim()}
                  onClick={() =>
                    run(() => saveNote(lead.id, note), () => setNote(""))
                  }
                  className="btn btn-secondary"
                >
                  Gem note
                </button>
              </div>

              <h2 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-faint">
                Registrér udfald
              </h2>
              <div className="grid grid-cols-2 gap-2">
                {OUTCOMES.map((o) => (
                  <button
                    key={o.status}
                    type="button"
                    disabled={pending}
                    onClick={() => recordOutcome(o.status, o.label)}
                    className={`rounded-lg border px-3 py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${OUTCOME_BTN[o.tone]}`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-faint">
                Gemmer noten (hvis udfyldt) og går videre til næste lead.
              </p>

              <h2 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-faint">
                Planlæg opfølgning
              </h2>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="input"
                />
                <button
                  type="button"
                  disabled={pending || !date}
                  onClick={() =>
                    run(() => scheduleFollowup(lead.id, date), () => setDate(""))
                  }
                  className="btn btn-primary"
                >
                  Tilføj
                </button>
              </div>

              {error && <p className="mt-3 text-sm text-rose-fg">{error}</p>}
            </section>

            <Link
              href={`/leads/${lead.id}`}
              className="block text-center text-sm text-muted transition-colors hover:text-brand-700"
            >
              Åbn fuld lead-profil →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
