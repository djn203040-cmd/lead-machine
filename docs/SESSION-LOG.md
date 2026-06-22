# Session Log & Resume Point

> **Read “▶ Resume here” first.** Session history is at the bottom (append new sessions there).

---

## ▶ Resume here (next session)

- **Project:** Lead Machine — Danish local-business lead engine (find → qualify → enrich → score). See [`PLAN.md`](../PLAN.md).
- **State:** V1 · **M0 COMPLETE** · **M1–M6 cores BUILT** · **M7 (#8) code+docs BUILT** — compliance (Robinson screening + LIA + Art. 14 notices), observability (`jobs` run-log), and deploy artifacts/runbook are done & green. **Remaining M7 = live deploy + the one-city E2E pass + closing the M1–M6 epics — all blocked on a live worker host + real creds (can't run in this sandbox).**
- **Branch:** working branch `claude/resume-point-branch-check-r90jni`. **Correction:** M1–M6 are on `main`; this branch carries M7. (Earlier logs said the working branch was `claude/exciting-tesla-o21we4`.)
- **Stack (locked):** Next.js 15 + Supabase (TS) `apps/web`; Python 3.11/uv worker `services/worker`; Scrapling for scraping; Claude for Danish angles.

### ▶ Next task — finish shipping M7 ([#8](https://github.com/djn203040-cmd/lead-machine/issues/8)) — needs a live host
M7 code + docs are **done** (see Session 6). What's left is the part that can't run in this sandbox:
- **Apply migration `0002_compliance.sql`** to Supabase (`supabase db push`).
- **Deploy** per [`docs/DEPLOY.md`](DEPLOY.md): web→Vercel, worker→Fly.io (Dockerfile + fly.toml ready), set the env matrix.
- **Provision the Robinson list** on the worker host, set `ROBINSON_LIST_PATH`, run `leadmachine screen` (warns loudly if the list is empty).
- **Fill the `[…]` placeholders** in `docs/compliance/LIA.md` + `privacy-notice.md` (controller/contact/URL) and **publish** the privacy notice.
- **Run the one-city E2E** (`discover → screen → qualify → enrich-financial → score → angles`) against real CVR creds + keys, then **close the M1–M6 epics** (#2/#3/#4/#5/#6/#7) once acceptance is confirmed on real data.
- **Deferred (V1 follow-ups or V2):** search-builder UI (create `searches` rows), lead assignment/archive UI, a "generér vinkel" button (on-demand M6). **V2:** reviews/reputation + outreach automation (#9).
- **Blockers needing a live host:** CVR ES creds (#14), `ANTHROPIC_API_KEY` (M6), `PAGESPEED_API_KEY` (optional), Supabase `service_role` key, the **Robinson register file** — see the table below.

### M7: compliance, deploy & ship — code + docs built (Session 6)
**Branch `claude/resume-point-branch-check-r90jni`. +20 tests → 165 green, ruff clean; web lint + build green.**
- **Robinson screening** (`services/worker/.../compliance/`): `robinson.py` `RobinsonList` (loads a licensed opt-out file from `ROBINSON_LIST_PATH`; JSONL or `name;postal` CSV; conservative `name+postal` match, NFKD accent-fold but keeps æ/ø/å) + `screen.py` `run_robinson_screening`/`SupabaseScreeningWriter` (flags **sole traders only**; limited companies skipped). CLI `leadmachine screen` — **warns loudly if the list is empty** so no one starts outreach unscreened. Migration `0002_compliance.sql` adds `leads.suppressed`/`suppression_reason`/`robinson_screened_at` + index, and adds `'robinson'` to the `jobs.type` CHECK.
- **Observability** (`jobs.py`): `JobRun` context manager wraps every CLI command (`discover`/`qualify`/`enrich-financial`/`score`/`angles`/`screen`) → inserts a `jobs` row `running`→`done`(result=stats)/`failed`(error); logging failures never break the job; `None` client = no-op. `JOB_TYPES` maps CLI name→CHECK value.
- **UI enforcement:** leads list now filters `suppressed=false` (alongside `is_archived=false`); detail page shows a red "Undertrykt — må ikke kontaktes" banner. `database.types.ts` updated by hand for the 3 new columns (regen with `supabase gen types` after `db push`).
- **Compliance docs** (`docs/compliance/`): `LIA.md` (Art. 6(1)(f) purpose/necessity/balancing + safeguards table mapping each rule to the code that enforces it), `privacy-notice.md` (public Art. 14, Danish + English), `first-contact-script.md` (verbal Art. 14 at first call — source = CVR), `README.md` (index + go-live checklist).
- **Deploy** (`docs/DEPLOY.md`): three-piece topology (Vercel/Supabase/Fly), **env-var matrix**, step-by-step web+worker deploy, the one-city E2E sequence, scheduling, and a `jobs`-backed observability/runbook + failure table. Artifacts: `services/worker/Dockerfile` (uv, Scrapling-browser block commented), `services/worker/fly.toml` (EU `arn`, sleep-infinity box + `/data` volume), `apps/web/vercel.json`. `ROBINSON_LIST_PATH` added to both `.env.example`s + `config.py`.
- **Still blocked (live host):** migration apply, deploy, Robinson file, real-creds E2E, epic closing — see "▶ Next task".

### Built so far (M1–M6 on `main`)

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

### M4: Lead scoring & qualification gate ([#5](https://github.com/djn203040-cmd/lead-machine/issues/5)) — built (no live run needed)
New package `services/worker/src/leadmachine/scoring/`; +42 tests (133 total), ruff clean. **Pure computation** over signals already on `leads` + `lead_enrichment` — no network, fully tested here.
- **`rubric.py`** — five factors capped to sum 100, *inverted for selling websites* (no/dead/parked/facebook-only/bad site = best lead):
  - **Website-need 45** ← `website_need`: `none`/`dead`/`parked`/`facebook_only` = 45; `bad` = sum of `website.signals` sub-points (no_viewport 12 / no_https 10 / legacy 8 / old_copyright 6 / psi<50 6, 50–69 3 / one_page 3), floored to 23 and capped 45 so it stays above `outdated` (22) > `modern` (4) > `unknown` (0) — ladder is monotonic by construction.
  - **Budget 20** ← employee count (`employees_exact` else `band_midpoint(employees_band)`): 0/1→4, 2–4→10, 5–9→16, 10–49→20, 50+→14; + small financial bump (gross_profit>0 +2, equity>0 +2), capped 20.
  - **Presence 15** ← `lead_enrichment.social`: has_fb_page +8, has_meta_pixel +7.
  - **Industry 12** ← `branchekode`: catalogued vertical →12, same DB07 division (not catalogued) →6, else →0.
  - **Recency 8** ← active CVR status +4, founded ≤3y +4 / ≤8y +2.
- **Hard gate** — `gate_reason()`: `reklamebeskyttet` or an explicitly-inactive `cvr_status` → total 0 (a *missing* status is not gated; it would zero valid leads). Already suppressed at discovery; gated here defensively.
- **Tunable weights** — `Weights.from_criteria()` overlays the 11 seeded `scoring_criteria` rows: `is_active=false` disables a signal, `config.points` overrides its value (the coarse low/medium/high `weight` column is a human label, not a numeric override). So weights retune from the DB with no code change.
- **`score.py`** — `score_lead()` → `ScoreBreakdown` (explainable per-factor `points`/`max`/`detail`, versioned for the UI); `run_scoring()` + `SupabaseScoreWriter` upserts `lead_scores` and mirrors the total onto `leads.score`. CLI: `leadmachine score` (loads `scoring_criteria`, scores qualified leads). Sanity check: a no-website local plumber (2–4 emp, FB page, founded ~3y) → **87/100**.

### M5: Leads dashboard ([#6](https://github.com/djn203040-cmd/lead-machine/issues/6)) — core built (`apps/web`)
First web milestone. Next.js 15 (App Router) + Supabase SSR; Danish UI; `pnpm --filter web lint` + `build` (type-check) green.
- **List** (`app/leads/page.tsx`) — URL-driven filters (free-text company, branche **group**, `website_need`, `pipeline_status`, min score) + pagination, ranked `score desc`. Server component reads `searchParams`; `FilterBar` (client) pushes query updates.
- **Detail** (`app/leads/[id]/page.tsx`) — firmographics; an **explainable score breakdown** (per-factor bars parsed from `lead_scores.breakdown`); website evidence; financials + revenue estimate; social; CVR decision-makers; a **phone-first** contact card with the §10 note (no cold-email UI).
- **Pipeline** — server actions (`actions.ts`, `revalidatePath`): change `pipeline_status`, add/list `lead_notes`, add/list `lead_followups`. Client `PipelinePanel` with `useTransition`.
- **Shared** (`apps/web/lib/`) — `branchekoder.ts` (group mirror of the worker catalog — keep in sync), `leadmeta.ts` (badges + da-DK formatters), `score-breakdown.ts` + `enrichment.ts` (typed views over the jsonb). `leads/layout.tsx` header + sign-out; `_components/Badge.tsx`.
- **Toolchain note:** supabase-js 2.108's typed client infers select `data` and insert/update params as `never` with our generated types — the list query uses `.returns<>()`, the detail page asserts the `Tables<>` row types, and writes use `satisfies <T> as never` (payload shape stays checked). If this gets annoying, pin/upgrade supabase-js or regen types to match.
- **Deferred:** search-builder UI (create `searches` rows for new discovery runs), lead assignment/archive, and live verification against real data.

### M6: AI Danish sales angles ([#7](https://github.com/djn203040-cmd/lead-machine/issues/7)) — core built (mock-tested)
New package `services/worker/src/leadmachine/angles/`; +17 tests (150 total), ruff clean. Added `anthropic>=0.111.0` (lockfile updated). Consulted the `claude-api` skill for the model + SDK shape.
- **Model:** `claude-opus-4-8` via the Anthropic Python SDK (the skill says don't downgrade for cost on our own). **Structured output**: `messages.create(..., output_config={"format": {"type": "json_schema", "schema": ANGLE_SCHEMA}})` → `json.loads` the text block (verified the param/shape against the installed SDK). `thinking` omitted (simple, schema-constrained). `max_tokens=2048`.
- **`prompt.py`** — builds a factual Danish brief from the lead's signals (firmographics + website weaknesses derived from `website.signals`/`website_need` + revenue estimate + social + `lead_scores.breakdown` factors) and a fixed English system prompt requiring Danish, **phone-first** output (a cold-call opener, not email).
- **`models.py`** `LeadForAngle`/`Angle` (`from_payload` coerces `competitor_angle_type` to the CHECK set + blanks→null); **`client.py`** `ClaudeAnglesClient` (anthropic import **lazy** in `from_settings` so tests need no key/SDK) behind `AnglesClientProtocol`; **`generate.py`** `generate_one` + `run_angles` + `SupabaseAngleWriter` → upsert `lead_angles`. CLI `leadmachine angles` (`--only-missing` skips leads that already have one).
- **UI:** read-only **"Salgsvinkel"** section at the top of `/leads/[id]` — the opening line as a quote + resumé/vinkel/svagheder + competitor-angle tag.
- **Live note:** the actual Claude call needs `ANTHROPIC_API_KEY` + outbound to `api.anthropic.com` (sandbox-blocked); the code path is API-shape-verified against `anthropic==0.111.0`.

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
- **M4 scoring & qualification gate — code complete (mock-tested), not yet closed** ([#5]). Pure computation; no live run needed. Close once a live worker pass has populated real signals to score.
- **M5 leads dashboard — core code complete (builds green), not yet closed** ([#6]). List + detail + pipeline done; search-builder UI + assignment/archive deferred. Close after live verification against real data.
- **M6 AI Danish sales angles — core code complete (mock-tested), not yet closed** ([#7]). Worker + read-only UI done; needs `ANTHROPIC_API_KEY` for a live run. Close after a live pass.
- **M7 compliance/deploy/ship — code + docs complete (Session 6), not yet closed** ([#8]). Robinson screening + LIA/Art. 14 notices + `jobs` run-log + deploy artifacts/runbook all built & green. Remaining: apply migration, deploy, provision Robinson list, live E2E, then close M1–M7 epics.
- **Open epics:** M1 [#2], M2 [#3], M3 [#4], M4 [#5], M5 [#6], M6 [#7], M7 [#8], V2 [#9].
- **Open work issues:** none (remaining M7 + V2 tasks are checklists inside their epics — expand into issues when reached).

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

### Session 3 — 2026-06-22  (M4 — scoring & qualification gate)
Built **M4** (`scoring/`, #5) — the last worker milestone — on branch `claude/exciting-tesla-o21we4`. Pure computation, **no live blockers**, fully mock-tested: **+42 tests → 133 green, ruff clean.**
- `models.py` (`LeadToScore`/`FactorScore`/`ScoreBreakdown`, versioned) · `rubric.py` (five capped factors summing 100, `Weights` tunable via `scoring_criteria`, `gate_reason` hard gate) · `score.py` (`score_lead` → explainable breakdown; `run_scoring` + `SupabaseScoreWriter` → `leads.score` + `lead_scores`). CLI `leadmachine score`.
- Reused existing pieces: `band_midpoint` (M3), `branchekoder` catalog + `ACTIVE_STATUSES` (M1). Website ladder made monotonic by construction (none/dead/parked/fb 45 ≥ bad[23–45] > outdated 22 > modern 4 > unknown 0).
- **Correction to the record:** despite Session 2's note, the M1–M3 (and now M4) commits are **on the working feature branch, not on `main`** — `main` is still `3b2e0ab` (foundation only). Merge to `main` when the milestone epics are closed after a live pass.
- **Stopped at:** M4 built + committed on `claude/exciting-tesla-o21we4`. **Next = M5 leads dashboard (#6)** — see "▶ Next task" at top.

### Session 4 — 2026-06-22  (push M1–M4 to main · M5 leads dashboard)
- **Pushed M1–M4 to `main`** (fast-forward `220f44c..5c27e35`; `origin/main` already had M1–M3 + docs). Local `main` ref had been stale at `3b2e0ab`.
- **Built M5 core** — the leads dashboard in `apps/web` (Next.js 15 + Supabase SSR). List with URL-driven filters + pagination (ranked by score); rich lead detail with the explainable score breakdown + enrichment + phone-first contact; pipeline management (status / notes / follow-ups) via server actions. Shared lib: branchekode group mirror, badges + da-DK formatters, typed jsonb views. `pnpm --filter web lint` + `build` both green.
- **Toolchain snag:** supabase-js 2.108 typed-client infers `data`/write-params as `never` with our generated types → used `.returns<>()` / `Tables<>` assertions / `satisfies <T> as never` (the list page already did this). Noted for a future supabase-js pin or type regen.
- **Stopped at:** M5 core committed on `claude/exciting-tesla-o21we4`. **Next = M6 Claude Danish sales angles (#7)** — see "▶ Next task" at top.

### Session 5 — 2026-06-22  (push M5 to main · M6 Claude Danish sales angles)
- **Pushed M5 to `main`** (fast-forward to `3290759`). Established the per-milestone flow: build → update log → push branch + fast-forward `main`.
- **Built M6 core** — `angles/` worker package + a read-only "Salgsvinkel" UI section on `/leads/[id]`. **+17 tests → 150 green, ruff clean; web lint + build green.** Consulted the `claude-api` skill: **`claude-opus-4-8`**, structured output via `output_config.format` (json_schema) on `messages.create`, `thinking` omitted, `max_tokens=2048`. Added `anthropic>=0.111.0` (uv resolved/locked; PyPI reachable) and **verified the `output_config`/`json_schema` shape against the installed SDK**. Claude client behind `AnglesClientProtocol` with a **lazy** SDK import, so tests run with no key/network (mock client).
- **Prompt:** factual Danish brief from the lead's signals + a phone-first system prompt (cold-call opener, never email). Grounds "why now" in `lead_scores.breakdown` and the hook in the website weaknesses.
- **Live blocker only:** the real Claude call needs `ANTHROPIC_API_KEY` + outbound to `api.anthropic.com` (sandbox-blocked) — code path is API-shape-verified.
- **Stopped at:** M6 committed on `claude/exciting-tesla-o21we4` + pushed to `main`. **Next = M7 compliance/deploy/ship (#8)** — see "▶ Next task" at top.

### Session 6 — 2026-06-22  (M7 — compliance, observability, deploy artifacts)
Built the in-sandbox half of M7 on `claude/resume-point-branch-check-r90jni`: the **feature code + ops docs**, leaving only the live-host steps (deploy, Robinson file, real-creds E2E). **+20 tests → 165 green, ruff clean; web lint + build green.**
- **Robinson screening** (`compliance/robinson.py` + `screen.py`) — sole-trader-only opt-out gate behind a pluggable file source (`ROBINSON_LIST_PATH`); conservative name+postal match; CLI `screen` warns if the list is empty. Migration `0002_compliance.sql` (suppressed/suppression_reason/robinson_screened_at + `'robinson'` job type).
- **Observability** (`jobs.py` `JobRun`) — wraps all six CLI commands → `jobs` run-log; resilient to logging failures.
- **UI** — list excludes `suppressed`; detail shows a "må ikke kontaktes" banner; `database.types.ts` hand-updated.
- **Docs** — `docs/compliance/` (LIA, Art. 14 public notice + first-contact script, README+checklist) and `docs/DEPLOY.md` (env matrix, Vercel+Fly steps, E2E sequence, runbook). Artifacts: worker `Dockerfile`, `fly.toml`, web `vercel.json`.
- **Decision/scope:** kept V1 phone-first (no email channel); represented compliance suppression as explicit `leads.suppressed` columns (not reusing `is_archived`) for auditability; Robinson data is licensed → never committed, loaded at runtime.
- **Stopped at:** M7 code+docs committed + pushed on `claude/resume-point-branch-check-r90jni`. **Next = the live-host finish of M7** (deploy + E2E + close epics) — see "▶ Next task" at top. NOT yet merged to `main` (merge when M7 ships / epics close).
