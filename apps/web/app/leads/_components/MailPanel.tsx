"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { formatDate } from "@/lib/leadmeta";
import { MAIL_ARM_META, type MailArm, mailStatusMeta, publicUrl } from "@/lib/mail/letter";
import { enqueueLeads } from "../mail/actions";

export type LeadMailView = {
  id: string;
  arm: string;
  status: string;
  slug: string;
  scan_count: number;
  first_scanned_at: string | null;
  created_at: string;
  reject_reason: string | null;
} | null;

/** Lead-page card: the lead's current letter, or a "send letter" control. */
export default function MailPanel({ leadId, mail }: { leadId: string; mail: LeadMailView }) {
  const [arm, setArm] = useState<MailArm>("C");
  const [msg, setMsg] = useState<{ error?: string; info?: string } | null>(null);
  const [pending, start] = useTransition();

  if (mail) {
    const status = mailStatusMeta(mail.status);
    const armMeta = MAIL_ARM_META[mail.arm as MailArm];
    return (
      <div className="space-y-2 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`chip ${armMeta?.className ?? "chip-neutral"}`}>{armMeta?.label ?? mail.arm}</span>
          <span className={`chip ${status.className}`}>{status.label}</span>
          {mail.scan_count > 0 && <span className="chip chip-brand">🔥 scannet {mail.scan_count}×</span>}
        </div>
        <p className="font-mono text-xs text-brand-700">{publicUrl(mail.slug)}</p>
        <p className="text-xs text-muted">
          Oprettet {formatDate(mail.created_at)}
          {mail.first_scanned_at ? ` · første scan ${formatDate(mail.first_scanned_at)}` : ""}
          {mail.reject_reason ? ` · afvist: ${mail.reject_reason}` : ""}
        </p>
        <Link href="/leads/mail" className="text-xs text-brand-700 underline">
          Åbn i Breve →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2 text-sm">
      <p className="text-muted">Intet brev endnu.</p>
      <div className="flex flex-wrap items-center gap-2">
        <select className="select" value={arm} onChange={(e) => setArm(e.target.value as MailArm)}>
          {(["C", "A", "B"] as const).map((a) => (
            <option key={a} value={a}>{MAIL_ARM_META[a].label}</option>
          ))}
        </select>
        <button
          className="btn btn-secondary"
          disabled={pending}
          onClick={() => {
            setMsg(null);
            start(async () => setMsg(await enqueueLeads([leadId], arm)));
          }}
        >
          ✉ Læg brev i kø
        </button>
      </div>
      {msg?.error && <p className="text-xs text-rose-fg">{msg.error}</p>}
      {msg?.info && <p className="text-xs text-teal-fg">{msg.info}</p>}
    </div>
  );
}
