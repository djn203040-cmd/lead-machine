import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

type LeadRow = {
  id: string;
  company_name: string;
  city: string | null;
  website_need: string;
  score: number | null;
  pipeline_status: string;
};

export default async function LeadsPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  const { data } = await supabase
    .from("leads")
    .select("id, company_name, city, website_need, score, pipeline_status")
    .order("score", { ascending: false, nullsFirst: false })
    .limit(50);
  const leads = (data ?? []) as LeadRow[];

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Leads</h1>
        <span className="text-sm text-gray-500">{user?.email}</span>
      </header>

      {leads.length === 0 ? (
        <div className="rounded border border-dashed p-12 text-center text-gray-500">
          Ingen leads endnu. Kør en søgning for at finde danske virksomheder.
        </div>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2 font-medium">Virksomhed</th>
              <th className="font-medium">By</th>
              <th className="font-medium">Hjemmeside</th>
              <th className="font-medium">Score</th>
              <th className="font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.id} className="border-b">
                <td className="py-2 font-medium">{l.company_name}</td>
                <td>{l.city ?? "—"}</td>
                <td>{l.website_need}</td>
                <td>{l.score ?? "—"}</td>
                <td>{l.pipeline_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
