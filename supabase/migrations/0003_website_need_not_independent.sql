-- M2 follow-up: add the `not_independent` website-need tier.
-- A live site that lives on a shared "group" platform (a sub-page, not the
-- business's own domain) is a hot lead — they have no independent web presence.

alter table leads drop constraint if exists leads_website_need_check;

alter table leads
  add constraint leads_website_need_check
  check (website_need in
    ('unknown','none','dead','parked','facebook_only','not_independent','bad','outdated','modern'));
