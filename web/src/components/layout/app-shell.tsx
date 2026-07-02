"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/today/nurture", label: "Nurture", desc: "Trend keywords" },
  { href: "/today/beta", label: "Beta", desc: "Rewards keywords" },
  { href: "/batch", label: "Batch", desc: "Video curation" },
  { href: "/merge", label: "Merge", desc: "Build finals" },
  { href: "/pool/nurture", label: "Nurture pool", desc: "Ready clips" },
  { href: "/pool/beta", label: "Beta pool", desc: "Ready finals" },
  { href: "/profiles/nurture", label: "Nurture profiles", desc: "Grow accounts" },
  { href: "/profiles/beta", label: "Beta profiles", desc: "Rewards accounts" },
  { href: "/feedback", label: "Feedback", desc: "TikTok results" },
  { href: "/sources", label: "Sources", desc: "Channel list" },
  { href: "/insights", label: "Insights", desc: "Learning data" },
  { href: "/settings", label: "Settings", desc: "Weights & niche" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="relative z-10 flex min-h-screen text-(--foreground)">
      <aside className="flex w-60 shrink-0 flex-col border-r border-(--border) bg-(--surface) px-4 py-8">
        <div className="mb-10 px-2">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-(--muted)">
            VideoScout
          </p>
          <h1 className="font-editorial mt-2 text-2xl leading-none text-(--foreground-strong)">
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
                className={`rounded-(--radius-sm) px-3 py-2.5 transition-colors ${
                  active
                    ? "bg-(--surface-muted) text-(--foreground-strong)"
                    : "text-(--muted) hover:bg-(--surface-muted) hover:text-(--foreground)"
                }`}
              >
                <span className="block text-sm font-medium">{item.label}</span>
                <span className="block text-xs leading-snug opacity-80">{item.desc}</span>
              </Link>
            );
          })}
        </nav>
        <p className="px-2 font-mono text-[0.65rem] text-(--muted)">localhost:8000</p>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col bg-(--canvas)">{children}</main>
    </div>
  );
}
