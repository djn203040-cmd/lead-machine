"use client";

import { useState, useTransition } from "react";
import type { Tables } from "@/lib/database.types";
import { formatDate } from "@/lib/leadmeta";
import { markBatchOrdered, markBatchSent, markSeedReceived, updateBatchNotes } from "../actions";
import MailCard, { type MailView } from "./MailCard";

export type BatchView = Tables<"mail_batches"> & { letters: MailView[] };

const STATUS_DA: Record<string, { label: string; className: string }> = {
  open: { label: "Åben", className: "chip-amber" },
  ordered: { label: "Bestilt", className: "chip-cyan" },
  sent: { label: "Sendt", className: "chip-brand" },
  done: { label: "Afsluttet", className: "chip-teal" },
  cancelled: { label: "Annulleret", className: "chip-neutral" },
};

export default function BatchPanel({ batch }: { batch: BatchView }) {
  const [orderId, setOrderId] = useState(batch.vendor_order_id ?? "");
  const [offset, setOffset] = useState(String(batch.followup_offset_days));
  const [notes, setNotes] = useState(batch.notes ?? "");
  const [showLetters, setShowLetters] = useState(batch.status === "open");
  const [msg, setMsg] = useState<{ error?: string; warning?: string; info?: string } | null>(null);
  const [pending, start] = useTransition();
  const run = (fn: () => Promise<{ error?: string; warning?: string; info?: string }>) => {
    setMsg(null);
    start(async () => setMsg(await fn()));
  };

  const meta = STATUS_DA[batch.status] ?? STATUS_DA.open;
  const scanned = batch.letters.filter((l) => l.scan_count > 0).length;
  const transitDays =
    batch.seed_received_at && batch.ordered_at
      ? Math.round((new Date(batch.seed_received_at).getTime() - new Date(batch.ordered_at).getTime()) / 86_400_000)
      : null;

  return (
    <article className="card">
      <header className="flex flex-wrap items-center gap-2 px-4 py-3">
        <h2 className="text-sm font-semibold text-ink">{batch.name}</h2>
        <span className={`chip ${meta.className}`}>{meta.label}</span>
        <span className="text-xs text-muted">{batch.letters.length} breve{batch.seed_included ? " + seed" : ""}</span>
        {batch.ordered_at && <span className="text-xs text-muted">· bestilt {formatDate(batch.ordered_at)}</span>}
        {batch.sent_at && <span className="text-xs text-muted">· afsendt {formatDate(batch.sent_at)}</span>}
        {transitDays !== null && <span className="chip chip-teal">Seed modtaget efter {transitDays} dage</span>}
        {batch.letters.length > 0 && (
          <span className="ml-auto text-xs text-muted">
            Scannet {scanned}/{batch.letters.length} ({Math.round((scanned / batch.letters.length) * 100)}%)
          </span>
        )}
      </header>

      <div className="flex flex-wrap items-end gap-3 border-t border-line/60 px-4 py-3">
        <a className="btn btn-secondary" href={`/leads/mail/batches/${batch.id}/export`}>
          ⬇ Eksportér CSV (Pensaki-import)
        </a>
        {batch.status === "open" && (
          <>
            <label className="text-xs text-muted">
              Pensaki ordre-ID
              <input className="input mt-1 block w-40" value={orderId} onChange={(e) => setOrderId(e.target.value)} placeholder="fx 48213" />
            </label>
            <label className="text-xs text-muted">
              Opfølgning +dage
              <input className="input mt-1 block w-24" type="number" min={1} max={60} value={offset} onChange={(e) => setOffset(e.target.value)} />
            </label>
            <button
              className="btn btn-primary"
              disabled={pending || batch.letters.length === 0}
              onClick={() => run(() => markBatchOrdered(batch.id, orderId, Number(offset)))}
            >
              Markér som bestilt
            </button>
          </>
        )}
        {batch.status === "ordered" && (
          <button className="btn btn-primary" disabled={pending} onClick={() => run(() => markBatchSent(batch.id))}>
            Overdraget til Deutsche Post (bekræftelses-mail modtaget)
          </button>
        )}
        {(batch.status === "sent" || batch.status === "ordered") && batch.seed_included && !batch.seed_received_at && (
          <button className="btn btn-secondary" disabled={pending} onClick={() => run(() => markSeedReceived(batch.id))}>
            Seed-brev er landet i dag
          </button>
        )}
        <button className="btn btn-ghost" onClick={() => setShowLetters((s) => !s)}>
          {showLetters ? "Skjul breve" : "Vis breve"}
        </button>
      </div>

      <div className="border-t border-line/60 px-4 py-3">
        <label className="block text-xs text-muted">
          Noter (leveringstid, kvalitet, hvad vi lærte)
          <textarea
            className="input mt-1 w-full"
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => notes !== (batch.notes ?? "") && run(() => updateBatchNotes(batch.id, notes))}
          />
        </label>
        {msg?.error && <p className="mt-2 text-xs text-rose-fg">{msg.error}</p>}
        {msg?.warning && <p className="mt-2 text-xs text-amber-fg">{msg.warning}</p>}
        {msg?.info && <p className="mt-2 text-xs text-teal-fg">{msg.info}</p>}
      </div>

      {showLetters && (
        <div className="space-y-2 border-t border-line/60 bg-canvas p-3">
          {batch.letters.map((l) => (
            <MailCard key={l.id} mail={l} compact />
          ))}
        </div>
      )}
    </article>
  );
}
