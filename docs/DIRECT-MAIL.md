# Handwritten Direct Mail Arm — spec + runbook

Extension to the lead machine: robot-handwritten letters (Pensaki, DE) to
decision makers, triggered by call outcomes, each carrying a per-recipient
short URL whose hits are the only feedback channel. Lives at **`/leads/mail`
("Breve")** next to the Powerdialer.

Status (Session 27, 2026-08-19): **built, migration `0012` applied live, not yet
run against Pensaki.** Prices/facts verified August 2026. See §7 for what is
still open before batch 1.

---

## 1. What it does

| Arm | Trigger | Copy angle | Where it enters the queue |
|---|---|---|---|
| A | Called, no answer | References the call attempt, no timestamp | Powerdialer → **"Intet svar → brev"** |
| B | Called, spoke, not interested | Acknowledges the no, drops the pitch | Powerdialer → **"Ikke interesseret"** |
| C | Cold, never contacted | Specific observation about their business | Breve → **Find modtagere** (or the lead page) |

Every letter carries a handwritten short URL **`sonorous.dk/<firma>`** →
`app/[slug]/route.ts` logs the hit (device, referrer, hashed IP) and 302s to
the personalised landing page `/l/<slug>`. First real scan fires a webhook to
the phone.

## 2. How it is built (this repo — Next.js + Supabase, no n8n)

```
dialer outcome ─┐
lead page ──────┼─► enqueueMail()  ─► legal filters ─► lead_mail (draft | rejected+reason)
Find modtagere ─┘        │
                         └─► slug minted (company name → a-z0-9), recipient snapshotted from CVR
                                                     │
                     human review: observation + [X] (✨ Claude draft optional) ─► approve (letter frozen ≤650 chars)
                                                     │
                       ≥10 approved ─► Opret batch ─► ⬇ CSV (Pensaki import template, + seed row)
                                                     │
                 "Markér som bestilt" ─► ordered · lead_notes stamped · follow-up call +12 d (arms A/C only)
                                                     │
                 "Overdraget til Deutsche Post" ─► sent · "Seed-brev landet" ─► real DE→DK transit on the batch
                                                     │
              sonorous.dk/<slug> ─► mail_scans + scan_count ─► 🔥 on the card, phone webhook, Scanninger tab
```

- **Schema** — `supabase/migrations/0012_direct_mail.sql`: `lead_calls`
  (every dial attempt incl. `no_answer`, which never moved `pipeline_status`
  before), `mail_batches`, `lead_mail`, `mail_scans`; three `SECURITY DEFINER`
  RPCs (`mail_track_scan`, `mail_landing`, `mail_opt_out`) granted to `anon` so
  the public pages need no service key. RLS = authenticated full access.
- **Copy** — `apps/web/lib/mail/letter.ts`: the three arms, `slugify`,
  `buildLetter` (deterministic; the only variables are first name, company,
  observation, [X], slug), 650-char guard. `MAX_LETTER_CHARS = 650`.
- **Filters** — `apps/web/lib/mail/eligibility.ts`: reklamebeskyttelse →
  Robinson (`suppressed`) → sole trader without a provisioned Robinson pass →
  no address. Reason kept on the row (`reject_reason`) so attrition is
  measurable; "Kør filtre igen" re-checks after e.g. Robinson screening.
- **Enqueue** — `apps/web/lib/mail/enqueue.ts` (shared by dialer + page).
- **Claude draft** — `apps/web/lib/mail/observation.ts` (`claude-opus-5`,
  structured JSON: observation / focus / evidence / confidence). Human approval
  is mandatory; the card shows the model's evidence sentence for the reviewer.
- **Export** — `apps/web/lib/mail/export.ts` + `/leads/mail/batches/[id]/export`
  (CSV, `;`-separated, BOM). Pensaki API v4 is beta and undocumented on our
  side → the import template is the reliable path; wire the API later.
