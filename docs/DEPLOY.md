# Deploy & run V1 (runbook)

Three pieces ship V1:

| Piece | What | Where | Why there |
|---|---|---|---|
| **`apps/web`** | Next.js 15 dashboard (read/qualify leads) | **Vercel** | Serverless-friendly; SSR + Supabase auth. |
| **Database** | Postgres + RLS + auth | **Supabase** (`dxkxamlwucknndcqqtrj`, eu-north-1) | Already provisioned. |
| **`services/worker`** | Python CLI pipeline (discover → qualify → enrich → score → angles → screen) | **Fly.io / Railway** (a real box, not serverless) | Scrapling's browser fallback + long-running jobs don't fit serverless. |

Keep everything in the **EU** (Supabase eu-north-1, Vercel `arn1`, Fly `arn`) —
the data includes Danish personal data.

---

## 0. Pre-flight (compliance gate)

**Do not run live outreach until [`compliance/README.md`](./compliance/README.md)'s
go-live checklist is done** — in particular: publish the privacy notice,
provision the Robinson list, and run `leadmachine screen`.

## 1. Environment variable matrix

| Variable | web (Vercel) | worker (Fly) | Secret? | Notes |
|---|:--:|:--:|:--:|---|
| `NEXT_PUBLIC_SUPABASE_URL` | ✅ | — | no | `https://dxkxamlwucknndcqqtrj.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✅ | — | no | publishable key (`sb_publishable_…`) |
| `SUPABASE_URL` | — | ✅ | no | same project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | — | ✅ | **yes** | bypasses RLS — worker only, never in the web app |
| `CVR_ES_USER` / `CVR_ES_PASSWORD` | — | ✅ | **yes** | CVR system-to-system creds (free, via `cvrselvbetjening@erst.dk`) |
| `ANTHROPIC_API_KEY` | — | ✅ | **yes** | M6 Danish angles (`claude-opus-4-8`) |
| `PAGESPEED_API_KEY` | — | ✅ | no* | optional; PSI is skipped if unset |
| `ROBINSON_LIST_PATH` | — | ✅ | no | path to the licensed Robinson file on the host, e.g. `/data/robinson.txt` |

`*` not secret but treat as private. **Never** put `SUPABASE_SERVICE_ROLE_KEY`
in the web app — the browser must only see the anon key.

## 2. Supabase (already live)

Apply pending migrations to the project (M7 adds `0002_compliance.sql`):

```bash
supabase link --project-ref dxkxamlwucknndcqqtrj
supabase db push        # applies supabase/migrations/*.sql
```

After any schema change, regenerate the web types:

```bash
supabase gen types typescript --project-id dxkxamlwucknndcqqtrj \
  > apps/web/lib/database.types.ts
```

## 3. Web → Vercel

1. Import the repo into Vercel; set **root directory** to `apps/web` (the
   `vercel.json` there builds from the monorepo root with pnpm).
2. Set `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` (Production +
   Preview).
3. In Supabase → Auth → URL config, add the Vercel domain to the allowed
   redirect URLs so login works.
4. Deploy. Smoke test: visit `/` → redirected to `/login` → sign in → `/leads`.

## 4. Worker → Fly.io

```bash
cd services/worker
fly launch --no-deploy            # uses fly.toml; pick the EU region (arn)
fly volumes create lm_data --size 1 --region arn
fly secrets set \
  SUPABASE_URL=https://dxkxamlwucknndcqqtrj.supabase.co \
  SUPABASE_SERVICE_ROLE_KEY=… CVR_ES_USER=… CVR_ES_PASSWORD=… \
  ANTHROPIC_API_KEY=… PAGESPEED_API_KEY=… ROBINSON_LIST_PATH=/data/robinson.txt
fly deploy
# put the Robinson file on the volume (licensed data — not in git):
fly ssh sftp shell           # then: put robinson.txt /data/robinson.txt
fly ssh console -C "leadmachine health"   # smoke test DB connectivity
```

(Railway is equivalent: deploy the same Dockerfile, set the vars, attach a
volume for the Robinson file.)

## 5. End-to-end run (one category × one city)

Run from the worker host (the sandbox blocks outbound to CVR/Virk/web):

```bash
# 1. discover  (e.g. frisører in 2200 København N)
fly ssh console -C "leadmachine discover -b 960210 -p 2200"
# 2. compliance screen BEFORE any outreach
fly ssh console -C "leadmachine screen"
# 3. qualify websites
fly ssh console -C "leadmachine qualify"
# 4. enrich financials + CVR contacts
fly ssh console -C "leadmachine enrich-financial"
# 5. score
fly ssh console -C "leadmachine score"
# 6. Danish phone angles
fly ssh console -C "leadmachine angles"
```

Then open `/leads` in the dashboard — ranked, suppressed leads hidden, each with
an explainable score and a phone-first angle. That run is the **M1–M6 acceptance
pass**; close #2/#3/#4/#5/#6/#7 once confirmed on real data.

## 6. Scheduling

Each command is idempotent (CVR# dedup; `--only-*` flags skip done work), so a
nightly chain is safe. Options:

- **Fly Machines schedule** — a scheduled machine that runs the chain, or
  `fly machine exec` from a cron.
- **GitHub Actions cron** — a scheduled workflow that `fly ssh console -C`'s each
  step (store Fly + Supabase tokens as repo secrets).

Keep `screen` **before** any step that feeds outreach.

## 7. Observability & runbook

- **Run log:** every CLI run writes a row to the **`jobs`** table — `type`,
  `status` (`running`→`done`/`failed`), `result` (the run stats), `error`,
  `started_at`/`finished_at`. Check recent runs:

  ```sql
  select type, status, result, error, started_at, finished_at
  from jobs order by created_at desc limit 20;
  ```

- **Search status:** a `--search-id` discovery flips `searches.status`
  (`running`→`completed`) and stores `stats`.
- **Health:** `leadmachine health` checks Supabase connectivity.
- **Supabase advisors:** run the security/perf advisors after schema changes.

### Common failures
| Symptom | Likely cause | Fix |
|---|---|---|
| `discover` 401 | bad/missing `CVR_ES_*` | re-set Fly secrets; confirm creds active |
| `enrich-financial` 403 to virk.dk | host blocked / rate-limited | retry; confirm host has open outbound |
| `angles` auth error | missing `ANTHROPIC_API_KEY` | set the secret |
| `screen` warns "list empty" | `ROBINSON_LIST_PATH` unset/missing | put the file on the volume; **don't** start outreach until fixed |
| web shows no leads | RLS / wrong keys / all suppressed | check anon key + that a pipeline run populated `leads` |
| job stuck `running` in `jobs` | process died mid-run | safe to re-run (idempotent); investigate the host |
