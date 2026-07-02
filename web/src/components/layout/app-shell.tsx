"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/today", label: "Inbox", desc: "Review suggestions" },
  { href: "/sources", label: "Sources", desc: "YouTube channels" },
  { href: "/settings", label: "Settings", desc: "Weights & niche" },
  { href: "/insights", label: "Insights", desc: "Learning patterns" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-[var(--surface)] text-[var(--foreground)]">
      <aside className="flex w-56 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--sidebar)] px-3 py-6">
        <div className="mb-8 px-3">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--muted)]">
            VideoScout
          </p>
          <h1 className="mt-1 text-lg font-semibold text-white">Keyword Inbox</h1>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-lg px-3 py-2.5 transition-colors ${
                  active
                    ? "bg-[var(--accent-muted)] text-white"
                    : "text-[var(--sidebar-text)] hover:bg-white/5 hover:text-white"
                }`}
              >
                <span className="block text-sm font-medium">{item.label}</span>
                <span className="block text-xs opacity-70">{item.desc}</span>
              </Link>
            );
          })}
        </nav>
        <p className="px-3 text-xs text-[var(--muted)]">API → localhost:8000</p>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">{children}</main>
    </div>
  );
}
