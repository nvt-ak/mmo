"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api/client";
import type { ScoringWeights } from "@/lib/api/types";

const WEIGHT_LABELS: Record<keyof ScoringWeights, string> = {
  relevance: "Relevance",
  specificity: "Specificity",
  saturation: "Saturation",
  trend: "Trend",
  video_performance: "Video performance",
};

type SettingsData = Awaited<ReturnType<typeof api.getSettings>>;

function SettingsForm({ initial }: { initial: SettingsData }) {
  const queryClient = useQueryClient();
  const [weights, setWeights] = useState(initial.weights);
  const [topics, setTopics] = useState(initial.niche.topics.join(", "));
  const [saved, setSaved] = useState(false);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateSettings({
        weights,
        niche: {
          topics: topics.split(",").map((t) => t.trim()).filter(Boolean),
          preferred_language: initial.niche.preferred_language,
        },
      }),
    onSuccess: () => {
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setTimeout(() => setSaved(false), 2000);
    },
  });

  return (
    <>
      <section className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-zinc-900">Scoring weights</h2>
        <div className="mt-4 space-y-4">
          {(Object.keys(WEIGHT_LABELS) as (keyof ScoringWeights)[]).map((key) => (
            <label key={key} className="block">
              <div className="flex justify-between text-sm">
                <span className="text-zinc-700">{WEIGHT_LABELS[key]}</span>
                <span className="font-mono text-zinc-500">{weights[key].toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={weights[key]}
                onChange={(e) =>
                  setWeights({ ...weights, [key]: Number(e.target.value) })
                }
                className="mt-1 w-full"
              />
            </label>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="text-sm font-semibold text-zinc-900">Niche topics</h2>
        <p className="mt-1 text-xs text-zinc-500">Comma-separated keywords</p>
        <input
          value={topics}
          onChange={(e) => setTopics(e.target.value)}
          className="mt-3 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          placeholder="AI, marketing, TikTok growth"
        />
      </section>

      <button
        type="button"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending}
        className="rounded-lg bg-zinc-900 px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
      >
        {saveMutation.isPending ? "Saving…" : saved ? "Saved ✓" : "Save settings"}
      </button>
    </>
  );
}

export function SettingsPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-[var(--border)] bg-white px-8 py-6">
        <h1 className="text-2xl font-semibold text-zinc-900">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500">Scoring weights and niche definition</p>
      </header>

      <div className="max-w-2xl space-y-8 px-8 py-6">
        {isLoading && <p className="text-sm text-zinc-500">Loading…</p>}
        {isError && <p className="text-sm text-red-600">{(error as Error).message}</p>}

        {data && (
          <SettingsForm
            key={`${data.niche.topics.join()}|${Object.values(data.weights).join(",")}`}
            initial={data}
          />
        )}
      </div>
    </div>
  );
}
