"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api/client";

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
    onSuccess: (res) => setMessage(`Scan started (job ${res.job_id.slice(0, 8)}…)`),
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

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-[var(--border)] bg-white px-8 py-6">
        <h1 className="text-2xl font-semibold text-zinc-900">Sources</h1>
        <p className="mt-1 text-sm text-zinc-500">Manage YouTube channels for daily digest</p>
      </header>

      <div className="space-y-6 px-8 py-6">
        {message && (
          <p className="rounded-lg bg-zinc-100 px-4 py-2 text-sm text-zinc-700">{message}</p>
        )}

        <section className="rounded-xl border border-zinc-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-zinc-900">Add channel</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              value={channelInput}
              onChange={(e) => setChannelInput(e.target.value)}
              placeholder="@handle or UC… or youtube.com/channel/…"
              className="min-w-[280px] flex-1 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={() => addMutation.mutate()}
              disabled={!channelInput.trim() || addMutation.isPending}
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              Add
            </button>
            <button
              type="button"
              onClick={() => scanMutation.mutate()}
              disabled={scanMutation.isPending}
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
            >
              Run scan now
            </button>
          </div>
        </section>

        {isLoading && <p className="text-sm text-zinc-500">Loading channels…</p>}
        {isError && (
          <p className="text-sm text-red-600">{(error as Error).message}</p>
        )}

        <section className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
              <tr>
                <th className="px-4 py-3 font-medium">Channel</th>
                <th className="px-4 py-3 font-medium">Scan</th>
                <th className="px-4 py-3 font-medium">Last scan</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((ch) => (
                <tr key={ch.id} className="border-b border-zinc-100">
                  <td className="px-4 py-3">
                    <p className="font-medium text-zinc-900">{ch.name || ch.channel_id}</p>
                    <p className="text-xs text-zinc-400">{ch.channel_id}</p>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() =>
                        toggleMutation.mutate({
                          id: ch.channel_id,
                          enabled: !ch.scan_enabled,
                        })
                      }
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        ch.scan_enabled
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-zinc-100 text-zinc-600"
                      }`}
                    >
                      {ch.scan_enabled ? "Enabled" : "Disabled"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-zinc-500">
                    {ch.last_scan_at
                      ? new Date(ch.last_scan_at).toLocaleString()
                      : "Never"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => deleteMutation.mutate(ch.channel_id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data?.total === 0 && (
            <p className="px-4 py-8 text-center text-sm text-zinc-500">No channels yet.</p>
          )}
        </section>
      </div>
    </div>
  );
}
