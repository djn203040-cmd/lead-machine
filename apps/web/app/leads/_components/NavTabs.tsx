"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/leads", label: "Leads" },
  { href: "/leads/dialer", label: "Powerdialer" },
  { href: "/leads/mail", label: "Breve" },
] as const;

// Same tabs in two skins: inline in the header on desktop, a full-width row
// under the header on mobile (the header row has no room for tabs there).
export default function NavTabs({ mobile = false }: { mobile?: boolean }) {
  const pathname = usePathname();
  return (
    <nav
      className={`items-center gap-1 rounded-xl border border-line bg-card p-1 ${
        mobile ? "flex md:hidden" : "hidden md:flex"
      }`}
    >
      {TABS.map((t) => {
        const active =
          t.href === "/leads" ? pathname === "/leads" : pathname.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`rounded-lg text-sm font-medium transition-colors ${
              mobile ? "flex-1 px-3 py-2 text-center" : "px-3 py-1.5"
            } ${active ? "bg-brand-600 text-white shadow-sm" : "text-muted hover:text-ink"}`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
