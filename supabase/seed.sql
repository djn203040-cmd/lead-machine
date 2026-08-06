-- Seed scoring criteria, tuned for the SAVINGS offer (20% of what we save them).
-- The size of the prize (savings) dominates; the website signal survives only as
-- a read on digital maturity. Keys map to Weights fields via
-- services/worker/src/leadmachine/scoring/rubric.py CRITERION_FIELD.

insert into scoring_criteria (key, label_da, weight) values
  ('savings_potential',      'Besparelsespotentiale 250k–1 mio. kr./år', 'high'),
  ('savings_unknown',        'Intet omsætningsestimat (ukendt prize)',   'medium'),
  ('industry_local_service', 'Manuel-tung lokal servicebranche',         'high'),
  ('digital_mature',         'Digitalt moden (moderne hjemmeside)',      'medium'),
  ('bad_website',            'Dårlig/forældet hjemmeside',               'medium'),
  ('facebook_only',          'Kun Facebook-side, ingen hjemmeside',      'medium'),
  ('not_independent',        'Side på fælles platform, ikke eget domæne','medium'),
  ('no_website',             'Ingen hjemmeside (lav digital modenhed)',  'low'),
  ('dead_or_parked',         'Dødt/parkeret domæne',                     'low'),
  ('runs_paid_ads',          'Kører annoncer (Meta Pixel)',              'medium'),
  ('cares_online_presence',  'Aktiv online (FB-side/socials)',           'low'),
  ('employees_target',       'Antal medarbejdere 10–49',                 'medium'),
  ('recently_founded',       'Stiftet inden for 3 år',                   'low')
on conflict (key) do nothing;
