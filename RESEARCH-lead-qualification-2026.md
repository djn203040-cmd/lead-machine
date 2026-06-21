# Lead Machine — Qualification & Enrichment Research (June 2026)

B2B lead-gen for a web-design agency selling $1–2k websites to Danish local businesses, then upselling systems/infrastructure. Core qualifier: **does the business have NO website, or a BAD/outdated one?** Those are the best leads.

> Sourcing note: many official docs (Google, Meta, Trustpilot, risika.com, roaring.io, the `*.dk` gov sites) actively block automated fetching (HTTP 403). Figures below are cross-corroborated from multiple 2026 sources, but **verify the live pricing/limit pages before committing numbers to a cost model** — Google Maps SKU prices and marketplace scraper prices move quarterly. Conversions use ≈ $1 = €0.92 = 6.85 DKK (June 2026).

---

## 1. Website presence & quality detection (the core qualifier)

### 1.1 Does the business have a website? (Google Maps + does-it-load)

**Get the URL from Google Places API (New / v1).** The field is **`websiteUri`** (legacy API field = `website`). It is **not** returned by default — you must request it in the `X-Goog-FieldMask` header.

- The catch — **`websiteUri` is an Enterprise-tier field.** In the New API, Place Details is billed at the **highest SKU among the fields you request**, and `websiteUri`, `rating`, `userRatingCount`, `nationalPhoneNumber`/`internationalPhoneNumber`, and opening hours are all **Enterprise**. So any call that pulls the website is billed at the Enterprise rate, **even if every other field is cheaper**. Good news: pulling phone + rating + count in the *same* call costs no extra — it's one Enterprise charge per call.

**2026 Places API pricing (per 1,000 calls, first volume tier):**

| Place Details SKU | $/1,000 | Free/month | Gets you |
|---|---|---|---|
| Essentials | $5 | 10,000 | IDs, location, address components |
| Pro | $17 | 5,000 | displayName, formattedAddress, types |
| **Enterprise** | **$20** | **1,000** | **websiteUri, rating, userRatingCount, phone, hours** |
| Enterprise + Atmosphere | $25 | 1,000 | **`reviews` array**, reviewSummary |

- **The flat $200/month Maps credit is GONE** (removed **1 March 2025**), replaced by **per-SKU free caps: 10k Essentials / 5k Pro / 1k Enterprise per month.** API key + billing enabled are mandatory; no anonymous access.
- **Cost reality for you:** website lookups draw from the **Enterprise** bucket → **1,000 free/month, then $0.02 (~€0.0185 / ~13 øre) per business.** Enriching 10,000 businesses/month with website+phone+rating ≈ **$180 (~€166)/month**.
- Efficient pattern: **Text/Nearby Search** to discover businesses and resolve `place_id` with cheap fields, then **one Enterprise Place Details call** per promising business for website+phone+rating.
- Docs: `developers.google.com/maps/documentation/places/web-service/place-details` · field→SKU table: `.../web-service/data-fields` · pricing: `developers.google.com/maps/billing-and-pricing/sku-details` · March 2025 change: `developers.google.com/maps/billing-and-pricing/faq`

**Does the domain actually resolve/load?** (a `websiteUri` can be dead or parked). Run checks cheap→expensive and combine:

1. **DNS** — query A/AAAA on apex + `www`. `NXDOMAIN` or no address record = dead (free, kills obvious dead domains first). `NOERROR` ≠ working site.
2. **Nameserver match** — pull NS; if it matches a known parking provider, it's parked with high confidence **without loading the page**: `*.sedoparking.com`, `*.bodis.com`, `*.parkingcrew.net`, `*.above.com`, `*.afternic.com`, `*.dan.com`, `parkingpage.namecheap.com`, `*-domain.domrobot.com`. (List: gist.github.com/CodeAlDente/33aeb7ff369e7ecd2d52abd0d0ee7d59)
3. **HTTP status + redirects** — `HEAD` for up/down + status, then `GET` on survivors. Final `200` after redirects = reachable; `4xx/5xx`/refused/timeout = dead. **Redirect to a marketplace host** (sedo/dan/afternic) = parked/for-sale.
4. **Parked-content heuristics** (for the "200 but suspicious" bucket): high third-party/ad-iframe ratio, very low real-text ratio, "buy this domain / domain is parked / renew" markers, registrar placeholder pages.
5. **TLS cert** — handshake succeeds, not expired (`notAfter`), hostname matches SAN. A valid cert is a strong "real, maintained site" signal; absence alone isn't fatal (some tiny legit DK sites are HTTP-only).

