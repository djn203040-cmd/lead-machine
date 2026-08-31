// The call script — deliberately a FIXED template, not AI-generated. Every
// call opens, pitches, handles price and books the same way, word for word;
// the only things that vary are who answers (owner vs. gatekeeper), the
// owner's first name, the branche and the savings band the pitch quotes.
// The AI still supplies the private notes and lead-specific objections,
// never the script.
//
// v7 (Session 28, 2026-08-31): the number IS the opener. The "jeg er en
// sælger"-angle lacked a hook, so the owner opener now leads with peer
// credibility ("jeg har selv en virksomhed") + the lead's own savings band,
// then asks for 5 minutes. openerOwner is Segment[] so the band stays
// highlighted. The pitch (after they say yes) is just the branche proof +
// the 2 slots — the number was already said. savingsLine dropped (unused).
//
// v6 (Session 28, 2026-08-31): the show-up lock ("tsunami/jordskælv") is out
// of the script (retired below) — step 5 is now just the mail + day-before
// call, then the PS. Callers must pass `brancheLabel` from
// spokenBrancheForCode() (lib/branchekoder.ts), never raw CVR branche_text —
// so the pitch says "frisører og barbere", not "drift af sundhedsvæsen i
// øvrigt i.a.n.".
//
// v5 (Session 28, 2026-08-31): pitch reworked — shorter, outcome first. The
// savings band is now the FIRST sentence, framed as money the lead is losing;
// the 2-slots scarcity and branche proof follow in one line. The CVR line is
// OUT of the pitch, but Art. 14 still requires it on the first call, so it
// moved to `sourceLine` — a short mandatory line before hanging up (see
// docs/compliance/first-contact-script.md). The 30-days "how" was tightened
// too. Unchanged from v4: openers, split-test bank, pain, price, booking,
// booked/show-up/PS.
//
// RETIRED lines (not in the script right now — kept so we can bring them back):
//   Opener (ejer, v2–v3): "Hej, det er [dit navn]. Jeg ved godt det er pisse
//   irriterende at blive ringet op af en, man ikke har bedt om, men må jeg få
//   30 sekunder af din tid?"
//   Opener (ejer, v4–v6): "Hej, det er [dit navn]. Min mor har altid sagt, det
//   mest dyrebare, vi har, er tid — så jeg vil starte med at sige, at jeg er
//   en sælger, og høre, om du har 5 minutter?"
//   Pitch, money-first (v5–v6): "Jeg tror, jeg kan spare dig mellem [low] og
//   [high] kroner om året — penge, du taber lige nu på opgaver, der ikke er
//   din tid værd." (moved into the opener in v7)
//   Pitch (v3–v4): "Jeg har fundet dig i CVR-registret, og jeg tror, du vil
//   kunne være et godt fit til 1 af de 2 pladser, vi har åbne lige nu. Det, vi
//   gør, er helt simpelt: vi sparer [branche] en masse penge. Realistisk set,
//   for dig, ville det være mellem [low] og [high] kroner årligt."
//   How (v3–v4): "Så det, vi gør, er, at vi følger jeres virksomhed i 30 dage
//   — ikke fysisk, men remote selvfølgelig — og der ser vi præcis, hvor
//   pengene og tiden render hen. Derfra kigger vi på, hvordan vi kan sætte en
//   stopper for det."
//   Show-up lock (v3–v5): "Så [navn] — ud over en tsunami eller ét jordskælv,
//   ville der være noget som helst, der kunne forhindre dig i at møde op i
//   morgen?"

import type { PhoneType } from "./phone";
import type { SavingsView } from "./savings";

/** A run of spoken text. `kind` lets the UI highlight what must be said (the
 *  GDPR source) and what varies per lead (the savings figure). */
export type Segment = { text: string; kind: "plain" | "source" | "savings" };

export type CallScript = {
  /** Who is expected to pick up — decides which opener is shown first. */
  audience: "owner" | "gatekeeper";
  /** Owner picks up (mobile) — carries the lead's savings band (the hook). */
  openerOwner: Segment[];
  /** Staff/reception picks up (landline / 70-number) — get to the owner first. */
  openerGatekeeper: string;
  /**
   * The pitch after they say yes: the branche proof and the 2 open slots —
   * the savings band was already delivered in the opener.
   */
  pitch: Segment[][];
  /**
   * GDPR Art. 14 source disclosure — no longer part of the pitch, but it MUST
   * be said before the first call ends (booked or not). Rendered as its own
   * "inden du lægger på" step.
   */
  sourceLine: string;
  /** Split-test bank: SEVEN follow-ups — pick ONE per call, rotate. */
  splitTest: string[];
  /** The 30-day explanation, then the bridge into the pain question. */
  how: string;
  bridge: string;
  /** Pain question, then the follow-up after they answer. */
  pain: { ask: string; followup: string };
  /** "Hvad koster det?" — the long answer and the short one for interruptions. */
  price: { long: string; short: string; feeLine: string | null };
  /** The booking ask. */
  booking: string;
  /** After the time is agreed — mail + day-before prep call, then the PS. */
  showUp: { booked: string; ps: string };
};

// Spoken amounts: "120.000" — the script says "kroner" itself.
const NUM = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 0 });
const spoken = (n: number) => NUM.format(n);
const plain = (text: string): Segment => ({ text, kind: "plain" });

