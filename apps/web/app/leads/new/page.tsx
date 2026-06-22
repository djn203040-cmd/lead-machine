import Link from "next/link";
import { cvrCredsFromEnv } from "@/lib/cvr/client";
import DiscoverForm from "./_components/DiscoverForm";

export const metadata = { title: "Find virksomheder" };

export default function NewSearchPage() {
  const configured = cvrCredsFromEnv() !== null;

  return (
    <div className="max-w-xl">
      <Link href="/leads" className="text-sm text-gray-500 hover:underline">
        ← Tilbage til leads
      </Link>
      <h1 className="mb-1 mt-2 text-2xl font-semibold">Find virksomheder</h1>
      <p className="mb-6 text-sm text-gray-600">
        Søg i CVR efter en branche i et eller flere postnumre. Reklamebeskyttede
        og inaktive virksomheder frasorteres automatisk. Nye virksomheder uden
        hjemmeside markeres som de bedste leads.
      </p>

      {!configured && (
        <div className="mb-6 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <span className="font-medium">CVR-adgang mangler.</span> Tilføj{" "}
          <code>CVR_ES_USER</code> og <code>CVR_ES_PASSWORD</code> i miljøet for at
          søge. Gratis login fås ved at skrive til{" "}
          <code>cvrselvbetjening@erst.dk</code>.
        </div>
      )}

      <DiscoverForm />
    </div>
  );
}
