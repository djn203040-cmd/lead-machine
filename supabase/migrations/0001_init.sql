-- 0001_init.sql — Lead Machine V1 schema + RLS
--
-- Internal team tool: any authenticated user has full access. The Python
-- worker connects with the service-role key, which bypasses RLS.
-- (Unlike the legacy Outreach Tracker project, RLS is ON from day one.)

create extension if not exists "pgcrypto";

-- shared updated_at trigger
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- searches: a saved discovery definition (filters live in parameters jsonb)
-- ---------------------------------------------------------------------------
create table searches (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  type        text not null default 'cvr' check (type in ('cvr')),
  parameters  jsonb not null default '{}'::jsonb,
  status      text not null default 'pending'
              check (status in ('pending','running','completed','failed')),
  stats       jsonb not null default '{}'::jsonb,
  is_archived boolean not null default false,
  created_by  uuid references auth.users(id),
  created_at  timestamptz not null default timezone('utc', now()),
  updated_at  timestamptz not null default timezone('utc', now())
);

-- ---------------------------------------------------------------------------
-- leads: one row per company. CVR number is the canonical dedup key.
-- ---------------------------------------------------------------------------
create table leads (
  id              uuid primary key default gen_random_uuid(),
  search_id       uuid references searches(id) on delete set null,
  cvr_number      text unique,
  company_name    text not null,
  address         text,
  postal_code     text,
  city            text,
  kommune         text,
  phone           text[] not null default '{}',
  email           text,
  website         text,
  branchekode     text,
  branche_text    text,
  company_form    text,
  cvr_status      text,
  employees_band  text,
  employees_exact integer,
  founded_at      date,
  website_need    text not null default 'unknown'
                  check (website_need in
                    ('unknown','none','dead','parked','facebook_only','bad','outdated','modern')),
  score           integer check (score >= 0 and score <= 100),
  pipeline_status text not null default 'new'
                  check (pipeline_status in
                    ('new','enriched','qualified','contacted','meeting_booked','won','lost','discarded')),
  reklamebeskyttet boolean not null default false,
  is_sole_trader   boolean not null default false,
  assigned_to      uuid references auth.users(id),
  is_archived      boolean not null default false,
  created_at       timestamptz not null default timezone('utc', now()),
  updated_at       timestamptz not null default timezone('utc', now())
);
create index leads_search_id_idx       on leads(search_id);
create index leads_score_idx           on leads(score desc nulls last);
create index leads_website_need_idx    on leads(website_need);
create index leads_pipeline_status_idx on leads(pipeline_status);

-- ---------------------------------------------------------------------------
-- lead_enrichment: raw payloads per source (1:1 with leads)
-- ---------------------------------------------------------------------------
create table lead_enrichment (
  lead_id          uuid primary key references leads(id) on delete cascade,
  cvr              jsonb not null default '{}'::jsonb,
  website          jsonb not null default '{}'::jsonb,
  financial        jsonb not null default '{}'::jsonb,
  social           jsonb not null default '{}'::jsonb,
  contact          jsonb not null default '{}'::jsonb,
  last_enriched_at timestamptz
);

-- ---------------------------------------------------------------------------
-- lead_scores: explainable per-factor breakdown (1:1 with leads)
-- ---------------------------------------------------------------------------
create table lead_scores (
  lead_id   uuid primary key references leads(id) on delete cascade,
  total     integer not null check (total >= 0 and total <= 100),
  breakdown jsonb not null default '{}'::jsonb,
  scored_at timestamptz not null default timezone('utc', now())
);

-- ---------------------------------------------------------------------------
-- scoring_criteria: configurable weights (seeded for the website offer)
-- ---------------------------------------------------------------------------
create table scoring_criteria (
  id         uuid primary key default gen_random_uuid(),
  key        text unique not null,
  label_da   text not null,
  weight     text not null check (weight in ('low','medium','high')),
  config     jsonb,
  is_active  boolean not null default true,
  updated_at timestamptz not null default timezone('utc', now())
);

-- ---------------------------------------------------------------------------
-- lead_angles: AI-generated Danish sales angles (1:1 with leads)
-- ---------------------------------------------------------------------------
create table lead_angles (
  lead_id               uuid primary key references leads(id) on delete cascade,
  summary_da            text,
  weaknesses_da         text,
  angle_da              text,
  opening_line_da       text,
  competitor_name       text,
  competitor_angle_type text check (competitor_angle_type in ('fomo','first_mover','none')),
  generated_at          timestamptz not null default timezone('utc', now())
);

-- ---------------------------------------------------------------------------
-- lead_notes / lead_followups: lightweight CRM
-- ---------------------------------------------------------------------------
create table lead_notes (
  id         uuid primary key default gen_random_uuid(),
  lead_id    uuid not null references leads(id) on delete cascade,
  user_id    uuid references auth.users(id),
  body       text not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);
create index lead_notes_lead_id_idx on lead_notes(lead_id);

create table lead_followups (
  id             uuid primary key default gen_random_uuid(),
  lead_id        uuid not null references leads(id) on delete cascade,
  user_id        uuid references auth.users(id),
  follow_up_date timestamptz not null,
  reminder_sent  boolean not null default false,
  created_at     timestamptz not null default timezone('utc', now())
);
create index lead_followups_lead_id_idx on lead_followups(lead_id);

-- ---------------------------------------------------------------------------
-- jobs: the worker queue (discover / enrich / qualify / score / angle)
-- ---------------------------------------------------------------------------
create table jobs (
  id          uuid primary key default gen_random_uuid(),
  type        text not null check (type in
              ('discover','enrich_cvr','qualify_website','enrich_financial','score','angle')),
  search_id   uuid references searches(id) on delete cascade,
  lead_id     uuid references leads(id) on delete cascade,
  status      text not null default 'queued'
              check (status in ('queued','running','done','failed')),
  payload     jsonb not null default '{}'::jsonb,
  result      jsonb,
  error       text,
  attempts    integer not null default 0,
  created_at  timestamptz not null default timezone('utc', now()),
  started_at  timestamptz,
  finished_at timestamptz
);
create index jobs_status_idx on jobs(status);
create index jobs_type_idx   on jobs(type);

-- updated_at triggers
create trigger trg_searches_updated   before update on searches   for each row execute function set_updated_at();
create trigger trg_leads_updated      before update on leads      for each row execute function set_updated_at();
create trigger trg_lead_notes_updated before update on lead_notes for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS: enable on every table; authenticated users get full access.
-- ---------------------------------------------------------------------------
alter table searches         enable row level security;
alter table leads            enable row level security;
alter table lead_enrichment  enable row level security;
alter table lead_scores      enable row level security;
alter table scoring_criteria enable row level security;
alter table lead_angles      enable row level security;
alter table lead_notes       enable row level security;
alter table lead_followups   enable row level security;
alter table jobs             enable row level security;

do $$
declare t text;
begin
  foreach t in array array[
    'searches','leads','lead_enrichment','lead_scores','scoring_criteria',
    'lead_angles','lead_notes','lead_followups','jobs'
  ] loop
    execute format(
      'create policy "authenticated full access" on %I for all to authenticated using (true) with check (true);',
      t
    );
  end loop;
end$$;
