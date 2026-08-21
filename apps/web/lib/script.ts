// The call script — deliberately a FIXED template, not AI-generated. Every
// call opens, pitches, handles price and books the same way, word for word;
// the only things that vary are who answers (owner vs. gatekeeper), the
// owner's first name, the branche and the savings band the pitch quotes.
// The AI still supplies the private notes and lead-specific objections,
// never the script.
//
// v3 (Session 29): the user's final wording, verbatim (spelling normalised).
// Pitch = CVR + "1 af de 2 pladser" + the band; then a SPLIT-TEST bank of
// seven follow-up questions (pick one per call, rotate to see what lands);
// the 30-days explanation; pain; booking; show-up lock; PS. The band is the
// lead's own calculated amount — 240.000–400.000 is only the fallback when
// the lead has no figure.
//
// The Art. 14 source line ("fundet dig i CVR-registret") is the first thing
// said in the pitch on purpose — it has to be said on the first call. See
// docs/compliance/first-contact-script.md.

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
   * The pitch as one spoken paragraph: the CVR line (Art. 14), the 2 open
   * slots, and the lead's savings band.
   */
  pitch: Segment[][];
  /** The savings sentence in the pitch — always present (default band if no data). */
  savingsLine: string;
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
  /** After the time is agreed — lock the show-up, then the PS. */
  showUp: { ask: string; ps: string };
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
  /** Spoken industry ("frisørsaloner") — branche_text or the group label. */
  brancheLabel?: string | null;
}): CallScript {
  const { firstName, phoneType, savings, brancheLabel = null } = opts;
  const owner = firstName ?? "ejeren";
  const name = firstName ?? "[navn]";
  // The band is the lead's own calculated amount; 240–400k only as fallback.
  const low = savings?.annualLow ?? DEFAULT_LOW;
  const high = savings?.annualHigh ?? DEFAULT_HIGH;
  const money: Segment = {
    kind: "savings",
    text: `Det, vi gør, er helt simpelt: vi sparer ${spokenBranche(brancheLabel)} en masse penge. Realistisk set, for dig, ville det være mellem ${spoken(low)} og ${spoken(high)} kroner årligt.`,
  };
  return {
    audience: phoneType === "mobile" || phoneType === null ? "owner" : "gatekeeper",
    openerOwner:
      "Hej, det er [dit navn]. Jeg ved godt det er pisse irriterende at blive ringet op af en, man ikke har bedt om, men må jeg få 30 sekunder af din tid?",
    openerGatekeeper: `Hej, det er [dit navn]. Jeg ved godt jeg ringer helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I får hverdagen til at køre? … Er det ${owner}?`,
    pitch: [
      [
        // Art. 14: the CVR source, said first.
        { kind: "source", text: "Jeg har fundet dig i CVR-registret," },
        plain(
          "og jeg tror, du vil kunne være et godt fit til 1 af de 2 pladser, vi har åbne lige nu.",
        ),
        money,
      ],
    ],
    savingsLine: money.text,
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
    how: "Så det, vi gør, er, at vi følger jeres virksomhed i 30 dage — ikke fysisk, men remote selvfølgelig — og der ser vi præcis, hvor pengene og tiden render hen. Derfra kigger vi på, hvordan vi kan sætte en stopper for det.",
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
      ask: `Så ${name} — ud over en tsunami eller ét jordskælv, ville der være noget som helst, der kunne forhindre dig i at møde op i morgen?`,
      ps: "Oh, og imens jeg lige husker det — når du møder op [mødedag], har jeg faktisk allerede 2 ting klar til dig, som jeg ved vil spare dig penge og tid allerede 5 minutter efter mødet.",
    },
  };
}
