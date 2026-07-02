"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { BatchVideoAsset, VideoReviewStatus } from "@/lib/api/types";

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
      <header className="border-b border-[var(--border)] bg-white px-8 py-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900">Daily Batch</h1>
            <p className="mt-1 text-sm text-zinc-500">
              Keep videos for merge · Skip to exclude
            </p>
          </div>
          {data && (
            <dl className="flex gap-4 text-sm">
              <div>
                <dt className="text-zinc-400">Pending</dt>
                <dd className="font-semibold text-amber-600">{data.pending_count}</dd>
              </div>
              <div>
                <dt className="text-zinc-400">Kept</dt>
                <dd className="font-semibold text-emerald-600">{data.in_pool_count}</dd>
              </div>
              <div>
                <dt className="text-zinc-400">Skipped</dt>
                <dd className="font-semibold text-zinc-600">{data.skipped_count}</dd>
              </div>
            </dl>
          )}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {TABS.map((tab) => (
            <button
              key={tab.status}
              type="button"
              onClick={() => {
                setStatus(tab.status);
                setSelected(new Set());
              }}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                status === tab.status
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
          {isFetching && !isLoading && (
            <span className="text-xs text-zinc-400">Refreshing…</span>
          )}
        </div>

        {canBulkAct && (
          <div className="mt-4 flex flex-wrap items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3">
            <span className="text-sm text-zinc-600">{selectedIds.length} selected</span>
            <button
              type="button"
              onClick={() => bulkMutation.mutate({ ids: selectedIds, action: "keep" })}
              disabled={bulkMutation.isPending}
              className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              Keep all
            </button>
            <button
              type="button"
              onClick={() => bulkMutation.mutate({ ids: selectedIds, action: "skip" })}
              disabled={bulkMutation.isPending}
              className="rounded-lg bg-zinc-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
            >
              Skip all
            </button>
          </div>
        )}
      </header>

      <div className="flex-1 px-8 py-6">
        {isLoading && <p className="text-sm text-zinc-500">Loading videos…</p>}
        {isError && <p className="text-sm text-red-600">{(error as Error).message}</p>}

        {!isLoading && items.length === 0 && (
          <div className="rounded-xl border border-dashed border-zinc-300 bg-white px-6 py-12 text-center">
            <p className="text-sm font-medium text-zinc-700">No videos in this tab</p>
            <p className="mt-1 text-sm text-zinc-500">
              {status === "pending"
                ? "Downloads appear here after keyword cascade completes."
                : "Review pending videos to move them here."}
            </p>
          </div>
        )}

        {items.length > 0 && status === "pending" && (
          <label className="mb-4 flex items-center gap-2 text-sm text-zinc-600">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              className="rounded border-zinc-300"
            />
            Select all
          </label>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((video) => (
            <VideoCard
              key={video.id}
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
  selectable,
  selected,
  onToggle,
  onKeep,
  onSkip,
  busy,
}: {
  video: BatchVideoAsset;
  selectable: boolean;
  selected: boolean;
  onToggle: () => void;
  onKeep: () => void;
  onSkip: () => void;
  busy: boolean;
}) {
  return (
    <article className="overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
      <div className="relative aspect-video bg-zinc-100">
        {video.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-zinc-400">
            No thumbnail
          </div>
        )}
        {selectable && (
          <label className="absolute left-2 top-2 rounded bg-black/50 p-1">
            <input
              type="checkbox"
              checked={selected}
              onChange={onToggle}
              className="rounded"
            />
          </label>
        )}
      </div>
      <div className="space-y-2 p-4">
        <h2 className="line-clamp-2 text-sm font-semibold text-zinc-900">{video.title}</h2>
        <p className="text-xs text-zinc-500">
          {video.channel_name ?? "Unknown channel"}
          {video.keyword ? ` · ${video.keyword}` : ""}
        </p>
        <p className="text-xs text-zinc-400">
          {formatViews(video.view_count)} views · {formatDuration(video.duration_sec)}
        </p>
        {selectable && (
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onKeep}
              disabled={busy}
              className="flex-1 rounded-lg bg-emerald-600 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              Keep
            </button>
            <button
              type="button"
              onClick={onSkip}
              disabled={busy}
              className="flex-1 rounded-lg border border-zinc-300 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
            >
              Skip
            </button>
          </div>
        )}
        <a
          href={video.youtube_url}
          target="_blank"
          rel="noreferrer"
          className="block text-xs text-indigo-600 hover:underline"
        >
          Open on YouTube
        </a>
      </div>
    </article>
  );
}
