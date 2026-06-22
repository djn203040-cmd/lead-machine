# Legitimate Interest Assessment (LIA)

**Controller:** _[company name + CVR — fill in before go-live]_
**Processing:** B2B lead generation — discovering, qualifying and contacting
Danish businesses to offer website/online-presence services.
**Legal basis:** GDPR Art. 6(1)(f) — legitimate interests.
**Version:** 1.0 · **Last reviewed:** _[date]_ · **Owner:** _[DPO / responsible person]_

> This LIA documents why we may process limited personal data without consent
> for B2B prospecting, and the safeguards that keep that processing proportionate.
> It must be reviewed at least annually and whenever the processing changes
> (e.g. if an email channel is ever added — see §5).

---

## 1. Scope of personal data

Most of what we process is **company data**, not personal data (a CVR number,
a company name, an address, a landline, employee bands, financial figures from
published annual reports). Personal data enters only in two places:

| Data | Source | Subjects |
|---|---|---|
| Names + roles of management / owners (direktion, bestyrelse, reelle ejere) | CVR register (`lead_enrichment.contact`) | Decision-makers at limited companies |
| Name + address + phone of a **sole trader** (enkeltmandsvirksomhed / PMV) | CVR register (`leads`) | The natural person who *is* the business |

Sole-trader contact data is treated as **personal data** throughout. We process
**no special-category data** and do **no profiling with legal/​significant
effects** — scoring ranks businesses by website need, it does not make automated
decisions about individuals.

## 2. Purpose test — is there a legitimate interest?

Yes. Direct B2B marketing is a **recognised legitimate interest** (GDPR Recital
47). Our specific interest is to identify Danish businesses whose online presence
is weak or absent and offer them a relevant service. The interest is real,
present and lawful; CVR data is explicitly published for re-use, including
commercial re-use.

## 3. Necessity test — is the processing necessary?

Yes, and it is minimised:

- We use the **official CVR register** rather than scraping the open web at
  scale, and the CVR number as the dedup key.
- We collect only fields needed to qualify and contact a business (firmographics,
  website signals, a phone number, a named decision-maker).
- We do **not** enrich beyond what the offer needs (no private email harvesting,
  no social-graph building, reviews deferred to V2).
- Revenue is **estimated** from sector × employees rather than acquiring extra
  personal/financial data where the company has lawfully not disclosed it.

There is no less-intrusive way to run targeted B2B outreach than contacting the
relevant business with a relevant offer.

## 4. Balancing test — do our interests override the individual's?

For **limited companies**, the data subjects are reached in a purely
professional capacity at a legal person; the impact of a relevant B2B phone call
is minimal and within their reasonable expectations for a business listed in a
public register.

For **sole traders**, the balance is more sensitive because the person and the
business coincide. We therefore apply extra safeguards (§6). With those in place
— Robinson screening, reklamebeskyttelse suppression, phone-only, easy opt-out,
an Art. 14 notice at first contact — the residual impact is low and does not
override the individual's interests.

**Outcome: the balance favours processing, conditional on the §6 safeguards.**

## 5. Channel constraint (Markedsføringsloven §10)

Denmark's Markedsføringsloven §10 bans **unsolicited electronic marketing**
(email/SMS) without prior consent, with **no B2B exemption**. Cold **B2B phone
calls** are generally permitted. Therefore:

- **V1 is phone-first.** There is no email-send channel in the product.
- An email/SMS channel may only be added **after** building consent + opt-out
  capture, and this LIA must be revised first. (Code guard: the lead UI is
  phone-first and shows the §10 note; there is no compose-email action.)

## 6. Safeguards (enforced in code)

| Safeguard | Where enforced |
|---|---|
| Exclude `reklamebeskyttelse` (marketing-protected) entities | Discovery never inserts them — `cvr/discovery.py`, `cvr/mapper.py` |
| Exclude inactive / bankrupt / dissolved entities | Same — `SUPPRESS_INACTIVE` |
| **Robinson-list screening of sole traders** before outreach | `compliance/robinson.py` + `screen.py`; `leadmachine screen`; suppressed leads hidden from the dashboard |
| Phone-first only; no cold email | Product has no email-send channel; UI shows the §10 note |
| Art. 14 privacy notice at first contact (source = CVR) | [`first-contact-script.md`](./first-contact-script.md) |
| Public privacy notice + opt-out / Art. 21 objection route | [`privacy-notice.md`](./privacy-notice.md) |
| Data minimisation + retention | §7 below |

## 7. Retention & rights

- **Retention:** keep a lead only while it is an active prospect. Discard +
  delete (or fully suppress) leads that opt out, that go cold, or that we decide
  not to pursue. Set a concrete review window before go-live (suggested: purge
  non-converted leads after 12 months).
- **Rights:** the public notice describes access / rectification / erasure /
  **Art. 21 objection** (absolute for direct marketing — on objection we suppress
  immediately and permanently). Requests go to the contact in the notice.

## 8. Decision

Processing is **permitted under Art. 6(1)(f)** for V1 (phone-first B2B
prospecting from CVR data) provided every §6 safeguard is live — in particular,
**no live outreach begins until the Robinson list is provisioned and a screening
pass has run** (`leadmachine screen`). Re-assess on any material change.
