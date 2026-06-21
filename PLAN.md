# Lead Machine — Build Plan

> Status: V1 in planning. Canonical plan for the Danish local-business lead engine.
> Companion research: [`RESEARCH-lead-qualification-2026.md`](./RESEARCH-lead-qualification-2026.md).

## 1. What we're building

A **lead generation → qualification → enrichment engine** that is the *primary driver of the sales cycle* for a Danish web-design agency selling **$1–2k websites** (then upselling systems/infrastructure).

It **finds** Danish local businesses, **qualifies** them by website-readiness — the core signal is the *absence* or *poor quality* of a website (**no site / dead / parked / Facebook-only / bad-outdated = best lead**) — **enriches** them with firmographics + financials, **scores** them 0–100 for "needs a website now," and surfaces **pitch-ready leads** (with Danish AI sales angles) in a dashboard.

Outreach is **phone-first** (Danish law — see §8). **Reviews/reputation and outreach automation are V2.**

## 2. Principles

- **Free-first** — V1 runs at ≈ $0/month. No Apify, no paid scrapers.
- **CVR-as-discovery** — the *free official Danish business register* is the discovery engine, not a paid Google Maps scraper.
- **Legally defensible** — build on CVR (explicitly reusable for commercial use); don't scrape Google Maps at scale; phone-first outreach; honor `reklamebeskyttelse` + GDPR.
- **One identity** — the **CVR number** is the canonical lead key for dedup + joins.

## 3. Architecture

**Monorepo:**

| Path | Tech | Role |
|---|---|---|
| `apps/web` | Next.js (App Router, TypeScript) | Dashboard on Supabase (Auth + Postgres + RLS) |
| `services/worker` | Python (Scrapling, httpx, dnspython, lxml/selectolax) | Discovery + enrichment + scoring jobs |
| `supabase/` | SQL migrations | Schema + RLS policies |
| `docs/` | Markdown | Plan + research + runbooks |

**Data flow:**

```
CVR discovery ─► leads (dedup by CVR#) ─► website qualification ─► firmographic + financial
(branchekode +                            (Scrapling + DNS/TLS +     enrichment (CVR + XBRL)
 kommune/postnr +                          PageSpeed)                       │
 employee band)                                                             ▼
                                                              scoring 0–100 ─► dashboard
                                                              (website-selling)   │
                                                                                  ▼
                                                          Danish AI angles ─► pitch-ready lead
                                                                          (V2: reviews + outreach)
```

**Locked choices:** Next.js + Supabase (TS) for app/data; Python + Scrapling for scraping/enrichment; Claude (latest model) for Danish angles; deploy on Vercel (web) + Supabase (db) + a small worker host (Fly.io/Railway — Scrapling needs a real browser, so not serverless).

## 4. Data sources (free-first)

| Stage | Source | Cost | Notes |
|---|---|---|---|
| **Discover** | CVR register — Virk Elasticsearch `distribution.virk.dk/cvr-permanent` / Datafordeler | **Free** | `branchekode` + `kommune`/`postnr` + employee band; CVR# dedup key. Free creds via `cvrselvbetjening@erst.dk` + signed declaration. |
| **Qualify** | Scrapling (website fetch) | **Free** | viewport / HTTPS / legacy-markup / CMS-builder / copyright-year; FB link + Meta Pixel; contact scrape |
| **Qualify** | DNS + TLS (`dnspython`, `ssl`) | **Free** | dead / parked detection (NXDOMAIN, parking nameservers, HTTP final status, cert validity) |
| **Qualify** | PageSpeed Insights API | **Free** | 25k/day; `strategy=mobile`; lab scores + red-flag audits (small DK sites have no CrUX) |
| **Enrich** | Virk XBRL `distribution.virk.dk/offentliggoerelser` | **Free**, unauth | `GrossProfitLoss`, `ProfitLoss`, `Equity`, employees; **revenue often legally omitted (klasse B) → estimate** |
| **Angles** | Claude API | ~cents/lead | Danish sales angles |
| **Enrich (opt.)** | datacvrapi.dk / CVR Intel | ~199–499 DKK/mo | Only if pre-parsed financials/revenue become worth it |
| **(V2) Reviews** | Google Places free tier / Trustpilot public Business Units API | Free tier | **Deferred to V2** |

