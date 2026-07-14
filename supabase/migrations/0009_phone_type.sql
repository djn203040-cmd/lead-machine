-- Phone-type classification: who is likely to answer the call?
--
-- Danish numbers are assigned by range (Energistyrelsens nummerplan), so the
-- first digits reveal the service type:
--   mobile   (2x, 30-31, 40-42, 50-53, 60-61, 71, 81, 91-93) — a personal
--            handset; for a small business, near-always the owner directly.
--   landline (geographic ranges)                             — the shop's main
--            line; staff or reception may pick up (gatekeeper likely).
--   service  (70/80/90)                                      — non-geographic
--            corporate line / switchboard; never a person's own phone.
--
-- The dialer uses this to pick the call angle: a mobile gets the direct owner
-- pitch, a landline/service number gets the gatekeeper variant ("who'd be the
-- right person to talk to about this?"). Classification is a prefix heuristic
-- (DK allows cross-service porting, but ranges hold in practice) — a wrong
-- guess only softens the angle, it never hides a lead.
--
-- `phone_type` is a stored generated column (same pattern as has_phone in
-- 0008) so every write path — CVR discovery, find-phones recovery, manual
-- edits — classifies automatically, and existing rows backfill at ALTER time.
-- Mirrors classify_phone()/best_phone_type() in worker website/phones.py.

-- Classify one raw number. Mirrors normalize_phone(): strip non-digits and the
-- 0045/45 country prefix, require 8 digits starting 2-9.
create or replace function dk_phone_class(raw text)
returns text
language sql
immutable
as $$
  select case
    when d is null then null
    when left(d, 2) in ('70', '80', '90') then 'service'
    when left(d, 1) = '2'
      or left(d, 2) in ('30','31','40','41','42','50','51','52','53',
                        '60','61','71','81','91','92','93') then 'mobile'
    else 'landline'
  end
  from (
    select case
      when n ~ '^0045[2-9]\d{7}$' then substr(n, 5)
      when n ~ '^45[2-9]\d{7}$' then substr(n, 3)
      when n ~ '^[2-9]\d{7}$' then n
    end as d
    from (select regexp_replace(coalesce(raw, ''), '\D', '', 'g') as n) s
  ) t
$$;

-- Lead-level rollup: the most *personal* class across the lead's numbers — a
-- lead with any mobile is 'mobile' (that's the number to dial first).
create or replace function dk_phone_type(phones text[])
returns text
language sql
immutable
as $$
  select case
    when 'mobile' = any(classes) then 'mobile'
    when 'landline' = any(classes) then 'landline'
    when 'service' = any(classes) then 'service'
  end
  from (
    select array(select dk_phone_class(p) from unnest(coalesce(phones, '{}')) p) as classes
  ) t
$$;

alter table leads
  add column if not exists phone_type text
  generated always as (dk_phone_type(phone)) stored;

create index if not exists leads_phone_type_idx on leads(phone_type);
