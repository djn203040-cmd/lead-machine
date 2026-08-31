"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { displayBranche, spokenBrancheForCode } from "@/lib/branchekoder";
import {
  type AngleObjection,
  type ContactEnrichment,
  type FinancialEnrichment,
  view,
} from "@/lib/enrichment";
import {
  employeesLabel,
  formatDKK,
  formatDKKEstimate,
  pipelineMeta,
  websiteNeedMeta,
} from "@/lib/leadmeta";
import { classifyPhone, phoneTypeMeta } from "@/lib/phone";
import type { SavingsView } from "@/lib/savings";
import { buildCallScript } from "@/lib/script";
import { buildVoicemail, voicemailFirstName } from "@/lib/voicemail";
import CallScriptCard from "../../_components/CallScriptCard";
import { logNoAnswer, logOutcome, saveNote, scheduleFollowup } from "../actions";

// What the AI still contributes per lead: private notes + tailored objections.
// The spoken script itself is fixed — see lib/script.ts.
export type DialerAngle = {
  summary_da: string | null;
  weaknesses_da: string | null;
  objections: AngleObjection[];
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
  /** Realistic annual saving + our 20% cut — the number the pitch quotes. */
  savings: SavingsView | null;
  financial: unknown;
  contact: unknown;
};

const COMPETITOR_ANGLE_DA: Record<string, string> = {
  fomo: "FOMO — andre i branchen automatiserer allerede",
  first_mover: "First mover — først lokalt til at køre driften sådan",
};

const CAPPED_BY_DA: Record<string, string> = {
  gross_profit: "skåret ned efter bruttofortjenesten",
  headcount: "skåret ned efter antal ansatte",
  ceiling: "loft sat — større end vores typiske kunde",
};

// Outcome buttons — each moves the pipeline forward and advances to the next lead.
const OUTCOMES = [
  { status: "contacted", label: "Kontaktet", tone: "cyan" },
  { status: "meeting_booked", label: "Møde booket", tone: "teal" },
  { status: "lost", label: "Ikke interesseret", tone: "rose" },
  { status: "discarded", label: "Kassér", tone: "neutral" },
] as const;

