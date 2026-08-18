-- 0012_direct_mail.sql — Handwritten direct-mail arm (Pensaki)
--
-- Robot-handwritten letters to decision makers, triggered by call outcomes
-- (arm A = no answer, arm B = spoke/not interested) or picked cold (arm C).
-- Letters are queued per lead, human-reviewed (the observation line), batched
-- (Pensaki MOQ is 10), exported/ordered, and tracked through a per-recipient
-- short URL (sonorous.dk/<slug>) whose hits are the only feedback channel.
--
-- Three legal filters are enforced at enqueue time (see lib/mail/eligibility.ts)
-- and the reject reason is kept on the row so attrition can be measured.

-- ---------------------------------------------------------------------------
-- lead_calls: every dial attempt, incl. "no answer" (which never moved
-- pipeline_status before). Arm A hangs off this.
-- ---------------------------------------------------------------------------
create table if not exists lead_calls (
  id         uuid primary key default gen_random_uuid(),
  lead_id    uuid not null references leads(id) on delete cascade,
  user_id    uuid references auth.users(id),
  outcome    text not null check (outcome in
             ('no_answer','contacted','meeting_booked','lost','discarded')),
  called_at  timestamptz not null default timezone('utc', now())
);
create index if not exists lead_calls_lead_id_idx on lead_calls(lead_id, called_at desc);

-- ---------------------------------------------------------------------------
-- mail_batches: one Pensaki order. Open → ordered → sent (handed to Deutsche
-- Post) → done. Seed = our own address included to measure DE→DK transit.
-- ---------------------------------------------------------------------------
create table if not exists mail_batches (
  id               uuid primary key default gen_random_uuid(),
  name             text not null,
  status           text not null default 'open'
                   check (status in ('open','ordered','sent','done','cancelled')),
  vendor           text not null default 'pensaki',
  vendor_order_id  text,
  ordered_at       timestamptz,
  sent_at          timestamptz,             -- handed to Deutsche Post (vendor email)
  seed_included    boolean not null default false,
  seed_received_at timestamptz,             -- when our seed letter hit our mailbox
  followup_offset_days integer not null default 12,
  notes            text,
  created_by       uuid references auth.users(id),
  created_at       timestamptz not null default timezone('utc', now()),
  updated_at       timestamptz not null default timezone('utc', now())
);
create trigger trg_mail_batches_updated before update on mail_batches
  for each row execute function set_updated_at();