Classify **DEAD** (NXDOMAIN / no A / refused / 4xx-5xx), **PARKED** (parking NS / marketplace redirect / parked content), or **LIVE & REAL** (A-record + final 200 same-domain + valid TLS + substantive content). Optional turnkey: APIVoid parked-domain API (`apivoid.com/api/parked-domain/`).

### 1.2 Programmatically scoring "needs a new website"

Detection method and strength for each signal (strongest first):

**Tier 1 — strongest, cheapest, score heavily (all from a single static HTML fetch):**

- **No responsive viewport meta tag** — parse `<head>` for `<meta name="viewport" content="width=device-width...">`. Absence ⇒ non-responsive, pre-~2015 site. **The single most decisive cheap signal** in a mobile-first world; Lighthouse even skips its `font-size`/`tap-targets` audits when it's missing.
- **No HTTPS / expired-invalid SSL** — try `https://` first; flag HTTP-only or no HTTP→HTTPS redirect; read the cert and catch expiry/mismatch. **Very strong and rising:** Chrome's "Always Use Secure Connections" warning rolls out to ~1B users **April 2026 (Chrome 147)** and **all users by Oct 2026** — a concrete, datable sales hook ("your visitors will see a Google security warning this year").
- **Legacy hand-coded markup** — `<table>` used for layout, `<font>` tags, `bgcolor`/`align`, spacer GIFs, framesets, and **old-editor `generator` metas** (`Microsoft FrontPage`, `Adobe Dreamweaver`). Dead giveaways of a decade-old site.
- **No CMS at all** (detection by elimination, see 1.4) — for a non-technical local business this almost always means "built once years ago, never updated."

**Tier 2 — strong positive filters, especially combined:**

- **Old copyright year in footer** — regex `(?:©|&copy;|&#169;|copyright)\s*(?:\d{4}\s*[–-]\s*)?(\d{4})`, take **max** year, compare to 2026. **Caveat:** many footers auto-update via JS `new Date().getFullYear()` — a static fetch won't execute it (you'll see no year, not a current one), and a current year is a *weak* signal; an **old hardcoded year is a reliable positive**. This is exactly the technique the lead-gen playbooks use (Datablist flags copyright ≤2020 + non-responsive; `datablist.com/how-to/find-old-websites`).
- **Slow PageSpeed/Lighthouse score** — see 1.3. Moderate as proof of age, but the **best pain-point sales argument** (53% of mobile users abandon >3s loads). Gate it behind Tier-1 static filters to conserve quota.

**Tier 3 — supporting/tie-breakers only (noisy, often absent):**

- **`Last-Modified` header / sitemap `lastmod`** — frequently missing or auto-stamped to redeploy/regeneration time; **>50% of sitemaps have wrong/missing lastmod** (HTTP Archive). A *consistently old* sitemap across all URLs corroborates staleness; a single header doesn't.
- **One-page vs multi-page** — count distinct internal links (drop `#anchors`/`mailto:`/`tel:`); single `<url>` sitemap confirms. **Ambiguous alone** — many modern local sites are deliberately single-page. More an *upsell/thinness* angle ("you're leaving search traffic on the table") than proof of age.

**Mobile-friendliness note:** Google's standalone **Mobile-Friendly Test + its API were retired (Dec 2023)**; the old URL now redirects to Lighthouse docs. **Lighthouse/PageSpeed Insights is the 2026 replacement** — read the `viewport`, `font-size`, `tap-targets` audits, or detect viewport yourself + render with a mobile UA and check `scrollWidth > innerWidth` for horizontal overflow.

### 1.3 PageSpeed Insights API / Lighthouse

