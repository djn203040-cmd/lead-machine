"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/leads", label: "Leads" },
  { href: "/leads/dialer", label: "Powerdialer" },
] as const;

export default function NavTabs() {
  const pathname = usePathname();
  return (
    <nav className="hidden items-center gap-1 rounded-xl border border-line bg-card p-1 md:flex">
      {TABS.map((t) => {
        const active =
          t.href === "/leads" ? pathname === "/leads" : pathname.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              active ? "bg-brand-600 text-white shadow-sm" : "text-muted hover:text-ink"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
