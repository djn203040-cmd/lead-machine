import type { Tables } from "@/lib/database.types";

// One Danish calendar day of dialing, from the call_stats_daily view (which
// buckets lead_calls by Europe/Copenhagen — the app never does tz math on
// timestamps, only on ready-made "YYYY-MM-DD" day strings).
export type CallDay = Tables<"call_stats_daily">;

/** Today as "YYYY-MM-DD" in Danish local time — the view's `day` format. */
export function cphToday(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Copenhagen" }).format(new Date());
}

/** "2026-08-31" → UTC-midnight Date, safe for day arithmetic on day strings. */
export function dayDate(day: string): Date {
  return new Date(`${day}T00:00:00Z`);
}

export function addDays(day: string, n: number): string {
  const d = dayDate(day);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Monday of the ISO week containing `day`, as "YYYY-MM-DD". */
export function isoWeekStart(day: string): string {
  const d = dayDate(day);
  const isoDow = (d.getUTCDay() + 6) % 7; // Mon=0 … Sun=6
  return addDays(day, -isoDow);
}
