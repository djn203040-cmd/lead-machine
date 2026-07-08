-- ---------------------------------------------------------------------------
-- 0006_angle_cta_objections
-- Sales angle v2: the cold call now books a viewing of an already-built demo.
-- Add the booking ask (cta_da) and tailored objection rebuttals (objections).
-- ---------------------------------------------------------------------------
alter table lead_angles
  add column if not exists cta_da     text,
  add column if not exists objections jsonb not null default '[]'::jsonb;

comment on column lead_angles.cta_da is
  'Spoken booking ask — the assumptive CTA to schedule a short demo-viewing call.';
comment on column lead_angles.objections is
  'Array of {objection_da, response_da} — the 2–3 most likely cold-call objections for this lead.';
