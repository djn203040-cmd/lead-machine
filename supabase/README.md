# Supabase

Schema + RLS for Lead Machine. The durable lead spine lives here (Postgres),
keyed by **CVR number**.

## Files

- `migrations/0001_init.sql` — schema + RLS policies (see `PLAN.md` §3).
- `seed.sql` — `scoring_criteria` seeded for the website-selling offer.
- `config.toml` — Supabase CLI config.

## Applying the schema

Once the project is provisioned (issue #11):

```bash
# Option A — Supabase CLI
supabase link --project-ref <ref>
supabase db push          # applies migrations
psql "$DATABASE_URL" -f seed.sql

# Option B — via the Supabase MCP / SQL editor
# run migrations/0001_init.sql then seed.sql
```

After the schema is live, regenerate TypeScript types for the web app:

```bash
supabase gen types typescript --project-id <ref> > ../apps/web/lib/database.types.ts
```

## RLS model

Internal team tool: every table has RLS **enabled** with a single
`authenticated full access` policy. The worker uses the **service-role key**
(bypasses RLS); the web app uses the **anon key** + user session.
