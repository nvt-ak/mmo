"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { BatchVideoAsset, VideoReviewStatus } from "@/lib/api/types";
import { ActionBar } from "@/components/shared/action-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatPill } from "@/components/shared/stat-pill";
import { TabBar } from "@/components/shared/tab-bar";

const TABS: { status: VideoReviewStatus; label: string }[] = [
  { status: "pending", label: "Pending" },
  { status: "in_pool", label: "Kept" },
  { status: "skipped", label: "Skipped" },
];

function formatDuration(sec?: number) {
  if (!sec) return "—";
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatViews(n?: number) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function BatchPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<VideoReviewStatus>("pending");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const queryKey = ["batch", status];

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey,
    queryFn: () => api.listBatchVideos({ review_status: status, limit: 100 }),
    refetchInterval: 30_000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["batch"] });

  const reviewMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "keep" | "skip" }) =>
      api.reviewVideo(id, action),
    onSuccess: () => {
      setSelected(new Set());
      invalidate();
    },
  });

  const bulkMutation = useMutation({
    mutationFn: ({ ids, action }: { ids: string[]; action: "keep" | "skip" }) =>
      api.bulkReviewVideos(ids, action),
    onSuccess: () => {
      setSelected(new Set());
      invalidate();
    },
  });

  const items = data?.items ?? [];
  const allSelected = items.length > 0 && selected.size === items.length;

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(items.map((i) => i.id)));
  };

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedIds = useMemo(() => Array.from(selected), [selected]);
  const canBulkAct = status === "pending" && selectedIds.length > 0;

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Daily batch"
        description="Keep clips for merge. Skip the rest."
        meta={
          data ? (
            <div className="flex flex-wrap gap-6">
              <StatPill label="Pending" value={data.pending_count} tone="yellow" />
              <StatPill label="Kept" value={data.in_pool_count} tone="green" />
              <StatPill label="Skipped" value={data.skipped_count} tone="neutral" />
            </div>
          ) : null
        }
        tabs={
          <TabBar
            tabs={TABS.map((t) => ({ value: t.status, label: t.label }))}
            value={status}
            onChange={(next) => {
              setStatus(next);
              setSelected(new Set());
            }}
          />
        }
      />

      {isFetching && !isLoading && (
        <p className="border-b border-[var(--border)] px-8 py-2 font-mono text-xs text-[var(--muted)]">
          Syncing batch
        </p>
      )}

      {canBulkAct && (
        <ActionBar count={selectedIds.length}>
          <button
            type="button"
            onClick={() => bulkMutation.mutate({ ids: selectedIds, action: "keep" })}
            disabled={bulkMutation.isPending}
            className="btn btn-primary"
          >
            Keep all
          </button>
          <button
            type="button"
            onClick={() => bulkMutation.mutate({ ids: selectedIds, action: "skip" })}
            disabled={bulkMutation.isPending}
            className="btn btn-secondary"
          >
            Skip all
          </button>
        </ActionBar>
      )}

      <div className="flex-1 px-8 py-6">
        {isLoading && <p className="text-sm text-[var(--muted)]">Loading videos</p>}
        {isError && (
          <div className="surface-card bg-[var(--pastel-red-bg)] px-4 py-3 text-sm text-[var(--pastel-red-text)]">
            {(error as Error).message}
          </div>
        )}

        {!isLoading && items.length === 0 && (
          <EmptyState
            title="Nothing here yet"
            description={
              status === "pending"
                ? "Downloaded videos land here after keyword cascade completes."
                : "Move pending videos with Keep or Skip to populate this tab."
            }
          />
        )}

        {items.length > 0 && status === "pending" && (
          <label className="mb-5 flex items-center gap-2 text-sm text-[var(--muted)]">
            <input type="checkbox" checked={allSelected} onChange={toggleAll} />
            Select all
          </label>
        )}

        <div className="grid gap-5 sm:grid-cols-2 2xl:grid-cols-3">
          {items.map((video, index) => (
            <VideoCard
              key={video.id}
              index={index}
              video={video}
              selectable={status === "pending"}
              selected={selected.has(video.id)}
              onToggle={() => toggleOne(video.id)}
              onKeep={() => reviewMutation.mutate({ id: video.id, action: "keep" })}
              onSkip={() => reviewMutation.mutate({ id: video.id, action: "skip" })}
              busy={reviewMutation.isPending}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function VideoCard({
  video,
  index,
  selectable,
  selected,
  onToggle,
  onKeep,
  onSkip,
  busy,
}: {
  video: BatchVideoAsset;
  index: number;
  selectable: boolean;
  selected: boolean;
  onToggle: () => void;
  onKeep: () => void;
  onSkip: () => void;
  busy: boolean;
}) {
  return (
    <article
      className="surface-card stagger-item overflow-hidden"
      style={{ ["--stagger-index" as string]: index }}
    >
      <div className="relative aspect-video bg-[var(--surface-muted)]">
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt={video.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-[var(--muted)]">
            No preview
          </div>
        )}
        {selectable && (
          <label className="absolute left-3 top-3 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface)]/95 p-1.5">
            <input type="checkbox" checked={selected} onChange={onToggle} />
          </label>
        )}
      </div>
      <div className="space-y-3 p-5">
        <h2 className="line-clamp-2 text-sm font-medium leading-snug text-[var(--foreground-strong)]">
          {video.title}
        </h2>
        <div className="flex flex-wrap gap-2">
          {video.keyword && <span className="tag-pill tag-blue">{video.keyword}</span>}
          <span className="tag-pill bg-[var(--surface-muted)] text-[var(--muted)]">
            {video.channel_name ?? "Unknown channel"}
          </span>
        </div>
        <p className="font-mono text-xs text-[var(--muted)]">
          {formatViews(video.view_count)} views · {formatDuration(video.duration_sec)}
        </p>
        {selectable && (
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onKeep} disabled={busy} className="btn btn-primary flex-1">
              Keep
            </button>
            <button
              type="button"
              onClick={onSkip}
              disabled={busy}
              className="btn btn-secondary flex-1"
            >
              Skip
            </button>
          </div>
        )}
        <a
          href={video.youtube_url}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-xs text-[var(--pastel-blue-text)] hover:underline"
        >
          Open source video
        </a>
      </div>
    </article>
  );
}
