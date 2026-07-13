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
  const selectable = status === "pending";

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
  const canBulkAct = selectable && selectedIds.length > 0;

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
        <p className="border-b border-(--border) px-8 py-2 font-mono text-xs text-(--muted)">
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

      <div className="flex-1 overflow-auto px-8 py-6">
        {isLoading && <p className="text-sm text-(--muted)">Loading videos</p>}
        {isError && (
          <div className="surface-card bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
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

        {items.length > 0 && (
          <div className="data-panel overflow-hidden">
            <table className="data-table w-full min-w-0 border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-(--border) bg-(--surface-muted) text-xs uppercase tracking-wider text-(--muted)">
                  {selectable && (
                    <th className="w-10 px-4 py-3">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleAll}
                        aria-label="Select all"
                      />
                    </th>
                  )}
                  <th className="w-16 px-4 py-3 font-medium">Preview</th>
                  <th className="px-4 py-3 font-medium">Title</th>
                  <th className="px-4 py-3 font-medium">Keyword</th>
                  <th className="px-4 py-3 font-medium">Channel</th>
                  <th className="px-4 py-3 font-medium">Views</th>
                  <th className="px-4 py-3 font-medium">Duration</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((video, index) => (
                  <VideoRow
                    key={video.id}
                    video={video}
                    index={index}
                    selectable={selectable}
                    selected={selected.has(video.id)}
                    onToggle={() => toggleOne(video.id)}
                    onKeep={() => reviewMutation.mutate({ id: video.id, action: "keep" })}
                    onSkip={() => reviewMutation.mutate({ id: video.id, action: "skip" })}
                    busy={reviewMutation.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.total > items.length && (
          <p className="mt-4 font-mono text-xs text-(--muted)">
            Showing {items.length} of {data.total}
          </p>
        )}
      </div>
    </div>
  );
}

function VideoRow({
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
    <tr
      className="border-b border-(--border-subtle) last:border-b-0"
      style={{ ["--stagger-index" as string]: index }}
    >
      {selectable && (
        <td className="px-4 py-3.5">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggle}
            aria-label={`Select ${video.title}`}
          />
        </td>
      )}
      <td className="px-4 py-3.5">
        <div className="h-10 w-16 overflow-hidden rounded-(--radius-sm) bg-(--surface-muted)">
          {video.thumbnail_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={video.thumbnail_url}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-[0.6rem] text-(--muted)">
              —
            </div>
          )}
        </div>
      </td>
      <td className="max-w-xs px-4 py-3.5 font-medium text-(--foreground-strong)">
        <span className="line-clamp-2">{video.title}</span>
      </td>
      <td className="px-4 py-3.5">
        {video.keyword ? (
          <span className="tag-pill tag-blue">{video.keyword}</span>
        ) : (
          <span className="text-(--muted)">—</span>
        )}
      </td>
      <td className="max-w-[10rem] truncate px-4 py-3.5 text-(--muted)">
        {video.channel_name ?? "Unknown"}
      </td>
      <td className="px-4 py-3.5 font-mono text-xs">{formatViews(video.view_count)}</td>
      <td className="px-4 py-3.5 font-mono text-xs">{formatDuration(video.duration_sec)}</td>
      <td className="px-4 py-3.5">
        <div className="flex flex-wrap items-center gap-1.5">
          {selectable && (
            <>
              <button
                type="button"
                onClick={onKeep}
                disabled={busy}
                className="btn btn-primary px-2 py-1 text-xs"
              >
                Keep
              </button>
              <button
                type="button"
                onClick={onSkip}
                disabled={busy}
                className="btn btn-secondary px-2 py-1 text-xs"
              >
                Skip
              </button>
            </>
          )}
          <a
            href={video.youtube_url}
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost px-2 py-1 text-xs text-(--pastel-blue-text)"
          >
            YouTube
          </a>
        </div>
      </td>
    </tr>
  );
}
