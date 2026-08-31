import Link from "next/link";
import { type CallDay, addDays, cphToday, dayDate, isoWeekStart } from "@/lib/callstats";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

// Call activity stats, all derived from the call_stats_daily view (one row per
// Danish calendar day). "Svar" = every dial that wasn't "intet svar".

const DAY_FMT = new Intl.DateTimeFormat("da-DK", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});
const RANGE_FMT = new Intl.DateTimeFormat("da-DK", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

function isoWeekNumber(weekStart: string): number {
  const thu = dayDate(addDays(weekStart, 3));
  const yearStart = Date.UTC(thu.getUTCFullYear(), 0, 1);
  return Math.ceil(((thu.getTime() - yearStart) / 86_400_000 + 1) / 7);
}

const EMPTY = { calls: 0, no_answer: 0, contacted: 0, meetings: 0, lost: 0, discarded: 0 };
type Totals = typeof EMPTY;

function add(a: Totals, b: Totals): Totals {
  return {
    calls: a.calls + b.calls,
    no_answer: a.no_answer + b.no_answer,
    contacted: a.contacted + b.contacted,
    meetings: a.meetings + b.meetings,
    lost: a.lost + b.lost,
    discarded: a.discarded + b.discarded,
  };
}

const answered = (t: Totals) => t.calls - t.no_answer;
const pct = (part: number, whole: number) =>
  whole > 0 ? `${Math.round((part / whole) * 100)} %` : "—";

function Tile({ value, label, detail }: { value: React.ReactNode; label: string; detail?: string }) {
  return (
    <div className="card card-pad">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums text-ink">{value}</p>
      {detail && <p className="mt-0.5 text-xs text-faint">{detail}</p>}
    </div>
  );
}

const TH = "px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted";
const TD = "px-4 py-2.5 text-sm tabular-nums";

export default async function StatsPage() {
  const supabase = await createClient();
  const { data } = await supabase
    .from("call_stats_daily")
    .select("day, calls, no_answer, contacted, meetings, lost, discarded")
    .order("day", { ascending: false })
    .limit(400)
    .returns<CallDay[]>();
  const byDay = new Map((data ?? []).map((r) => [r.day, r]));

  const today = cphToday();
  const weekStart = isoWeekStart(today);

  // Last 14 days, today first, zero-filled so quiet days stay visible.
  const days = Array.from({ length: 14 }, (_, i) => {
    const day = addDays(today, -i);
    return { day, ...(byDay.get(day) ?? EMPTY) };
  });

  // Last 8 ISO weeks, current week first, summed from the daily rows.
  const weeks = Array.from({ length: 8 }, (_, i) => {
    const start = addDays(weekStart, -7 * i);
    let totals = EMPTY;
    for (let d = 0; d < 7; d++) {
      const row = byDay.get(addDays(start, d));
      if (row) totals = add(totals, row);
    }
    return { start, end: addDays(start, 6), ...totals };
  });

  const todayT = days[0];
  const weekT = weeks[0];
  const allT = (data ?? []).reduce<Totals>((acc, r) => add(acc, r), EMPTY);
  const maxDay = Math.max(1, ...days.map((d) => d.calls));

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">Statistik</h1>
          <p className="mt-1 text-sm text-muted">
            Opkaldsaktivitet — dagen nulstilles ved midnat, uger er man–søn.
          </p>
        </div>
        <Link href="/leads/dialer" className="btn btn-primary">
          Til powerdialer
        </Link>
      </div>

      {allT.calls === 0 ? (
        <div className="card flex flex-col items-center gap-2 px-6 py-16 text-center">
          <h2 className="text-lg font-semibold text-ink">Ingen opkald logget endnu</h2>
          <p className="max-w-sm text-sm text-muted">
            Hvert udfald du logger i poweropkalderen (også &laquo;intet svar&raquo;) tæller
            med her.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Tile
              value={todayT.calls}
              label="Opkald i dag"
              detail={`${answered(todayT)} svar · ${todayT.meetings} møder`}
            />
            <Tile
              value={weekT.calls}
              label="Denne uge"
              detail={`${answered(weekT)} svar · uge ${isoWeekNumber(weekStart)}`}
            />
            <Tile
              value={weekT.meetings}
              label="Møder denne uge"
              detail={`${allT.meetings} i alt`}
            />
            <Tile
              value={pct(answered(weekT), weekT.calls)}
              label="Svarprocent (uge)"
              detail={`${pct(weekT.meetings, answered(weekT))} af svar blev til møde`}
            />
          </div>

          <section className="card mt-5 overflow-hidden">
            <h2 className="border-b border-line px-4 py-3 text-sm font-semibold text-ink">
              Seneste 14 dage
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[26rem]">
                <thead>
                  <tr className="border-b border-line">
                    <th className={TH}>Dag</th>
                    <th className={`${TH} w-full`}>Opkald</th>
                    <th className={`${TH} text-right`}>Svar</th>
                    <th className={`${TH} text-right`}>Møder</th>
                  </tr>
                </thead>
                <tbody>
                  {days.map((d) => (
                    <tr key={d.day} className="border-b border-line/60 last:border-0">
                      <td className={`${TD} whitespace-nowrap ${d.day === today ? "font-semibold text-ink" : "text-muted"}`}>
                        {d.day === today ? "I dag" : DAY_FMT.format(dayDate(d.day))}
                      </td>
                      <td className={`${TD} w-full`}>
                        <div className="flex items-center gap-2">
                          <div
                            className="h-2 shrink-0 rounded-full bg-brand-600"
                            style={{ width: `${(d.calls / maxDay) * 70}%`, minWidth: d.calls > 0 ? "0.5rem" : "0" }}
                            aria-hidden
                          />
                          <span className="text-ink">{d.calls}</span>
                        </div>
                      </td>
                      <td className={`${TD} text-right text-muted`}>{answered(d)}</td>
                      <td className={`${TD} text-right ${d.meetings > 0 ? "font-medium text-teal-fg" : "text-muted"}`}>
                        {d.meetings}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="card mt-5 overflow-hidden">
            <h2 className="border-b border-line px-4 py-3 text-sm font-semibold text-ink">
              Uge for uge
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[34rem]">
                <thead>
                  <tr className="border-b border-line">
                    <th className={TH}>Uge</th>
                    <th className={`${TH} text-right`}>Opkald</th>
                    <th className={`${TH} text-right`}>Svar</th>
                    <th className={`${TH} text-right`}>Møder</th>
                    <th className={`${TH} text-right`}>Svar-%</th>
                    <th className={`${TH} text-right`}>Møde-% af svar</th>
                  </tr>
                </thead>
                <tbody>
                  {weeks.map((w, i) => (
                    <tr key={w.start} className="border-b border-line/60 last:border-0">
                      <td className={`${TD} whitespace-nowrap ${i === 0 ? "font-semibold text-ink" : "text-muted"}`}>
                        Uge {isoWeekNumber(w.start)}
                        <span className="ml-1.5 text-xs text-faint">
                          {RANGE_FMT.format(dayDate(w.start))}–{RANGE_FMT.format(dayDate(w.end))}
                        </span>
                      </td>
                      <td className={`${TD} text-right text-ink`}>{w.calls}</td>
                      <td className={`${TD} text-right text-muted`}>{answered(w)}</td>
                      <td className={`${TD} text-right ${w.meetings > 0 ? "font-medium text-teal-fg" : "text-muted"}`}>
                        {w.meetings}
                      </td>
                      <td className={`${TD} text-right text-muted`}>{pct(answered(w), w.calls)}</td>
                      <td className={`${TD} text-right text-muted`}>{pct(w.meetings, answered(w))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="border-t border-line px-4 py-2.5 text-xs text-faint">
              Svar = alle loggede opkald minus &laquo;intet svar&raquo;. Alle udfald du logger i
              poweropkalderen tæller som ét opkald.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