-- ---------------------------------------------------------------------------
-- lead_mail: one letter to one lead. Status ladder:
--   rejected  — failed a legal/data filter at enqueue (reason kept)
--   draft     — queued, observation not yet approved by a human
--   approved  — observation approved, waiting for a batch
--   batched   — assigned to an open batch
--   ordered   — batch ordered at the vendor
--   sent      — vendor handed it to Deutsche Post
--   cancelled — pulled before ordering
-- Scans live in mail_scans; first_scanned_at/scan_count are denormalised here.
-- ---------------------------------------------------------------------------
create table if not exists lead_mail (
  id             uuid primary key default gen_random_uuid(),
  lead_id        uuid not null references leads(id) on delete cascade,
  batch_id       uuid references mail_batches(id) on delete set null,
  arm            text not null check (arm in ('A','B','C')),
  status         text not null default 'draft'
                 check (status in
                   ('rejected','draft','approved','batched','ordered','sent','cancelled')),
  -- unique, memorable slug — the handwritten URL: sonorous.dk/<slug>
  slug           text not null unique,
  -- recipient block (snapshotted at enqueue; editable before ordering)
  recipient_name text,
  first_name     text,
  company_name   text not null,
  address_line   text,
  postal_code    text,
  city           text,
  country        text not null default 'Danmark',
  -- copy
  observation_text text,                     -- "[konkret observation]"
  focus_text       text,                     -- "[X]" — what we looked at
  observation_approved_by uuid references auth.users(id),
  observation_approved_at timestamptz,
  letter_text    text,                       -- rendered letter, frozen at approval
  letter_chars   integer,
  -- filters
  reject_reason  text check (reject_reason in
                   ('reklamebeskyttelse','robinson','robinson_unscreened',
                    'adressebeskyttelse','no_address','suppressed','duplicate','archived')),
  -- landing page
  landing_video_url text,
  landing_headline  text,
  -- telemetry
  first_scanned_at timestamptz,
  last_scanned_at  timestamptz,
  scan_count       integer not null default 0,
  opted_out_at     timestamptz,
  followup_id      uuid references lead_followups(id) on delete set null,
  is_seed          boolean not null default false,
  created_by       uuid references auth.users(id),
  created_at       timestamptz not null default timezone('utc', now()),
  updated_at       timestamptz not null default timezone('utc', now())
);
create index if not exists lead_mail_lead_id_idx on lead_mail(lead_id);
create index if not exists lead_mail_status_idx  on lead_mail(status);
create index if not exists lead_mail_batch_id_idx on lead_mail(batch_id);
-- One live letter per lead at a time (rejected/cancelled don't block a retry).
create unique index if not exists lead_mail_one_active_per_lead
  on lead_mail(lead_id) where status not in ('rejected','cancelled');
create trigger trg_lead_mail_updated before update on lead_mail
  for each row execute function set_updated_at();

comment on column lead_mail.slug is 'Handwritten short URL path: <MAIL_PUBLIC_BASE>/<slug>';

-- ---------------------------------------------------------------------------
-- mail_scans: every hit on the redirect. The primary metric of the channel.
-- ---------------------------------------------------------------------------
create table if not exists mail_scans (
  id          uuid primary key default gen_random_uuid(),
  mail_id     uuid not null references lead_mail(id) on delete cascade,
  slug        text not null,
  scanned_at  timestamptz not null default timezone('utc', now()),
  user_agent  text,
  device      text,                          -- mobile / desktop / bot / unknown
  referrer    text,
  ip_hash     text
);
create index if not exists mail_scans_mail_id_idx on mail_scans(mail_id, scanned_at desc);

-- ---------------------------------------------------------------------------
-- RLS — same model as the rest: authenticated full access.
-- ---------------------------------------------------------------------------
alter table lead_calls   enable row level security;
alter table mail_batches enable row level security;
alter table lead_mail    enable row level security;
alter table mail_scans   enable row level security;

do $$
declare t text;
begin
  foreach t in array array['lead_calls','mail_batches','lead_mail','mail_scans'] loop
    execute format(
      'create policy "authenticated full access" on %I for all to authenticated using (true) with check (true);',
      t
    );
  end loop;
end$$;

-- ---------------------------------------------------------------------------
-- Public entry points (anon) — the redirect + landing page + opt-out run
-- without a session. SECURITY DEFINER functions expose exactly what the
-- landing page needs and nothing else; anon never reads the tables directly.
-- ---------------------------------------------------------------------------

-- Log a hit and return the landing payload. Bots are logged but not counted.
create or replace function mail_track_scan(
  p_slug text, p_user_agent text default null, p_referrer text default null, p_ip_hash text default null
) returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  m lead_mail%rowtype;
  v_device text;
  v_ua text := coalesce(p_user_agent, '');
begin
  select * into m from lead_mail where slug = lower(p_slug) limit 1;
  if not found then return null; end if;

  v_device := case
    when v_ua ~* '(bot|crawl|spider|preview|facebookexternalhit|slackbot|whatsapp|telegram|curl|wget)' then 'bot'
    when v_ua ~* '(iphone|android|mobile|ipad)' then 'mobile'
    when v_ua = '' then 'unknown'
    else 'desktop' end;

  insert into mail_scans (mail_id, slug, user_agent, device, referrer, ip_hash)
  values (m.id, m.slug, nullif(v_ua, ''), v_device, p_referrer, p_ip_hash);

  if v_device <> 'bot' then
    update lead_mail
       set scan_count = scan_count + 1,
           first_scanned_at = coalesce(first_scanned_at, timezone('utc', now())),
           last_scanned_at = timezone('utc', now())
     where id = m.id;
  end if;

  return jsonb_build_object(
    'slug', m.slug,
    'company_name', m.company_name,
    'first_name', m.first_name,
    'arm', m.arm,
    'landing_video_url', m.landing_video_url,
    'landing_headline', m.landing_headline,
    'is_first_scan', (m.first_scanned_at is null and v_device <> 'bot'),
    'device', v_device
  );
end;
$$;

-- Read-only landing payload (no logging) — the landing page render.
create or replace function mail_landing(p_slug text) returns jsonb
language sql security definer set search_path = public stable
as $$
  select jsonb_build_object(
    'slug', slug,
    'company_name', company_name,
    'first_name', first_name,
    'arm', arm,
    'landing_video_url', landing_video_url,
    'landing_headline', landing_headline,
    'observation_text', observation_text,
    'focus_text', focus_text,
    'opted_out', opted_out_at is not null,
    'branchekode', (select branchekode from leads l where l.id = lead_mail.lead_id)
  )
  from lead_mail where slug = lower(p_slug) limit 1;
$$;

-- Opt-out (MFL: recipient must be able to decline further advertising).
-- Suppresses the lead for every outreach surface.
create or replace function mail_opt_out(p_slug text) returns boolean
language plpgsql security definer set search_path = public
as $$
declare v_lead uuid;
begin
  update lead_mail set opted_out_at = coalesce(opted_out_at, timezone('utc', now()))
   where slug = lower(p_slug) returning lead_id into v_lead;
  if v_lead is null then return false; end if;
  update leads set suppressed = true,
                   suppression_reason = coalesce(suppression_reason, 'mail_optout')
   where id = v_lead;
  return true;
end;
$$;

revoke all on function mail_track_scan(text,text,text,text) from public;
revoke all on function mail_landing(text) from public;
revoke all on function mail_opt_out(text) from public;
grant execute on function mail_track_scan(text,text,text,text) to anon, authenticated;
grant execute on function mail_landing(text) to anon, authenticated;
grant execute on function mail_opt_out(text) to anon, authenticated;
