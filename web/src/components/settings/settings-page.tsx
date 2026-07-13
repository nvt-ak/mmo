"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { ScoringWeights } from "@/lib/api/types";
import { PageHeader } from "@/components/shared/page-header";

const WEIGHT_LABELS: Record<keyof ScoringWeights, string> = {
  relevance: "Relevance",
  specificity: "Specificity",
  saturation: "Saturation",
  trend: "Trend",
  video_performance: "Video performance",
};

type SettingsData = Awaited<ReturnType<typeof api.getSettings>>;

function RubricEditor({
  label,
  description,
  value,
  defaultText,
  isCustom,
  onChange,
  onReset,
}: {
  label: string;
  description: string;
  value: string;
  defaultText: string;
  isCustom: boolean;
  onChange: (text: string) => void;
  onReset: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-editorial text-lg text-(--foreground-strong)">{label}</h3>
          <p className="mt-1 text-sm text-(--muted)">{description}</p>
        </div>
        <span className={`tag-pill shrink-0 ${isCustom ? "tag-blue" : "tag-green"}`}>
          {isCustom ? "Custom" : "Default"}
        </span>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={14}
        spellCheck={false}
        className="field-input min-h-[280px] resize-y font-mono text-xs leading-relaxed"
      />
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-(--muted)">
          Injected into LLM prompt at discovery. Edit to override ship default.
        </p>
        <button
          type="button"
          onClick={onReset}
          disabled={!isCustom && value.trim() === defaultText.trim()}
          className="btn btn-ghost text-xs disabled:opacity-40"
        >
          Reset to default
        </button>
      </div>
    </div>
  );
}