**PSI API is FREE in 2026** (no paid tier). 
- **Quota: 25,000 queries/day, 400 queries/100s** (~4 req/s). **API key** is optional but required in practice for automated/batch use (free, from Google Cloud Console).
- **Endpoint (v5, current):** `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={URL}&strategy=mobile&category=performance&category=seo&category=accessibility&category=best-practices&locale=da&key={KEY}`. **Always set `strategy=mobile`** (default is desktop). `locale=da` gives Danish audit text for your client reports.
- **Returns:** `lighthouseResult.categories.{performance|accessibility|seo|['best-practices']}.score` (0–1, ×100). **PWA category was removed** (Lighthouse 12, May 2024) — four categories now. Lab metrics under `lighthouseResult.audits[...]`: `largest-contentful-paint`, `cumulative-layout-shift`, `total-blocking-time`, `speed-index`. Binary red-flag audits great for the pitch: `is-on-https`, `viewport`, `font-size`, `tap-targets`, `document-title`, `meta-description`.
- **Core Web Vitals:** LCP / CLS / **INP** (INP **replaced FID** in March 2024; FID gone). Good thresholds: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1.
- **Critical limitation for you:** CrUX **field data only exists for sufficiently-popular sites** — typical Danish plumber/restaurant sites return "No Data", so **rely on lab/`lighthouseResult` scores**. Also, Google is **deprecating CrUX out of the PSI API** anyway (use the dedicated CrUX API if you ever need field data). **Build scoring on lab data.**

**Self-hosted Lighthouse (free alternative, no rate limit):**
- `lighthouse` npm — **v13.4.0** (Jun 2026), **Apache-2.0**, needs **Node ≥22.19** + a Chrome/Chromium binary.
- `@lhci/cli` (Lighthouse CI) — v0.15.x, Apache-2.0; note it **bundles Lighthouse 12.6.1** (fine for scoring). `lhci assert` can enforce "fail if performance < 0.5".
- **PSI API vs local:** PSI = zero infra but 25k/day cap; local = unlimited but you run headless Chrome (RAM-heavy; fresh Chrome per URL, limit parallelism, scale horizontally on fixed-perf instances like `n2-standard-2`/`m5.large`, run each URL a few times and take the median). Common pattern: PSI API for low volume, switch to self-hosted once you exceed quota — both give the same *lab* scores for small sites.

### 1.4 Tech-stack / builder / CMS detection (tools + open-source)

