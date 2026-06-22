# Worker

Python jobs for Lead Machine: CVR discovery, website qualification (Scrapling /
DNS / TLS / PageSpeed), financial enrichment (XBRL), scoring, and Danish AI
angles. Connects to Supabase with the **service-role key** (bypasses RLS).

## Dev

```bash
uv sync                      # install deps (+ dev group)
cp .env.example .env         # fill in SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY
uv run leadmachine hello     # smoke test
uv run leadmachine health    # checks Supabase connectivity (needs env)
uv run pytest -q
uv run ruff check .
```

## Layout

- `src/leadmachine/config.py` — settings from env (pydantic-settings).
- `src/leadmachine/db.py` — Supabase client (service role).
- `src/leadmachine/cli.py` — Typer entrypoint (`leadmachine`).
- `src/leadmachine/cvr/` — CVR discovery client interface (M1, issue #14).
