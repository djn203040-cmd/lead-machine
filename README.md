# Lead Machine

A lead generation → qualification → enrichment engine for a Danish web-design
agency selling **$1–2k websites**. It finds Danish local businesses, qualifies
them by **website-readiness** (no / dead / parked / Facebook-only / bad site =
best lead), enriches them with firmographics + financials, scores them 0–100,
and surfaces pitch-ready leads with Danish AI sales angles.

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

V1 in progress — milestone **M0 (foundation)**. Tracking issues:
[milestones & backlog](https://github.com/djn203040-cmd/lead-machine/issues).
