# Session Log & Resume Point

> **Read “▶ Resume here” first.** Session history is at the bottom (append new sessions there).

---

## ▶ Resume here (next session)

- **Project:** Lead Machine — Danish local-business lead engine (find → qualify → enrich → score). See [`PLAN.md`](../PLAN.md).
- **State:** V1 · **M0–M7 all on `main`** · **PRODUCTION IS LIVE** · **Session 14 (2026-07-12): Brave web-search discovery ON + owner-suffix fix (worker v12) — 36 real sites recovered, 128/192 now have a website, 142 callable / 50 disqualified.** Prior: S13 phone-first qualifier, S12 P-enhed discovery. Worker on **Fly** (`lead-machine-worker`, region arn, on-demand one-shot machine `2863e24f51d328`, **image `deployment-01KXBSWC42E9NC839E65KQZX7E` = v12**), web on **Vercel**, migrations **`0001–0008`** applied to live Supabase (`dxkxamlwucknndcqqtrj`). **Brave is now ON** (`BRAVE_API_KEY` set — ⚠ rotate it, it passed through chat). Enrichment event-driven: Find virksomheder → "Ja, berig" → web starts the Fly worker → drains qualify→(discovery: email/name → P-enhed → **Brave search**, + grading)→find-phones→financial→score(gate `no_phone`)→angles and stops (~$0 idle). Prior: Session 11 shipped website discovery + Haiku grading + sales-angle v2 (all 192 re-enriched). Worker on **Fly** (`lead-machine-worker`, region arn, on-demand one-shot machine `2863e24f51d328`, **image `deployment-01KX1B2JG65CNPVZS4E7AV1G3Q` = v6 — still v6 until the user redeploys the P-enhed code**), web on **Vercel**, migrations **`0001–0007`** applied to live Supabase (`dxkxamlwucknndcqqtrj`). Enrichment event-driven: Find virksomheder → "Ja, berig" → web starts the Fly worker via the Machines API → drains qualify→(discovery+grading)→financial→score→angles and stops (~$0 idle). **Next = commit + deploy + re-enrich the `none` leads (see the ▶ Next task block right below).**
- **Branch:** `main`. Session-11 work is on `main` (`957b0f8`, `0500db4`). **Session-12 P-enhed work is UNCOMMITTED in the working tree** (see the Session 12 entry) — build done, migration `0007` already applied to prod, all checks green; **not yet committed/pushed** (waiting on the user for the commit + `fly deploy`).
- **⚠ Production `fly deploy` is gated to the USER** — the Claude Code auto-mode classifier blocks the agent from pushing to the live worker. When new worker code must go live, the user runs `cd services/worker && fly deploy` themselves. (Read-only `fly status`/`fly logs`/`fly machine start` are fine for the agent.)
- **⚠ Brave is OFF** — no `BRAVE_API_KEY` secret set. All website discovery so far runs on the **free** email-domain + name-guess (+ now **P-enhed**) tiers. To enable Tier-2 search (now **brand-aware**): `fly secrets set BRAVE_API_KEY=… -a lead-machine-worker`.
- **Stack (locked):** Next.js 15 + Supabase (TS) `apps/web`; Python 3.11/uv worker `services/worker`; Scrapling for scraping; Claude (`claude-opus-4-8`) for Danish angles, **`claude-haiku-4-5`** for website quality grading.
- **Local dev is set up:** `uv` installed; `services/worker/.env` + `apps/web/.env.local` filled with real creds (both gitignored). `pnpm install` + `uv sync` done. `pnpm --filter web dev` boots against live Supabase. **209 worker tests green**, ruff clean, web `tsc --noEmit` + lint clean.

