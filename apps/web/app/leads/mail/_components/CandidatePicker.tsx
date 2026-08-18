"use client";

import Link from "next/link";
import { useMemo, useState, useTransition } from "react";
import { websiteNeedMeta } from "@/lib/leadmeta";
import { MAIL_ARM_META, type MailArm } from "@/lib/mail/letter";
import { enqueueLeads } from "../actions";

export type Candidate = {
  id: string;
  company_name: string;
  address: string;
  branche: string | null;
  score: number | null;
  recipient: string | null;
  is_sole_trader: boolean;
  website: string | null;
  website_need: string;
};

export default function CandidatePicker({ candidates, arm }: { candidates: Candidate[]; arm: MailArm }) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [msg, setMsg] = useState<{ error?: string; info?: string } | null>(null);
  const [pending, start] = useTransition();

  const allIds = useMemo(() => candidates.map((c) => c.id), [candidates]);
  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  const submit = () => {
    setMsg(null);
    start(async () => {
      const r = await enqueueLeads([...selected], arm);
      setMsg(r);
      if (!r.error) setSelected(new Set());
    });
  };

  return (
    <div className="card overflow-hidden">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        <span className="text-sm text-ink">
          <span className={`chip ${MAIL_ARM_META[arm].className} mr-2`}>{MAIL_ARM_META[arm].label}</span>
          {candidates.length} kandidater · {selected.size} valgt
        </span>
        <button className="btn btn-ghost" onClick={() => setSelected(new Set(allIds))} disabled={!allIds.length}>
          Vælg alle
        </button>
        <button className="btn btn-ghost" onClick={() => setSelected(new Set())} disabled={!selected.size}>
          Ryd
        </button>
        <button className="btn btn-primary ml-auto" disabled={pending || !selected.size} onClick={submit}>
          Sæt {selected.size} i kø (arm {arm})
        </button>
      </div>
      {msg?.error && <p className="px-4 pb-2 text-xs text-rose-fg">{msg.error}</p>}
      {msg?.info && <p className="px-4 pb-2 text-xs text-teal-fg">{msg.info}</p>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-canvas text-left text-xs uppercase tracking-wide text-faint">
            <tr>
              <th className="px-4 py-2" />
              <th className="px-4 py-2">Virksomhed</th>
              <th className="px-4 py-2">Att.</th>
              <th className="px-4 py-2">Adresse</th>
              <th className="px-4 py-2">Branche</th>
              <th className="px-4 py-2">Web</th>
              <th className="px-4 py-2 text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => {
              const need = websiteNeedMeta(c.website_need);
              return (
                <tr
                  key={c.id}
                  className={`cursor-pointer border-t border-line/60 ${selected.has(c.id) ? "bg-brand-50" : "hover:bg-canvas"}`}
                  onClick={() => toggle(c.id)}
                >
                  <td className="px-4 py-2">
                    <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)} onClick={(e) => e.stopPropagation()} />
                  </td>
                  <td className="px-4 py-2 font-medium text-ink">
                    <Link href={`/leads/${c.id}`} className="hover:underline" onClick={(e) => e.stopPropagation()}>
                      {c.company_name}
                    </Link>
                    {c.is_sole_trader && <span className="ml-2 chip chip-neutral">Enkeltmand</span>}
                  </td>
                  <td className="px-4 py-2 text-muted">{c.recipient ?? <span className="text-amber-fg">ingen navn</span>}</td>
                  <td className="px-4 py-2 text-muted">{c.address}</td>
                  <td className="px-4 py-2 text-muted">{c.branche ?? "—"}</td>
                  <td className="px-4 py-2"><span className={`chip ${need.className}`}>{need.label}</span></td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{c.score ?? "—"}</td>
                </tr>
              );
            })}
            {candidates.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-sm text-muted">
                  Ingen kandidater med de valgte filtre.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
