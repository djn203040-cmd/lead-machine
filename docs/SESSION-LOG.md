# Session Log & Resume Point

> **Read “▶ Resume here” first.** Session history is at the bottom (append new sessions there).

---

## ▶ Resume here (next session)

- **Project:** Lead Machine — Danish local-business lead engine (find → qualify → enrich → score). See [`PLAN.md`](../PLAN.md).
- **State:** V1 · **M0 COMPLETE** · **M1 (discovery) + M2 (website qualification) + M3 (financial enrichment) cores BUILT against mocks** (pending live run) · **next = M4 (scoring & qualification gate, #5)**.
- **Branch:** `claude/compassionate-goldberg-x7nu36` == `main`, both at **`4fe09d1`** (M1+M2+M3 all on main, working tree clean).
- **Stack (locked):** Next.js 15 + Supabase (TS) `apps/web`; Python 3.11/uv worker `services/worker`; Scrapling for scraping; Claude for Danish angles.

### ▶ Next task — M4: scoring & qualification gate ([#5](https://github.com/djn203040-cmd/lead-machine/issues/5))
Turn the enriched signals into a 0–100 "needs a website now" score + ranking. All inputs already exist on `leads` + `lead_enrichment`; this is pure computation (no new network), so build + test it fully here (no live blockers).

- **Suggested layout:** new `services/worker/src/leadmachine/scoring/` — `models.py` (`LeadToScore`, `ScoreBreakdown`), `rubric.py` (per-factor functions + weights), `score.py` (`score_lead()` → total+breakdown; `run_scoring()` + `SupabaseScoreWriter`), CLI `score`.
- **Rubric (PLAN §5 / research §3), weights sum 100:**
  - **Website-need 45** ← `leads.website_need`: none/dead/parked/facebook_only = 45; `bad` from `lead_enrichment.website.signals` (no viewport +12, no https +10, legacy +8, old copyright +6, PSI perf <50 +6 / 50–69 +3, one-page +3, cap 45); `outdated` mid; `modern` ~0–5.
  - **Budget 20** ← `leads.employees_band`/`employees_exact` (1→4, 2–4→10, 5–9→16, 10–49→20, 50+→14, 0→4) + `lead_enrichment.financial` revenue/equity bump.
  - **Presence 15** ← `lead_enrichment.social` (has_fb_page / has_meta_pixel). *(Reviews are V2 — presence in V1 = social only.)*
  - **Industry 12** ← `leads.branchekode` via `cvr.branchekoder` group (local-service →12, marginal →6, poor →0).
  - **Recency 8** ← active CVR status (already gated at discovery) + `founded_at`; reviews-recency is V2.
- **Hard gate:** `reklamebeskyttet`/inactive are already suppressed at discovery, but encode the gate defensively (score 0 / skip).
- **Persistence:** update `leads.score` + upsert `lead_scores` (total + `breakdown` jsonb + scored_at). Make weights honor `scoring_criteria` (11 seeded rows) so they're tunable without code.
- **Then:** M5 leads dashboard (#6) surfaces ranked leads; M6 Claude angles (#7); M7 compliance/deploy (#8).

### Built so far (mock-tested, all on main)

### M1: CVR discovery ([#2](https://github.com/djn203040-cmd/lead-machine/issues/2)) — built (mock-tested)
All four work issues implemented under `services/worker/src/leadmachine/cvr/`, 32 tests green, ruff clean:
- [#14](https://github.com/djn203040-cmd/lead-machine/issues/14) **CVR ES client** — `cvr/client.py` `EsCvrClient`: Basic auth, **scroll pagination**, tenacity retries (transport + 5xx), injectable `httpx.Client` (tested via `MockTransport`). Behind the `CvrClient` Protocol (`cvr/__init__.py`). *P-unit (produktionsenhed) retrieval deferred to M3 enrichment — point the client URL at that index when needed.*
- [#15](https://github.com/djn203040-cmd/lead-machine/issues/15) **Branchekode catalog** — `cvr/branchekoder.py`: ~37 DB07 codes (6-digit CVR form) across 8 groups, Danish labels. `leadmachine categories` dumps it as JSON for the M5 filter.
- [#16](https://github.com/djn203040-cmd/lead-machine/issues/16) **Query builder** — `cvr/query.py` `SearchParameters` + `build_es_query()`: branchekode terms, postnr (discrete + ranges) / kommune OR-clause, employee band (matches monthly/quarterly/yearly cadence), status (defaults to active; explicit `[]` disables).
- [#17](https://github.com/djn203040-cmd/lead-machine/issues/17) **Discovery job** — `cvr/discovery.py` `run_discovery()` + `SupabaseLeadWriter`: upsert `leads` on_conflict `cvr_number` (idempotent dedup), raw → `lead_enrichment.cvr`, suppress `reklamebeskyttet` + non-active status. `cvr/mapper.py` flattens `Vrvirksomhed` (current/non-secret contacts, latest employment, sole-trader detection). CLI: `leadmachine discover`.
- **To run live:** get CVR creds (below) → `services/worker/.env` (`CVR_ES_USER`/`CVR_ES_PASSWORD`) → `uv run leadmachine discover -b 960210 -p 2200`.

### M2: Website qualification ([#3](https://github.com/djn203040-cmd/lead-machine/issues/3), #18–#21) — built (mock-tested)
The core qualifier. New package `services/worker/src/leadmachine/website/`; +37 tests (91 total), ruff clean. Added `dnspython` dep (lockfile updated).
- **Resolve** (`resolve.py`) — CVR `Hjemmeside` → bucket: none / social (FB/IG/linktree) / free_subdomain (wixsite, business.site → "no real site") / real URL (normalized to https).
- **Dead/parked** (`domain.py`, #19) — `Resolver` Protocol + `DnsResolver` (dnspython): no A/AAAA → dead; parking-NS (sedo/bodis/…) → parked; `classify_from_fetch` adds 4xx/marketplace-redirect/parked-content. Cheap DNS checks short-circuit before fetch.
- **Fetch** (`fetch.py`, #18) — `WebsiteFetcher` Protocol + `HttpxFetcher` (https→http fallback captures "no HTTPS"). **Scrapling `StealthyFetcher` is the documented escalation** (browser dep, add on the worker host) — not a dep here so CI stays browser-free.
- **Analyze** (`analyze.py`, #20) — stdlib HTML parse → viewport, HTTPS, legacy markup (font/frameset/FrontPage/table-layout), CMS/builder (WordPress/Wix/Squarespace/Webflow/Shopify + generator), copyright-year, one-page, FB link, Meta Pixel.
- **PageSpeed** (`pagespeed.py`, #21) — `PageSpeedClient` (mobile, lab scores + red-flag audits), **gated**: only spent on live real sites that pass Tier-1 static screens.
- **Classify** (`classify.py`) — ladder `none>dead>parked>facebook_only>bad>outdated>modern` + evidence payload → `leads.website_need` + `lead_enrichment.website`/`.social`. Job `run_qualification` + `SupabaseWebsiteWriter`. CLI: `leadmachine qualify`.
- **Live note:** sandbox blocks outbound; run from the worker host. PSI needs `PAGESPEED_API_KEY` (free) else it's skipped.

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
- **M2 website qualification — code complete (mock-tested), not yet closed** ([#3]: #18–#21). Close after a live run; consider Scrapling `StealthyFetcher` fallback when a browser host exists.
- **M3 financial enrichment — core code complete (mock-tested), not yet closed** ([#4]). Financials + revenue estimate + CVR contacts done; website contact-scrape folded into M2. Close after a live run.
- **Open epics:** M1 [#2], M2 [#3], M3 [#4], M4 [#5], M5 [#6], M6 [#7], M7 [#8], V2 [#9].
- **Open work issues:** none (M4–M7 + V2 tasks are checklists inside their epics — expand into issues when reached).

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

### Session 2 — 2026-06-22  (M1 + M3 + M2 — discovery, enrichment, qualification)
Built three worker milestones in one session, each **free-first and fully mock-tested** (no live creds needed to develop), then pushed each to `main`. End state: **91 tests green, ruff clean, lockfile synced; branch == main == `4fe09d1`.**

**M1 — CVR discovery** (`cvr/`, #14–#17): `branchekoder.py` catalog, `query.py` `SearchParameters`+`build_es_query`, `client.py` `EsCvrClient` (Basic auth, scroll, retries, injectable httpx behind `CvrClient` Protocol), `mapper.py` (`Vrvirksomhed`→lead), `discovery.py` `run_discovery`+`SupabaseLeadWriter` (CVR# dedup, raw→`lead_enrichment.cvr`, suppress reklamebeskyttet/inactive). CLI `discover`,`categories`. Pushed `3b2e0ab..69d0f55`.

**M3 — financial enrichment** (`financial/`, #4): `client.py` `FinancialClient` (Virk offentliggoerelser, free/unauth), `xbrl.py` `parse_xbrl` (primary-period fsa facts, stdlib ElementTree), `estimate.py` (actual→gross-margin→per-employee + sector benchmarks), `enrich.py` `run_financial_enrichment`+`SupabaseFinancialWriter`→`lead_enrichment.financial`/`.contact`; `cvr/mapper.extract_management()` (CVR decision-makers). Extracted shared `_http.py`. CLI `enrich-financial`. Pushed `69d0f55..37a2666`.

**M2 — website qualification** (`website/`, #3/#18–#21): the core qualifier. `resolve.py` (none/social/free_subdomain/url), `domain.py` `DnsResolver`+`classify_domain` (dead/parked), `fetch.py` `HttpxFetcher` (https→http fallback), `analyze.py` (viewport/HTTPS/legacy/CMS/copyright/FB/pixel/one-page), `pagespeed.py` (gated PSI), `classify.py` ladder→`leads.website_need`+`lead_enrichment.website`/`.social`, `qualify.py` `run_qualification`+`SupabaseWebsiteWriter`. CLI `qualify`. Added `dnspython`. Pushed `37a2666..4fe09d1`.

**Decisions/scope this session:** P-units deferred (not acceptance-gating; client supports the produktionsenhed index); website contact-scrape folded into M2; Scrapling `StealthyFetcher` documented as the escalation behind `WebsiteFetcher` (browser dep, add on worker host); enthec/webappanalyzer fingerprints can replace the DIY CMS detector later.

**Blockers (live runs only — all code is mock-tested):** sandbox blocks outbound to `distribution.virk.dk` (CVR ES + offentliggoerelser) and the open web, so live `discover`/`enrich-financial`/`qualify` must run from the worker host. M1 still needs CVR ES creds; offentliggoerelser + website fetch need none; PSI optional via `PAGESPEED_API_KEY`. After a live pass, close #14–#21 (#2/#3/#4).

**Stopped at:** M2 pushed to main. **Next = M4 scoring (#5)** — see "▶ Next task" at top.
