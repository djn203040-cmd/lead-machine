import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { groupForCode } from "@/lib/branchekoder";
import { type LandingPayload, SLUG_RE, embedUrl, publicClient } from "@/lib/mail/public";
import { SENDER_COMPANY, SENDER_EMAIL, SENDER_NAME, SENDER_PHONE } from "@/lib/mail/letter";

export const dynamic = "force-dynamic";

// Per-recipient landing page. Public. Shows THEIR company name (a generic
// page destroys what the letter just bought), one specific finding, an
// industry-specific demo (Loom/YouTube per letter, else the sector's typical
// time sinks), one CTA, and the legally required opt-out.

const SECTOR_DA: Record<string, { levers: string[]; demo: string }> = {
  trades: {
    levers: ["Tilbud der skrives fra bunden hver gang", "Timesedler samlet op om aftenen", "Fakturaer der sendes en uge for sent"],
    demo: "Et tilbud der bliver til en ordre, en timeseddel og en faktura — uden at nogen taster det ind tre gange.",
  },
  beauty: {
    levers: ["Bookinger over telefonen midt i en behandling", "Udeblivelser uden påmindelse", "Genbestilling der glemmes"],
    demo: "Booking, SMS-påmindelse og genbooking der kører af sig selv, så telefonen kan ligge.",
  },
  hospitality: {
    levers: ["Bordbestillinger på telefon og Facebook samtidig", "Vagtplaner i en gruppechat", "Gæster der aldrig hører fra jer igen"],
    demo: "Bordbestilling, vagtplan og gæsteopfølgning på ét sted — uden ekstra hænder.",
  },
  health: {
    levers: ["Aflysninger der ikke bliver fyldt op", "Journal- og forsikringspapirer i hånden", "Genbestilling der glemmes"],
    demo: "Ventelisten fylder selv en aflyst tid, og genbestillingen sender selv en SMS.",
  },
  auto: {
    levers: ["Tilbud på værkstedstimer i hånden", "Reservedele bestilt én ad gangen", "Kunder der ikke mindes om syn"],
    demo: "Synspåmindelse, tilbud og delebestilling der kører uden at nogen skal huske det.",
  },
  retail: {
    levers: ["Lager talt i hånden", "Bestillinger på mail, telefon og Instagram", "Ingen genkøbs-opfølgning"],
    demo: "Ordrer fra alle kanaler samlet ét sted, lageret opdaterer sig selv.",
  },
  business_services: {
    levers: ["Planlægning i regneark", "Timesedler tastet ind i hånden", "Fakturering en gang om måneden i ét ryk"],
    demo: "Fra opgave til timeseddel til faktura — uden genindtastning.",
  },
};
const SECTOR_FALLBACK = {
  levers: ["Ting der tastes ind to gange", "Påmindelser nogen skal huske", "Papirarbejde der samler sig til om aftenen"],
  demo: "Små automatiseringer der fjerner 5–10 timers manuelt arbejde om ugen — typisk uden at skifte systemer.",
};

async function load(slug: string): Promise<LandingPayload | null> {
  if (!SLUG_RE.test(slug)) return null;
  const { data } = await publicClient().rpc("mail_landing", { p_slug: slug });
  return (data as LandingPayload | null) ?? null;
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const p = await load(slug.toLowerCase());
  return {
    title: p ? `${p.company_name} · ${SENDER_COMPANY}` : SENDER_COMPANY,
    robots: { index: false, follow: false },
  };
}

