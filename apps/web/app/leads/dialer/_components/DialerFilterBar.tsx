"use client";

import { useRouter } from "next/navigation";
import { GROUP_OPTIONS } from "@/lib/branchekoder";
import { PHONE_TYPE_OPTIONS } from "@/lib/phone";

export type DialerFilters = {
  scope: string;
  group: string;
  phoneType: string;
  minScore: string;
};

const SCORE_OPTIONS = [
  { value: "", label: "Alle scorer" },
  { value: "75", label: "75+" },
  { value: "50", label: "50+" },
  { value: "25", label: "25+" },
];

const selectClass = "select w-auto";

// Narrow the ring list before a session — mainly by branche, so a calling
// block can stick to one industry and reuse the same pitch rhythm.
export default function DialerFilterBar({ filters }: { filters: DialerFilters }) {
  const router = useRouter();

  function apply(patch: Partial<DialerFilters>) {
    const next = { ...filters, ...patch };
    const params = new URLSearchParams();
    if (next.scope === "all") params.set("scope", "all");
    if (next.group) params.set("group", next.group);
    if (next.phoneType) params.set("phoneType", next.phoneType);
    if (next.minScore) params.set("minScore", next.minScore);
    const qs = params.toString();
    router.push(qs ? `/leads/dialer?${qs}` : "/leads/dialer");
  }

  return (
    <div className="card card-pad mb-5 flex flex-wrap items-center gap-2.5">
      <select
        value={filters.group}
        onChange={(e) => apply({ group: e.target.value })}
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
        value={filters.phoneType}
        onChange={(e) => apply({ phoneType: e.target.value })}
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
        value={filters.minScore}
        onChange={(e) => apply({ minScore: e.target.value })}
        className={selectClass}
      >
        {SCORE_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