const OUTCOME_BTN: Record<string, string> = {
  amber: "border-amber-fg/25 bg-amber-bg text-amber-fg hover:border-amber-fg/50",
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

function Objections({ items }: { items: AngleObjection[] }) {
  if (!items.length) return null;
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
        Indvendinger
      </p>
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

function SavingsPanel({ savings }: { savings: SavingsView }) {
  const fromAccounts = savings.basis === "accounts";
  return (
    <section
      className={`rounded-xl border p-4 ${
        fromAccounts ? "border-teal-fg/25 bg-teal-bg" : "border-line-strong bg-canvas"
      }`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2
          className={`text-xs font-semibold uppercase tracking-wide ${
            fromAccounts ? "text-teal-fg" : "text-muted"
          }`}
        >
          Realistisk besparelse
        </h2>
        <span className={`text-xs ${fromAccounts ? "text-teal-fg/80" : "text-faint"}`}>
          {savings.confidence && `${savings.confidence} sikkerhed`}
          {savings.cappedBy && ` · ${CAPPED_BY_DA[savings.cappedBy] ?? savings.cappedBy}`}
        </span>
      </div>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums text-ink">
        {formatDKK(savings.annualLow)} – {formatDKK(savings.annualHigh)}
        <span className="ml-1 text-sm font-normal text-muted">om året</span>
      </p>
      <p className="mt-1 text-sm text-muted">
        Dit honorar (20% af det sparede):{" "}
        <span className="font-medium text-ink">
          {formatDKK(savings.feeLow)} – {formatDKK(savings.feeHigh)}
        </span>{" "}
        om året
      </p>
      {/* Where the number came from decides what the caller may say out loud. */}
      {fromAccounts ? (
        <p className="mt-2 text-xs text-teal-fg/90">
          <span className="font-semibold">Fra deres eget regnskab.</span>{" "}
          {savings.rate !== null && `${Math.round(savings.rate * 100)}% af `}
          {savings.pool !== null && `${formatDKK(savings.pool)} `}i driftsomkostninger
          under bruttofortjenesten. Tallene er offentlige — du må citere dem. Selve
          besparelsen er stadig et estimat, aldrig et løfte.
        </p>
      ) : (
        <p className="mt-2 text-xs text-faint">
          <span className="font-semibold">Brancheestimat</span> — de har ikke
          offentliggjort brugbare regnskabstal. Sig det som et typisk spænd for deres
          størrelse, aldrig som deres tal.
        </p>
      )}
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

export default function Dialer({ queue }: { queue: DialerLead[] }) {
  const [index, setIndex] = useState(0);
  // Leads handled this session — greyed out in the rail, skipped by "next unhandled".
  const [handled, setHandled] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [date, setDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  // Non-blocking: the outcome was logged, but a side effect (PM sync) failed.
  const [warning, setWarning] = useState<string | null>(null);
  // Side-effect notice, e.g. "brev lagt til gennemsyn" (direct-mail arm).
  const [info, setInfo] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const total = queue.length;
  const lead = queue[index] as DialerLead | undefined;

  const go = useCallback(
    (dir: 1 | -1) => {
      setError(null);
      setWarning(null);
      setInfo(null);
      setNote("");
      setDate("");
      setIndex((i) => Math.min(total - 1, Math.max(0, i + dir)));
    },
    [total],
  );

  const run = useCallback(
    (
      action: () => Promise<{ error?: string; warning?: string; info?: string }>,
      onOk?: () => void,
    ) => {
      setError(null);
      setWarning(null);
      setInfo(null);
      startTransition(async () => {
        const res = await action();
        if (res.error) setError(res.error);
        else {
          if (res.warning) setWarning(res.warning);
          if (res.info) setInfo(res.info);
          onOk?.();
        }
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

  // "Intet svar": logs the attempt (lead stays in the ring list) and queues an
  // arm-A handwritten letter for review, then moves on.
  const recordNoAnswer = useCallback(() => {
    if (!lead) return;
    const leadId = lead.id;
    const noteText = note;
    run(
      () => logNoAnswer(leadId, noteText),
      () => {
        setHandled((h) => ({ ...h, [leadId]: "Intet svar" }));
        setNote("");
        setDate("");
        setIndex((i) => Math.min(total - 1, i + 1));
      },
    );
  }, [lead, note, run, total]);

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
  const firstName = voicemailFirstName(decisionMakers);
  const voicemail = buildVoicemail({
    firstName,
    companyName: lead.company_name,
    branchekode: lead.branchekode,
  });
  const angle = lead.angle;
  const branche = displayBranche(lead.branchekode, lead.branche_text) ?? "—";
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
  // Who picks up? With no mobile among the numbers, expect a gatekeeper —
  // surface the "ask for the owner" hint next to the call buttons.
  const phoneClasses = lead.phone.map((p) => classifyPhone(p));
  const gatekeeperMeta = phoneClasses.includes("mobile")
    ? null
    : phoneTypeMeta(phoneClasses.find((c) => c !== null) ?? null);
  // The fixed script — only the opener variant, first name and savings vary.
  const script = buildCallScript({
    firstName,
    phoneType: phoneClasses.includes("mobile")
      ? "mobile"
      : (phoneClasses.find((c) => c !== null) ?? null),
    savings: lead.savings,
    brancheLabel: spokenBrancheForCode(lead.branchekode),
  });

  // Shared panels — rendered high up on mobile (call → script → outcome) and in
  // the sticky right column on desktop. Same state either way; only one copy is
  // visible at a time.
  const callPanel = (
    <section className="card card-pad">
      <h2 className="mb-3 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-faint">
        Ring nu
        <span className="chip chip-neutral normal-case">{currentStatus}</span>
      </h2>
      {lead.phone.length > 0 ? (
        <div className="space-y-2">
          {lead.phone.map((p) => {
            const meta = phoneTypeMeta(classifyPhone(p));
            return (
              <div key={p}>
                <a
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
                {meta && (
                  <p className="mt-1.5 text-center">
                    <span className={`chip ${meta.className} text-[0.7rem]`} title={meta.hint}>
                      {meta.label}
                    </span>
                  </p>
                )}
              </div>
            );
          })}
          {gatekeeperMeta && (
            <p className="rounded-lg border border-amber-fg/25 bg-amber-bg px-3 py-2 text-xs text-amber-fg">
              {gatekeeperMeta.hint}
            </p>
          )}
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
      {lead.email && <p className="mt-1 break-all text-sm text-muted">{lead.email}</p>}
      <p className="mt-3 text-xs text-faint">
        Telefon-først — Markedsføringsloven §10 forbyder kold B2B-email uden samtykke.
      </p>
    </section>
  );

  const outcomePanel = (
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
          onClick={() => run(() => saveNote(lead.id, note), () => setNote(""))}
          className="btn btn-secondary"
        >
          Gem note
        </button>
      </div>

      <h2 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-faint">
        Registrér udfald
      </h2>
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={pending}
          onClick={recordNoAnswer}
          title="Logger forsøget, lader leadet blive i ringelisten og lægger et håndskrevet brev (arm A) til gennemsyn."
          className={`col-span-2 rounded-lg border px-3 py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${OUTCOME_BTN.amber}`}
        >
          Intet svar → brev
        </button>
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
          onClick={() => run(() => scheduleFollowup(lead.id, date), () => setDate(""))}
          className="btn btn-primary"
        >
          Tilføj
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-rose-fg">{error}</p>}
      {warning && <p className="mt-3 text-sm text-amber-fg">{warning}</p>}
      {info && <p className="mt-3 text-sm text-teal-fg">{info}</p>}
    </section>
  );

  const profileLink = (
    <Link
      href={`/leads/${lead.id}`}
      className="block text-center text-sm text-muted transition-colors hover:text-brand-700"
    >
      Åbn fuld lead-profil →
    </Link>
  );

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

          {/* Mobile: the call button belongs right under the company header. */}
          <div className="lg:hidden">{callPanel}</div>

          {lead.savings && <SavingsPanel savings={lead.savings} />}

          <CallScriptCard script={script} />

          {/* Mobile: log the outcome right after the script, before the deep-dive data. */}
          <div className="lg:hidden">{outcomePanel}</div>

          {angle && (
            <section className="card card-pad">
              <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-faint">
                  AI-noter til dette lead
                </h2>
                <span className="text-xs text-faint">
                  {COMPETITOR_ANGLE_DA[angle.competitor_angle_type ?? ""] ?? ""}
                  {angle.competitor_name ? ` · ${angle.competitor_name}` : ""}
                </span>
              </div>
              <Objections items={angle.objections} />
              <AnglePart label="Resumé" text={angle.summary_da} />
              <AnglePart label="Hvor tiden og pengene går (intern)" text={angle.weaknesses_da} />
            </section>
          )}

          <section className="card card-pad">
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">
              Telefonsvarer — ved intet svar
            </h2>
            <blockquote className="whitespace-pre-wrap border-l-2 border-brand-500 pl-3 text-sm text-ink">
              {voicemail}
            </blockquote>
            <p className="mt-2 text-xs text-faint">
              Fast script — kun fornavn og årsag skifter. Et «JA» på SMS er deres egen
              henvendelse, så du må ringe (og skrive) tilbage.
            </p>
          </section>

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
                    value={formatDKKEstimate(fin.revenue_estimate.value)}
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

          {/* Mobile: profile link closes the page (desktop shows it in the right rail). */}
          <div className="lg:hidden">{profileLink}</div>
        </div>

        {/* Right: the call panel (sticky, desktop only — mobile renders the same
            panels inline above) */}
        <div className="hidden space-y-6 lg:block">
          <div className="lg:sticky lg:top-24 space-y-6">
            {callPanel}
            {outcomePanel}
            {profileLink}
          </div>
        </div>
      </div>
    </div>
  );
}
