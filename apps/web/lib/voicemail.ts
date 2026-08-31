// Voicemail script ("indtal ved intet svar") — deliberately a fixed template,
// NOT AI-generated: the message is word-for-word the same on every call so it
// stays fast to speak and consistent; only the decision-maker's first name, the
// company, the savings band and the one sector-typical time drain vary. Since
// script v8.1 the voicemail is a mini version of the opener: the lead's own
// number first, then "30 dage på at kigge med" and pay-when-it-works — same
// voice, so a callback lands in a familiar pitch. One micro-commitment stays:
// reply "JA" by SMS. The prospect's SMS is their own henvendelse, so the
// callback (and a reply) is fine under Markedsføringsloven §10; the full
// Art. 14 notice is delivered on the callback, the voicemail only names the
// CVR source.

import { type BranchekodeGroup, groupForCode } from "./branchekoder";
import type { DecisionMaker } from "./enrichment";

// Branche group → the spoken hook, completing
// "… hjælper virksomheder som jeres med {hook}".
const HOOK_DA: Record<BranchekodeGroup, string> = {
  food_drink: "at få bestillinger, vagtplaner og bestik-arbejdet ud af telefonen",
  beauty_wellness: "at få booking, afbud og påmindelser til at køre af sig selv",
  health: "at få tidsbestilling, afbud og papirarbejde til at køre af sig selv",
  trades: "at få tilbud, timesedler og opfølgning ud af aftentimerne",
  cleaning: "at få vagtplaner, timesedler og fakturering til at køre af sig selv",
  auto: "at få værkstedsbooking og kundeopfølgning til at køre af sig selv",
  transport: "at få planlægning, fragtbreve og afregning ud af papirbunken",
  retail: "at få lager, genbestilling og kundeopfølgning til at køre af sig selv",
  professional: "at få sagsstyring, timeregistrering og fakturering til at køre af sig selv",
  finance: "at få papirarbejdet og opfølgningen til at køre af sig selv",
  realestate: "at få fremvisninger, dokumenter og opfølgning til at køre af sig selv",
  it_media: "at få projektstyring, timer og fakturering til at køre af sig selv",
  education: "at få tilmeldinger, betalinger og holdplaner til at køre af sig selv",
  hospitality: "at få bookinger, vagtplaner og gæsteopfølgning til at køre af sig selv",
  leisure: "at få medlemsadministration og betalinger til at køre af sig selv",
  business_services: "at få planlægning, timesedler og fakturering til at køre af sig selv",
};

const HOOK_FALLBACK = "at få det manuelle arbejde og papirarbejdet ud af hverdagen";

/** First name to address: prefer owner/director roles, else the first person listed. */
export function voicemailFirstName(decisionMakers: DecisionMaker[]): string | null {
  const preferred = decisionMakers.find((dm) =>
    /indehaver|ejer|direktør|adm/i.test(dm.role ?? ""),
  );
  const name = (preferred ?? decisionMakers[0])?.name?.trim();
  return name ? name.split(/\s+/)[0] : null;
}

// Spoken amounts, same format as the call script: "120.000".
const NUM = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 0 });
const spoken = (n: number) => NUM.format(n);

export function buildVoicemail(opts: {
  firstName: string | null;
  companyName: string;
  branchekode: string | null;
  /** Same band the opener quotes: calculated, else the size-aware fallback. */
  band: { low: number; high: number };
}): string {
  const { firstName, companyName, branchekode, band } = opts;
  const group = groupForCode(branchekode);
  const hook = (group && HOOK_DA[group]) || HOOK_FALLBACK;
  return [
    firstName ? `Hej ${firstName}, det er [dit navn].` : "Hej, det er [dit navn].",
    `Jeg prøvede lige at ringe — jeg fandt ${companyName} via CVR-registeret. Jeg har selv en virksomhed, og jeg tror, jeg kan spare din for mellem ${spoken(band.low)} og ${spoken(band.high)} kroner om året — typisk ved ${hook}. Jeg skal bare bruge 30 dage på at kigge med først, og du betaler først, når vi har vist, at det virker.`,
    'Jeg sidder ikke så meget ved telefonen, så det nemmeste er, hvis du bare sender en SMS med et "JA" til det her nummer — så ringer jeg tilbage.',
    firstName ? `Rigtig god dag, ${firstName}.` : "Rigtig god dag.",
  ].join("\n\n");
}
