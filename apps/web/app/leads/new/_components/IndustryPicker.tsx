"use client";

import { useMemo, useState } from "react";
import { BRANCHER, GROUPS, GROUP_OPTIONS, type Branche } from "@/lib/branchekoder";

function fold(s: string): string {
  return s.toLowerCase().replace(/å/g, "a").replace(/æ/g, "ae").replace(/ø/g, "oe");
}

const BY_GROUP: Record<string, Branche[]> = {};
for (const b of BRANCHER) (BY_GROUP[b.group] ??= []).push(b);

export default function IndustryPicker() {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Set<string>>(new Set());

  const q = fold(query.trim());
  const matches = useMemo(() => {
    if (!q) return null;
    return BRANCHER.filter(
      (b) => fold(b.label).includes(q) || fold(GROUPS[b.group]).includes(q) || b.code.includes(q),
    );
  }, [q]);

  function toggleCode(code: string) {
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(code)) n.delete(code);
      else n.add(code);
      return n;
    });
  }
  function toggleGroup(group: string, on: boolean) {
    setSelected((s) => {
      const n = new Set(s);
      for (const b of BY_GROUP[group]) {
        if (on) n.add(b.code);
        else n.delete(b.code);
      }
      return n;
    });
  }
  function toggleOpen(group: string) {
    setOpen((o) => {
      const n = new Set(o);
      if (n.has(group)) n.delete(group);
      else n.add(group);
      return n;
    });
  }

  const groupState = (group: string) => {
    const codes = BY_GROUP[group] ?? [];
    const sel = codes.filter((b) => selected.has(b.code)).length;
    return { sel, total: codes.length, all: sel === codes.length, some: sel > 0 };
  };

  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-ink">Brancher</label>

      {/* Hidden inputs the server action reads. */}
      {[...selected].map((c) => (
        <input key={c} type="hidden" name="codes" value={c} />
      ))}

      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Søg branche… (fx frisør, tømrer, restaurant)"
        className="input mb-2"
      />

      <div className="max-h-80 overflow-auto rounded-xl border border-line-strong bg-card">
        {matches ? (
          // Flat search results.
          matches.length === 0 ? (
            <p className="px-3 py-4 text-sm text-faint">Ingen brancher matcher “{query}”.</p>
          ) : (
            <ul className="divide-y divide-line">
              {matches.map((b) => (
                <li key={b.code}>
                  <label className="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm hover:bg-brand-50/50">
                    <input
                      type="checkbox"
                      checked={selected.has(b.code)}
                      onChange={() => toggleCode(b.code)}
                      className="accent-brand-700"
                    />
                    <span className="text-ink">{b.label}</span>
                    <span className="ml-auto text-xs text-faint">{GROUPS[b.group]}</span>
                  </label>
                </li>
              ))}
            </ul>
          )
        ) : (
          // Grouped accordion.
          <ul className="divide-y divide-line">
            {GROUP_OPTIONS.map((g) => {
              const st = groupState(g.value);
              const isOpen = open.has(g.value);
              return (
                <li key={g.value}>
                  <div className="flex items-center gap-2.5 px-3 py-2.5">
                    <input
                      type="checkbox"
                      checked={st.all}
                      ref={(el) => {
                        if (el) el.indeterminate = st.some && !st.all;
                      }}
                      onChange={(e) => toggleGroup(g.value, e.target.checked)}
                      className="accent-brand-700"
                      aria-label={`Vælg alle i ${g.label}`}
                    />
                    <button
                      type="button"
                      onClick={() => toggleOpen(g.value)}
                      className="flex flex-1 items-center justify-between text-left"
                    >
                      <span className="text-sm font-medium text-ink">{g.label}</span>
                      <span className="flex items-center gap-2 text-xs text-faint">
                        {st.sel > 0 && (
                          <span className="rounded-full bg-brand-100 px-2 py-0.5 font-semibold text-brand-800">
                            {st.sel}
                          </span>
                        )}
                        <span className="text-faint">{isOpen ? "▾" : "▸"}</span>
                      </span>
                    </button>
                  </div>
                  {isOpen && (
                    <ul className="border-t border-line bg-canvas/40 pb-1">
                      {(BY_GROUP[g.value] ?? []).map((b) => (
                        <li key={b.code}>
                          <label className="flex cursor-pointer items-center gap-2.5 py-1.5 pl-9 pr-3 text-sm hover:bg-brand-50/50">
                            <input
                              type="checkbox"
                              checked={selected.has(b.code)}
                              onChange={() => toggleCode(b.code)}
                              className="accent-brand-700"
                            />
                            <span className="text-ink">{b.label}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="mt-1.5 flex items-center justify-between text-xs text-faint">
        <span>
          {selected.size > 0
            ? `${selected.size} branche${selected.size === 1 ? "" : "r"} valgt`
            : "Vælg én eller flere brancher (eller en hel gruppe)."}
        </span>
        {selected.size > 0 && (
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            className="font-medium text-brand-700 hover:underline"
          >
            Ryd
          </button>
        )}
      </div>
    </div>
  );
}