function SettingsForm({ initial }: { initial: SettingsData }) {
  const queryClient = useQueryClient();
  const rubrics = initial.scoring_rubrics;
  const rubricsFromApi = initial.rubrics_available === true;
  const [weights, setWeights] = useState(initial.weights);
  const [minScoreThreshold, setMinScoreThreshold] = useState(
    initial.filters.min_score_threshold ?? 0.55,
  );
  const [minSpecificity, setMinSpecificity] = useState(
    initial.filters.min_specificity ?? 0.4,
  );
  const [topics, setTopics] = useState(initial.niche.topics.join(", "));
  const [nurtureRubric, setNurtureRubric] = useState(rubrics.nurture.text);
  const [betaRubric, setBetaRubric] = useState(rubrics.beta.text);
  const [nurtureCustom, setNurtureCustom] = useState(rubrics.nurture.is_custom);
  const [betaCustom, setBetaCustom] = useState(rubrics.beta.is_custom);
  const [llmBaseUrl, setLlmBaseUrl] = useState(initial.llm.base_url);
  const [llmModel, setLlmModel] = useState(initial.llm.model);
  const [llmApiKey, setLlmApiKey] = useState("");
  const [saved, setSaved] = useState(false);

  const modelsQuery = useQuery({
    queryKey: ["llm-models", llmBaseUrl, llmApiKey || (initial.llm.api_key_set ? "saved" : "")],
    queryFn: () =>
      api.listLlmModels({
        base_url: llmBaseUrl.trim() || undefined,
        ...(llmApiKey.trim() ? { api_key: llmApiKey.trim() } : {}),
      }),
    retry: false,
    staleTime: 60_000,
  });

  const modelOptions = useMemo(() => {
    const fetched = modelsQuery.data?.models ?? [];
    if (llmModel && !fetched.includes(llmModel)) {
      return [llmModel, ...fetched];
    }
    return fetched;
  }, [modelsQuery.data?.models, llmModel]);

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateSettings({
        weights,
        filters: {
          min_score_threshold: minScoreThreshold,
          min_specificity: minSpecificity,
        },
        niche: {
          topics: topics.split(",").map((t) => t.trim()).filter(Boolean),
          preferred_language: initial.niche.preferred_language,
        },
        llm: {
          base_url: llmBaseUrl.trim(),
          model: llmModel.trim(),
          ...(llmApiKey.trim() ? { api_key: llmApiKey.trim() } : {}),
        },
        scoring_rubrics: {
          nurture: nurtureRubric,
          beta: betaRubric,
        },
      }),
    onSuccess: () => {
      setSaved(true);
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const weightSum = Object.values(weights).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-6">
      <section className="panel-section p-6">
        <h2 className="font-editorial text-xl text-(--foreground-strong)">Scoring weights</h2>
        <p className="mt-1 text-sm text-(--muted)">
          Agent ranking blend. Total: {weightSum.toFixed(2)}
        </p>
        <div className="mt-5 space-y-5">
          {(Object.keys(WEIGHT_LABELS) as (keyof ScoringWeights)[]).map((key) => (
            <label key={key} className="block">
              <div className="flex justify-between text-sm">
                <span className="text-foreground">{WEIGHT_LABELS[key]}</span>
                <span className="font-mono text-(--muted)">{weights[key].toFixed(2)}</span>
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
                className="mt-2 w-full accent-(--foreground-strong)"
              />
            </label>
          ))}
        </div>
      </section>

      <section className="panel-section p-6">
        <h2 className="font-editorial text-xl text-(--foreground-strong)">Inbox gates</h2>
        <p className="mt-1 text-sm text-(--muted)">
          Discovery saves at most 10 keywords per run; only rows passing these floors
          are written to the inbox.
        </p>
        <div className="mt-5 space-y-5">
          <label className="block">
            <div className="flex justify-between text-sm">
              <span className="text-foreground">Minimum win score (beta)</span>
              <span className="font-mono text-(--muted)">
                {Math.round(minScoreThreshold * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={0.4}
              max={0.85}
              step={0.05}
              value={minScoreThreshold}
              onChange={(e) => setMinScoreThreshold(Number(e.target.value))}
              className="mt-2 w-full accent-(--foreground-strong)"
            />
          </label>
          <label className="block">
            <div className="flex justify-between text-sm">
              <span className="text-foreground">Minimum specificity (beta)</span>
              <span className="font-mono text-(--muted)">
                {Math.round(minSpecificity * 100)}%
              </span>
            </div>
            <input
              type="range"
              min={0.3}
              max={0.9}
              step={0.05}
              value={minSpecificity}
              onChange={(e) => setMinSpecificity(Number(e.target.value))}
              className="mt-2 w-full accent-(--foreground-strong)"
            />
          </label>
          <p className="text-xs text-(--muted)">
            Beta keywords also require relevance ≥ 30%. Nurture uses a lower score floor.
          </p>
        </div>
      </section>

      <section className="panel-section p-6">
        <h2 className="font-editorial text-xl text-(--foreground-strong)">Niche topics</h2>
        <p className="mt-1 text-sm text-(--muted)">Comma-separated focus areas for scans.</p>
        <input
          value={topics}
          onChange={(e) => setTopics(e.target.value)}
          className="field-input mt-4"
          placeholder="AI, marketing, TikTok growth"
        />
        {topics.trim() && (
          <div className="mt-3 flex flex-wrap gap-2">
            {topics
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
              .map((topic) => (
                <span key={topic} className="tag-pill tag-blue">
                  {topic}
                </span>
              ))}
          </div>
        )}
      </section>

      <section className="panel-section p-6">
        <h2 className="font-editorial text-xl text-(--foreground-strong)">Scoring instructions</h2>
        <p className="mt-1 text-sm text-(--muted)">
          Runtime rubrics sent to the LLM when ranking keywords during discovery.
        </p>
        {!rubricsFromApi && (
          <div className="mt-4 surface-card bg-(--pastel-yellow-bg) px-4 py-3 text-sm text-(--pastel-yellow-text)">
            Showing ship defaults — API chưa US-061. Edit được; Save persist sau khi restart
            API + <code className="font-mono text-xs">alembic upgrade head</code>.
          </div>
        )}
        <div className="mt-6 space-y-10">
          <RubricEditor
            label="Nurture track"
            description="Fast TikTok keywords (2–3 words) from YouTube trending titles."
            value={nurtureRubric}
            defaultText={rubrics.nurture.default_text}
            isCustom={nurtureCustom}
            onChange={(text) => {
              setNurtureRubric(text);
              setNurtureCustom(
                text.trim() !== rubrics.nurture.default_text.trim(),
              );
            }}
            onReset={() => {
              setNurtureRubric(rubrics.nurture.default_text);
              setNurtureCustom(false);
            }}
          />
          <RubricEditor
            label="Beta track"
            description="Full-gate niche phrases (3–5 words) with knowledge-base context."
            value={betaRubric}
            defaultText={rubrics.beta.default_text}
            isCustom={betaCustom}
            onChange={(text) => {
              setBetaRubric(text);
              setBetaCustom(
                text.trim() !== rubrics.beta.default_text.trim(),
              );
            }}
            onReset={() => {
              setBetaRubric(rubrics.beta.default_text);
              setBetaCustom(false);
            }}
          />
        </div>
      </section>

      <section className="panel-section p-6">
        <h2 className="font-editorial text-xl text-(--foreground-strong)">OpenAI / LLM</h2>
        <p className="mt-1 text-sm text-(--muted)">
          Override API endpoint and key. DB values take precedence over environment.
        </p>
        <div className="mt-5 space-y-4">
          <label className="block">
            <span className="text-sm text-foreground">Base URL</span>
            <input
              type="url"
              value={llmBaseUrl}
              onChange={(e) => setLlmBaseUrl(e.target.value)}
              className="field-input mt-2"
              placeholder="https://api.openai.com/v1"
            />
          </label>
          <label className="block">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">API key</span>
              <span className={`tag-pill ${initial.llm.api_key_set ? "tag-green" : "tag-yellow"}`}>
                {initial.llm.api_key_set ? "Configured" : "Missing"}
              </span>
            </div>
            <input
              type="password"
              value={llmApiKey}
              onChange={(e) => setLlmApiKey(e.target.value)}
              className="field-input mt-2"
              placeholder={initial.llm.api_key_set ? "Leave blank to keep current key" : "sk-..."}
              autoComplete="off"
            />
          </label>
          <label className="block">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">Model</span>
              <button
                type="button"
                onClick={() => modelsQuery.refetch()}
                disabled={modelsQuery.isFetching}
                className="text-xs text-(--muted) hover:text-foreground disabled:opacity-50"
              >
                {modelsQuery.isFetching ? "Loading…" : "Refresh"}
              </button>
            </div>
            <select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              disabled={modelsQuery.isLoading && modelOptions.length === 0}
              className="field-input mt-2"
            >
              {modelOptions.length === 0 ? (
                <option value={llmModel}>{llmModel || "Select model"}</option>
              ) : (
                modelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))
              )}
            </select>
            {modelsQuery.isError && (
              <p className="mt-1 text-xs text-(--pastel-red-text)">
                {(modelsQuery.error as Error).message}
              </p>
            )}
          </label>
        </div>
      </section>

      <section className="panel-section p-6">
        <h2 className="font-editorial text-xl text-(--foreground-strong)">Integrations</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex items-center justify-between border-b border-(--border-subtle) pb-3">
            <dt className="text-(--muted)">TikTok API key</dt>
            <dd>
              <span className={`tag-pill ${initial.tiktok.api_key_set ? "tag-green" : "tag-yellow"}`}>
                {initial.tiktok.api_key_set ? "Configured" : "Missing"}
              </span>
            </dd>
          </div>
          <div className="flex items-center justify-between">
            <dt className="text-(--muted)">TikTok checks</dt>
            <dd>
              <span className={`tag-pill ${initial.tiktok.check_enabled ? "tag-green" : "bg-(--surface-muted) text-(--muted)"}`}>
                {initial.tiktok.check_enabled ? "Enabled" : "Disabled"}
              </span>
            </dd>
          </div>
        </dl>
      </section>

      <button
        type="button"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending}
        className="btn btn-primary"
      >
        {saveMutation.isPending ? "Saving" : saved ? "Saved" : "Save settings"}
      </button>
    </div>
  );
}

export function SettingsPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.getSettings(),
  });

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Settings"
        description="Scoring weights, rubrics, niche definition, and integration status."
      />

      <div className="max-w-2xl px-8 py-6">
        {isLoading && <p className="text-sm text-(--muted)">Loading settings</p>}
        {isError && (
          <div className="surface-card bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
            {(error as Error).message}
          </div>
        )}

        {data && (
          <SettingsForm
            key={`${data.niche.topics.join()}|${Object.values(data.weights).join(",")}|${data.llm.base_url}|${data.llm.model}|${data.llm.api_key_set}|${data.rubrics_available}|${data.scoring_rubrics.nurture.is_custom}|${data.scoring_rubrics.beta.is_custom}`}
            initial={data}
          />
        )}
      </div>
    </div>
  );
}
