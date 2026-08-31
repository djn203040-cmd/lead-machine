// The call script — deliberately a FIXED template, not AI-generated. Every
// call opens, pitches, handles price and books the same way, word for word;
// the only things that vary are who answers (owner vs. gatekeeper), the
// owner's first name and the savings band the opener quotes.
// The AI still supplies the private notes and lead-specific objections,
// never the script.
//
// v8 (Session 28, 2026-08-31): the quick script — the user's four-beat flow.
// Opener = "tilbyde at følge din i 30 dage" + the band + 5-min ask (the
// mechanism makes the number credible). Yes → one breath: follow, find the
// leak, build, pay only when it works. Then ONE pain question (and silence —
// their answer is what makes them show up), then the alternative close
// ("i morgen eller i overmorgen", honest 20 minutes). Split-test bank, how,
// bridge, branche proof/2-slots and the pain follow-up are all retired below
// — the speed is the script's identity. Price, booked-step, PS and the
// Art. 14 sourceLine are unchanged.
//
// v7: number-first opener ("jeg har kigget lidt på jeres").
// v6: simple spoken branche labels; show-up lock retired.
// v5: pitch outcome-first; CVR moved out of the pitch to `sourceLine` —
// Art. 14 still requires it before the first call ends (see
// docs/compliance/first-contact-script.md).
//
// RETIRED lines (not in the script right now — kept so we can bring them back):
//   Opener (ejer, v2–v3): "Hej, det er [dit navn]. Jeg ved godt det er pisse
//   irriterende at blive ringet op af en, man ikke har bedt om, men må jeg få
//   30 sekunder af din tid?"
//   Opener (ejer, v4–v6): "Hej, det er [dit navn]. Min mor har altid sagt, det
//   mest dyrebare, vi har, er tid — så jeg vil starte med at sige, at jeg er
//   en sælger, og høre, om du har 5 minutter?"
//   Opener (ejer, v7): "Hej, det er [dit navn]. Jeg har selv en virksomhed, og
//   jeg har kigget lidt på jeres — jeg tror, jeg kan spare dig mellem [low] og
//   [high] kroner om året. Har du 5 minutter?"
//   Opener (ejer, v8.0): "Hej, det er [dit navn]. Jeg har selv en virksomhed,
//   og jeg vil gerne tilbyde at følge din i 30 dage for at spare dig mellem
//   [low] og [high] kroner om året. Er det noget, du vil bruge 5 minutter på?"
//   ("tilbyde at" felt too formal — replaced by "kigge med" in v8.1)
//   Pitch (v3–v4): "Jeg har fundet dig i CVR-registret, og jeg tror, du vil
//   kunne være et godt fit til 1 af de 2 pladser, vi har åbne lige nu. Det, vi
//   gør, er helt simpelt: vi sparer [branche] en masse penge. Realistisk set,
//   for dig, ville det være mellem [low] og [high] kroner årligt."
//   Pitch, money-first (v5–v6): "Jeg tror, jeg kan spare dig mellem [low] og
//   [high] kroner om året — penge, du taber lige nu på opgaver, der ikke er
//   din tid værd."
//   Pitch, proof + scarcity (v6–v7): "Det gør vi allerede for [branche], og vi
//   har 2 pladser åbne lige nu — jeg tror, du er et fit til den ene."
//   How (v3–v4): "Så det, vi gør, er, at vi følger jeres virksomhed i 30 dage
//   — ikke fysisk, men remote selvfølgelig — og der ser vi præcis, hvor
//   pengene og tiden render hen. Derfra kigger vi på, hvordan vi kan sætte en
//   stopper for det."
//   How (v5–v7): "Vi følger jeres virksomhed i 30 dage — remote selvfølgelig —
//   og finder præcis, hvor tiden og pengene siver ud. Så lukker vi hullerne."
//   Bridge (v3–v7): "Så med det sagt,"
//   Pain follow-up (v3–v7): "Og hvad hvis du fik bare halvdelen af den tid og
//   de penge tilbage — hvad ville du så bruge dem på?"
//   Booking (v3–v7): "Skal vi ikke tage ti minutter, hvor jeg spørger ind til,
//   hvordan I kører det i dag? Passer det bedst i morgen formiddag eller til
//   eftermiddag?"
//   Show-up lock (v3–v5): "Så [navn] — ud over en tsunami eller ét jordskælv,
//   ville der være noget som helst, der kunne forhindre dig i at møde op i
//   morgen?"
//   Split-test bank (v3–v7) — pick ONE per call, rotate:
//     "Ville du have noget imod at spare de penge?"
//     "Ville du smadre din telefon i jorden, hvis jeg fortalte, hvordan vi gør det?"
//     "Såå, kan du lide penge — eller er [low] eller mere uinteressant for dig?"
//     "Såå, hader du penge, eller lyder det spændende?"
//     "Er det ikke den bedste nyhed, du har hørt hele ugen, haha?"
//     "Men du skal love, at du ikke bruger de penge, vi sparer, på [noget
//     researchet til præcis den her person — deres hobby, bil, klub …]"
//     "Men fortæl ikke din hustru, at du sparer de penge — så vil hun have ny
//     bil og alt muligt."

import type { PhoneType } from "./phone";
import type { SavingsView } from "./savings";

/** A run of spoken text. `kind` lets the UI highlight what must be said (the
 *  GDPR source) and what varies per lead (the savings figure). */
export type Segment = { text: string; kind: "plain" | "source" | "savings" };

