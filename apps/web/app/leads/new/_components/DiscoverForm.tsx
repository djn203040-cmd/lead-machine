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
        <label className="block text-sm font-medium text-gray-700">Branche</label>
        <select
          name="group"
          required
          defaultValue=""
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        >
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
        <label className="block text-sm font-medium text-gray-700">
          Postnummer(e)
        </label>
        <input
          name="postnumre"
          required
          placeholder="f.eks. 2200 8000 9000"
          className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <p className="mt-1 text-xs text-gray-500">Adskil flere med mellemrum eller komma.</p>
      </div>

      <div>
        <span className="block text-sm font-medium text-gray-700">Antal ansatte (valgfrit)</span>
        <div className="mt-2 flex flex-wrap gap-3">
          {BANDS.map((b) => (
            <label key={b.value} className="flex items-center gap-1.5 text-sm text-gray-700">
              <input type="checkbox" name="bands" value={b.value} className="rounded" />
              {b.label}
            </label>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={pending}
        className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
      >
        {pending ? "Søger i CVR…" : "Find virksomheder"}
      </button>

      {state.error && (
        <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          {state.error}
        </div>
      )}

      {state.ok && state.stats && (
        <div className="rounded border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900">
          <p className="font-medium">Færdig! 🎉</p>
          <p className="mt-1">
            {state.stats.seen} fundet · {state.stats.upserted} tilføjet ·{" "}
            {state.stats.suppressed} undertrykt (reklamebeskyttet/inaktiv).
          </p>
          <Link href="/leads" className="mt-2 inline-block font-medium underline">
            Se leads →
          </Link>
        </div>
      )}
    </form>
  );
}
