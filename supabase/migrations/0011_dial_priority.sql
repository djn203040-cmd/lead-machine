-- 0011_dial_priority.sql
--
-- Lets a batch of leads jump the power-dialer queue. The dialer sorts by
-- dial_priority desc, then score desc — so a fresh discovery batch can be put
-- at the front (priority 1) without touching its score, and demoted back to 0
-- once it has been worked. Default 0 = ordinary score order.

alter table public.leads
  add column if not exists dial_priority smallint not null default 0;

comment on column public.leads.dial_priority is
  'Power-dialer queue boost: higher first, then score desc. 0 = normal.';

create index if not exists leads_dial_priority_score_idx
  on public.leads (dial_priority desc, score desc nulls last)
  where is_archived = false and suppressed = false;
