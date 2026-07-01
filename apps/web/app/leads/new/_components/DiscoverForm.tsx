"use client";

import { useActionState, useEffect, useState, useTransition } from "react";
import Link from "next/link";
import IndustryPicker from "./IndustryPicker";
import LocationPicker from "./LocationPicker";
import { discoverAction, type DiscoverState } from "../actions";
import { enqueueEnrichment, skipEnrichment } from "../../enrichment-actions";

const BANDS: { value: string; label: string }[] = [
  { value: "ANTAL_1_1", label: "1" },
  { value: "ANTAL_2_4", label: "2–4" },
  { value: "ANTAL_5_9", label: "5–9" },
  { value: "ANTAL_10_19", label: "10–19" },
  { value: "ANTAL_20_49", label: "20–49" },
  { value: "ANTAL_50_99", label: "50–99" },
];

export default function DiscoverForm() {
  const [state, action, pending] = useActionState<DiscoverState, FormData>(discoverAction, {});

  // Post-discovery enrich? prompt for the run's new/undecided leads.
  const [promptIds, setPromptIds] = useState<string[] | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [busy, startTransition] = useTransition();

  useEffect(() => {
    if (state.ok && state.pendingLeadIds && state.pendingLeadIds.length > 0) {
      setPromptIds(state.pendingLeadIds);
      setOutcome(null);
    }
  }, [state]);

  function decide(enrich: boolean) {
    const ids = promptIds ?? [];
    startTransition(async () => {
      const res = enrich ? await enqueueEnrichment(ids) : await skipEnrichment(ids);
      if (res.error) {
        setOutcome(`Kunne ikke opdatere: ${res.error}`);
      } else if (enrich) {
        setOutcome(
          `${res.count ?? ids.length} lead(s) sat i kø. De beriges automatisk om få minutter.`,
        );
      } else {
        setOutcome(`${res.count ?? ids.length} lead(s) gemt uden berigelse.`);
      }
      setPromptIds(null);
    });
  }

  return (
    <form action={action} className="space-y-6">
      <IndustryPicker />

      <LocationPicker />

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
          {outcome && <p className="mt-2 font-medium">{outcome}</p>}
          <Link href="/leads" className="mt-2 inline-block font-semibold text-brand-700 underline">
            Se leads →
          </Link>
        </div>
      )}

      {promptIds && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="enrich-prompt-title"
        >
          <div className="card card-pad w-full max-w-md">
            <h2 id="enrich-prompt-title" className="text-lg font-semibold text-ink">
              Berig {promptIds.length} nye lead{promptIds.length === 1 ? "" : "s"}?
            </h2>
            <p className="mt-2 text-sm text-muted">
              Berigelse tjekker hjemmeside, henter regnskab/omsætning, scorer leadet og
              genererer en dansk salgsvinkel. Det kører automatisk i baggrunden og tager
              typisk et par minutter.
            </p>
            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => decide(true)}
                disabled={busy}
                className="btn btn-primary flex-1"
              >
                {busy ? "Sætter i kø…" : "Ja, berig"}
              </button>
              <button
                type="button"
                onClick={() => decide(false)}
                disabled={busy}
                className="btn btn-secondary flex-1"
              >
                Nej, ikke nu
              </button>
            </div>
          </div>
        </div>
      )}
    </form>
  );
}
