"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

type NavItem = { href: string; label: string; desc: string };
type NavGroup = { label: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Inbox",
    items: [
      { href: "/today/nurture", label: "Nurture", desc: "Trend keywords" },
      { href: "/today/beta", label: "Beta", desc: "Rewards keywords" },
    ],
  },
  {
    label: "Pipeline",
    items: [
      { href: "/batch", label: "Batch", desc: "Video curation" },
      { href: "/merge", label: "Merge", desc: "Build finals" },
    ],
  },
  {
    label: "Nurture",
    items: [
      { href: "/pool/nurture", label: "Pool", desc: "Ready clips" },
      { href: "/profiles/nurture", label: "Profiles", desc: "Grow accounts" },
    ],
  },
  {
    label: "Beta",
    items: [
      { href: "/pool/beta", label: "Pool", desc: "Ready finals" },
      { href: "/profiles/beta", label: "Profiles", desc: "Rewards accounts" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/feedback", label: "Feedback", desc: "TikTok results" },
      { href: "/sources", label: "Sources", desc: "Channel list" },
      { href: "/insights", label: "Insights", desc: "Learning data" },
      { href: "/settings", label: "Settings", desc: "Weights & niche" },
    ],
  },
];

function isItemActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function isGroupActive(pathname: string, group: NavGroup) {
  return group.items.some((item) => isItemActive(pathname, item.href));
}

function activeGroupLabels(pathname: string) {
  return NAV_GROUPS.filter((group) => isGroupActive(pathname, group)).map(
    (group) => group.label,
  );
}

function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      viewBox="0 0 16 16"
      aria-hidden
      className={`h-3 w-3 shrink-0 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
    >
      <path
        d="M6 4l4 4-4 4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const activeLabels = activeGroupLabels(pathname);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => {
    const active = new Set(activeLabels);
    return new Set(
      NAV_GROUPS.filter((group) => !active.has(group.label) && group.label !== "Inbox").map(
        (group) => group.label,
      ),
    );
  });

  const isGroupOpen = (label: string) =>
    activeLabels.includes(label) || !collapsedGroups.has(label);

  const toggleGroup = (label: string) => {
    setCollapsedGroups((prev) => {
      const currentlyOpen = activeLabels.includes(label) || !prev.has(label);
      const next = new Set(prev);
      if (currentlyOpen) next.add(label);
      else next.delete(label);
      return next;
    });
  };

  return (
    <div className="relative z-10 flex min-h-screen text-foreground">
      <aside className="flex w-60 shrink-0 flex-col border-r border-(--border) bg-(--surface) px-4 py-8">
        <div className="mb-10 px-2">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-(--muted)">
            VideoScout
          </p>
          <h1 className="font-editorial mt-2 text-2xl leading-none text-(--foreground-strong)">
            Operator
          </h1>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV_GROUPS.map((group) => {
            const open = isGroupOpen(group.label);
            const groupActive = isGroupActive(pathname, group);

            return (
              <div key={group.label}>
                <button
                  type="button"
                  onClick={() => toggleGroup(group.label)}
                  aria-expanded={open}
                  className={`flex w-full items-center justify-between rounded-sm px-3 py-2 text-left transition-colors ${
                    groupActive
                      ? "text-(--foreground-strong)"
                      : "text-(--muted) hover:bg-(--surface-muted) hover:text-foreground"
                  }`}
                >
                  <span className="font-mono text-[0.6rem] uppercase tracking-[0.12em]">
                    {group.label}
                  </span>
                  <Chevron open={open} />
                </button>
                {open && (
                  <div className="mt-0.5 flex flex-col gap-0.5 pb-2 pl-1">
                    {group.items.map((item) => {
                      const active = isItemActive(pathname, item.href);
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          className={`rounded-sm px-3 py-2 transition-colors ${
                            active
                              ? "bg-(--surface-muted) text-(--foreground-strong)"
                              : "text-(--muted) hover:bg-(--surface-muted) hover:text-foreground"
                          }`}
                        >
                          <span className="block text-sm font-medium">{item.label}</span>
                          <span className="block text-xs leading-snug opacity-80">{item.desc}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
        <p className="px-2 font-mono text-[0.65rem] text-(--muted)">localhost:8000</p>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col bg-background">{children}</main>
    </div>
  );
}
