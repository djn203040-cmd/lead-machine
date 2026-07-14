"use client";

import { useRouter } from "next/navigation";
import { GROUP_OPTIONS } from "@/lib/branchekoder";
import { PIPELINE_STATUSES, PIPELINE_META, WEBSITE_NEED_OPTIONS } from "@/lib/leadmeta";
import { PHONE_TYPE_OPTIONS } from "@/lib/phone";

export type LeadFilters = {
  q: string;
  group: string;
  need: string;
  status: string;
  minScore: string;
  phoneType: string;
  view: string;
};

const SCORE_OPTIONS = [
  { value: "", label: "Alle scorer" },
  { value: "75", label: "75+" },
  { value: "50", label: "50+" },
  { value: "25", label: "25+" },
];

const selectClass = "select w-auto";

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
      className="card card-pad mb-6 flex flex-wrap items-center gap-2.5"
    >
      {/* Keep the active Beriget/Ikke-beriget tab when filters change. */}
      <input type="hidden" name="view" value={filters.view} />

      <div className="relative min-w-48 flex-1">
        <svg
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden
        >
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="m20 20-3.2-3.2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <input
          type="search"
          name="q"
          defaultValue={filters.q}
          placeholder="Søg virksomhed…"
          className="input pl-9"
        />
      </div>

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
        name="phoneType"
        defaultValue={filters.phoneType}
        onChange={(e) => submit(e.currentTarget.form!)}
        className={selectClass}
      >
        <option value="">Alle numre</option>
        {PHONE_TYPE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
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

      <button type="submit" className="btn btn-primary">
        Søg
      </button>
    </form>
  );
}
