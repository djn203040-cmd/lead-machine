-- Call stats for the dialer counter + /leads/stats.
--
-- lead_calls already logs every dial attempt (incl. "no answer") with a
-- timestamp; this view just buckets them into Danish calendar days so the web
-- app never has to reason about timezones. security_invoker so the caller's
-- RLS on lead_calls applies (authenticated full access, anon nothing).

create or replace view call_stats_daily
with (security_invoker = true) as
select
  (called_at at time zone 'Europe/Copenhagen')::date as day,
  count(*)::int                                          as calls,
  (count(*) filter (where outcome = 'no_answer'))::int      as no_answer,
  (count(*) filter (where outcome = 'contacted'))::int      as contacted,
  (count(*) filter (where outcome = 'meeting_booked'))::int as meetings,
  (count(*) filter (where outcome = 'lost'))::int           as lost,
  (count(*) filter (where outcome = 'discarded'))::int      as discarded
from lead_calls
group by 1;