**Detection markers (DIY from HTML/headers/asset paths — free):**
- **WordPress:** `/wp-content/`, `/wp-includes/`, `/wp-json/`, `/wp-login.php`; `X-Pingback` header; `<meta name="generator" content="WordPress X.Y">` (**leaked version dates the install**).
- **Wix:** `static.wixstatic.com`, `wix-warmup-data`, `X-Wix-*` headers.
- **Squarespace:** `static1.squarespace.com` / `*.squarespace-cdn.com`, `sqsp-`/`squarespace-` classes, `Static.SQUARESPACE_CONTEXT`.
- **Webflow:** `assets.webflow.com`, `*.webflow.io`.
- **Shopify:** `cdn.shopify.com`, `/cdn/shop/`, `Shopify.theme`, `X-Shopify-*`.
- **Hand-coded/legacy:** no generator or an old IDE generator + table layout/`<font>` (the prime targets).
- Builder identity itself is **neutral** (a current WordPress/Wix site can be modern). What's **strong** is legacy markup + a leaked old CMS version.
- Bulk reverse-search by source string: **PublicWWW** (`publicwww.com`, indexes 200M+ sites' HTML/JS, paid API) — query for FrontPage comments, a Wix script, etc., to *find* sites matching a legacy fingerprint at scale.

**Commercial APIs:**
- **Wappalyzer** — went **closed-source (July 2023)**; the *client* is proprietary, but the **fingerprint rules stay MIT and community-maintained**. API: **free 50 lookups/month**, then **Pro $250/mo (5k lookups), Business $450/mo (20k), Enterprise $850+/mo.** Credits ≈ 1/site, expire in 60 days. (`wappalyzer.com/pricing`, `/api`)
- **BuiltWith** — **free single-site lookup** (extension/web form); API gated to paid: **~$295 Basic / $495 Pro / $995 Team / $6,000 Team-Ultra** per month in 2026 (a ~6× hike). Returns CMS/builder/analytics/hosting + history. (`api.builtwith.com/domain-api`)

**Open-source / self-host alternatives (2026 status):**
- **`enthec/webappanalyzer`** and **`tunetheweb/wappalyzer`** — actively maintained MIT forks of the **fingerprint database** (the data everything else consumes). These are what keep the OSS ecosystem alive.
- **`dochne/wappalyzer`** — snapshot of the last open Wappalyzer before it went private.
- **`wappalyzer-next` (s0md3v)** — Python lib using the same approach; needs Firefox + geckodriver; output matches the extension (~20s/full analysis).
- **WappalyzerGo / webanalyze (Go)** — fast, consume Wappalyzer fingerprints; good for bulk.
- **`python-Wappalyzer` (chorsley)** — older, less maintained; the forks above are healthier.
- **Apify "Wappalyzer replacement" actor** (`nexgendata/wappalyzer-replacement`) — ~**$10/1,000 domains** managed.

**Recommendation:** for a high-volume Danish crawl, **self-host a Go/Python detector against the `enthec/webappanalyzer` fingerprints** (free, unlimited) and DIY the legacy-markup/viewport/HTTPS checks; reach for Wappalyzer/BuiltWith API only if you want a managed datastore or historical data.

### 1.5 "Just a Facebook page" / no site at all

Classify the `websiteUri` host into buckets (high value as a qualifier — these are your hottest leads):

- **NO website** — empty `websiteUri`.
- **Social-media-only** — host is `facebook.com`/`m.facebook.com`/`fb.me`, `instagram.com`, `linktr.ee`/`linktree`, `beacons.ai`, `linkin.bio`. Very common for small DK local businesses.
- **Free-subdomain / builder placeholder** — `*.wixsite.com`, `*.weebly.com`, `*.godaddysites.com`, `sites.google.com`, and especially **`business.site`** (Google's auto-generated Business Profile websites were **shut down by Google in 2024** and now 4xx/redirect — a `business.site` URL or a business that *had* one is a strong "no real website" lead).
- **Real custom-domain site** — then run the 1.2 quality scoring.

Maintain an explicit denylist of these hosts/patterns; anything on it = "no real website" = top lead.

---

## 2. Reviews & reputation enrichment (cares about presence / has budget)

### 2.1 Google reviews

**Places API (New):** fields `rating` (avg float), `userRatingCount` (int), `reviews` (array). Each review: `text`, `originalText`, `rating`, `authorAttribution`, `publishTime`, `relativePublishTimeDescription`.
- **Hard-capped at 5 reviews per place** via the API (unfixable; the Google Business Profile API returns all reviews but **only for locations you own** — useless for prospecting).
- **Cost:** `rating` + `userRatingCount` = **Enterprise $20/1k** (and you already pay this for `websiteUri` in the same call — free add-on). The `reviews` *text* array bumps you to **Enterprise + Atmosphere $25/1k**. **1,000 free/month** either way.
- **For lead scoring, pull `rating` + `userRatingCount` only** (cheaper, and that's the signal you need). Skip review text unless doing sentiment.

**Scraping alternatives (uncapped, cheaper per review, for full history/sentiment):**
- **Outscraper** — pay-as-you-go, no subscription: places $3/1k (first 500 free), **reviews $3/1k**, not capped. Simplest API. (`outscraper.com/google-maps-reviews-api`)
- **DataForSEO** — cheapest at scale, **~$0.00075–0.002 per request** billed per 10 reviews; $50 min deposit; async. (`dataforseo.com/pricing/business-data/google-reviews-api`)
- **SerpApi** — $0 (250/mo) → $75/mo (5,000 searches, 8 reviews/page). No Trustpilot engine. (`serpapi.com/google-maps-reviews-api`)
- **Apify** Compass actors — ~$0.25–0.50/1k reviews. (`apify.com/compass/google-maps-reviews-scraper`)
- **Legality:** scraping public data is CFAA-safe in the US (hiQ/Van Buren) but breaches Google ToS (risk = IP/key blocks). **GDPR matters:** review text contains reviewer PII — **store aggregate rating/count/sentiment, not reviewer identities/raw text.**

### 2.2 Trustpilot (big in Denmark — HQ Copenhagen; a low/zero TrustScore is a strong buying signal)

Three distinct API surfaces — don't conflate:
- **Business APIs** (manage your *own* profile) — OAuth, paid plan, owner-only. Not for prospecting.
- **Business Units API (public)** — **the right one for third-party enrichment.** `GET https://api.trustpilot.com/v1/business-units/find?name={domain}`, **API-key (Client ID) auth only**, no ownership needed. Returns exactly what you want: **`score.trustScore` (0–5), `score.stars`, `numberOfReviews` {total, oneStar…fiveStars}** (the full star distribution). Catch: getting an API key now generally ties to a Trustpilot account; Trustpilot increasingly steers third parties to Data Solutions.
- **Data Solutions API** — productized bulk feed with **country=DK filtering** + full review text (≤5 recent) + GDPR Deletions API. **Waitlist + contact-sales pricing** (Enterprise-only; likely over-budget for a small agency).
- Self-serve Business plans (Free / Starter ~$99 / Plus ~$319 / Premium ~$799 / Advanced ~$1,099 per month) are for managing *your own* reviews — **none include third-party data API** (only Enterprise ~$6k–30k/yr does). Don't buy these for enrichment.

**Scraping** `dk.trustpilot.com/review/{domain}`: structured data is **easy to parse** — every profile embeds `<script id="__NEXT_DATA__">` JSON (`props.pageProps.businessUnits.businesses` → trustScore/numberOfReviews) and schema.org `AggregateRating` JSON-LD (`ratingValue`, `reviewCount`). **But** Trustpilot runs aggressive anti-bot (Cloudflare-style; needs residential proxies; throttle to ~15–20 req/min), and ToS prohibits scraping. **Restrict any DIY scrape to aggregate facts (score, count, distribution)** — those are non-personal facts (low risk); storing review text/reviewer names concentrates GDPR + copyright + ToS risk.

**Turnkey scraper providers:** OpenWeb Ninja (free 100/mo, ~$25/mo Pro — cleanest for prototyping, returns TrustScore+reviews), DataForSEO ($0.00075/20 reviews, $50 min — cheapest at scale), Apify (`casper11515` $20/mo rental, or `automation-lab` pay-per-review).

**Recommendation:** try to get a **Trustpilot public Business Units API key** (free, returns all 3 core fields by domain); if hard to obtain, use **OpenWeb Ninja** (low volume) or **DataForSEO** (scale) — aggregate fields only.

### 2.3 Facebook ratings / page presence

**Reality: the official Graph API gives a third party essentially nothing here.**
- **Star ratings are dead** — replaced by yes/no **Recommendations**, which were **never exposed to the API**. `overall_star_rating`/`rating_count` return default/empty under the (now-mandatory) New Page Experience. The `ratings` edge needs a **page-admin access token** — you can't get it for a business you don't control.
- Reading *any other* business's page needs **Page Public Content Access (PPCA)** = app review + business verification + possibly contracts — **impractical and commonly rejected** for agency lead-gen. `fan_count` is being phased out for followers; Page Insights metrics are being pruned (a swath errors out by **June 15, 2026**). Current Graph API ~v23–v25.
- **What actually works:**
  1. **Best signal = detect on the business's own website** (free, legal, no Meta gatekeeping): a `facebook.com/<slug>` **link** in the HTML/footer, and the **Meta Pixel** (`connect.facebook.net/.../fbevents.js`, `fbq(`). The Pixel is a strong "actively markets / runs ads" signal. Parse it yourself from page HTML at ~zero cost. This *is* the "cares about online presence" signal you want.
  2. **Enrich on demand** only when a lead looks promising: **Apify Facebook Pages Scraper** (~$6.60/1k pages → name, followers, email, rating field, ad-running status), **Facebook Reviews Scraper** (~$2.50/1k → `isRecommended` yes/no), or **Bright Data** Web Scraper API ($0.75/1k) / Pages dataset ($250/100k). Legal tailwind: **Meta v. Bright Data (Jan 2024)** — logged-off scraping of public data isn't barred by Meta's Terms.

---

## 3. Lead scoring model (0–100) for ranking website-selling leads

Design principle: **website pain dominates** (that's what you sell), reviews/budget/fit modulate, recency and reachability gate. Two parts: a hard **qualification gate**, then a **0–100 weighted score**.

### Field list (per lead)

```
# Identity / source (Google Places + CVR)
place_id, cvr_number, name, address, postal_code, city, lat, lng
primary_type / branchekode (DB07/NACE)

# Website presence & quality
website_uri, website_bucket  # none | social_only | free_subdomain | real
domain_status                # dead | parked | live
has_https, ssl_valid
has_viewport_meta
copyright_year_max           # from footer; null if none/JS-rendered
cms / builder                # wordpress | wix | squarespace | none(handcoded) | ...
cms_version_leaked, legacy_markup_flag   # table layout / FrontPage etc.
psi_perf_score, psi_seo_score            # lab, 0-100
is_one_page

# Reviews / reputation
google_rating, google_review_count
trustpilot_score, trustpilot_review_count
has_fb_page, has_meta_pixel

# Budget proxy (CVR)
employee_band                # ANTAL_2_4 ... ANTAL_1000_999999
employee_count_exact         # monthly, where available
annual_revenue / equity      # from årsrapport, if class B+
company_age_years            # from start date

# Reachability / compliance
email, phone, decision_maker_name
reklamebeskyttelse_flag      # CVR marketing-protection flag (BLOCKS marketing)
```

### Qualification gate (drop or deprioritize before scoring)

- **Drop** if `reklamebeskyttelse_flag` = true (CVR marketing-protection — may not use CVR-sourced contact for direct marketing).
- **Drop** if industry/`branchekode` is out of target (e.g. pure holding companies, public authorities).
- **Hard "no website" leads** (`website_bucket ∈ {none, social_only, free_subdomain}` or `domain_status ∈ {dead, parked}`) **bypass the quality sub-score and get max website points.**

### Scoring rubric (weights sum to 100)

| Factor | Weight | Scoring |
|---|---:|---|
| **Website need** (core) | **45** | none/dead/parked/social-only/free-subdomain = **45**. Real site scored on badness: no viewport +12, no HTTPS/expired +10, legacy markup or no-CMS +8, copyright ≤2020 (hardcoded) +6, PSI perf <50 +6, PSI perf 50–69 +3, one-page +3 (cap 45). Modern real site (responsive, HTTPS, perf ≥70, recent) → ~0–5. |
| **Cares about online presence** | **15** | Google reviews: ≥20 →15, 5–19 →10, 1–4 →5, 0 →0. +Trustpilot presence or Meta Pixel/active FB page → small bonus (cap 15). High review *count* with a *bad website* is the sweet spot. |
| **Budget proxy** | **20** | Employee band: 1 →4, 2–4 →10, 5–9 →16, 10–49 →20, 50+ →14 (likely has an agency already / longer sales cycle). Or revenue/equity if available. Sole-trader (0 emp via ATP) → 4. |
| **Industry fit** | **12** | Local service businesses that live/die on local search and look good (restaurants, dentists, salons, trades, clinics, fitness, hospitality, real estate) →12; marginal →6; poor fit →0. |
| **Recency / activity** | **8** | Open/active in CVR + recent Google review (<6mo) →8; active but stale →4; dormant →0. (Confirms the business is alive and worth pitching.) |

`score = Σ factors` (0–100), applied only to gate-passing leads. **Sort desc.** A great lead ≈ no/bad website (45) + has reviews so cares (15) + 5–9 employees (16) + restaurant (12) + active (8) ≈ **96**.

### Worked example

Hair salon, Aarhus: website = `facebook.com/...` (social-only → **45**); 64 Google reviews at 4.6 (cares → **15**); employee band 2–4 (→ **10**); salon = strong fit (→ **12**); reviewed last month (→ **8**). **Score = 90.** Top-priority lead: clearly invests in reputation, has zero real website, sells a visual service. Perfect $1–2k website pitch.

> Tune weights against your own close-rate data after the first ~50 deals. Start here; let outcomes move the numbers.

---

## 4. Contact enrichment (decision-maker email/phone) + Danish GDPR

### 4.1 Danish CVR (the free firmographic backbone)

**Official, free, CC BY 4.0** (attribute "Det Centrale Virksomhedsregister (CVR)"). Three official access paths:
- **Erhvervsstyrelsen Elasticsearch distribution** — bulk channel. `http://distribution.virk.dk/cvr-permanent/virksomhed/_search` (+ `produktionsenhed/_search`, `deltager/_search`). HTTP Basic auth. **Register free** by emailing `cvrselvbetjening@erst.dk` (org name + CVR + contact, sign a declaration; ~2–3 weeks). No published rate limit.
- **Datafordeler** — REST `HentCVRData`/`SoegCVRData` **being phased out Q2 2026**; migrate to the new **CVR GraphQL** service (plus CVR Fildownload bulk + CVR Hændelser change-feed). *Most time-sensitive finding — build on GraphQL, not the REST that's sunsetting.*
- **Web UI** for manual checks: `datacvr.virk.dk`.

**Fields:** CVR number, name, address, start/end date, legal form, **industry (DB07/NACE: 1 hovedbranche + up to 3 bibrancher)**, phone/email/website **where registered**, **employee data**, P-numbers (per-location), owners >5%, management/board, signing rules.

**Budget proxies in CVR:**
- **Employees** — banded `intervalKodeAntalAnsatte` (always present: `ANTAL_0_0`, `ANTAL_1_1`, `ANTAL_2_4`, `ANTAL_5_9`, `ANTAL_10_19`, `ANTAL_20_49`, … `ANTAL_1000_999999`), plus an **exact monthly `antalAnsatte`** now surfaced (2024–25 rollout) where available. Sourced from ATP/eIndkomst via Danmarks Statistik, ~1.5mo in arrears. **Caveat:** an owner drawing no ATP-salary can show 0 employees despite an active business — use `antalInklusivEjere` and the annual-report figure as cross-checks.
- **Revenue/financials** — from the **årsrapport** (annual report). Class B+ must disclose **average full-time employees** (Årsregnskabsloven §68). For parsed financials use a commercial API (below) or pull XBRL from Virk.

**Commercial CVR/enrichment APIs** (easier than raw ES, add parsed financials/credit):
- **Risika** (`risika.com`) — Nordic firmographics + **parsed financials + credit score/limit + bankruptcy history**; REST/JSON, bearer token; explicitly lists **lead-gen/enrichment** as a use case. **Pricing = contact-sales** (annual; trial after a meeting).
- **Roaring** (`roaring.io`) — dedicated **DK CVR endpoints**, Financial Information (latest + 5-yr statements/ratios), beneficial owners; REST/JSON, OAuth2; **self-serve free sandbox**, pay on production activation; **from ~1,495 SEK/mo** (third-party figure) + volume/enterprise contact-sales. **Best self-serve option.**
- **cvrapi.dk** — free-but-rate-limited simple JSON proxy (firmographics + employee stats, **no parsed financials**); paid quota upgrade for commercial use. For cheap *financials*, that's **datacvrapi.dk** (different vendor; Business ~499 kr/mo with XBRL regnskab). Others: `cvr.dev`, `cvrintel.dk` (free 200/mo).

### 4.2 Finding the decision-maker email/phone

- **CVR first** — often has a registered company phone/email; owner/management names for small firms.
- **Website contact-page scraping** — parse `mailto:`/`tel:` links and the `/kontakt`, `/om-os` pages for emails, phones, contact forms. Cheap and high-yield for local businesses (owner's email is often right there).
- **Email pattern guessing + verification** — derive `fornavn@`, `fornavn.efternavn@domain` from the owner name (CVR) + domain, then verify.
- **Finder/enrichment tools (2026 pricing):**
  - **Dropcontact** (`dropcontact.com`) — **best for Europe/GDPR.** Algorithmic (no stored personal-data DB → sidesteps GDPR risk); strongest Western-EU coverage. **From €24/mo (1,000 credits); API gated to Business €79/mo.** Email-only (no phones).
  - **Hunter.io** — **Free 25 searches+50 verifications/mo**; Starter $49 (500+1,000), Growth $149 (5k+10k), Business $499 (50k+100k). **API needs Growth+.** Returns confidence score. Email-only.
  - **Apollo.io** — huge DB (US-skewed): Free 75 credits/mo; Basic $49, Professional $79/user/mo. Has phones + buying signals. EU match weaker (~40–50%).
  - **Snov.io** — Starter $39 (1k credits) → $369 (50k); find+verify = 2 credits; unlimited seats.
  - **Others:** FullEnrich / Dropcontact strongest for FR/EU; RocketReach, Anymailfinder, Clearbit (now HubSpot Breeze).
- **Email verification** (deliverability — protects sender reputation): NeverBounce, ZeroBounce, Bouncer — fractions of a cent per check; Hunter/Dropcontact include verification. Always verify before sending.
- **Recommended stack:** CVR + website scrape (free, highest local yield) → **Dropcontact** for EU-clean email enrichment → verify → fall back to pattern-guess + verify.

### 4.3 GDPR & Danish marketing law for B2B outreach (2026)

**Email (the strict one):**
- **Markedsføringsloven §10 (spam ban) applies to B2B too** — the prohibition on unsolicited electronic marketing without prior consent covers companies, authorities, *and* consumers. **Cold marketing email to a Danish business generally needs prior consent** (or the narrow "soft opt-in": existing customer, similar products, opt-out offered at collection and in every message).
- **Personal vs role addresses:** a generic role address (`info@`, `kontakt@`) is lower-risk than a named person's mailbox (`anna@`). Sending to a specific person's work email is processing personal data — needs a lawful basis.
- **GDPR Art. 6(1)(f) legitimate interest** can be the lawful basis for *processing* B2B prospect data, but it **does not override §10's consent requirement** for the act of sending marketing email. Net: cold *email* is legally constrained in DK — lean on consent/soft-opt-in or pivot to phone.

**Phone (the permissive one):**
- **B2B cold calling is generally lawful in Denmark without prior consent** for limited companies (A/S, ApS) — there's no general ban on unsolicited calls to *erhvervsdrivende*; you must still follow good marketing practice (no misleading/aggressive behavior).
- **Robinsonlisten** protects *private individuals*, not companies — but **sole proprietors run from home are protected** if they object or are on the list. So screen sole-traders.
- **This makes phone the stronger primary channel for your DK cold outreach;** use email for warm/consented follow-up.

**CVR-specific compliance:**
- **`reklamebeskyttelse` (marketing-protection) flag** — units flagged in CVR **may not have their CVR-sourced contact data used for direct marketing**, and you must pass the flag through to any customer you resell to. **Honor it as a hard gate** (it's in the rubric).

**Practical compliance checklist:** publish a privacy notice; identify lawful basis per channel (legitimate interest for processing; consent/soft-opt-in for email); data minimization (store aggregate review signals, not reviewer PII); easy opt-out in every message + suppression list; don't buy scraped contact lists; honor `reklamebeskyttelse` and Robinsonlisten (sole-traders). Watch Datatilsynet guidance. *(This is research, not legal advice — confirm with a Danish lawyer before launch.)*

---

## V1 qualification + scoring pipeline (recommended)

Cheap-to-expensive funnel; spend paid API quota only on survivors.

1. **Discover** (Google Places **Text/Nearby Search**, cheap fields) — pull Danish businesses by `branchekode`/type × city/postal grid → `place_id`, name, address. *(Pro/Essentials SKU.)*
2. **Firmographics gate** (**CVR**, free, GraphQL) — join on name/address → CVR number, branchekode, employee band, age, status, registered phone/email, **`reklamebeskyttelse`**. **Drop protected + out-of-industry + inactive.**
3. **Website presence** (one **Places Enterprise** Place Details call per survivor, $0.02) — get `websiteUri` + `rating` + `userRatingCount` + phone in a single call. **Bucket** the URL (none / social-only / free-subdomain / real). Non-real buckets → flag as hot, skip to step 6.
4. **Domain liveness** (free) — DNS → parking-NS → HTTP final-status → TLS. Dead/parked → hot lead.
5. **Quality scan** (free static fetch on real live sites) — viewport meta, HTTPS, copyright-year regex, CMS/legacy-markup fingerprint (self-hosted detector on `enthec/webappanalyzer` data), internal-link count, FB link + Meta Pixel. **Then** spend **PSI API** (`strategy=mobile`, lab scores) only on sites that passed the static filters and look borderline — conserve the 25k/day quota; self-host Lighthouse if you exceed it.
6. **Reputation enrich** — Google `rating`/`count` (already pulled in step 3); optionally **Trustpilot** public Business Units API (or OpenWeb Ninja) for TrustScore by domain.
7. **Score** — apply the 0–100 rubric (§3) to gate-passing leads; sort desc.
8. **Contact enrich** (top-N only) — CVR + website-scrape email/phone → **Dropcontact** (EU email) → **verify** → store decision-maker. Mark channel: **phone-OK** (B2B, non-sole-trader, not Robinson) vs **email-needs-consent/soft-opt-in**.
9. **Compliance pass** — enforce `reklamebeskyttelse` + Robinson (sole-traders) suppression; attach lawful-basis + opt-out metadata.

**V1 cost profile:** discovery + CVR ≈ free–cheap; website+rating ≈ $0.02/business (1,000 free/mo); PSI free; tech-detection self-hosted free; contact enrichment the main variable cost (Dropcontact €24–79/mo). You can qualify and score **~1,000 Danish businesses/month at ~$0**, scaling at ~$20 per additional 1,000 for the website/reviews call.
