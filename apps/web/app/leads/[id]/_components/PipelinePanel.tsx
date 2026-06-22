"use client";

import { useState, useTransition } from "react";
import { PIPELINE_META, PIPELINE_STATUSES, formatDate } from "@/lib/leadmeta";
import { addFollowup, addNote, setPipelineStatus } from "../actions";

export type NoteView = { id: string; body: string; created_at: string };
export type FollowupView = { id: string; follow_up_date: string; reminder_sent: boolean };

export default function PipelinePanel({
  leadId,
  status,
  notes,
  followups,
}: {
  leadId: string;
  status: string;
  notes: NoteView[];
  followups: FollowupView[];
}) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [date, setDate] = useState("");

  function run(action: () => Promise<{ error?: string }>, onOk?: () => void) {
    setError(null);
    startTransition(async () => {
      const res = await action();
      if (res.error) setError(res.error);
      else onOk?.();
    });
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Status</h3>
        <select
          value={status}
          disabled={pending}
          onChange={(e) => run(() => setPipelineStatus(leadId, e.target.value))}
          className="w-full rounded border bg-white px-2 py-1.5 text-sm disabled:opacity-50"
        >
          {PIPELINE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {PIPELINE_META[s].label}
            </option>
          ))}
        </select>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Noter</h3>
        <div className="flex flex-col gap-2">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Tilføj en note…"
            rows={2}
            className="rounded border px-2 py-1.5 text-sm"
          />
          <button
            type="button"
            disabled={pending || !note.trim()}
            onClick={() => run(() => addNote(leadId, note), () => setNote(""))}
            className="self-end rounded bg-black px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
          >
            Gem note
          </button>
        </div>
        <ul className="mt-3 space-y-2">
          {notes.map((n) => (
            <li key={n.id} className="rounded bg-gray-50 p-2 text-sm">
              <p className="whitespace-pre-wrap text-gray-800">{n.body}</p>
              <p className="mt-1 text-xs text-gray-400">{formatDate(n.created_at)}</p>
            </li>
          ))}
          {notes.length === 0 && <li className="text-sm text-gray-400">Ingen noter endnu.</li>}
        </ul>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-gray-700">Opfølgning</h3>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded border px-2 py-1.5 text-sm"
          />
          <button
            type="button"
            disabled={pending || !date}
            onClick={() => run(() => addFollowup(leadId, date), () => setDate(""))}
            className="rounded bg-black px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
          >
            Tilføj
          </button>
        </div>
        <ul className="mt-3 space-y-1">
          {followups.map((f) => (
            <li key={f.id} className="flex items-center justify-between text-sm">
              <span className="text-gray-800">{formatDate(f.follow_up_date)}</span>
              {f.reminder_sent && <span className="text-xs text-gray-400">påmindet</span>}
            </li>
          ))}
          {followups.length === 0 && (
            <li className="text-sm text-gray-400">Ingen opfølgninger planlagt.</li>
          )}
        </ul>
      </section>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
