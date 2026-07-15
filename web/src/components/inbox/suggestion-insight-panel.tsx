"use client";

/* Hallmark · component: score-insight-panel · genre: editorial · theme: design.md
 * pre-emit critique: P4 H5 E5 S5 R5 V4
 * Fix: proportions — final hero · compact path · 22/14/14/50 table · 2:1 body
 */

import type {
  ComponentScores,
  PlatformSignals,
  RankingAdjustments,
  ScoreBlendMeta,
  Suggestion,
} from "@/lib/api/types";

const COMPONENT_KEYS = [
  "relevance",
  "specificity",
  "saturation",
  "trend",
  "video_performance",
] as const satisfies ReadonlyArray<keyof ComponentScores>;

const COMPONENT_LABELS: Record<keyof ComponentScores, string> = {
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
    blend.llm_weight * blend.llm_final +
    blend.heuristic_weight * blend.heuristic_final
  );
}

function componentsDiffer(a?: ComponentScores, b?: ComponentScores) {
  if (!a || !b) return false;
  return COMPONENT_KEYS.some((key) => Math.abs(a[key] - b[key]) > 0.005);
}

type PathChip = {
  id: string;
  label: string;
  value: string;
};

function buildPathChips(
  blend?: ScoreBlendMeta,
  ranking?: RankingAdjustments,
): PathChip[] {
  const chips: PathChip[] = [];

  if (blend) {
    chips.push({
      id: "llm",
      label: `LLM · ${Math.round(blend.llm_weight * 100)}%`,
      value: formatPercent(blend.llm_final),
    });
    chips.push({
      id: "heuristic",
      label: `Heur · ${Math.round(blend.heuristic_weight * 100)}%`,
      value: formatPercent(blend.heuristic_final),
    });
    chips.push({
      id: "blend",
      label:
        blend.linked_beta_reports != null
          ? `Blend · ${blend.linked_beta_reports}/20`
          : "Blend",
      value: formatPercent(blendedScore(blend)),
    });
  }

  if (ranking) {
    if (!blend) {
      chips.push({
        id: "pre",
        label: "Pre-rank",
        value: formatPercent(ranking.pre_ranking_score),
      });
    }
    if (ranking.lifecycle_delta !== 0) {
      chips.push({
        id: "lifecycle",
        label: ranking.lifecycle_stage.replaceAll("_", " "),
        value: formatSignedPercent(ranking.lifecycle_delta),
      });
    }
    if (ranking.history_delta !== 0) {
      chips.push({
        id: "history",
        label: "History",
        value: formatSignedPercent(ranking.history_delta),
      });
    }
    if (ranking.supply_pressure_delta !== 0) {
      chips.push({
        id: "supply",
        label: "Supply",
        value: formatSignedPercent(ranking.supply_pressure_delta),
      });
    }
  }

  return chips;
}

function DualBar({ llm, heuristic }: { llm: number; heuristic: number }) {
  const llmPct = Math.round(Math.min(1, Math.max(0, llm)) * 100);
  const heurPct = Math.round(Math.min(1, Math.max(0, heuristic)) * 100);

  return (
    <div className="flex w-full flex-col gap-1" aria-hidden>
      <div className="h-1.5 overflow-hidden rounded-sm bg-(--surface-muted)">
        <div
          className="h-full rounded-sm bg-(--foreground-strong)/80"
          style={{ width: `${llmPct}%` }}
        />
      </div>
      <div className="h-1.5 overflow-hidden rounded-sm bg-(--surface-muted)">
        <div
          className="h-full rounded-sm bg-(--muted)"
          style={{ width: `${heurPct}%` }}
        />
      </div>
    </div>
  );
}

