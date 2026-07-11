-- Phone-first qualifier: a lead with no phone number is disqualified.
--
-- Outreach is phone-first, so a lead we can't call is worthless. Enrichment now
-- hunts for a number (CVR → production unit → website scrape) and scoring hard-
-- gates a lead that still has none (gate_reason 'no_phone', score 0). The UI
-- hides these from the working list + dialer.
--
-- `has_phone` is a generated column so the list/dialer can filter server-side
-- (Postgres can't cheaply filter on text[] emptiness otherwise).

alter table leads
  add column if not exists has_phone boolean
  generated always as (coalesce(array_length(phone, 1), 0) > 0) stored;

create index if not exists leads_has_phone_idx on leads(has_phone);

-- New job type for the standalone phone-recovery command.
alter table jobs drop constraint if exists jobs_type_check;
alter table jobs add constraint jobs_type_check check (type in
  ('discover','enrich_cvr','qualify_website','enrich_financial','score','angle',
   'robinson','enrich_queued','find_phones'));
