"use client";

import { useMemo, useRef, useState } from "react";
import {
  searchLocations,
  resolveLocations,
  type LocationOption,
} from "@/lib/geo";

const KIND_BADGE: Record<LocationOption["kind"], string> = {
  region: "Region",
  kommune: "Kommune",
  by: "By",
};

// Parse the free-text postal fallback ("2200 8000, 9000") into numbers.
function parseRawPostnumre(raw: string): number[] {
  return raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isInteger(n) && n >= 1000 && n <= 9999);
}

export default function LocationPicker() {
  const [selected, setSelected] = useState<LocationOption[]>([]);
  const [query, setQuery] = useState("");
  const [raw, setRaw] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedIds = useMemo(() => new Set(selected.map((s) => s.id)), [selected]);
  const results = useMemo(() => {
    if (!query.trim()) return [];
    return searchLocations(query).filter((o) => !selectedIds.has(o.id));
  }, [query, selectedIds]);

  // Resolve everything the form will submit (chips + raw fallback) for the count.
  const resolved = useMemo(() => {
    const fromChips = resolveLocations(selected.map((s) => s.id));
    const fromRaw = parseRawPostnumre(raw);
    const postnumre = new Set([...fromChips.postnumre, ...fromRaw]);
    return { postnumre, kommunekoder: new Set(fromChips.kommunekoder) };
  }, [selected, raw]);

  function add(o: LocationOption) {
    setSelected((s) => [...s, o]);
    setQuery("");
    setActive(0);
    inputRef.current?.focus();
  }
  function remove(id: string) {
    setSelected((s) => s.filter((o) => o.id !== id));
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      e.preventDefault();
      add(results[active]);
    } else if (e.key === "Backspace" && !query && selected.length) {
      remove(selected[selected.length - 1].id);
    }
  }

  const hasLocation = resolved.postnumre.size > 0 || resolved.kommunekoder.size > 0;

  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-ink">Område</label>

      {/* Hidden inputs the server action reads. */}
      {[...resolved.postnumre].map((n) => (
        <input key={`p${n}`} type="hidden" name="postnumre" value={n} />
      ))}
      {[...resolved.kommunekoder].map((k) => (
        <input key={`k${k}`} type="hidden" name="kommunekoder" value={k} />
      ))}

      {/* Chips + search input */}
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-line-strong bg-card p-2 focus-within:border-brand-500">
        {selected.map((o) => (
          <span
            key={o.id}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-sm text-brand-800"
          >
            <span className="text-[10px] font-semibold uppercase tracking-wide text-brand-600">
              {KIND_BADGE[o.kind]}
            </span>
            {o.label}
            <button
              type="button"
              onClick={() => remove(o.id)}
              className="ml-0.5 text-brand-600 hover:text-brand-900"
              aria-label={`Fjern ${o.label}`}
            >
              ✕
            </button>
          </span>
        ))}
        <div className="relative min-w-[8rem] flex-1">
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActive(0);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            onKeyDown={onKeyDown}
            placeholder={selected.length ? "Tilføj flere…" : "Søg by, kommune eller region…"}
            className="w-full bg-transparent px-1 py-1 text-sm text-ink outline-none placeholder:text-faint"
          />
          {open && results.length > 0 && (
            <ul className="absolute left-0 right-0 top-full z-20 mt-1 max-h-72 overflow-auto rounded-xl border border-line-strong bg-card py-1 shadow-lg">
              {results.map((o, i) => (
                <li key={o.id}>
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => add(o)}
                    onMouseEnter={() => setActive(i)}
                    className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm ${
                      i === active ? "bg-brand-50" : ""
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="w-14 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-faint">
                        {KIND_BADGE[o.kind]}
                      </span>
                      <span className="text-ink">{o.label}</span>
                    </span>
                    <span className="shrink-0 text-xs text-faint">{o.sublabel}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <details className="mt-2">
        <summary className="cursor-pointer text-xs text-faint hover:text-ink">
          Eller indtast postnumre manuelt
        </summary>
        <input
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder="f.eks. 2200 8000 9000"
          className="input mt-2"
        />
      </details>

      <p className="mt-1.5 text-xs text-faint">
        {hasLocation ? (
          <>
            Søger i{" "}
            {resolved.postnumre.size > 0 && `${resolved.postnumre.size} postnr.`}
            {resolved.postnumre.size > 0 && resolved.kommunekoder.size > 0 && " + "}
            {resolved.kommunekoder.size > 0 && `${resolved.kommunekoder.size} kommune(r)`}.
          </>
        ) : (
          "Vælg mindst ét område, eller indtast postnumre manuelt."
        )}
      </p>
    </div>
  );
}