- **Public** — `app/[slug]/route.ts` (root catch-all → 404 for anything that
  isn't a letter), `app/l/[slug]/page.tsx` (landing), `app/l/[slug]/nej-tak`
  (opt-out → `leads.suppressed = true`, reason `mail_optout`). Middleware
  (`lib/supabase/middleware.ts` → `isPublicPath`) lets these through unauth'd.
- **UI** — `app/leads/mail/page.tsx` + `_components/` (MailCard, BatchPanel,
  CandidatePicker, CreateBatchForm); `MailPanel` on the lead page; "Intet svar
  → brev" in the dialer; "Breve" nav tab.

### Domain

The letter says `sonorous.dk/<slug>`. That host must reach this Vercel app:
add `sonorous.dk` as a domain on the Vercel project (or a 301 from wherever it
lives today to `<lead-machine-host>/<slug>` — path preserved). Change the
printed host with `NEXT_PUBLIC_MAIL_PUBLIC_BASE`. Test with any slug from the
Breve page: `curl -I https://sonorous.dk/<slug>` → 302 to `/l/<slug>` and a
row in `mail_scans` (device `bot`/`unknown` for curl — not counted).

### Env (web/Vercel) — full matrix in `DEPLOY.md` §1

`ANTHROPIC_API_KEY`, `MAIL_ROBINSON_PROVISIONED`, `MAIL_SCAN_WEBHOOK_URL`,
`MAIL_SEED_NAME/_COMPANY/_STREET/_ZIP/_CITY`, `NEXT_PUBLIC_MAIL_PUBLIC_BASE`,
`NEXT_PUBLIC_MAIL_SENDER_NAME`, `NEXT_PUBLIC_MAIL_BOOKING_URL/_CONTACT_PHONE/_CONTACT_EMAIL`.

## 3. Vendor: Pensaki (Pensaki GmbH, Germany)

No Danish robot-handwriting service exists; PostNord Strålfors / InterMail
print. RoboQuill (UK) is the alternative (real pen, 180 words, QR inserts,
white-label) but non-EU + transit.

**Product: "Letters 2Go" A4 650** — real Lamy fountain pen, blank 100 gsm
white, DIN Lang no-window envelope hand-addressed, German stamp, mailed from
Germany via Deutsche Post Global Mail. Style "ALEX".

| Format | Chars | Price (incl. 19 % DE VAT) | ≈ DKK |
|---|---|---|---|
| **A4 650** | 650 incl. spaces | €5.80 | ~43 kr |
| A4 1000 | 1,000 | €6.80 | ~51 kr |

All-in (paper, envelope, writing, addressing, postage, worldwide delivery,
VAT). Envelope gets a separate 200-char allowance.

- **MOQ 10** per order (fewer = pay for 10). ⇒ batch, never per lead. The
  page warns under 10.
- **Timeline** ~8–12 business days order → mailbox (3 bd to Deutsche Post,
  confirmed by email, then DE→DK 3–7 bd — unverified; **seed your own address
  into batch 1** and record it with "Seed-brev er landet i dag").
- Copy never says "I called you Tuesday". Follow-up call is +12 days after
  order (batch setting), recalibrate off the seed.
- **Cannot** do a unique QR per letter (printed stationery = one static PDF
  per run; they advise blank paper for lead gen anyway). Workaround if ever
  needed: pre-printed inserts + their matching service. Never take the
  "shipped to you in open envelopes" route (Danish postage from 23 kr).
- **VAT:** 19 % DE VAT is not offsettable on a DK return → budget €5.80 real.
  Ask them about net invoicing under EU reverse charge (~16 % saving).
- Made-to-order 250+: "from €1.58" is net, ex-postage — not comparable. Ask
  for one all-in per-letter figure.

## 4. Why not a plotter (yet)

NextDraw 8511 Handwriting Bundle ($1,297.50), refurb AxiDraw V3, iDraw 2.0.
Blockers: Hershey fonts look drafted (need own hand vectorised + jitter — the
software Pensaki sells), no paper feeder (3–5 min/letter), and **Danish
postage**: PostNord stopped letters 30 Dec 2025; dao is the only operator,
from 23 kr, no red postboxes. DIY ≈ 26 kr vs 43 kr; pays back only if your
time is free (crossover at ~250 kr/h). Revisit if reselling, same-day, or a dao
erhverv volume deal.

## 5. Address sourcing & the three filters

We mail the **company address, att. the named decision maker**
(`lead_enrichment.contact.decision_makers` — owner/director first). Sole
trader → CVR address is the home address, and exactly the Robinson case.

1. **Reklamebeskyttelse** (CVR-loven §19) — `leads.reklamebeskyttet`;
   discovery already drops these, enqueue re-checks.
2. **Robinsonlisten** (MFL §10 stk. 4) — `leads.suppressed`. The worker stamps
   `robinson_screened_at` on every sole trader even with an **empty** list, so
   that stamp alone is not evidence: sole traders are rejected
   (`robinson_unscreened`) until `MAIL_ROBINSON_PROVISIONED=1`.
3. **Adressebeskyttelse** — irrelevant for the company address; surfaces as
   `no_address` when CVR has none.

Opt-out notice: there is no insert in the standard product, so it lives on
the landing page (footer form → `mail_opt_out`). Confirm this is acceptable
(open question) — if not, spend ~60 chars of the letter on it.

## 6. Copy, landing, follow-up, test design

- Never "jeg har undersøgt din virksomhed" — the observation is the proof.
  **A wrong observation is worse than none** → human pass on every letter.
- Landing shows *their* name, the observation, an industry demo (Loom/YouTube
  URL per letter, else the sector's typical time sinks), one CTA, opt-out.
- Follow-up: A/C call at +12 d ("Did my letter arrive?") — created as
  `lead_followups` on "Markér som bestilt". B: no call (judge on scan rate).
  No email (MFL §10). Land Tue–Thu, avoid Mondays and July: order ~10 bd
  before the target.
- **Pilot: 100 cold letters, 25 then 75, one copy variant, own address
  seeded.** Primary metric = scan rate. Decision rule set before sending:
  3+ real conversations → scale to 250 + made-to-order quote · 0 responses but
  decent scans → fix copy/landing · 0 responses, ~0 scans → list/channel
  problem, stop. List quality beats copy quality.

## 7. Open before batch 1

1. Pensaki: reverse-charge invoicing against the CVR number?
2. Pensaki: real DE→DK transit (measure via seed).
3. Pensaki: API v4 docs / auth / callbacks — until then CSV import.
4. Pensaki: can the robot plot a vector QR? Don't plan around a yes.
5. Legal: opt-out on the landing page instead of in the letter — acceptable?
6. Provision the Robinson list on the worker, run `leadmachine screen`, then
   set `MAIL_ROBINSON_PROVISIONED=1` — otherwise no sole traders are mailed.
7. Point `sonorous.dk` at the app (or set `NEXT_PUBLIC_MAIL_PUBLIC_BASE`).
8. Set the landing CTA env vars + `MAIL_SEED_*` + `MAIL_SCAN_WEBHOOK_URL`.
9. Order Pensaki (and RoboQuill) samples first — see the handwriting.

## 8. Do first (operator checklist)

1. Env vars above on Vercel; redeploy.
2. Breve → Find modtagere → arm C, one branche, pick 25 → Sæt i kø.
3. Queue: ✨ Foreslå observation → read it against their site → edit → Godkend.
4. Klar til batch → Opret batch (seed ✓) → Batches → ⬇ CSV → upload at
   Pensaki → pay → "Markér som bestilt" with the order ID.
5. When their email arrives: "Overdraget til Deutsche Post". When your seed
   lands: "Seed-brev er landet i dag" (transit shows on the batch).
6. Watch Scanninger; follow-up calls surface via `lead_followups` at +12 d.
