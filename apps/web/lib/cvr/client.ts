// CVR Elasticsearch client (server-only) — fetches company records over Basic
// auth, scrolling through results with a hard cap so it stays within a
// serverless function's time budget. TypeScript port of the worker's
// EsCvrClient (scroll loop).
//
// Free system-to-system credentials are requested from cvrselvbetjening@erst.dk.

import "server-only";
import { buildEsQuery, type SearchParameters } from "./query";

const DEFAULT_PAGE_SIZE = 500;
const SCROLL_TTL = "2m";
// Cap one in-app run so it fits Vercel's function timeout. Larger sweeps should
// run from the worker host.
export const MAX_RESULTS = 2000;

export type CvrCreds = { url: string; user: string; password: string };

export function cvrCredsFromEnv(): CvrCreds | null {
  const url =
    process.env.CVR_ES_URL ||
    "https://distribution.virk.dk/cvr-permanent/virksomhed/_search";
  const user = process.env.CVR_ES_USER ?? "";
  const password = process.env.CVR_ES_PASSWORD ?? "";
  if (!user || !password) return null;
  return { url, user, password };
}

function scrollEndpoint(searchUrl: string): string {
  const u = new URL(searchUrl);
  return `${u.protocol}//${u.host}/_search/scroll`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = any;

async function post(url: string, auth: string, body: Json): Promise<Json> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: auth,
      "User-Agent": "lead-machine/1.0",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`CVR ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

/** Fetch raw `Vrvirksomhed` records matching `params` (capped at MAX_RESULTS). */
export async function fetchCvrCompanies(
  params: SearchParameters,
  creds: CvrCreds,
  maxResults: number = MAX_RESULTS,
): Promise<Json[]> {
  const auth = `Basic ${Buffer.from(`${creds.user}:${creds.password}`).toString("base64")}`;
  const query = buildEsQuery(params);
  const scrollUrl = scrollEndpoint(creds.url);

  const out: Json[] = [];
  let data = await post(`${creds.url}?scroll=${SCROLL_TTL}`, auth, {
    size: DEFAULT_PAGE_SIZE,
    query,
  });
  let scrollId: string | undefined = data?._scroll_id;

  try {
    while (out.length < maxResults) {
      const hits = data?.hits?.hits ?? [];
      if (!hits.length) break;
      for (const hit of hits) {
        const source = hit?._source ?? {};
        out.push(source?.Vrvirksomhed ?? source);
        if (out.length >= maxResults) break;
      }
      if (!scrollId || out.length >= maxResults) break;
      data = await post(scrollUrl, auth, { scroll: SCROLL_TTL, scroll_id: scrollId });
      scrollId = data?._scroll_id ?? scrollId;
    }
  } finally {
    if (scrollId) {
      // Best-effort release of the server-side scroll context.
      fetch(scrollUrl, {
        method: "DELETE",
        headers: { "Content-Type": "application/json", Authorization: auth },
        body: JSON.stringify({ scroll_id: [scrollId] }),
      }).catch(() => {});
    }
  }
  return out;
}
