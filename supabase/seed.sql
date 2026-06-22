-- Seed scoring criteria, tuned for selling WEBSITES (not ads/video).
-- Website-need signals carry the most weight; the old leadforge logic is inverted.

insert into scoring_criteria (key, label_da, weight) values
  ('no_website',            'Ingen hjemmeside',                      'high'),
  ('dead_or_parked',        'Dødt/parkeret domæne',                  'high'),
  ('facebook_only',         'Kun Facebook-side, ingen hjemmeside',   'high'),
  ('bad_website',           'Dårlig/forældet hjemmeside',            'high'),
  ('not_mobile_friendly',   'Ikke mobilvenlig (manglende viewport)', 'medium'),
  ('no_https',              'Ingen HTTPS/SSL',                       'medium'),
  ('low_pagespeed',         'Lav PageSpeed-score (mobil)',           'medium'),
  ('employees_target',      'Antal medarbejdere 2–20',               'medium'),
  ('has_gross_profit',      'Positiv bruttofortjeneste (budget)',    'medium'),
  ('cares_online_presence', 'Aktiv online (FB-side/pixel/socials)',  'low'),
  ('recently_founded',      'Stiftet inden for 3 år',                'low')
on conflict (key) do nothing;
