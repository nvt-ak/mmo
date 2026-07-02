"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { BatchVideoAsset, MergeJob } from "@/lib/api/types";
import { ActionBar } from "@/components/shared/action-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatPill } from "@/components/shared/stat-pill";

function formatDuration(sec?: number) {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function MergePage() {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>([]);
  const [lastJob, setLastJob] = useState<MergeJob | null>(null);

  const poolQuery = useQuery({
    queryKey: ["merge-pool"],
    queryFn: () => api.listMergePool({ limit: 100 }),
    refetchInterval: 30_000,
  });

  const finalsQuery = useQuery({
    queryKey: ["finals"],
    queryFn: () => api.listFinals(50),
    refetchInterval: 30_000,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["merge-pool"] });
    queryClient.invalidateQueries({ queryKey: ["finals"] });
  };

  const manualMutation = useMutation({
    mutationFn: (ids: [string, string]) => api.enqueueManualMerge(ids),
    onSuccess: async (data) => {
      setSelected([]);
      const job = await api.getMergeJob(data.job_id);
      setLastJob(job);
      invalidate();
    },
  });

  const randomMutation = useMutation({
    mutationFn: () => api.enqueueRandomMerge(),
    onSuccess: async (data) => {
      const job = await api.getMergeJob(data.job_id);
      setLastJob(job);
      invalidate();
    },
  });

  const items = poolQuery.data?.items ?? [];
  const finals = finalsQuery.data?.items ?? [];

  const toggle = (id: string) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const canMerge = selected.length === 2;
  const selectedPair = useMemo(
    () => (canMerge ? (selected as [string, string]) : null),
    [canMerge, selected],
  );

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Merge"
        description="Combine two kept clips into one final file under data/finals/."
        meta={
          <div className="flex flex-wrap gap-6">
            <StatPill label="Pool" value={poolQuery.data?.total ?? 0} tone="blue" />
            <StatPill label="Finals" value={finalsQuery.data?.total ?? 0} tone="green" />
          </div>
        }
        actions={
          <button
            type="button"
            onClick={() => randomMutation.mutate()}
            disabled={randomMutation.isPending || (poolQuery.data?.total ?? 0) < 2}
            className="btn btn-secondary"
          >
            Random same-keyword pair
          </button>
        }
      />

      {canMerge && selectedPair && (
        <ActionBar count={2} label="clips selected">
          <button
            type="button"
            onClick={() => manualMutation.mutate(selectedPair)}
            disabled={manualMutation.isPending}
            className="btn btn-primary"
          >
            Merge selected
          </button>
        </ActionBar>
      )}

      {lastJob && (
        <div className="border-b border-[var(--border)] bg-[var(--surface-muted)] px-8 py-3 text-sm">
          <span className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
            Last job
          </span>
          <p className="mt-1 text-[var(--foreground-strong)]">
            {lastJob.status}
            {lastJob.final_video_id ? ` · final ${lastJob.final_video_id.slice(0, 8)}` : ""}
            {lastJob.error_message ? ` · ${lastJob.error_message}` : ""}
          </p>
        </div>
      )}

      <div className="grid flex-1 gap-8 px-8 py-6 xl:grid-cols-[1.4fr_1fr]">
        <section>
          <h2 className="font-editorial text-xl text-[var(--foreground-strong)]">Merge pool</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Pick exactly two clips for manual merge.</p>

          {poolQuery.isLoading && <p className="mt-4 text-sm text-[var(--muted)]">Loading pool</p>}
          {poolQuery.isError && (
            <p className="mt-4 text-sm text-[var(--pastel-red-text)]">
              {(poolQuery.error as Error).message}
            </p>
          )}

          {!poolQuery.isLoading && items.length === 0 && (
            <div className="mt-4">
              <EmptyState
                title="Pool is empty"
                description="Keep videos on the Batch screen to make them eligible for merge."
              />
            </div>
          )}

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {items.map((video, index) => (
              <PoolCard
                key={video.id}
                video={video}
                index={index}
                selected={selected.includes(video.id)}
                onToggle={() => toggle(video.id)}
              />
            ))}
          </div>
        </section>

        <section>
          <h2 className="font-editorial text-xl text-[var(--foreground-strong)]">Final videos</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Ready for upload handoff.</p>

          {finals.length === 0 && (
            <p className="mt-4 text-sm text-[var(--muted)]">No finals yet.</p>
          )}

          <ul className="mt-4 space-y-3">
            {finals.map((final) => (
              <li key={final.id} className="surface-card p-4">
                <p className="text-sm font-medium text-[var(--foreground-strong)]">
                  {final.keyword ?? "Untitled merge"}
                </p>
                <p className="mt-1 truncate font-mono text-xs text-[var(--muted)]">
                  {final.file_path}
                </p>
                <p className="mt-2 font-mono text-xs text-[var(--muted)]">
                  {formatDuration(final.duration_sec)} ·{" "}
                  {new Date(final.created_at).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}

function PoolCard({
  video,
  index,
  selected,
  onToggle,
}: {
  video: BatchVideoAsset;
  index: number;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`surface-card stagger-item overflow-hidden text-left ${
        selected ? "ring-2 ring-[var(--foreground-strong)]" : ""
      }`}
      style={{ ["--stagger-index" as string]: index }}
    >
      <div className="relative aspect-video bg-[var(--surface-muted)]">
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={video.thumbnail_url} alt={video.title} className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-[var(--muted)]">
            No preview
          </div>
        )}
      </div>
      <div className="space-y-2 p-4">
        <p className="line-clamp-2 text-sm font-medium text-[var(--foreground-strong)]">
          {video.title}
        </p>
        {video.keyword && <span className="tag-pill tag-blue">{video.keyword}</span>}
      </div>
    </button>
  );
}
