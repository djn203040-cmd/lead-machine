-- ===========================================================================
-- 0002_compliance.sql — M7: Robinson-list suppression + worker run logging
-- ===========================================================================
-- Discovery already drops `reklamebeskyttelse` + inactive entities (they never
-- enter `leads`). Robinson-list screening is different: it runs *after* leads
-- exist, because it matches the natural person behind a sole trader
-- (enkeltmandsvirksomhed / PMV) by name + address. A matched lead must never be
-- contacted, so we flag it here and exclude it from every outreach surface.

alter table leads
  add column if not exists suppressed           boolean      not null default false,
  add column if not exists suppression_reason    text,
  add column if not exists robinson_screened_at  timestamptz;

-- The default leads list filters on `suppressed = false`; index that path.
create index if not exists leads_suppressed_idx on leads(suppressed);

-- Allow the screening job to be logged in the worker queue.
alter table jobs drop constraint if exists jobs_type_check;
alter table jobs add constraint jobs_type_check check (type in
  ('discover','enrich_cvr','qualify_website','enrich_financial','score','angle','robinson'));
