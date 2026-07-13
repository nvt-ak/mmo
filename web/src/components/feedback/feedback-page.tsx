"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api/client";
import type { FinalVideo } from "@/lib/api/types";
import {
  PerformanceReportForm,
  PendingFinalPicker,
  type PerformanceReportPrefill,
} from "@/components/insights/performance-report-form";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatPill } from "@/components/shared/stat-pill";

function outcomeTag(outcome?: string) {
  if (outcome === "success") return "tag-green";
  if (outcome === "failure") return "tag-red";
  return "tag-yellow";
}

export function FeedbackPage() {
  const queryClient = useQueryClient();
  const [prefill, setPrefill] = useState<PerformanceReportPrefill | null>(null);

  const accuracyQuery = useQuery({
    queryKey: ["feedback-accuracy"],
    queryFn: () => api.getFeedbackAccuracy(),
  });

  const pendingQuery = useQuery({
    queryKey: ["pending-finals"],
    queryFn: () => api.listPendingFinals(20),
  });

  const historyQuery = useQuery({
    queryKey: ["performance-reports"],
    queryFn: () => api.listPerformanceReports({ limit: 30 }),
  });

  const proposalsQuery = useQuery({
    queryKey: ["weight-proposals"],
    queryFn: () => api.listWeightProposals("pending"),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["feedback-accuracy"] });
    queryClient.invalidateQueries({ queryKey: ["pending-finals"] });
    queryClient.invalidateQueries({ queryKey: ["performance-reports"] });
    queryClient.invalidateQueries({ queryKey: ["weight-proposals"] });
    queryClient.invalidateQueries({ queryKey: ["insights"] });
    queryClient.invalidateQueries({ queryKey: ["settings"] });
    queryClient.invalidateQueries({ queryKey: ["suggestions"] });
  };

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.approveWeightProposal(id),
    onSuccess: invalidate,
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.rejectWeightProposal(id),
    onSuccess: invalidate,
  });

  const handleSelectFinal = (final: FinalVideo) => {
    setPrefill({
      keyword: final.keyword,
      suggestionId: final.suggestion_id,
      finalVideoId: final.id,
    });
  };

  const metrics = accuracyQuery.data;

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title="Feedback"
        description="Report TikTok performance after upload. Closes the learning loop."
        meta={
          metrics ? (
            <div className="flex flex-wrap gap-6">
              <StatPill label="Reports" value={metrics.total_reports} tone="blue" />
              <StatPill
                label="Success rate"
                value={`${(metrics.success_rate * 100).toFixed(0)}%`}
                tone="green"
              />
              <StatPill label="Pending finals" value={metrics.pending_finals} tone="yellow" />
            </div>
          ) : null
        }
      />

      <div className="grid gap-6 px-8 py-6 xl:grid-cols-[1.2fr_1fr]">
        <div className="space-y-6">
          <PendingFinalPicker
            items={pendingQuery.data?.items ?? []}
            onSelect={handleSelectFinal}
          />
          <PerformanceReportForm
            key={prefill?.finalVideoId ?? "new-report"}
            prefill={prefill}
            onSubmitted={invalidate}
          />
        </div>

        <section className="panel-section p-6">
          <h2 className="font-editorial text-xl text-(--foreground-strong)">
            Agent accuracy
          </h2>
          {accuracyQuery.isLoading && (
            <p className="mt-4 text-sm text-(--muted)">Loading metrics</p>
          )}
          {metrics && (
            <dl className="mt-4 space-y-4 text-sm">
              <div className="flex justify-between border-b border-(--border-subtle) pb-3">
                <dt className="text-(--muted)">Linked suggestions</dt>
                <dd className="font-mono">{metrics.linked_suggestions}</dd>
              </div>
              <div className="flex justify-between border-b border-(--border-subtle) pb-3">
                <dt className="text-(--muted)">Avg views</dt>
                <dd className="font-mono">{metrics.avg_views.toLocaleString()}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-(--muted)">High-score success rate</dt>
                <dd className="font-mono">
                  {(metrics.high_score_success_rate * 100).toFixed(1)}%
                </dd>
              </div>
            </dl>
          )}

          <h3 className="font-editorial mt-8 text-lg text-(--foreground-strong)">
            Pending weight proposals
          </h3>
          <p className="mt-1 text-sm text-(--muted)">
            Beta learning cycle suggestions — approve before settings update.
          </p>
          {proposalsQuery.isLoading && (
            <p className="mt-3 text-sm text-(--muted)">Loading proposals</p>
          )}
          {(proposalsQuery.data?.items ?? []).length === 0 && !proposalsQuery.isLoading && (
            <p className="mt-3 text-sm text-(--muted)">No pending proposals.</p>
          )}
          <ul className="mt-4 space-y-3">
            {(proposalsQuery.data?.items ?? []).map((proposal) => (
              <li
                key={proposal.id}
                className="rounded-lg border border-(--border-subtle) p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium capitalize text-(--foreground-strong)">
                      {proposal.factor}
                    </p>
                    <p className="mt-1 font-mono text-xs text-(--muted)">
                      {proposal.old_value.toFixed(2)} → {proposal.new_value.toFixed(2)}
                    </p>
                    {proposal.reason && (
                      <p className="mt-2 text-sm text-(--foreground)">{proposal.reason}</p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      className="btn btn-secondary text-xs"
                      disabled={rejectMutation.isPending}
                      onClick={() => rejectMutation.mutate(proposal.id)}
                    >
                      Reject
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary text-xs"
                      disabled={approveMutation.isPending}
                      onClick={() => approveMutation.mutate(proposal.id)}
                    >
                      Approve
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <h3 className="font-editorial mt-8 text-lg text-(--foreground-strong)">
            Recent reports
          </h3>
          {historyQuery.isLoading && (
            <p className="mt-3 text-sm text-(--muted)">Loading history</p>
          )}
          {(historyQuery.data ?? []).length === 0 && !historyQuery.isLoading && (
            <div className="mt-4">
              <EmptyState
                title="No reports yet"
                description="Submit TikTok stats after your first upload."
              />
            </div>
          )}
          <ul className="mt-4 space-y-3">
            {(historyQuery.data ?? []).map((report, index) => (
              <li
                key={report.id}
                className="border-b border-(--border-subtle) pb-3 last:border-b-0"
                style={{ ["--stagger-index" as string]: index }}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium text-(--foreground-strong)">{report.keyword}</p>
                  <span className={`tag-pill ${outcomeTag(report.outcome)}`}>
                    {report.outcome ?? "neutral"}
                  </span>
                </div>
                <p className="mt-1 font-mono text-xs text-(--muted)">
                  {report.actual_views.toLocaleString()} views ·{" "}
                  {new Date(report.reported_at).toLocaleString()}
                </p>
                {report.notes && (
                  <p className="mt-2 text-sm text-(--foreground)">{report.notes}</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
