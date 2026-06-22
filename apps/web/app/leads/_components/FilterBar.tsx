"use client";

import { useRouter } from "next/navigation";
import { GROUP_OPTIONS } from "@/lib/branchekoder";
import { PIPELINE_STATUSES, PIPELINE_META, WEBSITE_NEED_OPTIONS } from "@/lib/leadmeta";

export type LeadFilters = {
  q: string;
  group: string;
  need: string;
  status: string;
  minScore: string;
};

const SCORE_OPTIONS = [
  { value: "", label: "Alle scorer" },
  { value: "75", label: "75+" },
  { value: "50", label: "50+" },
  { value: "25", label: "25+" },
];

const selectClass = "rounded border bg-white px-2 py-1.5 text-sm";

export default function FilterBar({ filters }: { filters: LeadFilters }) {
  const router = useRouter();

  function submit(form: HTMLFormElement) {
    const data = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of data.entries()) {
      const v = String(value).trim();
      if (v) params.set(key, v);
    }
    // any filter change resets pagination
    const qs = params.toString();
    router.push(qs ? `/leads?${qs}` : "/leads");
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit(e.currentTarget);
      }}
      className="mb-5 flex flex-wrap items-center gap-2"
    >
      <input
        type="search"
        name="q"
        defaultValue={filters.q}
        placeholder="Søg virksomhed…"
        className="min-w-48 flex-1 rounded border px-3 py-1.5 text-sm"
      />

      <select
        name="group"
        defaultValue={filters.group}
        onChange={(e) => submit(e.currentTarget.form!)}
        className={selectClass}
      >
        <option value="">Alle brancher</option>
        {GROUP_OPTIONS.map((g) => (
          <option key={g.value} value={g.value}>
            {g.label}
          </option>
        ))}
      </select>

      <select
        name="need"
        defaultValue={filters.need}
        onChange={(e) => submit(e.currentTarget.form!)}
        className={selectClass}
      >
        <option value="">Alle hjemmesidebehov</option>
        {WEBSITE_NEED_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <select
        name="status"
        defaultValue={filters.status}
        onChange={(e) => submit(e.currentTarget.form!)}
        className={selectClass}
      >
        <option value="">Alle statusser</option>
        {PIPELINE_STATUSES.map((s) => (
          <option key={s} value={s}>
            {PIPELINE_META[s].label}
          </option>
        ))}
      </select>

      <select
        name="minScore"
        defaultValue={filters.minScore}
        onChange={(e) => submit(e.currentTarget.form!)}
        className={selectClass}
      >
        {SCORE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <button
        type="submit"
        className="rounded bg-black px-3 py-1.5 text-sm font-medium text-white"
      >
        Søg
      </button>
    </form>
  );
}