export type CallScript = {
  /** Who is expected to pick up — decides which opener is shown first. */
  audience: "owner" | "gatekeeper";
  /** Owner picks up (mobile) — 30 days + the lead's savings band + 5-min ask. */
  openerOwner: Segment[];
  /** Staff/reception picks up (landline / 70-number) — get to the owner first. */
  openerGatekeeper: string;
  /** After they say yes: follow → find the leak → build → pay when it works. */
  pitch: Segment[][];
  /**
   * GDPR Art. 14 source disclosure — not part of the pitch, but it MUST be
   * said before the first call ends (booked or not). Rendered as its own
   * "inden du lægger på" step.
   */
  sourceLine: string;
  /** The ONE question before booking — then silence; their answer sells the meeting. */
  pain: string;
  /** "Hvad koster det?" — the long answer and the short one for interruptions. */
  price: { long: string; short: string; feeLine: string | null };
  /** The booking ask: bridge off their answer + alternative close. */
  booking: string;
  /** After the time is agreed — mail + day-before prep call, then the PS. */
  showUp: { booked: string; ps: string };
};

// Spoken amounts: "120.000" — the script says "kroner" itself.
const NUM = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 0 });
const spoken = (n: number) => NUM.format(n);
const plain = (text: string): Segment => ({ text, kind: "plain" });

// Last-resort band when the lead has no calculated figure AND the caller
// passed no size-aware fallback (fallbackSavingsBand in lib/savings.ts —
// 1 person → 90–150k, 2 → 180–300k, 3+ → this cap).
const DEFAULT_LOW = 240_000;
const DEFAULT_HIGH = 400_000;

export function buildCallScript(opts: {
  firstName: string | null;
  phoneType: PhoneType | null;
  savings: SavingsView | null;
  /** Spoken industry — pass spokenBrancheForCode(), never raw CVR branche_text. */
  brancheLabel?: string | null;
  /** Size-aware band for leads with no calculated figure (fallbackSavingsBand). */
  fallback?: { low: number; high: number };
}): CallScript {
  const { firstName, phoneType, savings, fallback } = opts;
  const owner = firstName ?? "ejeren";
  // The band is the lead's own calculated amount; the size-aware fallback
  // only when no figure exists — a 1-man shop is never quoted 240–400k.
  const low = savings?.annualLow ?? fallback?.low ?? DEFAULT_LOW;
  const high = savings?.annualHigh ?? fallback?.high ?? DEFAULT_HIGH;
  return {
    audience: phoneType === "mobile" || phoneType === null ? "owner" : "gatekeeper",
    // Number first (the hook), then the 30 days as a casual precondition —
    // "kigge med" is colleague-talk, not vendor-talk, and doesn't sound like
    // surveillance the way "følge din virksomhed" could.
    openerOwner: [
      plain("Hej, det er [dit navn]. Jeg har selv en virksomhed, og jeg tror, jeg kan spare din for"),
      {
        kind: "savings",
        text: `mellem ${spoken(low)} og ${spoken(high)} kroner om året`,
      },
      plain(
        "— jeg skal bare bruge 30 dage på at kigge med først. Er det noget, du vil bruge 5 minutter på?",
      ),
    ],
    openerGatekeeper: `Hej, det er [dit navn]. Jeg ved godt jeg ringer helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I får hverdagen til at køre? … Er det ${owner}?`,
    pitch: [
      [
        // One breath: mechanism + risk reversal. Then straight to the question.
        plain(
          "Fedt. Vi følger din virksomhed, finder ud af præcis hvor tiden og pengene siver ud — og så bygger vi det, der stopper det. Og du betaler selvfølgelig først, når vi har vist, at det virker.",
        ),
      ],
    ],
    // Art. 14 — said before hanging up, in EVERY first call, booked or not.
    sourceLine:
      "Inden jeg lægger på — helt kort, for en god ordens skyld: jeg fandt dig via CVR-registret. Og vil du ikke ringes op igen, siger du bare til, så fjerner jeg dig med det samme.",
    pain: "Så lad mig spørge dig — hvad bruger du mest tid på lige nu, som du VED ikke er din tid værd?",
    price: {
      long: "Det er 100 % gratis at kigge. Finder vi noget, laver vi et estimat på, hvad det sparer jer — eller hvad det genererer i omsætning. Det kigger vi så på sammen, og først derefter bygger vi det. Og først når det er bygget, betaler I: 20 % af det, vi rent faktisk har sparet jer i tid eller skabt i omsætning på et år — og det betaler I én gang. Derefter er besparelsen jeres.",
      short:
        "Ingenting, før det virker. 20 % af det, vi kan dokumentere, vi har sparet jer på et år — én gang, resten beholder I. Sparer vi jer ingenting, betaler I ingenting.",
      feeLine: savings
        ? `Med jeres tal ville det typisk være ${spoken(savings.feeLow)} til ${spoken(savings.feeHigh)} kroner — én gang — for at få ${spoken(savings.annualLow)} til ${spoken(savings.annualHigh)} kroner tilbage hvert år.`
        : null,
    },
    booking:
      "Præcis den slags er det, vi fjerner. Passer en 20 minutters snak dig bedst i morgen eller i overmorgen?",
    showUp: {
      booked:
        "Jeg sender lige nogle oplysninger på mail, så du ved, hvad du går ind til. Og ville det være okay, at jeg ringede dagen før og lige stillede nogle spørgsmål, så jeg kan forberede mødet specifikt til dig?",
      ps: "Oh, og imens jeg lige husker det — når du møder op [mødedag], har jeg faktisk allerede 2 ting klar til dig, som jeg ved vil spare dig penge og tid allerede 5 minutter efter mødet.",
    },
  };
}
