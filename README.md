# Lead Machine

A lead generation → qualification → enrichment engine for a Danish operations
partner selling **time and money back on commission**: we follow a business,
build the systems that remove its manual work, and take **20% of what we
actually save it**. The engine finds Danish local businesses, enriches them with
firmographics + financials, estimates the **realistic annual saving in DKK**
(~10% of revenue, sector-adjusted and capped by gross profit), scores them
0–100 on the size of that prize, and surfaces pitch-ready leads with Danish AI
sales angles. Website signals survive only as a read on digital maturity.

See **[`PLAN.md`](./PLAN.md)** for the full plan and
**[`RESEARCH-lead-qualification-2026.md`](./RESEARCH-lead-qualification-2026.md)**
for the research behind it.

## Monorepo layout

| Path | Tech | Role |
|---|---|---|
| `apps/web` | Next.js 15 (App Router, TS) + Tailwind | Dashboard on Supabase (Auth + Postgres + RLS) |
| `services/worker` | Python 3.11 (uv) | Discovery + enrichment + scoring jobs |
| `supabase/` | SQL migrations | Schema + RLS policies |
| `docs/` | Markdown | Architecture & runbooks |

## Prerequisites

- Node ≥ 22.19 + pnpm (via `corepack enable`)
- Python ≥ 3.11 + [uv](https://docs.astral.sh/uv/)
- A Supabase project (see `supabase/README.md`)

## Quick start

```bash
# Web
corepack enable
pnpm install
cp apps/web/.env.local.example apps/web/.env.local   # fill in Supabase URL + anon key
pnpm --filter web dev                                 # http://localhost:3000

# Worker
cd services/worker
cp .env.example .env                                  # fill in Supabase service-role key
uv sync
uv run leadmachine hello                              # smoke test
```

## Status

V1 in progress — **M0 (foundation) complete; next: M1 (CVR discovery)**.
Resume point & state: [`docs/SESSION-LOG.md`](./docs/SESSION-LOG.md) ·
[milestones & backlog](https://github.com/djn203040-cmd/lead-machine/issues).
