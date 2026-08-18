import { createHash } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import { notifyScan } from "@/lib/mail/alerts";
import { SLUG_RE, publicClient } from "@/lib/mail/public";

export const dynamic = "force-dynamic";

// The handwritten URL: <MAIL_PUBLIC_BASE>/<slug>. Logs the hit (device, referrer,
// hashed IP) via the anon RPC, fires the phone alert on a first real scan, and
// 302s to the personalised landing page. Unknown slug → 404 (this route is the
// root catch-all, so anything that isn't a letter must fail closed).
export async function GET(req: NextRequest, { params }: { params: Promise<{ slug: string }> }) {
  const { slug: raw } = await params;
  const slug = raw.toLowerCase();
  if (!SLUG_RE.test(slug)) return new NextResponse("Not found", { status: 404 });

  const ua = req.headers.get("user-agent");
  const referrer = req.headers.get("referer");
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "";
  const ipHash = ip ? createHash("sha256").update(ip).digest("hex").slice(0, 16) : null;

  const supabase = publicClient();
  const { data, error } = await supabase.rpc("mail_track_scan", {
    p_slug: slug,
    p_user_agent: ua,
    p_referrer: referrer,
    p_ip_hash: ipHash,
  });
  if (error || !data) return new NextResponse("Not found", { status: 404 });

  const hit = data as {
    company_name: string;
    arm: string;
    device: string;
    is_first_scan: boolean;
  };
  if (hit.device !== "bot") {
    await notifyScan({
      slug,
      company_name: hit.company_name,
      arm: hit.arm,
      device: hit.device,
      first: hit.is_first_scan,
    });
  }

  const url = req.nextUrl.clone();
  url.pathname = `/l/${slug}`;
  url.search = "";
  return NextResponse.redirect(url, { status: 302, headers: { "cache-control": "no-store" } });
}
