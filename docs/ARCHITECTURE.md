# Architecture

Full detail in [`../PLAN.md`](../PLAN.md). Summary:

```
CVR discovery ─► leads (dedup by CVR#) ─► website qualification ─► firmographic +
(branchekode +                            (Scrapling + DNS/TLS +     financial enrichment
 kommune/postnr +                          PageSpeed)                 (CVR + XBRL)
 employee band)                                                            │
                                                                           ▼
                                                            scoring 0–100 ─► dashboard
                                                                                │
                                                                                ▼
                                                            Danish AI angles ─► pitch-ready
```

- **`apps/web`** — Next.js dashboard (Supabase Auth + Postgres + RLS).
- **`services/worker`** — Python jobs: discovery (CVR), qualification
  (Scrapling/DNS/TLS/PageSpeed), enrichment (CVR/XBRL), scoring, angles.
- **`supabase/`** — schema + RLS; the worker writes via the service-role key,
  the web app reads/writes via the user session.
- **Queue** — the `jobs` table; the worker polls it (kept simple for V1).
