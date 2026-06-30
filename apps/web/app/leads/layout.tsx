import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import SignOutButton from "./_components/SignOutButton";

function LogoMark() {
  return (
    <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-b from-brand-700 to-brand text-white shadow-sm">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M4 13.5 9 18l11-12"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  );
}

export default async function LeadsLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const initial = user?.email?.[0]?.toUpperCase() ?? "·";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-line/80 bg-canvas/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Link href="/leads" className="flex items-center gap-2.5">
            <LogoMark />
            <span className="text-[1.05rem] font-semibold tracking-tight text-ink">
              Lead Machine
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/leads/new" className="btn btn-primary">
              <span className="text-base leading-none">+</span> Find virksomheder
            </Link>
            <div className="hidden items-center gap-2 rounded-full border border-line bg-card py-1 pl-1 pr-3 sm:flex">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-brand-100 text-xs font-semibold text-brand-800">
                {initial}
              </span>
              <span className="max-w-[14rem] truncate text-xs text-muted">{user?.email}</span>
            </div>
            <SignOutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
