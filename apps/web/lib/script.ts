// The call script — deliberately a FIXED template, not AI-generated. Every
// call opens, pitches, handles price and books the same way, word for word;
// the only things that vary are who answers (owner vs. gatekeeper), the
// owner's first name, the branche and the savings band the pitch quotes.
// The AI still supplies the private notes and lead-specific objections,
// never the script.
//
// v2 (Session 28): pitch restructured per the user's draft — CVR + "2 slots"
// + the savings band up front, "ville du have noget imod det?", a bank of
// optional one-liner jokes, then the 30-day explanation, pain, booking, and
// a new "make sure they show up" step (earthquake/tsunami line + the PS about
// the 2 things ready for them). The old A/C variant switch is gone — there is
// one pitch now.
//
// The Art. 14 source line ("fundet jer i CVR-registeret") is woven into the
// first sentence of the pitch on purpose — it has to be said on the first
// call. See docs/compliance/first-contact-script.md.

import type { PhoneType } from "./phone";
import type { SavingsView } from "./savings";

/** A run of spoken text. `kind` lets the UI highlight what must be said (the
 *  GDPR source) and what varies per lead (the savings figure). */
export type Segment = { text: string; kind: "plain" | "source" | "savings" };

export type CallScript = {
  /** Who is expected to pick up — decides which opener is shown first. */
  audience: "owner" | "gatekeeper";
  /** Owner picks up (mobile). */
  openerOwner: string;
  /** Staff/reception picks up (landline / 70-number) — get to the owner first. */
  openerGatekeeper: string;
  /**
   * The pitch: CVR line (the Art. 14 disclosure) + the 2 open slots + the
   * savings band, as one spoken flow.
   */
  pitch: Segment[][];
  /** The savings sentence in the pitch — always present (default band if no data). */
  savingsLine: string;
  /** "Ville du have noget imod det?" — said right after the band. */
  objectionCheck: string;
  /** Optional one-liners while they digest the number. Pick ONE, not all. */
  jokes: string[];
  /** The 30-day explanation, then the bridge into the pain question. */
  how: string;
  bridge: string;
  /** Pain question, then the follow-up after they answer. */
  pain: { ask: string; followup: string };
  /** "Hvad koster det?" — the long answer and the short one for interruptions. */
  price: { long: string; short: string; feeLine: string | null };
  /** The booking ask. */
  booking: string;
  /** After the time is agreed — lock the show-up, then the PS. */
  showUp: { ask: string; ps: string };
};

// Spoken amounts: "120.000" — the script says "kroner" itself.
const NUM = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 0 });
const spoken = (n: number) => NUM.format(n);
const plain = (text: string): Segment => ({ text, kind: "plain" });

// Default band when the lead has no savings figure of its own.
const DEFAULT_LOW = 240_000;
const DEFAULT_HIGH = 400_000;

/** "Frisørsaloner" → "frisørsaloner"; nothing → "virksomheder som jeres". */
function spokenBranche(label: string | null): string {
  const t = label?.trim();
  if (!t) return "virksomheder som jeres";
  return t.charAt(0).toLowerCase() + t.slice(1);
}

// The savings sentence: the lead's own band when we have one (their filed
// accounts may be quoted back to them), else the default 240–400k band.
function savingsSegment(savings: SavingsView | null, branche: string | null): Segment {
  const low = savings?.annualLow ?? DEFAULT_LOW;
  const high = savings?.annualHigh ?? DEFAULT_HIGH;
  const band = `${spoken(low)} til ${spoken(high)} kroner om året`;
  const base = `For det, vi gør, er at spare ${spokenBranche(branche)} for rigtig mange penge — realistisk set ville I se mellem ${band}.`;
  return {
    kind: "savings",
    text:
      savings?.basis === "accounts"
        ? `${base} Og det siger jeg ud fra jeres eget offentlige regnskab.`
        : base,
  };
}

export function buildCallScript(opts: {
  firstName: string | null;
  phoneType: PhoneType | null;
  savings: SavingsView | null;
  /** Spoken industry ("frisørsaloner") — branche_text or the group label. */
  brancheLabel?: string | null;
}): CallScript {
  const { firstName, phoneType, savings, brancheLabel = null } = opts;
  const owner = firstName ?? "ejeren";
  const money = savingsSegment(savings, brancheLabel);
  return {
    audience: phoneType === "mobile" || phoneType === null ? "owner" : "gatekeeper",
    openerOwner:
      "Hej, det er [dit navn]. Jeg ved godt det er pisse irriterende at blive ringet op af en, man ikke har bedt om, men må jeg få 30 sekunder af din tid?",
    openerGatekeeper: `Hej, det er [dit navn]. Jeg ved godt jeg ringer helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I får hverdagen til at køre? … Er det ${owner}?`,
    pitch: [
      [
        // Art. 14: the CVR source, said in the first sentence.
        {
          kind: "source",
          text: "Jeg har fundet jer i CVR-registeret,",
        },
        plain("og jeg tror, I kunne være et rigtig godt fit til en af de 2 pladser, vi har åbne lige nu."),
      ],
      [money],
    ],
    savingsLine: money.text,
    objectionCheck: "Ville du have noget imod det?",
    // One-liners while the number sinks in — pick ONE that fits the mood.
    jokes: [
      "Ville du smadre din telefon, hvis jeg fortalte dig, hvordan vi gør det?",
      "Kan du lide penge?",
      "Hader du penge?",
      "Er det ikke det bedste, du har hørt hele ugen, haha?",
      "Men lov mig, du ikke bruger det hele på whisky?",
      "Og sig det ikke til din bedre halvdel — så bliver det bare til en ny bil, haha.",
    ],
    how: "Det, vi gør, er at følge jeres virksomhed i 30 dage — ikke fysisk, remote — og se præcis, hvor penge og tid forsvinder. Derfra kigger vi på, hvad vi kan gøre for at stoppe det.",
    bridge: "Så med det sagt:",
    pain: {
      ask: "Hvad bruger du en masse tid på, som du godt ved ikke er værdifuld tid for DIG?",
      followup: "Og hvis du fik bare halvdelen af det tilbage — hvad ville du så bruge det på?",
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
      ask: "Ud over et jordskælv eller en tsunami — er der så nogen grund til, at du ikke skulle dukke op?",
      ps: "Nå, for resten — når du dukker op [dag], har jeg faktisk 2 ting klar til dig, som sparer dig tid lige efter mødet.",
    },
  };
}
