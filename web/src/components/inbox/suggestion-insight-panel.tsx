"use client";

import type { PlatformSignals, Suggestion } from "@/lib/api/types";

const COMPONENT_LABELS: Record<string, string> = {
  relevance: "Relevance",
  specificity: "Specificity",
  saturation: "Saturation",
  trend: "Trend",
  video_performance: "Video performance",
};

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

interface SuggestionInsightPanelProps {
  suggestion: Suggestion;
}

export function SuggestionInsightPanel({ suggestion }: SuggestionInsightPanelProps) {
  const signals = suggestion.platform_signals as PlatformSignals | undefined;
  const agent = signals?.agent;
  const tiktok = signals?.tiktok;
  const youtube = signals?.youtube;
  const components = agent?.component_scores ?? suggestion.component_scores;
  const reasons = agent?.component_reasons ?? {};

  return (
    <div className="border-t border-(--border-subtle) bg-(--surface-muted)/40 px-4 py-4 text-sm">
      {agent?.rationale && (
        <p className="mb-3 text-(--foreground-strong)">{agent.rationale}</p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section>
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-(--muted)">
            Score breakdown
          </h4>
          <ul className="space-y-2">
            {Object.entries(components).map(([key, value]) => (
              <li key={key} className="rounded-(--radius-sm) bg-(--surface) px-3 py-2">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-(--foreground-strong)">
                    {COMPONENT_LABELS[key] ?? key}
                  </span>
                  <span className="font-mono text-xs">{formatPercent(value)}</span>
                </div>
                {reasons[key] && (
                  <p className="mt-1 text-xs text-(--muted)">{reasons[key]}</p>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section className="space-y-4">
          <div>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-(--muted)">
              TikTok
            </h4>
            <div className="rounded-(--radius-sm) bg-(--surface) px-3 py-2 text-xs text-(--muted)">
              <p>
                Status:{" "}
                <span className="capitalize text-(--foreground-strong)">
                  {tiktok?.status ?? suggestion.tiktok_status ?? "—"}
                </span>
              </p>
              {tiktok?.stats && (
                <>
                  <p>Videos (7d): {tiktok.stats.video_count_7d}</p>
                  <p>Avg views: {Math.round(tiktok.stats.avg_views).toLocaleString()}</p>
                  <p>Avg likes: {Math.round(tiktok.stats.avg_likes).toLocaleString()}</p>
                  <p>Avg comments: {Math.round(tiktok.stats.avg_comments).toLocaleString()}</p>
                </>
              )}
              {tiktok?.unverified && <p className="text-(--pastel-amber-text)">Unverified gate</p>}
            </div>
          </div>

          <div>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-(--muted)">
              YouTube
            </h4>
            <div className="rounded-(--radius-sm) bg-(--surface) px-3 py-2 text-xs text-(--muted)">
              <p>Source: {youtube?.discovery_source ?? suggestion.discovery_source ?? "—"}</p>
              {youtube?.source_title && (
                <p className="mt-1 text-(--foreground-strong)">{youtube.source_title}</p>
              )}
            </div>
          </div>

          {agent && (
            <p className="font-mono text-[0.65rem] uppercase text-(--muted)">
              {agent.scored_with}
              {agent.confidence != null && agent.confidence > 0
                ? ` · confidence ${formatPercent(agent.confidence)}`
                : ""}
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
