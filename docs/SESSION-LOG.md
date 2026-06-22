# Session Log & Resume Point

> **Read “▶ Resume here” first.** Session history is at the bottom (append new sessions there).

---

## ▶ Resume here (next session)

- **Project:** Lead Machine — Danish local-business lead engine (find → qualify → enrich → score). See [`PLAN.md`](../PLAN.md).
- **State:** V1 · **M0 (foundation) COMPLETE** · **next = M1 (CVR discovery)**.
- **Branch:** `claude/dazzling-hypatia-w3seu6` · latest commit `abb869f`.
- **Stack (locked):** Next.js 15 + Supabase (TS) `apps/web`; Python 3.11/uv worker `services/worker`; Scrapling for scraping; Claude for Danish angles.

### Next task — M1: CVR discovery ([#2](https://github.com/djn203040-cmd/lead-machine/issues/2))
Build the engine that finds Danish businesses by branchekode + area and writes deduped leads:
- [#14](https://github.com/djn203040-cmd/lead-machine/issues/14) **CVR Elasticsearch client** — `distribution.virk.dk/cvr-permanent/_search`, Basic auth, scroll/pagination, behind an interface (`services/worker/src/leadmachine/cvr/__init__.py` already has the `CvrClient` Protocol). **Build against a mocked CVR response so it's testable before creds arrive.**
- [#15](https://github.com/djn203040-cmd/lead-machine/issues/15) **Branchekode catalog** — map local-business types → DB07 codes (hairdresser 96.02.10, restaurant 56.10.10, plumber 43.22.00, dentist 86.23.00, gym 93.13.00, …) with Danish labels.
- [#16](https://github.com/djn203040-cmd/lead-machine/issues/16) **Query builder** — `searches.parameters` → ES query (branchekode, kommune/postnr, employee band, status).
- [#17](https://github.com/djn203040-cmd/lead-machine/issues/17) **Discovery job** — upsert `leads` (dedup by `cvr_number`), store raw payload in `lead_enrichment.cvr`, **suppress `reklamebeskyttet` + inactive/bankrupt/dissolved**.

### To run the project locally
```bash
corepack enable && pnpm install        # or: bash scripts/setup.sh
# apps/web/.env.local  (values below — non-secret)
pnpm --filter web dev                  # http://localhost:3000  (redirects to /login)

cd services/worker && uv sync
# services/worker/.env  (add the SECRET service_role key — see below)
uv run leadmachine hello               # smoke test
```

### Blockers / external things to obtain
| Need | For | How |
|---|---|---|
| **CVR system-to-system creds** (free) | M1 #14 | Email `cvrselvbetjening@erst.dk`, sign the protection-marking declaration → user/password |
| **Supabase `service_role` key** (secret) | worker → DB | Dashboard → Project Settings → API → `service_role`; put in `services/worker/.env` (NOT committed) |
| **PageSpeed Insights API key** (free) | M2 | Google Cloud console → enable PageSpeed Insights API |
| **Anthropic API key** | M6 | console.anthropic.com |

---

## Key resources

- **GitHub:** `djn203040-cmd/lead-machine` · default branch = working branch `claude/dazzling-hypatia-w3seu6`.
- **Supabase project (this app):** name `lead-machine`, ref **`dxkxamlwucknndcqqtrj`**, region `eu-north-1`, org **Conversiatech** (`aytobdmpximsadxjnknj`), **~$10/mo**.
  - URL: `https://dxkxamlwucknndcqqtrj.supabase.co`
  - Publishable (anon) key — *non-secret, safe to expose*: `sb_publishable_VimnnrFRb7jkvWlaoAA5Lg_2Dx87Duy`
  - `service_role` key: **NOT stored here** — copy from dashboard when needed.
- **Related existing Supabase projects (context, not used by this app):**
  - `C&C leadforge` (`ftzzddahxjopfhbbwyer`) — earlier lead-gen prototype (scored for ads/video, different ICP).
  - `Outreach Tracker` (`dmmvgabwbamcyoxguxwp`) — 2,498 leads; ⚠️ **RLS disabled** on all tables (separate cleanup, not in this repo).

## Decisions locked (don't relitigate)

1. **Discovery = free official CVR register**, not Google Maps scraping (Places `websiteUri` is Enterprise $20/1k since the $200 credit ended; SerpAPI is under active Google lawsuit). CVR# is the dedup key.
2. **Free-first** data: CVR + Scrapling + PageSpeed + XBRL. Paid (datacvrapi.dk / Risika, reviews APIs) deferred.
3. **Reviews/ratings (Google/Trustpilot/Facebook) = V2.** ([#9](https://github.com/djn203040-cmd/lead-machine/issues/9))
4. **Outreach is phone-first** — Danish Markedsføringsloven §10 bans cold B2B *email* without consent; cold *calls* to companies are allowed. Suppress `reklamebeskyttelse` + Robinson-list (sole traders).
5. **Scoring is inverted vs the old leadforge** — weights: website-need 45 / budget 20 / presence 15 / industry 12 / recency 8. `no/dead/parked/facebook-only/bad site` = best lead.
6. **Revenue is often legally undisclosed** (klasse B reports *bruttofortjeneste*) → estimate from sector × employees; never hard-gate on revenue.
7. **Scrapling** is for business-website + DK-directory scraping (light anti-bot), **not** Google Maps. ~58% bypass rate → retry + StealthyFetcher fallback.

## Milestone / issue map

- **M0 Foundation — ✅ closed** ([#1](https://github.com/djn203040-cmd/lead-machine/issues/1): #10, #11, #12, #13).
- **Open epics:** M1 [#2], M2 [#3], M3 [#4], M4 [#5], M5 [#6], M6 [#7], M7 [#8], V2 [#9].
- **Open work issues:** M1 #14–#17, M2 #18–#21. (M3–M7 + V2 tasks are checklists inside their epics — expand into issues when reached.)

## Schema cheat-sheet (`supabase/migrations/0001_init.sql`)

`searches` → `leads` (CVR# unique; `website_need`, `pipeline_status`, `score` first-class) → `lead_enrichment` (jsonb: cvr/website/financial/social/contact) · `lead_scores` · `scoring_criteria` (11 seeded) · `lead_angles` · `lead_notes` · `lead_followups` · `jobs` (worker queue). RLS on all; `authenticated full access` policy (internal tool). Regenerate web types after schema changes: `supabase gen types typescript --project-id dxkxamlwucknndcqqtrj > apps/web/lib/database.types.ts`.

---

## Session history

### Session 1 — 2026-06-22
- Researched the Danish lead-gen landscape (CVR/XBRL, employee data, §10/GDPR, Scrapling vs Apify/Outscraper/SerpAPI/Places, website-quality scoring, Trustpilot, Facebook, contact enrichment) → [`RESEARCH-lead-qualification-2026.md`](../RESEARCH-lead-qualification-2026.md).
- Wrote [`PLAN.md`](../PLAN.md); created 9 milestone epics + 12 work issues on GitHub.
- **Built & shipped M0:** monorepo scaffold, Supabase project provisioned (eu-north-1) + schema/RLS/seed applied, typed client wired, CI green. Commits `cbaff15` (plan), `e0feb1d` (scaffold), `abb869f` (provision + typed client).
- Decisions: reviews → V2; phone-first; free-first; CVR-as-discovery.
- **Stopped at:** M0 done, ready to start M1. SessionStart hook was blocked by the auto-mode classifier (agent self-config) — using `scripts/setup.sh` instead.
