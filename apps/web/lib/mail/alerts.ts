// "Scan webhook → instant alert to phone" (spec §7.7). Best-effort POST to a
// webhook (ntfy.sh topic, Slack incoming webhook, Pushover-compatible relay …)
// with a one-line message. Never throws; missing env = no-op.

import "server-only";

export async function notifyScan(payload: {
  slug: string;
  company_name: string;
  arm: string;
  device: string;
  first: boolean;
}): Promise<void> {
  const url = process.env.MAIL_SCAN_WEBHOOK_URL;
  if (!url) return;
  const text = `${payload.first ? "🔥 FØRSTE SCAN" : "Scan"} — ${payload.company_name} (arm ${payload.arm}, ${payload.device}) åbnede /${payload.slug}`;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json", Title: "Brev scannet" },
      body: JSON.stringify({ text, message: text, ...payload }),
      signal: AbortSignal.timeout(4000),
    });
  } catch {
    // alerting is best-effort — the scan is already logged
  }
}
