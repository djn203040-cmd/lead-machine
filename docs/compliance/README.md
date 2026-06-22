# Compliance (Denmark) — index

Lead Machine does targeted **B2B** prospecting from the public **CVR** register
and contacts businesses **by phone**. These documents cover the legal basis and
the safeguards; the safeguards are enforced in code, not just on paper.

| Document | What it is |
|---|---|
| [`LIA.md`](./LIA.md) | Written legitimate-interest assessment (GDPR Art. 6(1)(f)) — purpose / necessity / balancing + safeguards. |
| [`privacy-notice.md`](./privacy-notice.md) | Public Art. 14 privacy notice (Danish + English summary) to publish at a stable URL. |
| [`first-contact-script.md`](./first-contact-script.md) | The Art. 14 disclosure delivered verbally at first phone contact (source = CVR). |

## The four rules (and where they live)

1. **No marketing email/SMS without consent** (Markedsføringsloven §10) →
   product is **phone-first**; there is no email-send channel. Cold B2B *calls*
   are allowed.
2. **Exclude `reklamebeskyttelse` + inactive entities** → enforced at discovery
   (`services/worker/.../cvr/discovery.py` + `mapper.py`); they never enter
   `leads`.
3. **Screen sole traders against the Robinson list** before outreach →
   `services/worker/.../compliance/` + `leadmachine screen`. Matches are flagged
   `suppressed` and hidden from the dashboard.
4. **Art. 14 notice at first contact; absolute Art. 21 opt-out** → the
   first-contact script; objections set the lead `suppressed` permanently.

## Before live outreach (gate)

- [ ] Fill in the `[…]` placeholders (controller, contact, URL) in the LIA +
      privacy notice and **publish** the privacy notice.
- [ ] Provision the **Robinson list** on the worker host and set
      `ROBINSON_LIST_PATH` (licensed data — never commit it).
- [ ] Run `leadmachine screen` and confirm sole-trader leads are screened (the
      command **warns loudly** if the list is empty).
- [ ] Brief callers on the first-contact script.

See [`../DEPLOY.md`](../DEPLOY.md) for how these slot into the deployment.
