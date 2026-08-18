"use client";

import { useState, useTransition } from "react";
import { createBatch } from "../actions";

export default function CreateBatchForm({ approvedCount }: { approvedCount: number }) {
  const [name, setName] = useState(`Batch ${new Date().toISOString().slice(0, 10)}`);
  const [seed, setSeed] = useState(true);
  const [msg, setMsg] = useState<{ error?: string; warning?: string; info?: string } | null>(null);
  const [pending, start] = useTransition();
  const underMoq = approvedCount > 0 && approvedCount < 10;

  return (
    <div className="card card-pad">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs text-muted">
          Batchnavn
          <input className="input mt-1 block w-56" value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm text-ink">
          <input type="checkbox" checked={seed} onChange={(e) => setSeed(e.target.checked)} />
          Inkludér seed-brev til egen adresse
        </label>
        <button
          className="btn btn-primary"
          disabled={pending || approvedCount === 0}
          onClick={() => {
            setMsg(null);
            start(async () => setMsg(await createBatch(name, seed)));
          }}
        >
          Opret batch med {approvedCount} godkendte
        </button>
        <p className={`text-xs ${underMoq ? "text-amber-fg" : "text-muted"}`}>
          {underMoq
            ? `Pensaki fakturerer minimum 10 stk. (10 × €5,80) — ${approvedCount} breve koster det samme som 10.`
            : "Min. 10 pr. ordre · A4 650 · ~€5,80 pr. brev inkl. porto og tysk moms."}
        </p>
      </div>
      {msg?.error && <p className="mt-2 text-xs text-rose-fg">{msg.error}</p>}
      {msg?.warning && <p className="mt-2 text-xs text-amber-fg">{msg.warning}</p>}
      {msg?.info && <p className="mt-2 text-xs text-teal-fg">{msg.info}</p>}
    </div>
  );
}
