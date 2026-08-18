import { NextResponse, type NextRequest } from "next/server";
import { SLUG_RE, publicClient } from "@/lib/mail/public";

export const dynamic = "force-dynamic";

// Opt-out (markedsføringsloven: the recipient must be able to decline further
// addressed advertising). Suppresses the lead everywhere; idempotent.
export async function POST(req: NextRequest, { params }: { params: Promise<{ slug: string }> }) {
  const { slug: raw } = await params;
  const slug = raw.toLowerCase();
  const url = req.nextUrl.clone();
  url.pathname = `/l/${slug}`;
  url.search = "?nejtak=1";
  if (SLUG_RE.test(slug)) {
    await publicClient().rpc("mail_opt_out", { p_slug: slug });
  }
  return NextResponse.redirect(url, { status: 303 });
}
