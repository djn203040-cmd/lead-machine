-- Website discovery follow-up: production-unit (P-enhed) / trading-name source.
--
-- Some leads are an operating company (e.g. "Kakurega ApS") running a
-- differently-branded storefront ("Noribar"). The website lives under the brand
-- — registered on the production unit (produktionsenhed), a separate CVR object
-- keyed by pNummer — not on the company record. Discovery now fetches the
-- P-enhed to recover the trading name + its own site/contact, so these leads
-- stop being wrongly qualified `website_need='none'`.
--
-- Records the new provenance value `penhed` on `leads.website_source`.

alter table leads drop constraint if exists leads_website_source_check;
alter table leads
  add constraint leads_website_source_check
  check (website_source is null or website_source in
    ('cvr','email_domain','name_guess','penhed','search'));
