"use client";

import { useActionState } from "react";
import Link from "next/link";
import { GROUP_OPTIONS } from "@/lib/branchekoder";
import { discoverAction, type DiscoverState } from "../actions";

const BANDS: { value: string; label: string }[] = [
  { value: "ANTAL_1_1", label: "1" },
  { value: "ANTAL_2_4", label: "2–4" },
  { value: "ANTAL_5_9", label: "5–9" },
  { value: "ANTAL_10_19", label: "10–19" },
  { value: "ANTAL_20_49", label: "20–49" },
];

export default function DiscoverForm() {
  const [state, action, pending] = useActionState<DiscoverState, FormData>(discoverAction, {});

  return (
    <form action={action} className="space-y-5">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink">Branche</label>
        <select name="group" required defaultValue="" className="select">
          <option value="" disabled>
            Vælg branche…
          </option>
          {GROUP_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-ink">Postnummer(e)</label>
        <input name="postnumre" required placeholder="f.eks. 2200 8000 9000" className="input" />
        <p className="mt-1.5 text-xs text-faint">Adskil flere med mellemrum eller komma.</p>
      </div>

      <div>
        <span className="mb-2 block text-sm font-medium text-ink">Antal ansatte (valgfrit)</span>
        <div className="flex flex-wrap gap-2">
          {BANDS.map((b) => (
            <label
              key={b.value}
              className="flex cursor-pointer items-center gap-1.5 rounded-full border border-line-strong bg-card px-3 py-1.5 text-sm text-ink transition-colors hover:border-brand-500 has-[:checked]:border-brand-600 has-[:checked]:bg-brand-50 has-[:checked]:text-brand-800"
            >
              <input type="checkbox" name="bands" value={b.value} className="accent-brand-700" />
              {b.label}
            </label>
          ))}
        </div>
      </div>

      <button type="submit" disabled={pending} className="btn btn-primary w-full">
        {pending ? "Søger i CVR…" : "Find virksomheder"}
      </button>

      {state.error && (
        <div className="rounded-xl border border-rose-fg/30 bg-rose-bg p-4 text-sm text-rose-fg">
          {state.error}
        </div>
      )}

      {state.ok && state.stats && (
        <div className="rounded-xl border border-brand-100 bg-brand-50 p-4 text-sm text-brand-800">
          <p className="font-semibold">Færdig! 🎉</p>
          <p className="mt-1">
            {state.stats.seen} fundet · {state.stats.upserted} tilføjet ·{" "}
            {state.stats.suppressed} undertrykt (reklamebeskyttet/inaktiv).
          </p>
          <Link href="/leads" className="mt-2 inline-block font-semibold text-brand-700 underline">
            Se leads →
          </Link>
        </div>
      )}
    </form>
  );
}