export default async function LandingPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { slug: raw } = await params;
  const sp = await searchParams;
  const slug = raw.toLowerCase();
  const p = await load(slug);
  if (!p) notFound();

  const justOptedOut = sp.nejtak === "1";
  const sector = SECTOR_DA[groupForCode(p.branchekode) ?? ""] ?? SECTOR_FALLBACK;
  const video = embedUrl(p.landing_video_url);
  const bookingUrl = process.env.NEXT_PUBLIC_MAIL_BOOKING_URL;
  // Same contact details as the letter itself (env-overridable defaults).
  const phone = SENDER_PHONE;
  const email = SENDER_EMAIL;
  const headline =
    p.landing_headline ??
    (p.arm === "B"
      ? `Det jeg fandt hos ${p.company_name} — brug det som du vil`
      : `En side lavet til ${p.company_name}`);

  return (
    <main className="mx-auto max-w-2xl px-6 py-14">
      <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{SENDER_COMPANY}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink">{headline}</h1>
      <p className="mt-3 text-base text-muted">
        {p.first_name ? `Hej ${p.first_name}. ` : ""}
        Ingen tilmelding, ingen formular. Bare det jeg lovede i brevet.
      </p>

      {(p.observation_text || p.focus_text) && (
        <section className="card card-pad mt-8">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-faint">Det jeg blev hængende ved</h2>
          {p.observation_text && <p className="mt-2 text-lg text-ink">{p.observation_text}</p>}
          {p.focus_text && (
            <p className="mt-2 text-sm text-muted">
              Da jeg kiggede på {p.focus_text}, kunne jeg se to steder hvor der ligger manuelt arbejde, som kunne køre af sig selv.
            </p>
          )}
        </section>
      )}

      <section className="card card-pad mt-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-faint">Sådan ser det ud i praksis</h2>
        {video ? (
          <div className="mt-3 aspect-video overflow-hidden rounded-xl border border-line">
            <iframe src={video} title="Demo" className="h-full w-full" allow="autoplay; fullscreen; picture-in-picture" allowFullScreen />
          </div>
        ) : (
          <>
            <p className="mt-2 text-sm text-ink">{sector.demo}</p>
            <ul className="mt-3 space-y-1.5 text-sm text-muted">
              {sector.levers.map((l) => (
                <li key={l} className="flex gap-2">
                  <span className="text-brand-700">→</span>
                  {l}
                </li>
              ))}
            </ul>
          </>
        )}
        <p className="mt-4 text-sm text-muted">
          Modellen er enkel: vi følger jeres hverdag i 30 dage, bygger det der fjerner arbejdet, og tager 20 % af ét års
          dokumenteret besparelse — betalt én gang, kun hvis det virker. Finder vi ikke noget, koster det ikke en krone.
        </p>
      </section>

      <section className="mt-6 rounded-2xl bg-gradient-to-b from-brand-700 to-brand p-6 text-white shadow-sm">
        <h2 className="text-lg font-semibold">10 minutter, så ved du om det er noget for jer.</h2>
        <p className="mt-1 text-sm text-white/80">Ring, skriv eller book — det du foretrækker.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {bookingUrl && (
            <a href={bookingUrl} className="btn bg-white text-brand-800 hover:bg-white/90">
              Book 10 minutter
            </a>
          )}
          {phone && (
            <a href={`tel:${phone.replace(/[^\d+]/g, "")}`} className="btn border border-white/40 text-white hover:bg-white/10">
              Ring {phone}
            </a>
          )}
          {phone && (
            <a href={`sms:${phone.replace(/[^\d+]/g, "")}?&body=Hej%20${encodeURIComponent(SENDER_NAME)}%2C%20det%20er%20${encodeURIComponent(p.company_name)}`} className="btn border border-white/40 text-white hover:bg-white/10">
              Send en SMS
            </a>
          )}
          {email && (
            <a href={`mailto:${email}?subject=${encodeURIComponent(p.company_name)}`} className="btn border border-white/40 text-white hover:bg-white/10">
              Skriv en mail
            </a>
          )}
        </div>
        <p className="mt-3 text-xs text-white/70">— {SENDER_NAME}, {SENDER_COMPANY}</p>
      </section>

      <footer className="mt-10 border-t border-line pt-4 text-xs text-faint">
        <p>
          Brevet blev sendt til {p.company_name} på baggrund af offentlige oplysninger fra CVR-registeret. Vil du ikke
          modtage flere henvendelser fra {SENDER_COMPANY}?
        </p>
        {p.opted_out || justOptedOut ? (
          <p className="mt-2 text-teal-fg">Noteret — I hører ikke mere fra os. Tak.</p>
        ) : (
          <form method="post" action={`/l/${p.slug}/nej-tak`} className="mt-2">
            <button type="submit" className="underline hover:text-ink">Nej tak til flere henvendelser</button>
          </form>
        )}
        <p className="mt-3">
          {SENDER_COMPANY} · Behandling af oplysninger sker efter databeskyttelsesforordningens art. 6(1)(f) — kontakt os for
          indsigt eller sletning.
        </p>
      </footer>
    </main>
  );
}
