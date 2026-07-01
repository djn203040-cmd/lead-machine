import Link from "next/link";
import { cvrCredsFromEnv } from "@/lib/cvr/client";
import DiscoverForm from "./_components/DiscoverForm";

export const metadata = { title: "Find virksomheder" };

export default function NewSearchPage() {
  const configured = cvrCredsFromEnv() !== null;

  return (
    <div className="mx-auto max-w-2xl">
      <Link
        href="/leads"
        className="inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-brand-700"
      >
        ← Tilbage til leads
      </Link>
      <h1 className="mb-1 mt-3 text-3xl font-semibold tracking-tight text-ink">
        Find virksomheder
      </h1>
      <p className="mb-6 text-sm text-muted">
        Vælg en eller flere brancher og et område — søg på by, kommune eller
        region. Reklamebeskyttede og inaktive virksomheder frasorteres
        automatisk. Nye virksomheder uden hjemmeside markeres som de bedste leads.
      </p>

      {!configured && (
        <div className="mb-6 rounded-xl border border-amber-fg/30 bg-amber-bg p-4 text-sm text-amber-fg">
          <span className="font-semibold">CVR-adgang mangler.</span> Tilføj{" "}
          <code className="rounded bg-card/60 px-1 font-mono">CVR_ES_USER</code> og{" "}
          <code className="rounded bg-card/60 px-1 font-mono">CVR_ES_PASSWORD</code> i miljøet for
          at søge. Gratis login fås ved at skrive til{" "}
          <code className="rounded bg-card/60 px-1 font-mono">cvrselvbetjening@erst.dk</code>.
        </div>
      )}

      <div className="card card-pad">
        <DiscoverForm />
      </div>
    </div>
  );
}
