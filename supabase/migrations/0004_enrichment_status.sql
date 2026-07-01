-- Enrichment gate: discovery now inserts raw leads that a user explicitly opts
-- in (or out) of enrichment. `enrichment_status` tracks that decision and the
-- worker's progress, and drives the "Beriget / Ikke beriget" split in the UI.
--
--   pending    discovered, awaiting the user's enrich? decision (default)
--   queued     user said yes — waiting for the worker to pick it up
--   enriching  worker is currently running the pipeline on it
--   enriched   qualify → financial → score → angles completed
--   skipped    user said no — kept, but not enriched
--   failed     worker errored on it (safe to re-queue)

alter table leads
  add column enrichment_status text not null default 'pending'
    check (enrichment_status in
      ('pending','queued','enriching','enriched','skipped','failed'));

create index leads_enrichment_status_idx on leads(enrichment_status);

-- Backfill: any lead that already has a score has been through the pipeline.
update leads set enrichment_status = 'enriched' where score is not null;

-- Log the new orchestrator run (qualify→financial→score→angles over the queue).
alter table jobs drop constraint if exists jobs_type_check;
alter table jobs add constraint jobs_type_check check (type in
  ('discover','enrich_cvr','qualify_website','enrich_financial','score','angle',
   'robinson','enrich_queued'));
