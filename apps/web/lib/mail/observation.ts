// Draft the "[konkret observation]" + "[X]" lines for one lead with Claude.
// Server-only. The draft is ALWAYS reviewed by a human before the letter is
// approved (spec §5: a wrong observation is worse than none). Requires
// ANTHROPIC_API_KEY in the web app's server env; without it the action
// returns a clear error and the reviewer writes the line by hand.

import "server-only";

import Anthropic from "@anthropic-ai/sdk";
import type { MailArm } from "./letter";

export type ObservationContext = {
  arm: MailArm;
  company_name: string;
  branche_text: string | null;
  city: string | null;
  website: string | null;
  website_need: string;
  employees: string | null;
  founded_at: string | null;
  /** lead_angles.summary_da / weaknesses_da — the private "where time leaks" notes. */
  angle_summary: string | null;
  angle_notes: string | null;
  /** lead_enrichment.website — evidence signals, quality reasons */
  website_evidence: unknown;
  /** what the caller wrote during the call, if any (arm A/B) */
  call_notes: string[];
};

export type ObservationDraft = {
  observation: string;
  focus: string;
  /** which fact in the context the observation rests on — for the reviewer */
  evidence: string;
  confidence: "høj" | "middel" | "lav";
};

const SYSTEM = `Du skriver ÉN linje til et håndskrevet brev fra Sonorous Digital til en dansk lokal virksomhed. Brevet er kort (max 650 tegn) og handler om små automatiseringer der fjerner manuelt arbejde.

Du skal levere to udfyldninger:
1) "observation" — fuldender sætningen "Jeg faldt over [Firma] og blev hængende ved ___". Det skal være ÉN konkret, tjekbar iagttagelse om netop denne virksomhed (fx "at I stadig tager bookinger over telefonen ifølge jeres side", "jeres tilbudsformular der sender til en Gmail", "at I kører tre afdelinger fra én kalender"). Max 90 tegn. Ingen ros, ingen "jeg har undersøgt jeres virksomhed", ingen generiske brancheudsagn.
2) "focus" — fuldender "Da jeg kiggede på ___" (fx "jeres booking", "jeres tilbudsflow", "måden I tager imod ordrer på"). 2–5 ord, med "jeres".

Regler:
- Brug KUN fakta fra konteksten. Hvis der ikke er en konkret iagttagelse at bygge på, så vælg det mest specifikke der ER belæg for og sæt confidence "lav" — det er bedre at anmelderen skriver linjen selv end at brevet påstår noget forkert.
- Ingen tal om besparelser, ingen priser, ingen tidsangivelser for opkald.
- Naturligt dansk, uformelt "du/I". Ingen anførselstegn i teksten.
- "evidence" er én sætning til den menneskelige anmelder om hvilket faktum i konteksten observationen hviler på.`;

const SCHEMA = {
  type: "object",
  properties: {
    observation: { type: "string" },
    focus: { type: "string" },
    evidence: { type: "string" },
    confidence: { type: "string", enum: ["høj", "middel", "lav"] },
  },
  required: ["observation", "focus", "evidence", "confidence"],
  additionalProperties: false,
} as const;

function contextText(c: ObservationContext): string {
  const lines = [
    `Arm: ${c.arm} (${c.arm === "A" ? "ringet, intet svar" : c.arm === "B" ? "talt sammen, ikke interesseret" : "kold, aldrig kontaktet"})`,
    `Virksomhed: ${c.company_name}`,
    `Branche: ${c.branche_text ?? "ukendt"}`,
    `By: ${c.city ?? "ukendt"}`,
    `Ansatte: ${c.employees ?? "ukendt"}`,
    `Stiftet: ${c.founded_at ?? "ukendt"}`,
    `Hjemmeside: ${c.website ?? "ingen"} (vurdering: ${c.website_need})`,
    c.angle_summary ? `Opsummering (intern): ${c.angle_summary}` : null,
    c.angle_notes ? `Hvor tiden siver (intern): ${c.angle_notes}` : null,
    c.website_evidence ? `Website-signaler (json): ${JSON.stringify(c.website_evidence).slice(0, 2500)}` : null,
    c.call_notes.length ? `Noter fra opkald: ${c.call_notes.join(" | ")}` : null,
  ];
  return lines.filter(Boolean).join("\n");
}

export async function draftObservation(
  ctx: ObservationContext,
): Promise<{ draft?: ObservationDraft; error?: string }> {
  if (!process.env.ANTHROPIC_API_KEY) {
    return { error: "ANTHROPIC_API_KEY mangler i web-miljøet — skriv observationen manuelt." };
  }
  const client = new Anthropic();
  try {
    const response = await client.messages.create({
      model: "claude-opus-5",
      max_tokens: 2000,
      system: SYSTEM,
      output_config: { effort: "medium", format: { type: "json_schema", schema: SCHEMA } },
      messages: [{ role: "user", content: contextText(ctx) }],
    });
    if (response.stop_reason === "refusal") {
      return { error: "Modellen afviste forespørgslen — skriv observationen manuelt." };
    }
    const text = response.content.find((b) => b.type === "text")?.text ?? "";
    const parsed = JSON.parse(text) as ObservationDraft;
    if (!parsed.observation || !parsed.focus) return { error: "Tomt udkast fra modellen." };
    return { draft: parsed };
  } catch (e) {
    if (e instanceof Anthropic.AuthenticationError) return { error: "Ugyldig ANTHROPIC_API_KEY." };
    if (e instanceof Anthropic.RateLimitError) return { error: "Rate limit — prøv igen om lidt." };
    if (e instanceof Anthropic.APIError) return { error: `Claude-fejl ${e.status}: ${e.message}` };
    return { error: e instanceof Error ? e.message : "Ukendt fejl" };
  }
}
