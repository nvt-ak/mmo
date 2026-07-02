"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { PerformanceReportForm } from "@/components/insights/performance-report-form";

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
      <header className="border-b border-[var(--border)] bg-white px-8 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900">Insights</h1>
            <p className="mt-1 text-sm text-zinc-500">Learning patterns from rejections & reports</p>
          </div>
          <button
            type="button"
            onClick={() => cycleMutation.mutate()}
            disabled={cycleMutation.isPending}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {cycleMutation.isPending ? "Running…" : "Run learning cycle"}
          </button>
        </div>
      </header>

      <div className="grid gap-6 px-8 py-6 lg:grid-cols-2">
        <div className="lg:col-span-2">
          <PerformanceReportForm
            onSubmitted={() => {
              queryClient.invalidateQueries({ queryKey: ["experiments"] });
              queryClient.invalidateQueries({ queryKey: ["insights"] });
            }}
          />
        </div>

        {isLoading && <p className="text-sm text-zinc-500">Loading insights…</p>}
        {isError && <p className="text-sm text-red-600">{(error as Error).message}</p>}

        {data && (
          <>
            {data.summary_metrics && (
              <section className="rounded-xl border border-zinc-200 bg-white p-5 lg:col-span-2">
                <h2 className="text-sm font-semibold text-zinc-900">Summary</h2>
                <dl className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {Object.entries(data.summary_metrics).map(([key, val]) => (
                    <div key={key}>
                      <dt className="text-xs uppercase text-zinc-400">{key.replace(/_/g, " ")}</dt>
                      <dd className="text-xl font-semibold text-zinc-900">
                        {typeof val === "number" ? val.toFixed(2) : val}
                      </dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}

            <section className="rounded-xl border border-zinc-200 bg-white p-5">
              <h2 className="text-sm font-semibold text-zinc-900">Rejection patterns</h2>
              <ul className="mt-3 space-y-3">
                {(data.rejection_patterns ?? []).length === 0 && (
                  <li className="text-sm text-zinc-500">No rejection data yet.</li>
                )}
                {(data.rejection_patterns ?? []).map((p) => (
                  <li key={p.reason} className="rounded-lg bg-zinc-50 px-3 py-2 text-sm">
                    <span className="font-medium capitalize">{p.reason.replace(/_/g, " ")}</span>
                    <span className="text-zinc-500"> · {p.frequency}×</span>
                    <p className="mt-1 text-xs text-zinc-600">{p.suggested_action}</p>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-xl border border-zinc-200 bg-white p-5">
              <h2 className="text-sm font-semibold text-zinc-900">Success patterns</h2>
              <ul className="mt-3 space-y-3">
                {(data.success_patterns ?? []).length === 0 && (
                  <li className="text-sm text-zinc-500">Need more reported keywords.</li>
                )}
                {(data.success_patterns ?? []).map((p) => (
                  <li key={p.keyword_example} className="rounded-lg bg-emerald-50 px-3 py-2 text-sm">
                    <p className="font-medium text-zinc-900">{p.keyword_example}</p>
                    <p className="text-xs text-zinc-600">
                      ~{p.avg_views.toLocaleString()} views · {(p.avg_engagement_rate * 100).toFixed(1)}% engagement
                    </p>
                    <p className="mt-1 text-xs text-emerald-800">{p.replication_strategy}</p>
                  </li>
                ))}
              </ul>
            </section>

            <section className="overflow-hidden rounded-xl border border-zinc-200 bg-white lg:col-span-2">
              <div className="border-b border-zinc-200 px-5 py-4">
                <h2 className="text-sm font-semibold text-zinc-900">Recent experiments</h2>
                <p className="mt-1 text-xs text-zinc-500">Showing in-progress and reported experiments</p>
              </div>

              {experimentsQuery.isLoading && (
                <p className="px-5 py-4 text-sm text-zinc-500">Loading experiments…</p>
              )}
              {experimentsQuery.isError && (
                <p className="px-5 py-4 text-sm text-red-600">
                  {(experimentsQuery.error as Error).message}
                </p>
              )}

              {!experimentsQuery.isLoading && !experimentsQuery.isError && (
                <>
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase text-zinc-500">
                      <tr>
                        <th className="px-4 py-3 font-medium">Keyword</th>
                        <th className="px-4 py-3 font-medium">Status</th>
                        <th className="px-4 py-3 font-medium">Predicted</th>
                        <th className="px-4 py-3 font-medium">Actual views</th>
                        <th className="px-4 py-3 font-medium">Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentExperiments.map((item) => (
                        <tr key={item.id} className="border-b border-zinc-100">
                          <td className="px-4 py-3 font-medium text-zinc-900">{item.keyword}</td>
                          <td className="px-4 py-3">
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                item.test_status === "reported"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {item.test_status.replace(/_/g, " ")}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-zinc-700">{item.predicted_score}</td>
                          <td className="px-4 py-3 text-zinc-700">
                            {item.actual_views?.toLocaleString() ?? "-"}
                          </td>
                          <td className="px-4 py-3 text-zinc-500">
                            {new Date(item.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {recentExperiments.length === 0 && (
                    <p className="px-4 py-8 text-center text-sm text-zinc-500">
                      No in-progress or reported experiments yet.
                    </p>
                  )}
                </>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
