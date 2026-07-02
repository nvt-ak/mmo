"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/today", label: "Inbox", desc: "Keyword review" },
  { href: "/batch", label: "Batch", desc: "Video curation" },
  { href: "/merge", label: "Merge", desc: "Build finals" },
  { href: "/sources", label: "Sources", desc: "Channel list" },
  { href: "/insights", label: "Insights", desc: "Learning data" },
  { href: "/settings", label: "Settings", desc: "Weights & niche" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="relative z-10 flex min-h-screen text-[var(--foreground)]">
      <aside className="flex w-60 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface)] px-4 py-8">
        <div className="mb-10 px-2">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-[var(--muted)]">
            VideoScout
          </p>
          <h1 className="font-editorial mt-2 text-2xl leading-none text-[var(--foreground-strong)]">
            Operator
          </h1>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5">
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-[var(--radius-sm)] px-3 py-2.5 transition-colors ${
                  active
                    ? "bg-[var(--surface-muted)] text-[var(--foreground-strong)]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)]"
                }`}
              >
                <span className="block text-sm font-medium">{item.label}</span>
                <span className="block text-xs leading-snug opacity-80">{item.desc}</span>
              </Link>
            );
          })}
        </nav>
        <p className="px-2 font-mono text-[0.65rem] text-[var(--muted)]">localhost:8000</p>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col bg-[var(--canvas)]">{children}</main>
    </div>
  );
}
