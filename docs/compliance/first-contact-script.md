# Art. 14-meddelelse ved første kontakt (telefon-script)

> GDPR Art. 14 requires that when personal data is obtained from a third source
> (here: CVR), the data subject is informed **at the latest at first contact**.
> For our phone-first model, the caller delivers this verbally on the first call.
> Keep it short, say the source out loud, and point to the full notice. This is a
> **compliance step, not a pitch** — deliver it even if the call is brief.

## Caller checklist (every first call)

1. **Identify** yourself + the company.
2. **State the source:** "vi har fundet jer i CVR-registeret."
3. **State the purpose:** a relevant offer to cut manual work and costs.
4. **Point to the full notice** and the opt-out right.
5. **Honour any objection immediately** → mark the lead suppressed (do not call
   again).

## Danish script (sole traders & company decision-makers)

The spoken script is fixed and lives in `apps/web/lib/script.ts` (rendered in
the dialer and on the lead page). Since script v5 the Art. 14 disclosure is
**no longer inside the pitch** (the pitch leads with the outcome instead) — it
is a mandatory stand-alone line said **before hanging up**, in every first
call, booked or not. That is still "at the latest at first contact", so Art. 14
is satisfied. It has its own highlighted step in the app so it is never
skipped:

> **Åbning (ejer tager den):** "Hej, det er [navn]. Jeg har selv en virksomhed,
> og jeg tror, jeg kan spare din for [besparelse] kroner om året — jeg skal bare
> bruge 30 dage på at kigge med først. Er det noget, du vil bruge 5 minutter på?"
>
> **Åbning (medarbejder/reception):** "Hej, det er [navn]. Jeg ved godt jeg
> ringer helt uopfordret — hvem er den rigtige at fange, når det handler om
> hvordan I får hverdagen til at køre? … Er det [ejer]?"
>
> **Inden du lægger på (Art. 14, every first call):** "Inden jeg lægger på —
> helt kort, for en god ordens skyld: jeg fandt dig via **CVR-registret**. Og
> vil du ikke ringes op igen, siger du bare til, så fjerner jeg dig med det
> samme."
>
> If they ask about their data or want to be left alone, add:
> "I kan læse vores privatlivspolitik på [link], og I kan til enhver tid bede os
> om **ikke** at kontakte jer igen — så fjerner vi jer med det samme."

If the person objects to marketing at any point:

> "Selvfølgelig — jeg sørger for, at vi ikke kontakter jer igen. Beklager
> forstyrrelsen, og hav en god dag."

→ Then set the lead's pipeline status to **discarded** and have it suppressed so
it cannot resurface (an Art. 21 objection is absolute and permanent).

## What to log after the call
- That the Art. 14 notice was given (date/time — the call itself is the record).
- Any objection / opt-out → lead suppressed.
- Outcome / next step in the pipeline.

## Do / don't
- **Do** say "CVR-registeret" explicitly — that is the Art. 14 source disclosure.
- **Do** offer the opt-out proactively.
- **Don't** send a cold marketing **email/SMS** afterwards without consent
  (Markedsføringsloven §10). Follow-up by phone, or by email only if the contact
  has **asked** you to send something.
