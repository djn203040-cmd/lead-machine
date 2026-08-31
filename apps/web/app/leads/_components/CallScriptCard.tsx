import type { CallScript, Segment } from "@/lib/script";

// The fixed call script, laid out in the order it is spoken. Pure display —
// no state, so it renders in both the client-side dialer and the server-side
// lead page.

function Step({
  n,
  label,
  children,
  hint,
}: {
  n: string;
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="mt-4 first:mt-0">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-brand-700">
        <span className="grid h-5 w-5 place-items-center rounded-md bg-brand-700 font-mono text-[0.7rem] text-white">
          {n}
        </span>
        {label}
        {hint && <span className="font-normal normal-case tracking-normal text-faint">· {hint}</span>}
      </p>
      <div className="mt-1.5 space-y-2">{children}</div>
    </div>
  );
}

// One paragraph of the pitch: plain text runs, with the GDPR source line and
// the per-lead savings sentence highlighted so the caller can see at a glance
// that (a) the CVR disclosure was said and (b) which words came from the data.
const SEGMENT_CLASS: Record<Segment["kind"], string> = {
  plain: "",
  source: "rounded bg-amber-bg px-1 text-amber-fg",
  savings: "rounded bg-brand-100 px-1 text-brand-800",
};

function Paragraph({ segments, inline }: { segments: Segment[]; inline?: boolean }) {
  const Tag = inline ? "span" : "p";
  return (
    <Tag>
      {segments.map((seg, i) => (
        <span key={i} className={SEGMENT_CLASS[seg.kind]}>
          {i > 0 ? " " : ""}
          {seg.text}
        </span>
      ))}
    </Tag>
  );
}

function Line({ children, muted }: { children: React.ReactNode; muted?: boolean }) {
  return (
    <blockquote
      className={`border-l-2 pl-3 text-sm ${
        muted ? "border-line-strong text-muted" : "border-brand-500 font-medium text-ink"
      }`}
    >
      {children}
    </blockquote>
  );
}

export default function CallScriptCard({ script }: { script: CallScript }) {
  const gatekeeperFirst = script.audience === "gatekeeper";
  return (
    <section className="overflow-hidden rounded-xl border border-brand-100 bg-gradient-to-br from-brand-50 to-brand-100/50 p-5 shadow-[var(--shadow-card)]">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-brand-800">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-brand-700 text-white">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path d="m13 2-9 11h6l-1 9 9-11h-6z" fill="currentColor" />
            </svg>
          </span>
          Script
        </h2>
        <span className="text-xs text-brand-700">
          Fast script — kun navn og besparelse skifter
        </span>
      </div>

      <Step
        n="1"
        label="Åbning"
        hint={gatekeeperFirst ? "medarbejder/reception tager den" : "ejeren tager den"}
      >
        {gatekeeperFirst ? (
          <>
            <Line>«{script.openerGatekeeper}»</Line>
            <p className="text-xs text-faint">Når du har ejeren:</p>
            <Line muted>
              «<Paragraph segments={script.openerOwner} inline />»
            </Line>
          </>
        ) : (
          <>
            <Line>
              «<Paragraph segments={script.openerOwner} inline />»
            </Line>
            <p className="text-xs text-faint">Hvis en medarbejder tager den:</p>
            <Line muted>«{script.openerGatekeeper}»</Line>
          </>
        )}
        <p className="text-xs text-faint">
          <span className="rounded bg-brand-100 px-1 text-brand-800">blå</span> = besparelsen —
          beregnet pr. lead (240–400k når leadet intet tal har)
        </p>
      </Step>

      <Step n="2" label="Pitch" hint="når de siger ja — tallet er allerede sagt">
        <blockquote className="space-y-2 border-l-2 border-brand-500 pl-3 text-sm font-medium leading-relaxed text-ink">
          {script.pitch.map((para, i) => (
            <Paragraph key={i} segments={para} />
          ))}
        </blockquote>
        <p className="text-xs text-faint">
          Split-test — vælg ÉT spørgsmål pr. opkald, rotér og notér hvad der lander:
        </p>
        {script.splitTest.map((j) => (
          <Line key={j} muted>
            «{j}»
          </Line>
        ))}
        <Line>«{script.how}»</Line>
        <Line>«{script.bridge}»</Line>
      </Step>

      <Step n="3" label="Smerte" hint="stil spørgsmålet — og ti stille">
        <Line>«{script.pain.ask}»</Line>
        <p className="text-xs text-faint">(lad dem svare)</p>
        <Line>«{script.pain.followup}»</Line>
      </Step>

      <Step n="4" label="Book mødet">
        <Line>«{script.booking}»</Line>
      </Step>

      <Step n="5" label="Når mødet er booket" hint="mail + opkald dagen før">
        <Line>«{script.showUp.booked}»</Line>
        <p className="text-xs text-faint">PS, lige inden du lægger på:</p>
        <Line>«{script.showUp.ps}»</Line>
      </Step>

      <Step n="✓" label="Inden du lægger på" hint="GDPR art. 14 — skal siges i hvert første opkald, booket eller ej">
        <Line>
          «<span className="rounded bg-amber-bg px-1 text-amber-fg">{script.sourceLine}</span>»
        </Line>
      </Step>

      <Step n="?" label="«Hvad koster det?»" hint="20 % af ét års besparelse, betalt én gang">
        <Line>«{script.price.long}»</Line>
        <p className="text-xs text-faint">Kort version, hvis de afbryder:</p>
        <Line muted>«{script.price.short}»</Line>
        {script.price.feeLine && (
          <>
            <p className="text-xs text-faint">Hvis de vil have et tal:</p>
            <Line muted>«{script.price.feeLine}»</Line>
          </>
        )}
      </Step>
    </section>
  );
}
