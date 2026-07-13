"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { ProfileStage } from "@/lib/api/types";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatPill } from "@/components/shared/stat-pill";

function formatDuration(sec?: number) {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface PoolPageProps {
  poolType: ProfileStage;
}

export function PoolPage({ poolType }: PoolPageProps) {
  const title = poolType === "nurture" ? "Nurture pool" : "Beta pool";
  const description =
    poolType === "nurture"
      ? "Ready clips for nurture accounts — single assets or merged finals."
      : "Ready finals and clips for Creator Rewards beta accounts.";

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["pools", poolType],
    queryFn: () => api.listPoolMedia(poolType),
    refetchInterval: 30_000,
  });

  const items = data?.items ?? [];

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title={title}
        description={description}
        toolbar={
          <StatPill label="Ready" value={String(items.length)} />
        }
      />

      <div className="flex-1 overflow-auto px-8 py-6">
        {isLoading && <p className="text-sm text-(--muted)">Loading pool</p>}
        {isError && (
          <div className="surface-card border-(--pastel-red-bg) bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
            {(error as Error).message}
          </div>
        )}
        {!isLoading && !isError && items.length === 0 && (
          <EmptyState
            title="Pool empty"
            description="Approve keywords, download, batch Keep — assets appear here when ready."
          />
        )}
        {items.length > 0 && (
          <div className="data-panel overflow-hidden">
            <table className="data-table w-full min-w-0 border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-(--border) bg-(--surface-muted) text-xs uppercase tracking-wider text-(--muted)">
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Kind</th>
                  <th className="px-4 py-3 font-medium">Keyword</th>
                  <th className="px-4 py-3 font-medium">Duration</th>
                  <th className="px-4 py-3 font-medium">Path</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr
                    key={`${item.kind}-${item.id}`}
                    className="border-b border-(--border-subtle) last:border-b-0"
                    style={{ ["--stagger-index" as string]: index }}
                  >
                    <td className="px-4 py-3.5 font-medium text-(--foreground-strong)">
                      {item.title}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-(--muted)">
                      {item.kind}
                    </td>
                    <td className="px-4 py-3.5 text-(--muted)">{item.keyword ?? "—"}</td>
                    <td className="px-4 py-3.5 font-mono text-xs">
                      {formatDuration(item.duration_sec)}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3.5 font-mono text-xs text-(--muted)">
                      {item.file_path}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
