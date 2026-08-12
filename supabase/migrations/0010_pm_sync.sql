-- 0010_pm_sync.sql
--
-- Dialer outcomes sync into Sonorous OS (the self-built PM system, separate
-- Supabase project — its CRM "Leads" module). A booked meeting creates a PM
-- lead; pm_lead_id links the two so later outcomes (contacted / lost /
-- discarded→archived) update that PM lead instead of duplicating it.

alter table public.leads
  add column if not exists pm_lead_id uuid,
  add column if not exists pm_synced_at timestamptz;

comment on column public.leads.pm_lead_id is
  'id of the linked lead in the Sonorous OS PM system (separate Supabase project)';
