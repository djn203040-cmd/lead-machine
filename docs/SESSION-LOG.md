# Session Log & Resume Point

> **Read “▶ Resume here” first.** Session history is at the bottom (append new sessions there).

---

## ▶ Resume here (next session)

- **Project:** Lead Machine — Danish local-business lead engine (find → qualify → enrich → score). See [`PLAN.md`](../PLAN.md).
- **State:** V1 · **M0 COMPLETE** · **M1 (CVR discovery) + M3 (financial enrichment) cores BUILT against mocks** (pending live run) · **next = M2 (website qualification, #18–#21)** → then M4 (scoring).
- **Branch:** `claude/compassionate-goldberg-x7nu36` (also fast-forwarded to `main`) · latest commit = the M3 commit below.
- **Stack (locked):** Next.js 15 + Supabase (TS) `apps/web`; Python 3.11/uv worker `services/worker`; Scrapling for scraping; Claude for Danish angles.

### M1: CVR discovery ([#2](https://github.com/djn203040-cmd/lead-machine/issues/2)) — built (mock-tested)
All four work issues implemented under `services/worker/src/leadmachine/cvr/`, 32 tests green, ruff clean:
- [#14](https://github.com/djn203040-cmd/lead-machine/issues/14) **CVR ES client** — `cvr/client.py` `EsCvrClient`: Basic auth, **scroll pagination**, tenacity retries (transport + 5xx), injectable `httpx.Client` (tested via `MockTransport`). Behind the `CvrClient` Protocol (`cvr/__init__.py`). *P-unit (produktionsenhed) retrieval deferred to M3 enrichment — point the client URL at that index when needed.*
- [#15](https://github.com/djn203040-cmd/lead-machine/issues/15) **Branchekode catalog** — `cvr/branchekoder.py`: ~37 DB07 codes (6-digit CVR form) across 8 groups, Danish labels. `leadmachine categories` dumps it as JSON for the M5 filter.
- [#16](https://github.com/djn203040-cmd/lead-machine/issues/16) **Query builder** — `cvr/query.py` `SearchParameters` + `build_es_query()`: branchekode terms, postnr (discrete + ranges) / kommune OR-clause, employee band (matches monthly/quarterly/yearly cadence), status (defaults to active; explicit `[]` disables).
- [#17](https://github.com/djn203040-cmd/lead-machine/issues/17) **Discovery job** — `cvr/discovery.py` `run_discovery()` + `SupabaseLeadWriter`: upsert `leads` on_conflict `cvr_number` (idempotent dedup), raw → `lead_enrichment.cvr`, suppress `reklamebeskyttet` + non-active status. `cvr/mapper.py` flattens `Vrvirksomhed` (current/non-secret contacts, latest employment, sole-trader detection). CLI: `leadmachine discover`.
- **To run live:** get CVR creds (below) → `services/worker/.env` (`CVR_ES_USER`/`CVR_ES_PASSWORD`) → `uv run leadmachine discover -b 960210 -p 2200`.

### M3: Firmographic & financial enrichment ([#4](https://github.com/djn203040-cmd/lead-machine/issues/4)) — core built (mock-tested)
New package `services/worker/src/leadmachine/financial/`; +22 tests (54 total), ruff clean. Scope confirmed with user = **financials core + CVR owners/management; website contact-scrape deferred to M2.**
- **XBRL financials** — `client.py` `FinancialClient` reads Virk `offentliggoerelser` (**free, no auth**) → newest annual report w/ XBRL; `xbrl.py` `parse_xbrl()` extracts primary-period `fsa:GrossProfitLoss/ProfitLoss/Equity/Assets/Revenue/EmployeeBenefitsExpense/AverageNumberOfEmployees` (stdlib ElementTree, ignores prior-year + dimensional contexts).
- **Revenue estimation** — `estimate.py`: actual → gross-margin back-out → per-employee, with sector benchmarks (by catalog group, prefix fallback) + confidence. Never hard-gates.
- **Decision-makers** — `cvr/mapper.py` `extract_management()` pulls current direktion/bestyrelse/owners from `deltagerRelation` → `lead_enrichment.contact` (best-effort, CVR-only).
- **Job** — `enrich.py` `run_financial_enrichment()` + `SupabaseFinancialWriter` → `lead_enrichment.financial` + `.contact`. CLI: `leadmachine enrich-financial`.
- **Shared** — extracted `leadmachine/_http.py` (retrying httpx JSON/bytes + UA header); CVR client now uses it.
- **Live note:** sandbox blocks outbound to `distribution.virk.dk` (403); run `enrich-financial` from the worker host after a `discover` populates leads.
- **Deferred (not acceptance-gating):** website contact-scrape → M2; per-location P-units → when multi-location targeting matters.

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

- **GitHub:** `djn203040-cmd/lead-machine` · default branch `main` · current working branch `claude/compassionate-goldberg-x7nu36`.
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
- **M1 CVR discovery — code complete (mock-tested), not yet closed** ([#2]: #14–#17). Close after a live CVR-creds run confirms acceptance.
- **M3 financial enrichment — core code complete (mock-tested), not yet closed** ([#4]). Financials + revenue estimate + CVR contacts done; website contact-scrape deferred to M2. Close after a live run.
- **Open epics:** M1 [#2], M2 [#3], M3 [#4], M4 [#5], M5 [#6], M6 [#7], M7 [#8], V2 [#9].
- **Open work issues:** M2 #18–#21. (M4–M7 + V2 tasks are checklists inside their epics — expand into issues when reached.)

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

### Session 2 — 2026-06-22
- **Built M1 (CVR discovery)** entirely against mocked CVR responses (creds not yet obtained), per the resume-point instruction. New package `services/worker/src/leadmachine/cvr/`: `branchekoder.py` (#15), `query.py` (#16), `mapper.py`, `client.py` (#14), `discovery.py` (#17); facade + `CvrClient` Protocol in `__init__.py`. Config default ES URL → `cvr-permanent/virksomhed/_search`. CLI gained `discover` + `categories`.
- **Tests:** added `tests/conftest.py` (fakes + `httpx.MockTransport` scroll emulator + `tests/fixtures/cvr_companies.json`) and 5 test modules. **32 passed, ruff clean.** Verified scroll pagination, suppression (reklame + bankrupt), CVR# dedup, contact/employment mapping, query-builder clauses.
- **Scope call:** production-unit fetching (mentioned in #14 acceptance) deferred to M3 enrichment, where per-location P-numbers are actually consumed; the client supports it by pointing at the produktionsenhed index.
- **Next:** obtain CVR creds → live `discover` run to close #14–#17; then M2 (website qualification, #18–#21).

### Session 3 — 2026-06-22
- **Pushed M1 to `main`** (fast-forward `3b2e0ab..69d0f55`).
- **Built M3 (financial enrichment) core** against mocks: new `financial/` package (XBRL fetch+parse, sector revenue estimation, enrichment job + Supabase writer) + `cvr/mapper.extract_management()` for best-effort CVR decision-makers. Extracted shared `_http.py`. CLI `enrich-financial`. **+22 tests → 54 total, ruff clean.**
- **Scope confirmed w/ user:** financials core + CVR owners; **website contact-scrape deferred to M2** (needs Scrapling website-fetch infra). P-units deferred (not acceptance-gating).
- **Live note:** outbound to `distribution.virk.dk` is 403 in this sandbox; `offentliggoerelser` is free/unauth, so a worker-host run needs no creds. CVR discovery still needs the ES creds.
- **Next:** M2 (website qualification, #18–#21) to complete qualification signals, then M4 (scoring) which consumes M2 `website_need` + M3 financials.
