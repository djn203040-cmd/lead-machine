// Voicemail script ("indtal ved intet svar") — deliberately a fixed template,
// NOT AI-generated: the message is word-for-word the same on every call so it
// stays fast to speak and consistent; only the decision-maker's first name,
// the company and the one observed reason vary. Tone follows the sales-angle
// voice (Miner-led): calm, no pitch, one micro-commitment — reply "JA" by SMS.
// The prospect's SMS is their own henvendelse, so the callback (and a reply)
// is fine under Markedsføringsloven §10; the full Art. 14 notice is delivered
// on the callback, the voicemail only names the CVR source.

import type { DecisionMaker } from "./enrichment";

// website_need → the spoken reason, completing "… og kunne se, at {reason}".
const REASON_DA: Record<string, string> = {
  none: "I ikke rigtig har en hjemmeside endnu",
  dead: "jeres hjemmeside-domæne ikke virker længere",
  parked: "jeres domæne bare står parkeret uden en rigtig hjemmeside",
  facebook_only: "I kun har en Facebook-side — ikke jeres egen hjemmeside",
  not_independent: "I ikke har jeres egen hjemmeside, kun en side på en fælles platform",
  bad: "jeres nuværende hjemmeside godt kunne trænge til en opgradering",
  outdated: "jeres nuværende hjemmeside trænger til en opdatering",
};

const REASON_FALLBACK = "der er mere at hente i jeres online-tilstedeværelse";

/** First name to address: prefer owner/director roles, else the first person listed. */
export function voicemailFirstName(decisionMakers: DecisionMaker[]): string | null {
  const preferred = decisionMakers.find((dm) =>
    /indehaver|ejer|direktør|adm/i.test(dm.role ?? ""),
  );
  const name = (preferred ?? decisionMakers[0])?.name?.trim();
  return name ? name.split(/\s+/)[0] : null;
}

export function buildVoicemail(opts: {
  firstName: string | null;
  companyName: string;
  websiteNeed: string;
}): string {
  const { firstName, companyName, websiteNeed } = opts;
  const reason = REASON_DA[websiteNeed] ?? REASON_FALLBACK;
  return [
    firstName ? `Hej ${firstName}, det er [dit navn].` : "Hej, det er [dit navn].",
    `Jeg prøvede lige at ringe til dig. Jeg fandt ${companyName} via CVR-registeret og kunne se, at ${reason} — så jeg har allerede bygget en færdig demo af en ny hjemmeside til jer. Den er helt gratis at se.`,
    'Jeg sidder ikke så meget ved telefonen, så det nemmeste er, hvis du bare sender en SMS med et "JA" til det her nummer — så ringer jeg tilbage og viser dig den.',
    firstName ? `Rigtig god dag, ${firstName}.` : "Rigtig god dag.",
  ].join("\n\n");
}
