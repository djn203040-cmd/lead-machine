import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Public surfaces (no session): login/auth, the direct-mail landing pages
// (/l/<slug>, its opt-out) and the root-level handwritten short URLs
// (/<slug> → app/[slug]/route.ts, which 404s anything that isn't a letter).
// Known app roots are excluded so /leads etc. still require a session.
const APP_ROOTS = new Set(["leads", "login", "auth", "api", "l", "go"]);
export function isPublicPath(pathname: string): boolean {
  if (pathname.startsWith("/login") || pathname.startsWith("/auth")) return true;
  if (pathname.startsWith("/l/")) return true;
  const m = pathname.match(/^\/([a-z0-9]{2,32})\/?$/i);
  return Boolean(m && !APP_ROOTS.has(m[1].toLowerCase()));
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  // Missing env at runtime would make createServerClient throw, which surfaces
  // as a site-wide MIDDLEWARE_INVOCATION_FAILED 500. Fail soft instead: log
  // once and let the request through so the misconfiguration is diagnosable
  // (the page-level client will still surface a clear error). Set both vars in
  // the host's env (e.g. Vercel project settings) and redeploy.
  if (!supabaseUrl || !supabaseAnonKey) {
    console.error(
      "[middleware] Missing NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY — skipping auth refresh.",
    );
    return supabaseResponse;
  }

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(
          cookiesToSet: { name: string; value: string; options: CookieOptions }[],
        ) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value),
          );
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // IMPORTANT: do not run code between createServerClient and getUser().
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user && !isPublicPath(request.nextUrl.pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  return supabaseResponse;
}
