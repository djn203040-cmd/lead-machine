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
// The Art. 14 source line ("fundet jer i CVR-registeret") is part of the
// opener on purpose — it has to be said on the first call.
// See docs/compliance/first-contact-script.md.

import type { PhoneType } from "./phone";
import type { SavingsView } from "./savings";

export type CallScript = {
  /** Who is expected to pick up — decides which opener is shown first. */
  audience: "owner" | "gatekeeper";
  /** Owner picks up (mobile). */
  openerOwner: string;
  /** Staff/reception picks up (landline / 70-number) — get to the owner first. */
  openerGatekeeper: string;
  /** Said right after they give the 30 seconds. Also the Art. 14 disclosure. */
  source: string;
  /** The pitch, one spoken sentence-group per entry. */
  pitch: string[];
  /** The savings line inside the pitch — variable, kept separate so the UI can flag it. */
  savingsLine: string;
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

// Sentence 3 of the pitch: what we can typically get back. How it is phrased
// depends on where the number came from — accounts we may quote back to them,
// a benchmark we may only call a typical range for their size.
function savingsLine(savings: SavingsView | null): string {
  if (!savings) {
    return "Hos de fleste på jeres størrelse er det et pænt beløb om året — men præcis hvor meget, er lige det, vi finder ud af.";
  }
  const band = `${spoken(savings.annualLow)} til ${spoken(savings.annualHigh)} kroner om året`;
  if (savings.basis === "accounts") {
    return `Jeg har kigget i jeres offentlige regnskab, og hos en virksomhed som jeres ligger der typisk ${band}, der kan hentes hjem.`;
  }
  return `Hos virksomheder på jeres størrelse ligger der typisk ${band}, der kan hentes hjem.`;
}

export function buildCallScript(opts: {
  firstName: string | null;
  phoneType: PhoneType | null;
  savings: SavingsView | null;
}): CallScript {
  const { firstName, phoneType, savings } = opts;
  const owner = firstName ?? "ejeren";
  const line = savingsLine(savings);
  return {
    audience: phoneType === "mobile" || phoneType === null ? "owner" : "gatekeeper",
    openerOwner:
      "Hej, det er [dit navn]. Jeg ved godt det er pisse irriterende at blive ringet op af en, man ikke har bedt om, men må jeg få 30 sekunder af din tid?",
    openerGatekeeper: `Hej, det er [dit navn]. Jeg ved godt jeg ringer helt uopfordret — hvem er den rigtige at fange, når det handler om hvordan I får hverdagen til at køre? … Er det ${owner}?`,
    source: "Jeg har fundet jer i CVR-registeret og undersøgt lidt om, hvad I laver.",
    pitch: [
      "Vi følger jeres virksomhed i 30 dage — ikke fysisk, remote — og ser helt konkret, hvor timerne og kronerne forsvinder. Derfra kigger vi på, hvad vi kan optimere i lige præcis de huller.",
      line,
      "Finder vi ikke noget, siger vi det til jer, og I betaler ikke en krone. Finder vi noget, betaler I først den første krone, når vi rent faktisk har bygget det til jer.",
      "Så med det sagt:",
    ],
    savingsLine: line,
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
