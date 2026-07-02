"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { PerformanceReportForm } from "@/components/insights/performance-report-form";

function statusTag(status: string) {
  if (status === "reported") return "tag-green";
  if (status === "in_progress") return "tag-yellow";
  return "bg-(--surface-muted) text-(--muted)";
}

export function InsightsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["insights"],
    queryFn: () => api.getInsights(),
  });

  const cycleMutation = useMutation({
    mutationFn: () => api.runLearningCycle(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["insights"] }),
  });

  const experimentsQuery = useQuery({
    queryKey: ["experiments", "recent"],
    queryFn: () => api.listExperiments(),
  });

  const recentExperiments = (experimentsQuery.data?.items ?? []).filter((item) =>
    ["in_progress", "reported"].includes(item.test_status),
  );

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Insights"
        description="Patterns from rejections, reports, and keyword experiments."
        actions={
          <button
            type="button"
            onClick={() => cycleMutation.mutate()}
            disabled={cycleMutation.isPending}
            className="btn btn-primary"
          >
            {cycleMutation.isPending ? "Running" : "Run learning cycle"}
          </button>
        }
      />

      <div className="grid gap-6 px-8 py-6 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <PerformanceReportForm
            onSubmitted={() => {
              queryClient.invalidateQueries({ queryKey: ["experiments"] });
              queryClient.invalidateQueries({ queryKey: ["insights"] });
            }}
          />
        </div>

        {isLoading && <p className="text-sm text-(--muted)">Loading insights</p>}
        {isError && (
          <div className="surface-card bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
            {(error as Error).message}
          </div>
        )}

        {data && (
          <>
            {data.summary_metrics && (
              <section className="surface-card p-6 lg:col-span-2 animate-fade-rise">
                <h2 className="font-editorial text-xl text-(--foreground-strong)">Summary</h2>
                <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {Object.entries(data.summary_metrics).map(([key, val]) => (
                    <div key={key}>
                      <dt className="text-xs uppercase tracking-wider text-(--muted)">
                        {key.replace(/_/g, " ")}
                      </dt>
                      <dd className="mt-1 font-mono text-2xl text-(--foreground-strong)">
                        {typeof val === "number" ? val.toFixed(2) : val}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}

            <section className="surface-card p-6 animate-fade-rise">
              <h2 className="font-editorial text-xl text-(--foreground-strong)">
                Rejection patterns
              </h2>
              <ul className="mt-4 space-y-3">
                {(data.rejection_patterns ?? []).length === 0 && (
                  <li className="text-sm text-(--muted)">No rejection data yet.</li>
                )}
                {(data.rejection_patterns ?? []).map((p, index) => (
                  <li
                    key={p.reason}
                    className="stagger-item border-b border-(--border-subtle) pb-3 last:border-b-0"
                    style={{ ["--stagger-index" as string]: index }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="tag-pill tag-red capitalize">
                        {p.reason.replace(/_/g, " ")}
                      </span>
                      <span className="font-mono text-xs text-(--muted)">{p.frequency}x</span>
                    </div>
                    <p className="mt-2 text-sm text-(--foreground)">{p.suggested_action}</p>
                  </li>
                ))}
              </ul>
            </section>

            <section className="surface-card p-6 animate-fade-rise">
              <h2 className="font-editorial text-xl text-(--foreground-strong)">
                Success patterns
              </h2>
              <ul className="mt-4 space-y-3">
                {(data.success_patterns ?? []).length === 0 && (
                  <li className="text-sm text-(--muted)">Need more reported keywords.</li>
                )}
                {(data.success_patterns ?? []).map((p, index) => (
                  <li
                    key={p.keyword_example}
                    className="stagger-item rounded-(--radius-sm) bg-(--pastel-green-bg) px-4 py-3"
                    style={{ ["--stagger-index" as string]: index }}
                  >
                    <p className="font-medium text-(--foreground-strong)">{p.keyword_example}</p>
                    <p className="mt-1 font-mono text-xs text-(--muted)">
                      ~{p.avg_views.toLocaleString()} views ·{" "}
                      {(p.avg_engagement_rate * 100).toFixed(1)}% engagement
                    </p>
                    <p className="mt-2 text-sm text-(--pastel-green-text)">
                      {p.replication_strategy}
                    </p>
                  </li>
                ))}
              </ul>
            </section>

            <section className="surface-card overflow-hidden lg:col-span-2 animate-fade-rise">
              <div className="border-b border-(--border) px-6 py-4">
                <h2 className="font-editorial text-xl text-(--foreground-strong)">
                  Recent experiments
                </h2>
                <p className="mt-1 text-sm text-(--muted)">
                  In-progress and reported runs
                </p>
              </div>

              {experimentsQuery.isLoading && (
                <p className="px-6 py-4 text-sm text-(--muted)">Loading experiments</p>
              )}
              {experimentsQuery.isError && (
                <p className="px-6 py-4 text-sm text-(--pastel-red-text)">
                  {(experimentsQuery.error as Error).message}
                </p>
              )}

              {!experimentsQuery.isLoading &&
                !experimentsQuery.isError &&
                recentExperiments.length === 0 && (
                  <div className="p-6">
                    <EmptyState
                      title="No active experiments"
                      description="Approve keywords and submit performance reports to populate this table."
                    />
                  </div>
                )}

              {recentExperiments.length > 0 && (
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-(--border) bg-(--surface-muted) text-xs uppercase tracking-wider text-(--muted)">
                    <tr>
                      <th className="px-4 py-3 font-medium">Keyword</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium">Predicted</th>
                      <th className="px-4 py-3 font-medium">Actual views</th>
                      <th className="px-4 py-3 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentExperiments.map((item, index) => (
                      <tr
                        key={item.id}
                        className="stagger-item border-b border-(--border-subtle) last:border-b-0"
                        style={{ ["--stagger-index" as string]: index }}
                      >
                        <td className="px-4 py-3.5 font-medium text-(--foreground-strong)">
                          {item.keyword}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className={`tag-pill ${statusTag(item.test_status)}`}>
                            {item.test_status.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-(--muted)">
                          {item.predicted_score}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-(--muted)">
                          {item.actual_views?.toLocaleString() ?? "-"}
                        </td>
                        <td className="px-4 py-3.5 font-mono text-xs text-(--muted)">
                          {new Date(item.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
