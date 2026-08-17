// The call script — deliberately a FIXED template, not AI-generated. Every
// call opens, pitches, handles price and books the same way, word for word;
// the only things that vary are who answers (owner vs. gatekeeper), the
// owner's first name, and the savings figure the pitch quotes. The AI still
// supplies the private notes and lead-specific objections, never the script.
//
// The offer: we follow the business for 30 days (remote), find where the
// hours and kroner leak, build what closes those holes, and get paid 20% of
// one year's documented saving — once, only after it is built. Nothing found
// = nothing paid. Never a website.
//
// The Art. 14 source line ("fundet jer i CVR-registeret") is woven into the
// first sentence of the pitch on purpose — it has to be said on the first
// call. See docs/compliance/first-contact-script.md.

import type { PhoneType } from "./phone";
import type { SavingsView } from "./savings";

/** A run of spoken text. `kind` lets the UI highlight what must be said (the
 *  GDPR source) and what varies per lead (the savings figure). */
export type Segment = { text: string; kind: "plain" | "source" | "savings" };

export type PitchVariant = "a" | "c";

/**
 * Which pitch wording is in use. Both are kept so we can switch back without
 * digging through git:
 *  - "c": risk first; the savings figure lands just before the pain question.
 *  - "a": the savings figure IS the reason for calling — right after the CVR
 *         line, then "sådan gør vi", then risk.
 */
export const PITCH_VARIANT: PitchVariant = "c";

export type CallScript = {
  /** Who is expected to pick up — decides which opener is shown first. */
  audience: "owner" | "gatekeeper";
  /** Owner picks up (mobile). */
  openerOwner: string;
  /** Staff/reception picks up (landline / 70-number) — get to the owner first. */
  openerGatekeeper: string;
  /**
   * The pitch as one spoken flow, paragraph by paragraph. Opens with the CVR
   * line (the Art. 14 disclosure) and ends on "Så med det sagt:" — the pain
   * question follows directly.
   */
  pitch: Segment[][];
  /** The savings sentence in the pitch, or null when the lead has no figure. */
  savingsLine: string | null;
  /** Pain question, then the follow-up after they answer. */
  pain: { ask: string; followup: string };
  /** "Hvad koster det?" — the long answer and the short one for interruptions. */
  price: { long: string; short: string; feeLine: string | null };
  /** The booking ask. */
  booking: string;
};

// Spoken amounts: "120.000" — the script says "kroner" itself.
const NUM = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 0 });
const spoken = (n: number) => NUM.format(n);
const plain = (text: string): Segment => ({ text, kind: "plain" });

// The Art. 14 source disclosure — "CVR-registeret" must be said out loud.
const SOURCE = "Jeg har fundet jer i CVR-registeret og kigget lidt på, hvad I laver.";
// Why them, why now — said right after the CVR line so the call has a reason
// beyond "we found you". Keep the number true: we run 5 slots a quarter.
const WHY =
  "Jeg har 2 slots åbne og vil rigtig gerne have fundet et godt fit til dem — det er derfor jeg ringer.";
const HOW =
  "Det, vi gør, er at følge jeres virksomhed i 30 dage — ikke fysisk, remote — og se helt konkret, hvor timerne og kronerne forsvinder. Derfra kigger vi på, hvad vi kan optimere i lige præcis de huller.";
const RISK =
  "Finder vi ikke noget, siger vi det til jer, og I betaler ikke en krone. Finder vi noget, betaler I først den første krone, når vi rent faktisk har bygget det til jer.";
const SO = "Så med det sagt:";

// The savings sentence, phrased by where the number came from. Their own
// filed accounts we may quote back to them; a benchmark is only "typical for
// their size"; no figure = say nothing about money and let the 30 days find it.
function savingsSegment(savings: SavingsView | null, variant: PitchVariant): Segment | null {
  if (!savings) return null;
  const band = `${spoken(savings.annualLow)} til ${spoken(savings.annualHigh)} kroner om året`;
  const accounts = savings.basis === "accounts";
  if (variant === "a") {
    return {
      kind: "savings",
      text: accounts
        ? `også jeres offentlige regnskab — og hos en virksomhed som jeres ligger der typisk ${band}, der forsvinder i timer og småting, som kan hentes hjem.`
        : `Hos virksomheder på jeres størrelse ligger der typisk ${band}, der forsvinder i timer og småting, som kan hentes hjem.`,
    };
  }
  return {
    kind: "savings",
    text: accounts
      ? `Og bare så du ved, hvad vi taler om: hos en virksomhed som jeres — jeg har kigget i jeres offentlige regnskab — ligger der typisk ${band}, der kan hentes hjem.`
      : `Og bare så du ved, hvad vi taler om: hos virksomheder på jeres størrelse ligger der typisk ${band}, der kan hentes hjem.`,
  };
}

function buildPitch(savings: SavingsView | null, variant: PitchVariant): Segment[][] {
  const money = savingsSegment(savings, variant);
  if (variant === "a") {
    // A: CVR (+ accounts + figure) → why → how → risk → so.
    const source: Segment = {
      kind: "source",
      // "…kigget lidt på, hvad I laver — også jeres offentlige regnskab…"
      text: money && savings?.basis === "accounts" ? SOURCE.replace(/\.$/, " —") : SOURCE,
    };
    return [money ? [source, money] : [source], [plain(WHY)], [plain(HOW)], [plain(RISK)], [plain(SO)]];
  }
  // C: CVR + why + how → risk + figure → so.
  return [
    [{ kind: "source", text: SOURCE }, plain(WHY), plain(HOW)],
    money ? [plain(RISK), money] : [plain(RISK)],
    [plain(SO)],
  ];
}

export function buildCallScript(opts: {
  firstName: string | null;
  phoneType: PhoneType | null;
  savings: SavingsView | null;
  variant?: PitchVariant;
}): CallScript {
  const { firstName, phoneType, savings, variant = PITCH_VARIANT } = opts;
  const owner = firstName ?? "ejeren";
  const pitch = buildPitch(savings, variant);
  const money = pitch.flat().find((seg) => seg.kind === "savings");
  return {
    audience: phoneType === "mobile" || phoneType === null ? "owner" : "gatekeeper",
    openerOwner:
      "Hej, det er [dit navn]. Jeg ved godt det er pisse irriterende at blive ringet op af en, man ikke har bedt om, men må jeg få 30 sekunder af din tid?",
    openerGatekeeper: `Hej, det er [dit navn]. Jeg ved godt jeg ringer helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I får hverdagen til at køre? … Er det ${owner}?`,
    pitch,
    savingsLine: money?.text ?? null,
    pain: {
      ask: "Hvad er det hos jer, der æder tid, uden at det egentlig er dét, du er der for?",
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
  };
}