// Fallback band when the lead has no calculated savings figure of its own.
const DEFAULT_LOW = 240_000;
const DEFAULT_HIGH = 400_000;

/** "Frisørsaloner" → "frisørsaloner"; nothing → "virksomheder som jeres". */
function spokenBranche(label: string | null): string {
  const t = label?.trim();
  if (!t) return "virksomheder som jeres";
  return t.charAt(0).toLowerCase() + t.slice(1);
}

export function buildCallScript(opts: {
  firstName: string | null;
  phoneType: PhoneType | null;
  savings: SavingsView | null;
  /** Spoken industry — pass spokenBrancheForCode(), never raw CVR branche_text. */
  brancheLabel?: string | null;
}): CallScript {
  const { firstName, phoneType, savings, brancheLabel = null } = opts;
  const owner = firstName ?? "ejeren";
  // The band is the lead's own calculated amount; 240–400k only as fallback.
  const low = savings?.annualLow ?? DEFAULT_LOW;
  const high = savings?.annualHigh ?? DEFAULT_HIGH;
  return {
    audience: phoneType === "mobile" || phoneType === null ? "owner" : "gatekeeper",
    // The number IS the hook — said before they can hang up.
    openerOwner: [
      plain("Hej, det er [dit navn]. Jeg har selv en virksomhed, og jeg har kigget lidt på jeres —"),
      {
        kind: "savings",
        text: `jeg tror, jeg kan spare dig mellem ${spoken(low)} og ${spoken(high)} kroner om året.`,
      },
      plain("Har du 5 minutter?"),
    ],
    openerGatekeeper: `Hej, det er [dit navn]. Jeg ved godt jeg ringer helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I får hverdagen til at køre? … Er det ${owner}?`,
    pitch: [
      [
        // They said yes to the number — now the proof and the scarcity.
        plain(
          `Det gør vi allerede for ${spokenBranche(brancheLabel)}, og vi har 2 pladser åbne lige nu — jeg tror, du er et fit til den ene.`,
        ),
      ],
    ],
    // Art. 14 — said before hanging up, in EVERY first call, booked or not.
    sourceLine:
      "Inden jeg lægger på — helt kort, for en god ordens skyld: jeg fandt dig via CVR-registret. Og vil du ikke ringes op igen, siger du bare til, så fjerner jeg dig med det samme.",
    // Split-test — pick ONE per call and rotate; note in the call log what landed.
    splitTest: [
      "Ville du have noget imod at spare de penge?",
      "Ville du smadre din telefon i jorden, hvis jeg fortalte, hvordan vi gør det?",
      `Såå, kan du lide penge — eller er ${spoken(low)} eller mere uinteressant for dig?`,
      "Såå, hader du penge, eller lyder det spændende?",
      "Er det ikke den bedste nyhed, du har hørt hele ugen, haha?",
      "Men du skal love, at du ikke bruger de penge, vi sparer, på [noget researchet til præcis den her person — deres hobby, bil, klub …]",
      "Men fortæl ikke din hustru, at du sparer de penge — så vil hun have ny bil og alt muligt.",
    ],
    how: "Vi følger jeres virksomhed i 30 dage — remote selvfølgelig — og finder præcis, hvor tiden og pengene siver ud. Så lukker vi hullerne.",
    bridge: "Så med det sagt,",
    pain: {
      ask: "Hvad bruger du mest tid på lige nu, som du VED ikke er din tid værd?",
      followup:
        "Og hvad hvis du fik bare halvdelen af den tid og de penge tilbage — hvad ville du så bruge dem på?",
    },
    price: {
      long: "Det er 100 % gratis at kigge. Finder vi noget, laver vi et estimat på, hvad det sparer jer — eller hvad det genererer i omsætning. Det kigger vi så på sammen, og først derefter bygger vi det. Og først når det er bygget, betaler I: 20 % af det, vi rent faktisk har sparet jer i tid eller skabt i omsætning på et år — og det betaler I én gang. Derefter er besparelsen jeres.",
      short:
        "Ingenting, før det virker. 20 % af det, vi kan dokumentere, vi har sparet jer på et år — én gang, resten beholder I. Sparer vi jer ingenting, betaler I ingenting.",
      feeLine: savings
        ? `Med jeres tal ville det typisk være ${spoken(savings.feeLow)} til ${spoken(savings.feeHigh)} kroner — én gang — for at få ${spoken(savings.annualLow)} til ${spoken(savings.annualHigh)} kroner tilbage hvert år.`
        : null,
    },
    booking:
      "Skal vi ikke tage ti minutter, hvor jeg spørger ind til, hvordan I kører det i dag? Passer det bedst i morgen formiddag eller til eftermiddag?",
    showUp: {
      booked:
        "Jeg sender lige nogle oplysninger på mail, så du ved, hvad du går ind til. Og ville det være okay, at jeg ringede dagen før og lige stillede nogle spørgsmål, så jeg kan forberede mødet specifikt til dig?",
      ps: "Oh, og imens jeg lige husker det — når du møder op [mødedag], har jeg faktisk allerede 2 ting klar til dig, som jeg ved vil spare dig penge og tid allerede 5 minutter efter mødet.",
    },
  };
}