### ▶ Next task — P-enhed discovery + phone-first qualifier are DONE & LIVE. Remaining = secondary paperwork  ← START HERE
Sessions 12–14 (P-enhed discovery, phone-first qualifier, Brave web search) are **built, deployed (worker v12), and applied to production**. The book is now **142 callable / 50 disqualified**, **128/192 with a website**. Open items:
- **⚠ Rotate `BRAVE_API_KEY`** — it passed through chat. `fly secrets set BRAVE_API_KEY=<new> -a lead-machine-worker`.
- **Spot-check a couple of Brave finds** that look uncertain (GRAPPA PICCOLO→jakobsenco.dk, København Frisør→pnoergaard.dk). If false positives recur, tighten `verify_ownership` for `source='search'` (require name AND a second signal).
- **Smoke-test the real UI flow** (Find virksomheder → "Ja, berig" → auto-enrich → Beriget tab; the list hides no-phone leads).
- **M7 paperwork:** Robinson list (still dormant — sole traders called on reklamebeskyttelse only), publish privacy notice/LIA, close M1–M6 epics.
- **Provision the Robinson list** (`ROBINSON_LIST_PATH`) + run `leadmachine screen` — the worker still WARNs "Robinson list is empty" every drain; do not start live outreach until provisioned.
- **Fill + publish** the privacy notice / LIA placeholders; **close the M1–M6 epics** (#2–#7).

**Re-enrich recipe (reference):** reset target leads' `website_need`→`unknown` + `enrichment_status`→`queued` (clear `website_source/discovered_url/website_quality`); `delete from lead_angles` for them only if you want angles regenerated; `fly machine start 2863e24f51d328 -a lead-machine-worker`; poll `enrichment_status`/`lead_angles`. **Angle regen is the slow tail** (Opus, this session ran ~1/min under load) — regenerate angles only for leads that actually flip.

### ▶ Secondary paperwork (still open from M7) — real-UI smoke test + Robinson list + publish privacy notice + close M1–M6 epics (details in the M7 block lower down).

### (HISTORICAL — long since committed) Uncommitted working-tree changes (Session 7)
1. **`cvr/query.py`** + `tests/test_query.py` — **status-filter bug fix.** `sammensatStatus` is analyzed *text*, so the old `terms:["NORMAL","AKTIV"]` filter matched nothing → `discover` returned 0 leads. Now `_status_clause()` uses `match`-per-status in a `should`. This was the bug blocking ALL discovery.
2. **`cvr/branchekoder.py`** + `apps/web/lib/branchekoder.ts` + `tests/test_branchekoder.py` + `tests/test_scoring.py` — **catalog regenerated** against the live register (Denmark migrated active companies to revised DB codes; ~half the old codes matched only ceased firms). Key remaps: 960210→962100 frisør, 561010→561110 restaurant, 691010→741100 advokat, 692020→692000, 452010→953190, 477100→477110, 960220→962200, 960400→962300, 960900→969900, 869010+869090→869900, 107100→107120, 563000→563020. Low-yield kept-as-is: 561020 pizza, 451120 car, 477810 optiker, 562900.

### (HISTORICAL — M7 shipped) finish shipping M7 ([#8](https://github.com/djn203040-cmd/lead-machine/issues/8))
The live E2E pass is **done** (Session 7) and **production is deployed & running** (Session 10). What remains is a real-UI smoke test + paperwork:
- ~~**Commit & push** the Session-7 files to `main`.~~ **DONE (Session 9)** — pushed alongside the Find virksomheder UX overhaul.
- ~~**Deploy** per [`docs/DEPLOY.md`](DEPLOY.md): web→Vercel, worker→Fly.io, set the env matrix.~~ **DONE (Session 10)** — worker live on Fly (on-demand), web on Vercel, migration `0004` applied, enrichment event-driven. Anthropic + Fly cards on file.
- **Smoke-test the real UI flow** (user, still pending): Find virksomheder → "Ja, berig" → confirm leads auto-enrich within a few minutes and land under the "Beriget" tab. Needs `FLY_API_TOKEN` in Vercel (user added) for the instant trigger.
- **Provision the Robinson list** on the worker host, set `ROBINSON_LIST_PATH`, run `leadmachine screen` (warns loudly if the list is empty).
- **Fill the `[…]` placeholders** in `docs/compliance/LIA.md` + `privacy-notice.md` (controller/contact/URL) and **publish** the privacy notice.
- **Close the M1–M6 epics** (#2/#3/#4/#5/#6/#7) — acceptance now confirmed on real data.
- ~~**Optional cleanup:** the 99 restaurant leads (8000) are discovered but not yet qualified/enriched/scored/angled.~~ **DONE (Session 8, 2026-06-30):** ran qualify→enrich→score→angles on them; all 147 leads now fully processed + angled (0 missing).
- **Deferred (V1 follow-ups or V2):** search-builder UI, lead assignment/archive UI, on-demand "generér vinkel" button. **V2:** reviews/reputation + outreach automation (#9).
- **Tuning idea (declined this session):** tune the catalog to the user's real target industries + surface contactable-yield % per vertical.

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

### Session 9 — 2026-07-01  (Find virksomheder UX overhaul — industries + locations)
Rebuilt the **Find virksomheder** discovery form (`apps/web/app/leads/new`) to be far easier and more intuitive, per the user's ask for "a lot more industries" + an easier way to pick areas.
- **Industries 37 → 170, searchable & grouped.** Replaced the single-group `<select>` with a searchable, collapsible [`IndustryPicker`](../apps/web/app/leads/new/_components/IndustryPicker.tsx) (type to filter; tick a whole group or individual industries) across **16 categories**.
- **Authoritative DB25 catalog.** The live CVR register uses **Dansk Branchekode DB25** (Danmarks Statistik, eff. 2025-01-01), *not* DB07. Downloaded the official DB25 CSV → 738 leaf codes → curated 170 SMB-relevant ones, **every code validated to exist in DB25**. Fixed legacy/wrong codes carried over from Session 7's live-audit (dropped `561020`/`451120`/`477810`/`562900` which aren't in DB25; `741100` "Advokat" was wrong → law firms are `691000`).
- **Location: free-text postnr → city/kommune/region autocomplete.** New [`LocationPicker`](../apps/web/app/leads/new/_components/LocationPicker.tsx) with chips; CVR can only filter `postnummer` + `kommuneKode` (not city name), so a city resolves to its postnumre and kommune/region to kommunekoder. Geo data (5 regions→98 kommuner→1,089 postnumre, 32 KB) from DAWA/dataforsyningen.dk → `apps/web/lib/geo/denmark.geo.json` + `lib/geo.ts`. Manual postal entry kept as a fallback. Wired `kommunekoder` through `actions.ts` (the query builder already supported it — just wasn't exposed).
- **Worker kept in sync:** regenerated `cvr/branchekoder.py`, added benchmarks + prefix mappings for the new group keys in `financial/estimate.py`. **172 worker tests green; web tsc + build + lint green.**
- **Reproducible pipeline committed:** `scripts/catalog/` (gen_catalog.js + db25_leaf_codes.json + gen_geo.js + README) so both datasets can be regenerated.
- **Env limitation found:** the live CVR ES endpoint (`distribution.virk.dk`) is **TCP-unreachable from this machine/sandbox** (DAWA + dst.dk work) — could not aggregate the live register here; built the catalog from the official DST DB25 CSV instead. Codes are standard-correct but per-industry live yield wasn't verifiable from here.
- **Note:** this push also carries the previously-uncommitted **Session 7** fix (`cvr/query.py` status-filter) that had never been committed.

**Then wired up CVR access for the app (was showing "CVR-adgang er ikke konfigureret"):** the web app reads its *own* env, not `services/worker/.env`.
- **Local:** added `CVR_ES_USER` / `CVR_ES_PASSWORD` / `CVR_ES_URL` to `apps/web/.env.local` (gitignored); documented them in `.env.local.example`. Requires a dev-server restart to load.
- **Vercel (production):** linked the `lead-machine-web` project (team `daniel-nissens-projects`) and added the three CVR vars to **Production** via `vercel env add`. **Preview not set** — the CLI kept returning `git_branch_required` even with `--value … --yes` (v54.6.1 quirk); do it in the dashboard if branch deploys need it.
- **Redeploy gotcha:** Vercel snapshots env vars at *deploy-creation* time, so the existing build couldn't see them. `vercel redeploy` **fails** here ("No Next.js version detected") because it ignores the project's `apps/web` Root Directory. Empty commits get **auto-canceled** (monorepo "skip build if root dir unchanged" rule). Fix: push a real change *under `apps/web`* → git-integration build picks up the vars. Live deploy `6ye61a0cq` is Ready + holds the prod aliases.
- **Region:** already **Stockholm (`arn1`)** via `apps/web/vercel.json` `"regions":["arn1"]` (set Session 6) — verified honored at the deployment level via the Vercel API (not overridden to US). Best case for reaching `distribution.virk.dk` from a Nordic IP.
- **Stopped at:** committed + pushed to `main`; CVR creds live locally + on Vercel Production; functions in Stockholm. **Unverified:** an actual live discovery search on the deployed site (needs login) — CVR endpoint was TCP-unreachable from this sandbox, so real end-to-end from Vercel is still to be confirmed by the user. Remaining M7 ship steps unchanged (Fly worker deploy, Robinson list, publish privacy notice, close epics).

### Session 8 — 2026-06-30  (finish the 99 restaurant leads)
Ran the rest of the pipeline on the 99 discovered-only restaurant leads (561110, Aarhus 8000) so every lead in the DB is complete. All against live creds from local dev; all stages logged to `jobs`.
- **qualify** (99 unknown): 90 `none` (no website) · 1 `dead` · 8 `modern`. PSI skipped (no `PAGESPEED_API_KEY`).
- **enrich-financial** (ran over all 147): 78 real annual reports · 93 revenue estimates · 82 CVR contacts · 0 errors.
- **score** (147): all scored, 0 gated. Top restaurants ~81–83 (e.g. Kakurega ApS 83, Bistro Solera 83 — all no-website ApS in Aarhus C).
- **angles**: needed two passes — `--limit 120` only fetched 120 of 147 rows before the only-missing filter, leaving 27 uncovered; re-ran `--limit 200` → 27 more. **Final: 147/147 leads angled, 0 missing.** Sampled output is factual + neighborhood-aware + phone-first (verified Kakurega's opener/angle).
- **Note for next time:** `angles`/`qualify` apply their limit *before* the only-missing/only-unknown filter, so set `--limit ≥ total leads` to guarantee full coverage in one pass.
- **Stopped at:** all 147 leads fully processed. Remaining M7 ship steps unchanged (deploy to Vercel/Fly, Robinson list, publish privacy notice, close M1–M6 epics) — see "▶ Next task" at top.

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

### Session 7 — 2026-06-30  (cloned to local · FULL LIVE E2E · discovery bug fix · catalog regen)
Cloned the repo into `Desktop/Claude code/Lead machine`, stood up local dev, and ran the **entire pipeline live on real Danish data** for the first time. Provided creds: real Supabase `service_role`, CVR ES system creds, real `ANTHROPIC_API_KEY` (all in gitignored `.env`s).
- **Got everything green locally:** installed `uv`, `pnpm install`, `uv sync`; 165 worker tests pass, ruff clean, web lint+build green, dev server boots against live Supabase (auth middleware redirects `/`→`/login`).
- **Confirmed live DB state:** all 9 tables migrated incl. `0002_compliance` **already applied**; 11 `scoring_criteria` seeded.
- **Found & fixed the discovery-blocking bug:** first `discover` returned 0. Root cause: `sammensatStatus` is an **analyzed text field**, so `terms:["NORMAL","AKTIV"]` never matched → 0 active companies. Fixed `cvr/query.py` to use `match`. Also discovered the index name `cvr-v-20220630` is a **stale alias on LIVE data** (36k companies founded 2026, updated within days) — NOT a 2022 snapshot. The XBRL/financial channel (`regnskaber.virk.dk`) is also live (2026 reports).
- **Ran the full live E2E** (hairdressers 962100 / postnr 2200): `discover` → 48 leads (91 suppressed reklamebeskyttet) → `qualify` → 45 no-website / 3 modern → `enrich-financial` → 5 real annual reports + 10 revenue estimates + 5 contacts → `score` → top "The Choice ApS" 73 → `angles` → 48 Danish phone-first pitches (genuinely good, neighborhood-aware). Every step logged to `jobs`. **All 5 stages work on real data.**
- **Regenerated the branchekode catalog** (the user asked). Audited all 38 codes live: ~half matched only ceased companies because Denmark revised the codes. Rewrote `branchekoder.py` + the `apps/web` mirror + tests with live-verified current codes (see "Uncommitted changes" up top). Proven live: restaurants 561110 in Aarhus 8000 → 99 leads (was 0 under old 561010). DB now has 147 leads (48 fully processed + 99 restaurants discovered-only).
- **Measured `reklamebeskyttelse`:** ~**67% of active companies** are ad-protected (range 47% dentists → 76% photographers; by form: A/S 44% < sole-trader 63% < ApS 65% < I/S 80%). So a search yields ~⅓ contactable leads — the pipeline auto-suppresses the rest at discovery.
- **Decisions this session:** (1) keep dropping reklamebeskyttet leads at discovery — storing them adds no value (the count is already in job stats; re-discovery re-checks protection); do NOT fold them into the scored pipeline with a low score (reklamebeskyttelse is a legal opt-out under CVR-loven, applies regardless of score/channel incl. phone). (2) Declined catalog target-tuning for now.
- **Stopped at:** Session-7 changes UNCOMMITTED on `main` (6 files). **Next = commit/push + production deploy** — see "▶ Next task" at top.

### Session 10 — 2026-07-07  (production is LIVE · 3 prod bugfixes · opt-in enrichment · on-demand Fly worker · first real deploy)
Took the app from "deploy artifacts exist" to **fully deployed and running on real data in production.** Worker is now live on Fly, web on Vercel, migration `0004` applied, and enrichment is event-driven. All 192 leads enriched + angled.

- **Fixed 3 production bugs the user hit, in order:**
  1. **"fetch failed" on Find virksomheder** — the CVR ES endpoint `distribution.virk.dk` serves **plain HTTP on port 80 only** (no https/443 listener); the default + `.env.local` used `https://` → TCP hang → bare "fetch failed". Switched to `http://` (matches the worker's `config.py`); also surfaced the underlying `error.cause` in `post()`. Commit `a3664b6`. **The Vercel `CVR_ES_URL` env var had to be corrected to http too** (user did it).
  2. **Vercel build failed ("No Next.js version detected")** — `apps/web/vercel.json` made the install command a no-op (`echo…`) and shoved `pnpm install` into `buildCommand`, but Vercel runs Next.js detection **between** install and build → next wasn't installed yet. Removed the custom commands; Vercel auto-detects Next.js + pnpm workspace. Commit `bd04f07` (+ `4050040` docs).
  3. **Discovery returned "0 found"** — the **same `sammensatStatus` analyzed-text bug from Session 7, but in the web TS port** (`apps/web/lib/cvr/query.ts` still used `terms`, never fixed alongside the Python). Ported `_status_clause` → `match`-in-`should`. Verified live: branchekode 962100 went **0 → 7800 hits**. Commit `5367148`. Lesson: `query.py` and `query.ts` are parallel builders that MUST stay in sync (recorded in memory).
- **Built opt-in enrichment (user's spec: prompt after discovery + Beriget/Ikke-beriget list split).** Commit `7d686ed`:
  - Migration `0004_enrichment_status.sql`: `enrichment_status` on `leads` (`pending`→`queued`→`enriching`→`enriched`, plus `skipped`/`failed`), indexed, backfills scored leads to `enriched`; adds `enrich_queued` jobs.type.
  - Web: discovery returns still-`pending` lead IDs → post-discovery **modal** ("Berig N nye leads?" Ja/Nej); Ja→`queued`, Nej→`skipped`. Leads list gets a **Beriget / Ikke beriget** tab (defaults to enriched) with an enrichment badge + per-row "Berig" button. Shared `enrichment-actions.ts` (chunked, gated transitions).
  - Worker: new `pipeline.py` houses per-stage runners (select/map/run, optional `lead_ids` scope) shared by the CLI commands **and** a new `enrich-queued` orchestrator that drains the queue through qualify→financial→score→angles and flips to `enriched`/`failed`. Refactored the 4 stage commands onto these runners (single source of truth — the fix for the cli/pipeline drift class of bug). 172 worker tests green.
- **Reworked to ON-DEMAND (user: "no need to keep it active always").** Commit `977c615` (+ `a557858` Dockerfile fix):
  - Fly worker is now a **one-shot machine that stays stopped (~$0)**: `fly.toml` runs `enrich-queued --drain && screen` with `[[restart]] policy = "never"`. On opt-in, the web `enqueueEnrichment` action starts it via the **Fly Machines API** (`apps/web/lib/fly.ts`); it drains the whole queue (looping — concurrent searches self-heal), screens, and stops.
  - **Dockerfile fix:** dropped `ENTRYPOINT ["leadmachine"]` — it turned `[processes] sleep infinity`/drain into `leadmachine sleep infinity` (exits on boot). Now `CMD ["leadmachine","hello"]` so the process string fully replaces the command.
  - Cron: the 15-min ssh-poll became a **daily backstop** that just starts the machine (safety net for a failed web trigger).
- **First real production deploy (worker had never been deployed — earlier sessions ran it locally):**
  - Installed `flyctl`; **created the Fly app `lead-machine-worker`** (region arn) + `lm_data` volume; imported all secrets from `services/worker/.env`; `fly deploy` (remote build).
  - Applied migration `0004` to the live Supabase (`dxkxamlwucknndcqqtrj`) via MCP — backfilled 147 scored leads → `enriched`.
  - Ran the full pipeline on the queue: **all 192 leads enriched + 192 angles (0 missing).**
- **Two account blockers surfaced & resolved (both user-side, needed a card):**
  - **Anthropic API was out of credits** — the `angles` stage 400'd (`credit balance too low`) for 39/45 leads. This is the **API**, billed separately from any Claude.ai subscription (prepaid credits in console.anthropic.com — a subscription does NOT cover programmatic API calls). User added a card → re-ran → all angles generated.
  - **Fly was on the free trial** — machines are killed after 5 min, which cut off longer drains. User added a card → verified an **8.5-min drain ran to completion** with no trial-stop.
- **Wired the on-demand trigger auth:** `FLY_API_TOKEN` (Fly deploy token) → user added to **Vercel** env (instant trigger); I set it as a **GitHub repo secret** via `gh` and **test-ran the backstop workflow → success (14s).** Both trigger paths confirmed live end-to-end (Machines-API start → drain → stop).
- **Cost model:** marginal ≈ **$0.03–0.05/lead** (all Claude/Opus angles; Fly compute ~$0.00002/lead). Fixed ≈ Fly ~$0.30/mo (volume) + Supabase $0 free/$25 Pro + Vercel $0 Hobby/$20 Pro. Realistic steady use ≈ **$80–125/mo all-in** at ~2k leads/mo, dominated by lead volume. Lever: angles are ~100% of Claude spend (generate only for high-score leads, or use Haiku, to cut it).
- **Stopped at:** everything committed & pushed to `main` (through `977c615`); production live. **Next = user smoke-tests the real UI flow** (Find virksomheder → Ja, berig → auto-enrich) + provision Robinson list + publish privacy notice + close M1–M6 epics.

### Session 14 — 2026-07-12  (Brave web search ON + owner-suffix fix — 36 real sites recovered, 125→142 callable)
Turned on the Tier-2 web-search leg of discovery (Brave) and fixed the verification gap it exposed. Trigger: the user found **Tandlægerne i Centrum** (site `tandicentrum.dk`, #1 on Google) still labelled "Ingen hjemmeside" — because we never *search* the web (only email/name-guess), and Brave was off.

- **Brave enabled:** user subscribed to Brave Search's pay-as-you-go plan ($5/1k, free $5/mo credit ≈ 1k searches) and set `BRAVE_API_KEY`. **First key was truncated** (a stray `>` ate the last char) → 0/104 silent misses; corrected key (`…cahNW7`) works. **Diagnosed via the DB** (0 hits across 104 diverse queries ⇒ auth failure) since prod-shell/CVR are agent-gated.
- **Discovery fixes (commit `e88275c`, worker v12):**
  - **`independence.strip_owner_suffix` / `search_name`:** Danish CVR names append the owner ("TANDLÆGERNE I CENTRUM **V/LARS WELTZER** ApS"); the storefront site never says "Lars Weltzer", so verification's all-tokens name check failed. Now the `v/<owner>` (and `/<owner>`) suffix is stripped before tokenizing → `business_key`, `name_domain_candidates`, and the Brave query all focus on the business name. Brave query also drops the legal form and is unquoted (the full legal string tanked recall).
  - **verify** street-match handles house ranges ("Algade 5-7"). **Brave sped up:** single attempt (was a 4× retry storm), 8s timeout, candidates 6→4 — a slow search no longer stalls the per-lead pipeline. `request_json_get` removed. **221 tests green.**
- **Canary (6 leads) confirmed the fix:** Tandlægerne→`tandicentrum.dk`, LA CABRA→`lacabra.com`, SPECIALTANDLÆGERNE→`specialtandlaegerne.com` (all `search`/modern); 3 correct declines (AniCura/Domestic/Svane = chains/pharmacy, not independent).
- **Full run (101 no-site leads):** **36 sites found via Brave** (Cafe Folkeven, Casa Frisør→casa17.dk, Chicago, Gundsø Dyreklinik, Det Glade Vanvid chain, kiropraktorroskilde.dk, …). **callable 125→142** (+17 phones scraped off the new sites), **disqualified 67→50**, **still-no-site 119→62**. Book now: **128/192 have a website** (36 search + 62 free + 17 cvr + 13 penhed). A couple finds worth a spot-check (GRAPPA PICCOLO→jakobsenco.dk, København Frisør→pnoergaard.dk). **Note: the drain's first lead can stall ~10 min on a hanging host, then it recovers to ~2–3/min** (don't mistake the slow first lead for a hang).
- **Angle regen:** the 36 flipped from `none`→has-site, so their "no website" angles are stale → deleted + re-queued the **31 callable** ones to regenerate as redesign pitches (running at session end; Opus ~1/min tail).
- **Stopped at:** Brave discovery + fixes live (worker v12); 36 new sites, 142 callable. Angle regen for the 31 flipped leads draining. **⚠ Rotate the `BRAVE_API_KEY`** (it passed through chat). All committed to `main` (`e88275c`).

### Session 13 — 2026-07-11  (phone-first qualifier — hunt for a number, disqualify leads without one · shipped, deployed v9, applied to the book)
Made **a present phone number the top qualifier**: outreach is phone-first, so a lead we can't call is disqualified. ~49% of the book (94/192) had no CVR number. Built phone-hunting + a hard disqualification gate + UI hiding, deployed (worker **v9**), and backfilled the book. **219 worker tests green (+10), ruff clean, web tsc + lint clean.**

- **Phone hunt** (`website/phones.py` `extract_phones`/`normalize_phone` + `pipeline.find_missing_phones`): for each phone-less lead, **scrape its own site** (registered or discovered) for Danish numbers — `tel:` links, `+45`-prefixed, or numbers next to a cue (`tlf`/`telefon`/`ring`/☎) — then fall back to the **P-enhed's registered number**. Precision-first: a bare 8-digit run with no phone context is ignored (could be a CVR number/price), and the lead's own CVR number is excluded; validates 8 digits, first 2–9. Runs in `enrich_queued` between qualify and score. Standalone CLI `leadmachine find-phones`.
- **Disqualification:** `scoring.gate_reason` gains a **`no_phone`** hard gate (score 0) after the compliance gates; `LeadToScore.phone` wired through. `generate_angles` **skips** phone-less leads (no wasted Claude spend).
- **DB + UI:** migration **`0008_phone_qualifier.sql`** — `leads.has_phone` generated column (`array_length(phone,1)>0`) + index (so list/dialer filter server-side), and `jobs_type_check` gains `find_phones`. **Applied to prod.** Web: leads list **hides no-phone enriched leads** (`has_phone` filter); dialer already filtered in-app. `database.types.ts` + `has_phone`.
- **Result (backfilled all 94 no-phone leads):** **recovered 27 numbers** (98→**125 callable**) — from **both** the website scrape (e.g. Chickii→chickii.dk `31656255`) and the P-enhed fallback (e.g. Bar'ista/Papillon, which have no website at all). **67 leads truly disqualified** — all score 0, all gated `no_phone`, all hidden. Every one of the 125 callable leads has a score + an angle.
- **Robinson:** left **dormant** per user decision — keep calling sole traders on reklamebeskyttelse alone for now (the screening code stays as a switch-on-later safety net; §10 exposure noted). Robinson ≠ reklamebeskyttelse: the former is a per-person opt-out (markedsføringsloven §10) that can apply to the 73 sole traders even when not reklamebeskyttet.
- **Stopped at:** phone-first qualifier **shipped, deployed (v9), and applied to the whole book** (27 recovered, 67 disqualified). All committed/pushed to `main` (`da0d4a5`). Worker idle/stopped.

### Session 12 — 2026-07-11  (trading-name / P-enhed discovery — BUILT + tested + migration applied; uncommitted, awaiting deploy)
Built the whole **production-unit (P-enhed) / trading-name discovery** feature scoped in Session 11's ▶ Next task. A lead like **Kakurega ApS** runs a differently-branded storefront **Noribar**; the site (`noribar.dk`) + public contact live on the **P-enhed** — a separate CVR object keyed by `pNummer`, in the `cvr-permanent/produktionsenhed` index — which we never fetched, so those leads were falsely `website_need='none'`. **209 worker tests green (+18), ruff clean, web `tsc --noEmit` + lint clean.**

- **New `cvr/penhed.py`** — `PenhedInfo` + `map_penhed()` (flattens trading name + own `hjemmeside`/`elektroniskPost`/`telefonNummer`/`beliggenhedsadresse`, reusing the company mapper's period-stamped helpers `_pick_current`/`_pick_current_all`/`_format_address`/`_latest_named`/`_is_current`/`_unwrap`), `current_pnummer()` (picks the open-period pNummer from a company blob's `penheder`), and `EsPenhedClient` (single-shot `term` query on **`Vrproduktionsenhed.pNummer`**, best-effort → `None`; `from_settings` returns `None` without CVR creds). Exported from `cvr/__init__.py`. Confirmed the `penheder` shape live via the stored Kakurega blob: `[{pNummer, periode{gyldigTil:null}, sidstOpdateret}]`.
- **`website/discover.py`** — new **Tier 1.5 (P-enhed)** between name-guess and Brave: fetch the P-enhed once, then try (a) its own registered `hjemmeside` as a direct candidate, (b) its email domain, (c) trading-name → domain guesses — all with `source="penhed"` and `brand=penhed`. **`verify_ownership` is now brand- + address-aware:** matches the P-enhed **trading name** as a name anchor (so a brand site verifies though it never says "Kakurega") and adds **street-address matching** (`_street_name`/`_street_match` strip the house number, match the street as a run in the page) as corroboration. `email_domain` + `penhed` are the "trusted sources" that accept a name-only match (0.6/0.85) or a corroborated no-name match (0.7). **Brave is now brand-aware** — queries the trading name + city when present. `DiscoveryResult` gained `brand_name` (the storefront name, surfaced in evidence + on the lead detail as "Butiksnavn").
- **Wiring:** `LeadToQualify` gained `pnummer` + `address` (`models.py`); `pipeline.py qualify_leads` now selects `address` + joins `lead_enrichment(cvr)` and derives the pNummer via `current_pnummer`, and `WebsiteDiscoverer.from_settings` builds/owns the `EsPenhedClient` (closed in `close()`). `config.py` adds `cvr_es_penhed_url` (default = produktionsenhed endpoint) + it's in `.env.example`.
- **DB + UI:** migration **`0007_website_source_penhed.sql`** extends `leads_website_source_check` to allow **`penhed`** — **applied to prod (`dxkxamlwucknndcqqtrj`) + verified**. Web: `WEBSITE_SOURCE_META.penhed` label ("Fundet via P-enhed (butiksnavn)"), `enrichment.ts` discovery type gained `brand_name`, lead detail shows the **Butiksnavn** field.
- **⚠ Field-path caveat:** the P-enhed ES **field path + record shape are assumed** (`Vrproduktionsenhed.pNummer`, `produktionsEnhedMetadata.nyeste*`), unit-tested with fakes but **not yet confirmed against live CVR** (sandbox blocks it). If the post-deploy re-enrich yields **zero** `penhed` sources, check the field path / index name first.
- **Deployed + live-tested + fixed a real bug the sandbox couldn't catch:**
  - Committed (`3646a3f`) + pushed; first `fly deploy` (worker image `deployment-01KX74RH...`); migration `0007` applied to prod (`penhed` source allowed).
  - **First re-drain of all 118 `none` leads → 0 `penhed` sources.** Diagnosed via the **Erhvervsstyrelsen ES docs** (production-shell diagnostic was gated to the agent): the produktionsenhed **root document key is `VrproduktionsEnhed` — capital E**. ES field names are case-sensitive, so the `term` on `Vrproduktionsenhed.pNummer` (lowercase e) matched nothing → every lookup silently returned `None`. **Fix `693a2ec`:** correct root key (`PENHED_ROOT`) + query pNummer as a **string** (docs use string). 209 tests green.
  - **User redeployed** (worker **v8**, image `deployment-01KX8GJQ...`) — the bug-fix `fly deploy` was gated to the agent. Re-queued + re-drained the 118 `none` leads.
  - **Result: 13 `penhed` rescues** — all correct storefront matches, most **ungessable from the company name** (verified via the trading name and/or street address): Kakurega ApS→Noribar (noribar.dk), 17 Sky ApS→PHO OISHII (phooishii.dk), 2CHUBBY ApS→Escobar (escobar.dk), Frisør Strandvejen 138 ApS→Frisør Pii Vanløse (frisorpii.dk), KYLLESBECH'S GOURMET-CAFE ApS→Mefisto (mefisto.dk), MKO ApS→Restaurant Medvind (medvind.dk), TIR NA NÓG ApS→tirnanog.dk, THYGE & TALLE ApS→restaurantkomfur.dk, and the **Det Glade Vanvid** chain ×5 (each city's ApS → detgladevanvid.dk). Qualities: 8 modern, 4 basic, 1 dated.
  - **Angle regen:** those 13 had stale "no website" angles (they were `none`); deleted + re-queued just those 13 → angles regenerated as **redesign/refresh** pitches (verified Kakurega: "en moderne hjemmeside … et frisk bud på deres online-udtryk", v2 "already-built demo" CTA preserved). Angle regen was the slow tail (~1/min under Anthropic load). Machine auto-stopped after.
- **Stopped at:** P-enhed discovery **shipped, deployed (v8), and fully applied to prod** (13 rescues, angles regenerated, all verified). Everything committed/pushed to `main`. **Next = optional Brave ON + the M7 paperwork** — see the ▶ Next task block at the top.

### Session 11 — 2026-07-08→11  (website discovery + Haiku quality grading · shipped, deployed & applied to all 192 leads · sales-angle v2 deployed · next = P-enhed trading-name discovery)
Fixed the qualifier's core weakness: it branded most leads "Ingen hjemmeside" because it only trusted the CVR `hjemmeside` field (empty for most Danish SMBs). Built + shipped **website discovery** (find the real site) + **Haiku quality grading**, re-enriched the whole book, and deployed the user's **sales-angle v2**.

- **Website discovery + grading — the feature (commit `957b0f8`, on `main`, deployed).** All in `services/worker/src/leadmachine/website/`:
  - **`discover.py`** (new) — `WebsiteDiscoverer` runs cheapest-source-first, **verifying ownership before attaching anything**: **Tier 0 email domain** (`email_domain_candidate`, free-provider list stripped) → **Tier 1 name→domain guesses** (`name_domain_candidates`, `.dk`/`.com`, reuses the independence tokenizer) → **Tier 2 `BraveSearchClient`** (directory-blocklisted; opt-in via `BRAVE_API_KEY`). `verify_ownership()` scores CVR-nr (definitive) / company-name (required anchor) / phone / email / postal+city; accept threshold **0.6**. Follows redirects and rejects dead/parked/`not_independent`/directory hosts.
  - **`grade.py`** (new) — `ClaudeGrader` (**`claude-haiku-4-5`**, structured output) → tier **dated / basic / modern / premium** + Danish note. **Best-effort**: any error is swallowed, never fails qualification. `from_settings` reuses `ANTHROPIC_API_KEY`.
  - **`qualify.py`** — discovery runs at the old `none/social/free_subdomain` early-return; a discovered site flows through the normal DNS→fetch→analyze→PageSpeed path; grading runs on **every** live site (discovered + CVR). New `WebsiteAssessment` fields `website_source`/`discovered_url`/`website_quality`; `WebsiteWriter.write(lead_id, assessment)` now takes the whole assessment.
  - **`models.py`** — `LeadToQualify` gained `email`/`phone`/`city`/`postal_code`/`cvr_number`; added `DiscoveryResult`, `WebsiteQuality`. **`pipeline.py`** `qualify_leads` selects those columns and builds/closes the discoverer + grader. **`config.py`** adds `brave_api_key` + `website_grader_model` (default `claude-haiku-4-5`).
  - **DB:** migration **`0005_website_discovery.sql`** — `leads.website_source` / `discovered_url` / `website_quality` (+ CHECKs + index). **Applied to prod.**
  - **Web:** `database.types.ts` (3 cols), `enrichment.ts` (`WebsiteEvidence.discovery`+`.quality`), `leadmeta.ts` (`WEBSITE_QUALITY_META`, `WEBSITE_SOURCE_META`, helpers), lead detail page shows **Kilde / Kvalitet / Fundet URL / Kvalitetsnote**.
  - **Tests:** new `test_discover.py`, `test_grade.py`; extended `test_qualify.py` + conftest fakes (`StubDiscoverer`/`StubGrader`). **191 green, ruff clean, web `tsc` clean.**
- **Cost model (locked with user):** free email+name tiers ≈ **$0**; Brave ≈ $3–5/1k queries (free tier ~2k/mo); Haiku grade ≈ **$0.01/site**. All-in ≈ **1–2¢/lead** on top of existing enrichment. Decision: **Haiku for grading (not Opus/Sonnet), Brave optional.** No screenshots/browser.
- **Deploy sequence (BOTH went live this session):**
  - I ran `fly deploy` for `957b0f8` → image `deployment-01KX1340…`. Verified via `fly status` (read-only calls are allowed for the agent).
  - The user separately committed **sales-angle v2** (`0500db4` — "come see the demo we already built" cold-call reframe; adds `cta_da` + `objections`; migration **`0006_angle_cta_objections.sql`**, already applied to prod). I **merged it to `main` (ff) and pushed** → Vercel auto-deployed web.
  - **Production `fly deploy` is gated to the user** (auto-mode classifier blocks the agent). The user ran `cd services/worker && fly deploy` → worker image `deployment-01KX1B2JG65CNPVZS4E7AV1G3Q` (**v6**), which is what carries the v2 angle code.
- **Verified + full re-enrich of all 192 leads:**
  - **5-lead demo first:** reset 5 `none` leads → discovery found **4/5** real sites via email domain (`laegerneistoeden.dk`, `rhc.dk`, `tandroskilde.dk` [followed a redirect from the email domain `uldal.dk`], `rygcenterroskilde.dk`) and **correctly declined the 5th** (`e.gjessing@dadlnet.dk` is a shared doctors'-network domain — no false positive).
  - **Then re-ran ALL 192** as if new: `update leads set website_need='unknown', website_source=null, discovered_url=null, website_quality=null, enrichment_status='queued' where cvr_number is not null;` + `delete from lead_angles;` (so v2 angles regenerate — `generate_angles` is `only_missing`), then `fly machine start 2863e24f51d328 -a lead-machine-worker`. **Drain ≈ 50 min** — the 192 **sequential Opus angle calls** are the bottleneck (~3/min); qualify+discovery+grading is fast. Paced polling with background `sleep`.
  - **Results (192 enriched, 0 failed):** `website_source` = 121 none, **38 name_guess, 16 email_domain**, 17 cvr → **54 sites discovered that CVR never had** (would've stayed false "none"; ~76% of all on-file sites were discovered, not registered). `website_need` = **119 none** (down from ~173), 58 modern, 11 bad, 2 dead, 2 outdated. `website_quality` (71 live) = 35 modern, 31 basic, 4 dated, 1 premium. **All 192 angles regenerated with `cta_da` + `objections` populated** (v2 confirmed). **All discoveries came from the FREE tiers — Brave never fired (no key).**
- **Re-enrich recipe (for next time / after the P-enhed build):** reset the target leads' `website_need`→`unknown` + `enrichment_status`→`queued`; `delete from lead_angles` for them if you want v2 angles regenerated (else they're skipped as `only_missing`); `fly machine start 2863e24f51d328 -a lead-machine-worker`; poll `enrichment_status`/`lead_angles` count; angles are the slow tail. Machine drains + runs `screen` + stops itself.
- **Next task identified & scoped (user chose to defer the build to next session):** **trading-name / P-enhed discovery** — see the "▶ Next task" block at the top for the full plan (Kakurega ApS → Noribar; the brand + often the site live on the P-enhed, a separate CVR object we don't fetch). Root cause confirmed against the live CVR blob. User picked **"P-enhed lookup + Brave"**.
- **Stopped at:** website discovery+grading and sales-angle v2 both **committed, pushed to `main`, deployed, and applied to all 192 leads**; working tree clean. **Next = build P-enhed / trading-name discovery** (▶ Next task, top).