function ScoreHeader({
  finalScore,
  blend,
  ranking,
  meta,
}: {
  finalScore: number;
  blend?: ScoreBlendMeta;
  ranking?: RankingAdjustments;
  meta?: string;
}) {
  if (!blend && !ranking) {
    return (
      <header className="mb-5 flex items-end justify-between gap-4 border-b border-(--border) pb-4">
        <div>
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.08em] text-(--muted)">
            Final
          </p>
          <p className="mt-1 font-mono text-3xl tabular-nums leading-none text-(--foreground-strong)">
            {formatPercent(finalScore)}
          </p>
        </div>
        {meta && (
          <p className="max-w-[18rem] text-right font-mono text-[0.65rem] uppercase tracking-[0.06em] text-(--muted)">
            {meta}
          </p>
        )}
      </header>
    );
  }

  const chips = buildPathChips(blend, ranking);
  const warnings: string[] = [];
  if (!ranking && blend?.spread_enforced) {
    warnings.push(
      `Batch spread stretched from ${formatPercent(blend.pre_stretch_final ?? blendedScore(blend))} — re-run discovery for a clean final.`,
    );
  }
  if (
    !ranking &&
    blend &&
    !blend.spread_enforced &&
    Math.abs(blendedScore(blend) - finalScore) > 0.015
  ) {
    warnings.push(
      `Blend ${formatPercent(blendedScore(blend))} ≠ displayed ${formatPercent(finalScore)} — ranking metadata may be missing on older rows.`,
    );
  }

  return (
    <header className="mb-5 border-b border-(--border) pb-4">
      {/* 1 : 3 ratio — final hero | path track */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[7.5rem_minmax(0,1fr)] sm:items-end sm:gap-6">
        <div className="min-w-0">
          <p className="font-mono text-[0.65rem] uppercase tracking-[0.08em] text-(--muted)">
            Final
          </p>
          <p className="mt-1 font-mono text-3xl tabular-nums leading-none text-(--foreground-strong)">
            {formatPercent(finalScore)}
          </p>
        </div>

        <div className="min-w-0">
          <div className="mb-2 flex items-baseline justify-between gap-3">
            <p className="font-mono text-[0.65rem] uppercase tracking-[0.08em] text-(--muted)">
              Score path
            </p>
            {meta && (
              <p className="truncate font-mono text-[0.65rem] uppercase tracking-[0.06em] text-(--muted)">
                {meta}
              </p>
            )}
          </div>
          <ol className="flex flex-wrap items-center gap-x-1 gap-y-2">
            {chips.map((chip, index) => (
              <li key={chip.id} className="flex items-center gap-1">
                {index > 0 && (
                  <span
                    aria-hidden
                    className="px-0.5 font-mono text-(--border)"
                  >
                    →
                  </span>
                )}
                <div className="inline-flex items-baseline gap-1.5 border-b border-(--border) pb-0.5">
                  <span className="text-[0.65rem] text-(--muted)">
                    {chip.label}
                  </span>
                  <span className="font-mono text-sm tabular-nums text-foreground">
                    {chip.value}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {warnings.map((warning) => (
        <p
          key={warning}
          className="mt-3 border-l-2 border-(--pastel-amber-text) pl-2.5 text-xs text-(--pastel-amber-text)"
        >
          {warning}
        </p>
      ))}
    </header>
  );
}

function LayerCompare({
  llm,
  reasons,
  heuristic,
  heuristicRaw,
}: {
  llm?: ComponentScores;
  reasons?: Record<string, string>;
  heuristic?: ComponentScores;
  heuristicRaw?: ComponentScores;
}) {
  if (!llm && !heuristic) return null;

  const showRaw = componentsDiffer(heuristic, heuristicRaw);
  const hasHeur = Boolean(heuristic);

  return (
    <section className="min-w-0">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-mono text-[0.65rem] font-medium uppercase tracking-[0.08em] text-(--muted)">
          Layers
        </h4>
        {hasHeur && (
          <p className="flex items-center gap-3 text-[0.65rem] text-(--muted)">
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-3 rounded-sm bg-(--foreground-strong)/80" />
              LLM
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-3 rounded-sm bg-(--muted)" />
              Heuristic
            </span>
            {showRaw && <span>· raw when reconcile moved</span>}
          </p>
        )}
      </div>

      {/* Fixed numeric cols + reason takes leftover — not the reverse */}
      <div className="w-full overflow-x-auto">
        <table className="w-full min-w-xl border-collapse text-sm">
          <colgroup>
            <col style={{ width: "18%" }} />
            <col style={{ width: "10%" }} />
            {hasHeur && <col style={{ width: "10%" }} />}
            {hasHeur && <col style={{ width: "14%" }} />}
            <col />
          </colgroup>
          <thead>
            <tr className="border-b border-(--border) text-left">
              <th className="pb-2 pr-3 font-mono text-[0.65rem] font-medium uppercase tracking-[0.06em] text-(--muted)">
                Signal
              </th>
              <th className="pb-2 pr-2 text-right font-mono text-[0.65rem] font-medium uppercase tracking-[0.06em] text-(--muted)">
                LLM
              </th>
              {hasHeur && (
                <th className="pb-2 pr-2 text-right font-mono text-[0.65rem] font-medium uppercase tracking-[0.06em] text-(--muted)">
                  Heur
                </th>
              )}
              {hasHeur && (
                <th className="pb-2 pr-3 font-mono text-[0.65rem] font-medium uppercase tracking-[0.06em] text-(--muted)">
                  Mix
                </th>
              )}
              <th className="pb-2 font-mono text-[0.65rem] font-medium uppercase tracking-[0.06em] text-(--muted)">
                Why
              </th>
            </tr>
          </thead>
          <tbody>
            {COMPONENT_KEYS.map((key) => {
              const llmValue = llm?.[key];
              const heurValue = heuristic?.[key];
              const rawValue = heuristicRaw?.[key];
              const rawMoved =
                showRaw &&
                heurValue != null &&
                rawValue != null &&
                Math.abs(rawValue - heurValue) > 0.005;
              const gap =
                llmValue != null && heurValue != null
                  ? Math.abs(llmValue - heurValue)
                  : 0;
              const gapNotable = gap > 0.15;

              return (
                <tr
                  key={key}
                  className="border-b border-(--border-subtle) align-middle last:border-b-0"
                >
                  <td className="py-3 pr-3 text-(--foreground-strong)">
                    {COMPONENT_LABELS[key]}
                  </td>
                  <td className="py-3 pr-2 text-right font-mono text-xs tabular-nums text-foreground">
                    {llmValue != null ? formatPercent(llmValue) : "—"}
                  </td>
                  {hasHeur && (
                    <td
                      className={`py-3 pr-2 text-right font-mono text-xs tabular-nums ${
                        gapNotable
                          ? "text-(--pastel-amber-text)"
                          : "text-foreground"
                      }`}
                    >
                      <span>
                        {heurValue != null ? formatPercent(heurValue) : "—"}
                      </span>
                      {rawMoved && (
                        <span className="mt-0.5 block text-[0.65rem] font-normal text-(--muted)">
                          raw {formatPercent(rawValue!)}
                        </span>
                      )}
                    </td>
                  )}
                  {hasHeur && (
                    <td className="py-3 pr-3">
                      {llmValue != null && heurValue != null ? (
                        <DualBar llm={llmValue} heuristic={heurValue} />
                      ) : (
                        <span className="text-(--muted)">—</span>
                      )}
                    </td>
                  )}
                  <td className="py-3 text-xs leading-relaxed text-(--muted)">
                    {reasons?.[key] ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EvidenceColumn({
  tiktok,
  youtube,
  suggestion,
}: {
  tiktok?: PlatformSignals["tiktok"];
  youtube?: PlatformSignals["youtube"];
  suggestion: Suggestion;
}) {
  const tiktokStatus = tiktok?.status ?? suggestion.tiktok_status;

  return (
    <aside className="min-w-0">
      <h4 className="mb-3 font-mono text-[0.65rem] font-medium uppercase tracking-[0.08em] text-(--muted)">
        Evidence
      </h4>

      <div className="space-y-4 border-l-2 border-(--border) pl-4">
        <div>
          <p className="text-[0.65rem] uppercase tracking-[0.06em] text-(--muted)">
            TikTok
          </p>
          <dl className="mt-2 space-y-1.5 text-xs">
            <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
              <dt className="text-(--muted)">Status</dt>
              <dd className="capitalize text-(--foreground-strong)">
                {tiktokStatus ?? "—"}
              </dd>
            </div>
            {tiktok?.stats && (
              <>
                <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
                  <dt className="text-(--muted)">7d vids</dt>
                  <dd className="font-mono tabular-nums text-foreground">
                    {tiktok.stats.video_count_7d}
                  </dd>
                </div>
                <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
                  <dt className="text-(--muted)">Views</dt>
                  <dd className="font-mono tabular-nums text-foreground">
                    {Math.round(tiktok.stats.avg_views).toLocaleString()}
                  </dd>
                </div>
                <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
                  <dt className="text-(--muted)">Likes</dt>
                  <dd className="font-mono tabular-nums text-foreground">
                    {Math.round(tiktok.stats.avg_likes).toLocaleString()}
                  </dd>
                </div>
                <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
                  <dt className="text-(--muted)">Comments</dt>
                  <dd className="font-mono tabular-nums text-foreground">
                    {Math.round(tiktok.stats.avg_comments).toLocaleString()}
                  </dd>
                </div>
              </>
            )}
            {tiktok?.unverified && (
              <p className="pt-1 text-(--pastel-amber-text)">Unverified gate</p>
            )}
          </dl>
        </div>

        <div>
          <p className="text-[0.65rem] uppercase tracking-[0.06em] text-(--muted)">
            YouTube
          </p>
          <dl className="mt-2 space-y-1.5 text-xs">
            <div className="grid grid-cols-[4.5rem_minmax(0,1fr)] gap-2">
              <dt className="text-(--muted)">Source</dt>
              <dd className="truncate text-foreground">
                {youtube?.discovery_source ??
                  suggestion.discovery_source ??
                  "—"}
              </dd>
            </div>
            {youtube?.source_title && (
              <p className="leading-snug text-(--foreground-strong)">
                {youtube.source_title}
              </p>
            )}
          </dl>
        </div>
      </div>
    </aside>
  );
}

interface SuggestionInsightPanelProps {
  suggestion: Suggestion;
}

export function SuggestionInsightPanel({
  suggestion,
}: SuggestionInsightPanelProps) {
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
        : (agentBlend ?? scoringBlend);
  const ranking = agent?.ranking_adjustments;
  const heuristicComponents = blend?.heuristic_components;
  const heuristicRaw = blend?.heuristic_components_raw;

  const meta = [
    agent?.scored_with,
    agent?.confidence != null && agent.confidence > 0
      ? `${formatPercent(agent.confidence)} conf`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="border-t border-(--border-subtle) bg-(--surface-muted)/35 px-5 py-5 text-sm">
      {agent?.rationale && (
        <p className="mb-5 max-w-[72ch] leading-relaxed text-(--foreground-strong)">
          {agent.rationale}
        </p>
      )}

      <ScoreHeader
        finalScore={suggestion.final_score}
        blend={blend}
        ranking={ranking}
        meta={meta || undefined}
      />

      {/* Body ~ 2.2 : 1 — layers dominate, evidence secondary */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,2.2fr)_minmax(14rem,1fr)]">
        <LayerCompare
          llm={components}
          reasons={reasons}
          heuristic={heuristicComponents}
          heuristicRaw={heuristicRaw}
        />
        <EvidenceColumn
          tiktok={tiktok}
          youtube={youtube}
          suggestion={suggestion}
        />
      </div>
    </div>
  );
}
