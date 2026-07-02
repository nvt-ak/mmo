"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api/client";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatPill } from "@/components/shared/stat-pill";

export function SourcesPage() {
  const queryClient = useQueryClient();
  const [channelInput, setChannelInput] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["channels"],
    queryFn: () => api.listChannels(),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["channels"] });

  const addMutation = useMutation({
    mutationFn: () => api.addChannel(channelInput.trim()),
    onSuccess: () => {
      setChannelInput("");
      setMessage("Channel added.");
      invalidate();
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const scanMutation = useMutation({
    mutationFn: () => api.runScan(true),
    onSuccess: (res) => setMessage(`Scan started (job ${res.job_id.slice(0, 8)})`),
    onError: (e: Error) => setMessage(e.message),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.updateChannelScan(id, enabled),
    onSuccess: invalidate,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteChannel(id),
    onSuccess: invalidate,
  });

  const channels = data?.items ?? [];
  const enabledCount = channels.filter((ch) => ch.scan_enabled).length;

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Sources"
        description="YouTube channels linked to keyword discovery and ingestion."
        meta={
          data ? (
            <div className="flex flex-wrap gap-6">
              <StatPill label="Channels" value={data.total} tone="blue" />
              <StatPill label="Scan enabled" value={enabledCount} tone="green" />
            </div>
          ) : null
        }
      />

      <div className="space-y-6 px-8 py-6">
        {message && (
          <p className="surface-card bg-[var(--surface-muted)] px-4 py-2 text-sm text-[var(--foreground)]">
            {message}
          </p>
        )}

        <section className="surface-card p-6 animate-fade-rise">
          <h2 className="font-editorial text-xl text-[var(--foreground-strong)]">Add channel</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Handle, channel ID, or full YouTube URL.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <input
              value={channelInput}
              onChange={(e) => setChannelInput(e.target.value)}
              placeholder="@handle or UC channel id"
              className="field-input min-w-[280px] flex-1"
            />
            <button
              type="button"
              onClick={() => addMutation.mutate()}
              disabled={!channelInput.trim() || addMutation.isPending}
              className="btn btn-primary"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => scanMutation.mutate()}
              disabled={scanMutation.isPending}
              className="btn btn-secondary"
            >
              Run scan
            </button>
          </div>
        </section>

        {isLoading && <p className="text-sm text-[var(--muted)]">Loading channels</p>}
        {isError && (
          <div className="surface-card bg-[var(--pastel-red-bg)] px-4 py-3 text-sm text-[var(--pastel-red-text)]">
            {(error as Error).message}
          </div>
        )}

        {!isLoading && !isError && channels.length === 0 && (
          <EmptyState
            title="No channels yet"
            description="Add a channel manually or approve keywords to auto-subscribe from cascade."
          />
        )}

        {channels.length > 0 && (
          <div className="surface-card overflow-hidden animate-fade-rise">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[var(--border)] bg-[var(--surface-muted)] text-xs uppercase tracking-wider text-[var(--muted)]">
                <tr>
                  <th className="px-4 py-3 font-medium">Channel</th>
                  <th className="px-4 py-3 font-medium">Scan</th>
                  <th className="px-4 py-3 font-medium">Videos</th>
                  <th className="px-4 py-3 font-medium">Last scan</th>
                  <th className="px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {channels.map((ch, index) => (
                  <tr
                    key={ch.id}
                    className="stagger-item border-b border-[var(--border-subtle)] last:border-b-0"
                    style={{ ["--stagger-index" as string]: index }}
                  >
                    <td className="px-4 py-3.5">
                      <p className="font-medium text-[var(--foreground-strong)]">
                        {ch.name || ch.channel_id}
                      </p>
                      <p className="font-mono text-xs text-[var(--muted)]">{ch.channel_id}</p>
                    </td>
                    <td className="px-4 py-3.5">
                      <button
                        type="button"
                        onClick={() =>
                          toggleMutation.mutate({
                            id: ch.channel_id,
                            enabled: !ch.scan_enabled,
                          })
                        }
                        className={`tag-pill ${
                          ch.scan_enabled ? "tag-green" : "bg-[var(--surface-muted)] text-[var(--muted)]"
                        }`}
                      >
                        {ch.scan_enabled ? "Enabled" : "Disabled"}
                      </button>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-[var(--muted)]">
                      {ch.video_count}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-[var(--muted)]">
                      {ch.last_scan_at
                        ? new Date(ch.last_scan_at).toLocaleString()
                        : "Never"}
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        type="button"
                        onClick={() => deleteMutation.mutate(ch.channel_id)}
                        className="btn btn-ghost px-2 py-1 text-[var(--pastel-red-text)]"
                      >
                        Remove
                      </button>
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
