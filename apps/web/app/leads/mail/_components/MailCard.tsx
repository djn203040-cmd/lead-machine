"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import {
  MAIL_ARM_META,
  MAX_LETTER_CHARS,
  REJECT_REASON_DA,
  type MailArm,
  addressBlock,
  buildLetter,
  mailStatusMeta,
  publicUrl,
} from "@/lib/mail/letter";
import {
  approveMail,
  retryRejected,
  removeFromBatch,
  setMailStatus,
  suggestObservation,
  updateMail,
} from "../actions";

export type MailView = {
  id: string;
  lead_id: string;
  arm: MailArm;
  status: string;
  slug: string;
  recipient_name: string | null;
  first_name: string | null;
  company_name: string;
  address_line: string | null;
  postal_code: string | null;
  city: string | null;
  country: string;
  observation_text: string | null;
  focus_text: string | null;
  letter_text: string | null;
  letter_chars: number | null;
  reject_reason: string | null;
  landing_video_url: string | null;
  landing_headline: string | null;
  scan_count: number;
  first_scanned_at: string | null;
  opted_out_at: string | null;
  created_at: string;
  website: string | null;
  branche: string | null;
};

type Result = { error?: string; warning?: string; info?: string };

function Field({
  label,
  value,
  onChange,
  placeholder,
  wide,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  wide?: boolean;
  hint?: string;
}) {
  return (
    <label className={`block text-xs text-muted ${wide ? "sm:col-span-2" : ""}`}>
      {label}
      {hint && <span className="ml-1 text-faint">— {hint}</span>}
      <input
        className="input mt-1 w-full"
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

export default function MailCard({ mail, compact = false }: { mail: MailView; compact?: boolean }) {
  const editable = mail.status === "draft";
  const [open, setOpen] = useState(!compact && editable);
  const [form, setForm] = useState({
    recipient_name: mail.recipient_name ?? "",
    first_name: mail.first_name ?? "",
    address_line: mail.address_line ?? "",
    postal_code: mail.postal_code ?? "",
    city: mail.city ?? "",
    observation_text: mail.observation_text ?? "",
    focus_text: mail.focus_text ?? "",
    landing_video_url: mail.landing_video_url ?? "",
    landing_headline: mail.landing_headline ?? "",
    arm: mail.arm as string,
  });
  const [msg, setMsg] = useState<Result | null>(null);
  const [pending, start] = useTransition();

  const dirty =
    form.recipient_name !== (mail.recipient_name ?? "") ||
    form.first_name !== (mail.first_name ?? "") ||
    form.address_line !== (mail.address_line ?? "") ||
    form.postal_code !== (mail.postal_code ?? "") ||
    form.city !== (mail.city ?? "") ||
    form.observation_text !== (mail.observation_text ?? "") ||
    form.focus_text !== (mail.focus_text ?? "") ||
    form.landing_video_url !== (mail.landing_video_url ?? "") ||
    form.landing_headline !== (mail.landing_headline ?? "") ||
    form.arm !== mail.arm;

  // Live preview — the frozen text once approved, else rendered from the form.
  const preview =
    mail.letter_text && !editable
      ? { text: mail.letter_text, chars: mail.letter_chars ?? mail.letter_text.length, ok: true, missing: [] as string[] }
      : buildLetter({
          arm: form.arm as MailArm,
          firstName: form.first_name.trim() || null,
          companyName: mail.company_name,
          observation: form.observation_text.trim() || null,
          focus: form.focus_text.trim() || null,
          slug: mail.slug,
        });

  const run = (fn: () => Promise<Result>) => {
    setMsg(null);
    start(async () => {
      const r = await fn();
      setMsg(r);
    });
  };

  const save = () => run(() => updateMail(mail.id, form));
  const approve = () =>
    run(async () => {
      if (dirty) {
        const r = await updateMail(mail.id, form);
        if (r.error) return r;
      }
      return approveMail(mail.id);
    });

  const armMeta = MAIL_ARM_META[mail.arm];
  const statusMeta = mailStatusMeta(mail.status);
  const overflow = preview.chars > MAX_LETTER_CHARS;

  return (
    <article className="card">
      <header className="flex flex-wrap items-center gap-2 px-4 py-3">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="text-left text-sm font-semibold text-ink hover:underline"
        >
          {mail.company_name}
        </button>
        <span className={`chip ${armMeta.className}`}>{armMeta.label}</span>
        <span className={`chip ${statusMeta.className}`}>{statusMeta.label}</span>
        {mail.branche && <span className="text-xs text-muted">{mail.branche}</span>}
        <span className="ml-auto font-mono text-xs text-brand-700">{publicUrl(mail.slug)}</span>
        {mail.scan_count > 0 && (
          <span className="chip chip-brand">🔥 {mail.scan_count} scan{mail.scan_count > 1 ? "s" : ""}</span>
        )}
        {mail.opted_out_at && <span className="chip chip-rose">Frameldt</span>}
        <Link href={`/leads/${mail.lead_id}`} className="text-xs text-muted hover:text-ink">
          Lead →
        </Link>
      </header>

      {mail.status === "rejected" && (
        <div className="border-t border-line/60 px-4 py-3 text-sm">
          <p className="text-rose-fg">
            Afvist: {REJECT_REASON_DA[mail.reject_reason ?? ""] ?? mail.reject_reason ?? "ukendt årsag"}
          </p>
          <div className="mt-2 flex gap-2">
            <button className="btn btn-secondary" disabled={pending} onClick={() => run(() => retryRejected(mail.id))}>
              Kør filtre igen
            </button>
            <button className="btn btn-ghost" disabled={pending} onClick={() => run(() => setMailStatus(mail.id, "cancelled"))}>
              Fjern
            </button>
          </div>
          {msg?.error && <p className="mt-2 text-xs text-rose-fg">{msg.error}</p>}
          {msg?.warning && <p className="mt-2 text-xs text-amber-fg">{msg.warning}</p>}
          {msg?.info && <p className="mt-2 text-xs text-teal-fg">{msg.info}</p>}
        </div>
      )}

      {open && mail.status !== "rejected" && (
        <div className="grid gap-4 border-t border-line/60 p-4 lg:grid-cols-[1fr_22rem]">
          <div>
            {editable ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Modtager (att.)" value={form.recipient_name} onChange={(v) => setForm({ ...form, recipient_name: v })} placeholder="Fulde navn fra CVR" />
                <Field label="Fornavn i brevet" value={form.first_name} onChange={(v) => setForm({ ...form, first_name: v })} />
                <Field label="Adresse" value={form.address_line} onChange={(v) => setForm({ ...form, address_line: v })} wide />
                <Field label="Postnr." value={form.postal_code} onChange={(v) => setForm({ ...form, postal_code: v })} />
                <Field label="By" value={form.city} onChange={(v) => setForm({ ...form, city: v })} />
                <label className="block text-xs text-muted">
                  Arm
                  <select className="select mt-1 w-full" value={form.arm} onChange={(e) => setForm({ ...form, arm: e.target.value })}>
                    {(["A", "B", "C"] as const).map((a) => (
                      <option key={a} value={a}>{MAIL_ARM_META[a].label}</option>
                    ))}
                  </select>
                </label>
                <div />
                <Field
                  label="Observation"
                  hint="„…blev hængende ved ___“ — én konkret, tjekbar ting"
                  value={form.observation_text}
                  onChange={(v) => setForm({ ...form, observation_text: v })}
                  placeholder="at I stadig tager bookinger over telefonen"
                  wide
                />
                <Field
                  label="Fokus [X]"
                  hint="„Da jeg kiggede på ___“"
                  value={form.focus_text}
                  onChange={(v) => setForm({ ...form, focus_text: v })}
                  placeholder="jeres booking"
                  wide
                />
                <Field label="Landing: overskrift (valgfri)" value={form.landing_headline} onChange={(v) => setForm({ ...form, landing_headline: v })} wide />
                <Field label="Landing: video-URL (Loom/YouTube, valgfri)" value={form.landing_video_url} onChange={(v) => setForm({ ...form, landing_video_url: v })} wide />
              </div>
            ) : (
              <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                <div><dt className="text-xs text-faint">Modtager</dt><dd className="text-ink">{mail.recipient_name ?? "—"} · {mail.first_name ?? "—"}</dd></div>
                <div><dt className="text-xs text-faint">Adresse</dt><dd className="whitespace-pre-line text-ink">{addressBlock(mail)}</dd></div>
                <div className="sm:col-span-2"><dt className="text-xs text-faint">Observation</dt><dd className="text-ink">{mail.observation_text ?? "—"}</dd></div>
                <div className="sm:col-span-2"><dt className="text-xs text-faint">Fokus</dt><dd className="text-ink">{mail.focus_text ?? "—"}</dd></div>
                {mail.landing_video_url && <div className="sm:col-span-2"><dt className="text-xs text-faint">Video</dt><dd className="truncate text-ink">{mail.landing_video_url}</dd></div>}
              </dl>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {editable && (
                <>
                  <button className="btn btn-primary" disabled={pending || overflow} onClick={approve}>
                    Godkend brev
                  </button>
                  <button className="btn btn-secondary" disabled={pending || !dirty} onClick={save}>
                    Gem
                  </button>
                  <button className="btn btn-secondary" disabled={pending} onClick={() => run(() => suggestObservation(mail.id))} title="Claude foreslår observation + fokus ud fra lead-data. Du godkender stadig.">
                    ✨ Foreslå observation
                  </button>
                  <button className="btn btn-ghost" disabled={pending} onClick={() => run(() => setMailStatus(mail.id, "cancelled"))}>
                    Annullér
                  </button>
                </>
              )}
              {mail.status === "approved" && (
                <>
                  <button className="btn btn-secondary" disabled={pending} onClick={() => run(() => setMailStatus(mail.id, "draft"))}>
                    Ret igen
                  </button>
                  <button className="btn btn-ghost" disabled={pending} onClick={() => run(() => setMailStatus(mail.id, "cancelled"))}>
                    Annullér
                  </button>
                </>
              )}
              {mail.status === "batched" && (
                <button className="btn btn-ghost" disabled={pending} onClick={() => run(() => removeFromBatch(mail.id))}>
                  Tag ud af batch
                </button>
              )}
              {mail.website && (
                <a href={mail.website.startsWith("http") ? mail.website : `https://${mail.website}`} target="_blank" rel="noreferrer" className="text-xs text-muted hover:text-ink">
                  Åbn hjemmeside ↗
                </a>
              )}
              <a href={`/l/${mail.slug}`} target="_blank" rel="noreferrer" className="text-xs text-muted hover:text-ink">
                Se landing-side ↗
              </a>
              {pending && <span className="text-xs text-muted">Arbejder…</span>}
            </div>
            {msg?.error && <p className="mt-2 text-xs text-rose-fg">{msg.error}</p>}
            {msg?.warning && <p className="mt-2 text-xs text-amber-fg">{msg.warning}</p>}
            {msg?.info && <p className="mt-2 text-xs text-teal-fg">{msg.info}</p>}
          </div>

          <aside className="rounded-xl border border-line-strong bg-canvas p-4">
            <div className="flex items-baseline justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Brevet</p>
              <p className={`font-mono text-xs tabular-nums ${overflow ? "text-rose-fg" : "text-muted"}`}>
                {preview.chars}/{MAX_LETTER_CHARS}
              </p>
            </div>
            <pre className="mt-2 whitespace-pre-wrap font-[ui-serif,Georgia,serif] text-[0.95rem] leading-relaxed text-ink">
              {preview.text}
            </pre>
            {preview.missing.length > 0 && (
              <p className="mt-2 text-xs text-amber-fg">Mangler: {preview.missing.join(", ")}</p>
            )}
            {overflow && <p className="mt-1 text-xs text-rose-fg">For langt til A4 650 — kort observationen ned.</p>}
          </aside>
        </div>
      )}
    </article>
  );
}
