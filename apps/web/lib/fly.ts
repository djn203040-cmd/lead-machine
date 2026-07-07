// On-demand worker trigger (server-only). The enrichment worker on Fly is a
// one-shot machine that stays stopped (≈$0). When a user opts leads into
// enrichment we start it via the Fly Machines API; it drains the whole queue,
// runs the compliance screen, and stops again. Starting an already-running
// machine is a harmless no-op, and the worker's drain loop picks up anything
// queued while it runs — so this is safe to call on every opt-in.
//
// Requires FLY_API_TOKEN (app-scoped) in the web app's server env. Without it
// the trigger no-ops (leads stay 'queued' for the daily backstop / next opt-in).

import "server-only";

const FLY_API = "https://api.machines.dev/v1";

type FlyMachine = { id: string; state: string };

export type TriggerResult = { ok: boolean; started?: number; detail?: string };

/** Start the worker machine(s) so the enrichment queue gets drained. */
export async function triggerEnrichmentWorker(): Promise<TriggerResult> {
  const token = process.env.FLY_API_TOKEN;
  const app = process.env.FLY_WORKER_APP || "lead-machine-worker";
  if (!token) return { ok: false, detail: "FLY_API_TOKEN not set" };

  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  try {
    const listRes = await fetch(`${FLY_API}/apps/${app}/machines`, { headers, cache: "no-store" });
    if (!listRes.ok) return { ok: false, detail: `list ${listRes.status}` };
    const machines = (await listRes.json()) as FlyMachine[];
    if (!Array.isArray(machines) || machines.length === 0) {
      return { ok: false, detail: "no worker machine" };
    }

    // Start any machine that isn't already running (started/starting/replacing).
    const idle = machines.filter((m) => !["started", "starting", "replacing"].includes(m.state));
    if (idle.length === 0) return { ok: true, started: 0, detail: "already running" };

    let started = 0;
    for (const m of idle) {
      const res = await fetch(`${FLY_API}/apps/${app}/machines/${m.id}/start`, {
        method: "POST",
        headers,
      });
      if (res.ok) started += 1;
    }
    return { ok: started > 0, started };
  } catch (e) {
    return { ok: false, detail: e instanceof Error ? e.message : String(e) };
  }
}
