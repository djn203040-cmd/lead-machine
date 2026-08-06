# Architecture

Full detail in [`../PLAN.md`](../PLAN.md). Summary:

```
CVR discovery ─► leads (dedup by CVR#) ─► website qualification ─► firmographic +
(branchekode +                            (Scrapling + DNS/TLS +     financial enrichment
 kommune/postnr +                          PageSpeed) = digital       (CVR + XBRL)
 employee band)                            maturity signal                 │
                                                                           ▼
                                                        realistic savings estimate (DKK)
                                                        (~10% of revenue, sector-adjusted,
                                                         capped by gross profit) — our fee
                                                         is 20% of it
                                                                                │
                                                                                ▼
                                                            scoring 0–100 ─► dashboard
                                                                                │
                                                                                ▼
                                                            Danish AI angles ─► pitch-ready
```

- **`apps/web`** — Next.js dashboard (Supabase Auth + Postgres + RLS).
- **`services/worker`** — Python jobs: discovery (CVR), qualification
  (Scrapling/DNS/TLS/PageSpeed), enrichment (CVR/XBRL), savings estimation,
  scoring, angles.
- **`supabase/`** — schema + RLS; the worker writes via the service-role key,
  the web app reads/writes via the user session.
- **Queue** — the `jobs` table; the worker polls it (kept simple for V1).
