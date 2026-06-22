// Branchekode catalog (groups) for the leads filter.
//
// Mirrors services/worker/src/leadmachine/cvr/branchekoder.py — keep the two in
// sync. The worker is the source of truth (it writes leads.branchekode in the
// 6-digit CVR form, e.g. "960210"); here we only need the grouping so the
// dashboard can offer a grouped branche filter and render a group badge.

export type BranchekodeGroup =
  | "food_drink"
  | "beauty_wellness"
  | "health"
  | "trades"
  | "auto"
  | "retail"
  | "professional"
  | "leisure";

export const GROUPS: Record<BranchekodeGroup, string> = {
  food_drink: "Mad & drikke",
  beauty_wellness: "Skønhed & velvære",
  health: "Sundhed",
  trades: "Håndværk & bygge",
  auto: "Auto",
  retail: "Detailhandel",
  professional: "Liberale erhverv",
  leisure: "Sport & fritid",
};

// 6-digit CVR code -> group.
export const CODE_GROUP: Record<string, BranchekodeGroup> = {
  // Mad & drikke
  "561010": "food_drink",
  "561020": "food_drink",
  "563000": "food_drink",
  "562100": "food_drink",
  "562900": "food_drink",
  "107100": "food_drink",
  // Skønhed & velvære
  "960210": "beauty_wellness",
  "960220": "beauty_wellness",
  "960400": "beauty_wellness",
  "960900": "beauty_wellness",
  // Sundhed
  "862300": "health",
  "862100": "health",
  "862200": "health",
  "869010": "health",
  "869090": "health",
  "750000": "health",
  // Håndværk & bygge
  "432200": "trades",
  "432100": "trades",
  "433200": "trades",
  "433410": "trades",
  "433420": "trades",
  "439100": "trades",
  "813000": "trades",
  "812100": "trades",
  // Auto
  "452010": "auto",
  "451110": "auto",
  // Detailhandel
  "477810": "retail",
  "477620": "retail",
  "472200": "retail",
  "477100": "retail",
  "477700": "retail",
  // Liberale erhverv
  "683110": "professional",
  "691010": "professional",
  "692020": "professional",
  "742000": "professional",
  "855300": "professional",
  // Sport & fritid
  "931300": "leisure",
  "931200": "leisure",
};

export function normalizeCode(code: string): string {
  return code.replace(/[.\s]/g, "").trim();
}

export function groupForCode(code: string | null | undefined): BranchekodeGroup | null {
  if (!code) return null;
  return CODE_GROUP[normalizeCode(code)] ?? null;
}

export function groupLabel(code: string | null | undefined): string | null {
  const group = groupForCode(code);
  return group ? GROUPS[group] : null;
}

export function codesInGroup(group: string): string[] {
  return Object.entries(CODE_GROUP)
    .filter(([, g]) => g === group)
    .map(([code]) => code);
}

export const GROUP_OPTIONS: { value: BranchekodeGroup; label: string }[] = (
  Object.keys(GROUPS) as BranchekodeGroup[]
).map((value) => ({ value, label: GROUPS[value] }));
