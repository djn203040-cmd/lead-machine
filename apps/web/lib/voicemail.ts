// Voicemail script ("indtal ved intet svar") — deliberately a fixed template,
// NOT AI-generated: the message is word-for-word the same on every call so it
// stays fast to speak and consistent; only the decision-maker's first name, the
// company and the one sector-typical time drain vary. Tone follows the
// sales-angle voice (Miner-led): calm, no pitch, one micro-commitment — reply
// "JA" by SMS. The prospect's SMS is their own henvendelse, so the callback
// (and a reply) is fine under Markedsføringsloven §10; the full Art. 14 notice
// is delivered on the callback, the voicemail only names the CVR source.
//
// The offer is the savings model: we find where the hours go, build the systems
// that remove them, and take 20% of what is actually saved. Never a website.

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

export function buildVoicemail(opts: {
  firstName: string | null;
  companyName: string;
  branchekode: string | null;
}): string {
  const { firstName, companyName, branchekode } = opts;
  const group = groupForCode(branchekode);
  const hook = (group && HOOK_DA[group]) || HOOK_FALLBACK;
  return [
    firstName ? `Hej ${firstName}, det er [dit navn].` : "Hej, det er [dit navn].",
    `Jeg prøvede lige at ringe til dig. Jeg fandt ${companyName} via CVR-registeret. Jeg hjælper virksomheder som jeres med ${hook} — og I betaler kun 20% af det, vi rent faktisk sparer jer. Ikke en krone op front.`,
    'Jeg sidder ikke så meget ved telefonen, så det nemmeste er, hvis du bare sender en SMS med et "JA" til det her nummer — så ringer jeg tilbage og fortæller kort, hvordan det fungerer.',
    firstName ? `Rigtig god dag, ${firstName}.` : "Rigtig god dag.",
  ].join("\n\n");
}
