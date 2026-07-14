"use client";

import type { PlatformSignals, RankingAdjustments, ScoreBlendMeta, Suggestion } from "@/lib/api/types";

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

function formatSignedPercent(value: number) {
  const pct = Math.round(value * 100);
  if (pct > 0) return `+${pct}%`;
  if (pct < 0) return `${pct}%`;
  return "0%";
}

function blendedScore(blend: ScoreBlendMeta) {
  return (
    blend.llm_weight * blend.llm_final + blend.heuristic_weight * blend.heuristic_final
  );
}

function CompositionRow({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <li className="rounded-(--radius-sm) bg-(--surface) px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-(--foreground-strong)">{label}</span>
        <span className="font-mono text-xs">{value}</span>
      </div>
      {detail && <p className="mt-1 text-xs text-(--muted)">{detail}</p>}
    </li>
  );
}

function ScoreCompositionSection({
  finalScore,
  blend,
  ranking,
}: {
  finalScore: number;
  blend?: ScoreBlendMeta;
  ranking?: RankingAdjustments;
}) {
  if (!blend && !ranking) return null;

  return (
    <section className="mb-4">
      <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-(--muted)">
        Score composition
      </h4>
      <p className="mb-2 text-xs text-(--muted)">
        Final score includes layers beyond the LLM component breakdown below.
      </p>
      <ul className="space-y-2">
        {blend && (
          <>
            <CompositionRow
              label="LLM weighted"
              value={formatPercent(blend.llm_final)}
              detail={`${Math.round(blend.llm_weight * 100)}% of blend`}
            />
            <CompositionRow
              label="Heuristic weighted"
              value={formatPercent(blend.heuristic_final)}
              detail={`${Math.round(blend.heuristic_weight * 100)}% of blend · nurture track signals`}
            />
            <CompositionRow
              label="Blended score"
              value={formatPercent(blendedScore(blend))}
              detail={
                blend.linked_beta_reports != null
                  ? `${blend.linked_beta_reports} linked beta reports (calibration threshold 20)`
                  : undefined
              }
            />
          </>
        )}
        {ranking && (
          <>
            <CompositionRow
              label="Pre-ranking score"
              value={formatPercent(ranking.pre_ranking_score)}
            />
            {ranking.lifecycle_delta !== 0 && (
              <CompositionRow
                label={`Lifecycle (${ranking.lifecycle_stage.replaceAll("_", " ")})`}
                value={formatSignedPercent(ranking.lifecycle_delta)}
              />
            )}
            {ranking.history_delta !== 0 && (
              <CompositionRow
                label="History prior"
                value={formatSignedPercent(ranking.history_delta)}
              />
            )}
            {ranking.supply_pressure_delta !== 0 && (
              <CompositionRow
                label="Supply pressure"
                value={formatSignedPercent(ranking.supply_pressure_delta)}
              />
            )}
            <CompositionRow
              label="Post-ranking score"
              value={formatPercent(ranking.post_ranking_score)}
            />
          </>
        )}
        <CompositionRow label="Displayed final score" value={formatPercent(finalScore)} />
        {!ranking && blend?.spread_enforced && (
          <li className="rounded-(--radius-sm) border border-(--pastel-amber-text)/30 bg-(--surface) px-3 py-2 text-xs text-(--pastel-amber-text)">
            Batch spread adjusted this score from{" "}
            {formatPercent(blend.pre_stretch_final ?? blendedScore(blend))} — re-run discovery
            after the scoring fix for an accurate final.
          </li>
        )}
        {!ranking && blend && !blend.spread_enforced && Math.abs(blendedScore(blend) - finalScore) > 0.015 && (
          <li className="rounded-(--radius-sm) border border-(--pastel-amber-text)/30 bg-(--surface) px-3 py-2 text-xs text-(--pastel-amber-text)">
            Blended score ({formatPercent(blendedScore(blend))}) differs from final score —
            ranking adjustments may apply on records created before this metadata was stored.
          </li>
        )}
      </ul>
    </section>
  );
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
  const scoringBlend = suggestion.trend_signals?.scoring?.blend;
  const agentBlend = agent?.blend;
  const blend =
    agentBlend?.llm_final != null
      ? agentBlend
      : scoringBlend?.llm_final != null
        ? { ...scoringBlend, ...agentBlend }
        : agentBlend ?? scoringBlend;
  const ranking = agent?.ranking_adjustments;

  return (
    <div className="border-t border-(--border-subtle) bg-(--surface-muted)/40 px-4 py-4 text-sm">
      {agent?.rationale && (
        <p className="mb-3 text-(--foreground-strong)">{agent.rationale}</p>
      )}

      <ScoreCompositionSection
        finalScore={suggestion.final_score}
        blend={blend}
        ranking={ranking}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <section>
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-(--muted)">
            LLM component breakdown
          </h4>
          <p className="mb-2 text-xs text-(--muted)">
            Weighted average of these scores is the LLM layer only — not the full final score.
          </p>
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