## 5. Scoring — tuned for selling websites

**0–100, hard-gated.** Weights: **Website-need 45 / Budget proxy 20 / Cares-about-presence 15 / Industry fit 12 / Recency 8.**

- **Hard gates (excluded / score 0):** `reklamebeskyttelse` set; company status inactive / bankrupt / under dissolution.
- **Website-need ladder (highest → lowest):** no website → dead/parked → Facebook-only → bad (no viewport / no HTTPS / legacy markup / old CMS / low PageSpeed) → outdated → modern (deprioritize).
- **Budget proxy:** employee band (2–20 ideal) + gross profit / equity where filed.
- **Cares-about-presence:** has a FB page / Meta Pixel / socials (markets online → values web).

Full rubric + field list: [`RESEARCH-lead-qualification-2026.md`](./RESEARCH-lead-qualification-2026.md). The old `leadforge` scoring (rewarded modern sites + "no ads") is **inverted** for this offer.

## 6. Scope

- **V1 (this plan):** discovery · website qualification · firmographic + financial enrichment · scoring · dashboard · Danish AI angles · compliance · deploy. Phone-first.
- **V2:** reviews & reputation (Google / Trustpilot / Facebook) · outreach automation (Outreach Tracker + Dropcontact email + sequences) · scale (caching / scheduling / multi-region / cross-search dedup).

## 7. Milestones

| # | Milestone | Goal |
|---|---|---|
| **M0** | Foundation & scaffolding | Monorepo, Supabase project, schema + RLS, auth, CI |
| **M1** | CVR discovery engine | Find all businesses of a type in an area, dedup by CVR#, suppress protected |
| **M2** | Website qualification | Detect & score "no/bad website" (the core qualifier) |
| **M3** | Firmographic & financial enrichment | Employees, status, founding, P-units; XBRL financials + revenue estimate |
| **M4** | Lead scoring & qualification gate | 0–100 website-selling score + hard gates + ranking |
| **M5** | Leads dashboard | Search-with-filters UI, leads table, lead detail, pipeline |
| **M6** | AI Danish sales angles | Claude-generated pitch angles + "make demo" hook |
| **M7** | Compliance, deploy & ship V1 | LIA/privacy/suppression, deploy, observability, E2E |
| **V2** | Reviews, reputation & outreach | Deferred enhancements |

Each milestone is a GitHub **epic** issue with deliverables, acceptance criteria, and a task checklist; near-term tasks are broken out as linked sub-issues.

## 8. Compliance (Denmark) — design constraints

- **Markedsføringsloven §10:** cold B2B **email** needs prior consent (no B2B exemption) → **V1 is phone-first**; build consent/opt-out capture before any email channel. Cold **B2B phone calls are generally legal**.
- **GDPR:** Art. 6(1)(f) legitimate interest + a **written LIA**; **Art. 14** privacy notice delivered **at first contact** (state the source = CVR); **absolute Art. 21 opt-out**.
- **Suppression:** exclude CVR `reklamebeskyttelse`; screen sole-traders / natural persons against the **Robinson list**. Treat sole-trader (enkeltmandsvirksomhed) contact data as personal data.

## 9. Cost

V1 ≈ **$0/month**: free CVR + Scrapling + PageSpeed + XBRL. Variable: ~cents/lead for Claude angles; ~$5–10/mo worker host. Scale knobs (paid financials, reviews APIs) deferred to when volume justifies them.

## 10. Key risks & mitigations

- **Scrapling reliability on hard anti-bot targets (~58%)** → use it for business websites + DK directories (light anti-bot), not Google Maps; retry + `StealthyFetcher` fallback.
- **CVR ↔ website matching** (CVR website coverage is partial) → website resolver + search fallback; store match confidence.
- **Revenue often undisclosed (klasse B)** → estimate from sector × employees / gross-margin; never hard-gate on revenue.
- **Datafordeler REST → GraphQL migration (Q2 2026)** → use the stable Elasticsearch bulk channel; isolate behind a CVR client interface.
