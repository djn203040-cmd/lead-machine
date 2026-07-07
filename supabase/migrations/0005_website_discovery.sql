-- M2 follow-up: website discovery + quality grading.
--
-- The CVR `hjemmeside` field is empty for most Danish SMBs, so a lead with no
-- registered site was wrongly qualified `website_need='none'` (a hot lead) even
-- when a real site existed. The worker now *discovers* a site (email domain →
-- name guess → Brave search, with ownership verification) before concluding
-- "none", and grades every live site's quality with a cheap LLM pass.
--
-- Provenance + the LLM tier are surfaced as first-class columns so the UI can
-- show "how we found this" and "how good is it" without digging into the
-- lead_enrichment.website jsonb.

alter table leads
  add column if not exists website_source  text,   -- cvr | email_domain | name_guess | search
  add column if not exists discovered_url  text,    -- the verified URL, when found by discovery
  add column if not exists website_quality text;     -- LLM grade of a live site

alter table leads drop constraint if exists leads_website_quality_check;
alter table leads
  add constraint leads_website_quality_check
  check (website_quality is null or website_quality in
    ('dated','basic','modern','premium'));

alter table leads drop constraint if exists leads_website_source_check;
alter table leads
  add constraint leads_website_source_check
  check (website_source is null or website_source in
    ('cvr','email_domain','name_guess','search'));

create index if not exists leads_website_quality_idx on leads(website_quality);
