"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState, Fragment } from "react";
import { api } from "@/lib/api/client";
import type { RejectReason, Suggestion, SuggestionStatus, KeywordType, KeywordTypeFilter } from "@/lib/api/types";
import { ActionBar } from "@/components/shared/action-bar";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { ScoreBadge } from "@/components/shared/score-badge";
import { useKeywordScan } from "@/components/shared/keyword-scan-button";
import { TabBar } from "@/components/shared/tab-bar";
import { SuggestionInsightPanel } from "./suggestion-insight-panel";
import { RejectModal } from "./reject-modal";
import { ReportDialog } from "./report-dialog";

const TABS: { status: SuggestionStatus; label: string }[] = [
  { status: "pending", label: "Pending" },
  { status: "approved", label: "Approved" },
  { status: "reported", label: "Reported" },
  { status: "rejected", label: "Rejected" },
];

interface InboxPageProps {
  keywordType: KeywordType;
  title: string;
  description: string;
  discoveryFilter?: KeywordTypeFilter;
}

export function InboxPage({
  keywordType,
  title,
  description,
  discoveryFilter,
}: InboxPageProps) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<SuggestionStatus>("pending");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reportTarget, setReportTarget] = useState<Suggestion | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedClusters, setExpandedClusters] = useState<Set<string>>(new Set());

  const queryKey = ["suggestions", keywordType, status, search];

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey,
    queryFn: () =>
      api.listSuggestions({
        status,
        keyword_type: keywordType,
        limit: 100,
        search: search || undefined,
      }),
    refetchInterval: 30_000,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["suggestions"] });

  const approveMutation = useMutation({
    mutationFn: (ids: string[]) => api.bulkApprove(ids),
    onSuccess: () => {
      setSelected(new Set());
      invalidate();
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (payload: { keyword_ids: string[]; reason: RejectReason; note?: string }) =>
      api.bulkReject(payload),
    onSuccess: () => {
      setSelected(new Set());
      setRejectOpen(false);
      invalidate();
    },
  });

  const reportMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: Parameters<typeof api.reportSuggestion>[1];
    }) => api.reportSuggestion(id, payload),
    onSuccess: () => {
      setReportTarget(null);
      invalidate();
    },
  });

  const improveMutation = useMutation({
    mutationFn: (id: string) => api.improveSuggestion(id),
    onSuccess: invalidate,
  });

  const items = data?.items ?? [];

  const visibleRows = useMemo(() => {
    type Row = {
      item: Suggestion;
      clusterMeta?: {
        id: string;
        count: number;
        expanded: boolean;
        isChild?: boolean;
      };
    };

    const rows: Row[] = [];
    const handledClusters = new Set<string>();

    for (const item of items) {
      if (!item.cluster_id || (item.cluster_member_count ?? 0) < 2) {
        rows.push({ item });
        continue;
      }
      if (handledClusters.has(item.cluster_id)) {
        continue;
      }
      handledClusters.add(item.cluster_id);

      const members = items.filter((row) => row.cluster_id === item.cluster_id);
      const canonical =
        members.find((row) => row.is_cluster_canonical) ??
        members.find((row) => row.keyword === row.cluster_canonical_keyword) ??
        members[0];
      const expanded = expandedClusters.has(item.cluster_id);

      rows.push({
        item: canonical,
        clusterMeta: {
          id: item.cluster_id,
          count: members.length,
          expanded,
        },
      });

      if (expanded) {
        for (const member of members) {
          if (member.id !== canonical.id) {
            rows.push({
              item: member,
              clusterMeta: {
                id: item.cluster_id,
                count: members.length,
                expanded: true,
                isChild: true,
              },
            });
          }
        }
      }
    }

    return rows;
  }, [items, expandedClusters]);

  const allSelected = items.length > 0 && selected.size === items.length;

  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(items.map((i) => i.id)));
  };

  const toggleOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedIds = useMemo(() => Array.from(selected), [selected]);

  const onDiscoveryComplete = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ["suggestions"] });
    setStatus("pending");
  }, [queryClient]);

  const discovery = useKeywordScan({
    keywordTypeFilter: discoveryFilter ?? keywordType,
    label:
      discoveryFilter === "both" || discoveryFilter === undefined
        ? "Run trend discovery"
        : "Discover",
    onComplete: onDiscoveryComplete,
  });

  return (
    <div className="flex flex-1 flex-col">
      <PageHeader
        title={title}
        description={description}
        actions={discovery.actions}
        toolbar={
          <input
            type="search"
            placeholder="Filter keywords"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="field-input w-full min-w-[220px] max-w-xs"
          />
        }
        tabs={
          <TabBar
            tabs={TABS.map((t) => ({ value: t.status, label: t.label }))}
            value={status}
            onChange={(next) => {
              setStatus(next);
              setSelected(new Set());
            }}
          />
        }
      />

      {discovery.status && (
        <div className="border-b border-(--border) bg-(--surface-muted)/40 px-8 py-3">
          <div className="max-w-xl">{discovery.status}</div>
        </div>
      )}

      {isFetching && !isLoading && (
        <p className="border-b border-(--border) px-8 py-2 font-mono text-xs text-(--muted)">
          Syncing inbox
        </p>
      )}

      {status === "pending" && selectedIds.length > 0 && (
        <ActionBar count={selectedIds.length}>
          <button
            type="button"
            onClick={() => approveMutation.mutate(selectedIds)}
            disabled={approveMutation.isPending}
            className="btn btn-primary"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => setRejectOpen(true)}
            className="btn btn-secondary"
          >
            Reject
          </button>
        </ActionBar>
      )}

      <div className="flex-1 overflow-auto px-8 py-6">
        {isLoading && (
          <p className="text-sm text-(--muted)">Loading suggestions</p>
        )}
        {isError && (
          <div className="surface-card border-(--pastel-red-bg) bg-(--pastel-red-bg) px-4 py-3 text-sm text-(--pastel-red-text)">
            {(error as Error).message}. Check API on port 8000.
          </div>
        )}
        {!isLoading && !isError && items.length === 0 && (
          <EmptyState
            title={`No ${status} keywords`}
            description="Run a scan or adjust filters to populate this view."
          />
        )}

        {items.length > 0 && (
          <div className="surface-card overflow-hidden animate-fade-rise">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-(--border) bg-(--surface-muted) text-xs uppercase tracking-wider text-(--muted)">
                  {status === "pending" && (
                    <th className="w-10 px-4 py-3">
                      <input
                        type="checkbox"
                        checked={allSelected}
                        onChange={toggleAll}
                        aria-label="Select all"
                      />
                    </th>
                  )}
                  <th className="px-4 py-3 font-medium">Keyword</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">TikTok</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map(({ item, clusterMeta }, index) => {
                  const expanded = expandedId === item.id;
                  return (
                  <Fragment key={item.id}>
                  <tr
                    className={`stagger-item border-b border-(--border-subtle) last:border-b-0 hover:bg-(--surface-muted)/60${
                      clusterMeta?.isChild ? " bg-(--surface-muted)/30" : ""
                    }`}
                    style={{ ["--stagger-index" as string]: index }}
                  >
                    {status === "pending" && (
                      <td className="px-4 py-3.5">
                        <input
                          type="checkbox"
                          checked={selected.has(item.id)}
                          onChange={() => toggleOne(item.id)}
                          aria-label={`Select ${item.keyword}`}
                        />
                      </td>
                    )}
                    <td className="max-w-md px-4 py-3.5 font-medium text-(--foreground-strong)">
                      <div className={clusterMeta?.isChild ? "pl-6" : undefined}>
                        {item.keyword}
                        {clusterMeta && !clusterMeta.isChild && clusterMeta.count > 1 && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedClusters((prev) => {
                                const next = new Set(prev);
                                if (next.has(clusterMeta.id)) next.delete(clusterMeta.id);
                                else next.add(clusterMeta.id);
                                return next;
                              })
                            }
                            className="ml-2 rounded-(--radius-sm) bg-(--pastel-blue-bg) px-1.5 py-0.5 font-mono text-[0.65rem] uppercase text-(--pastel-blue-text)"
                          >
                            {clusterMeta.expanded
                              ? `${clusterMeta.count} variants`
                              : `+${clusterMeta.count - 1} variants`}
                          </button>
                        )}
                        {item.tiktok_unverified && (
                          <span className="ml-2 rounded-(--radius-sm) bg-(--pastel-amber-bg) px-1.5 py-0.5 font-mono text-[0.65rem] uppercase text-(--pastel-amber-text)">
                            unverified
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <ScoreBadge score={item.final_score} />
                    </td>
                    <td className="px-4 py-3.5 capitalize text-(--muted)">
                      {item.tiktok_status ?? "—"}
                      {item.tiktok_count_at_suggest != null && (
                        <span className="font-mono text-xs">
                          {" "}
                          ({item.tiktok_count_at_suggest})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-(--muted)">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3.5">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedId((prev) => (prev === item.id ? null : item.id))
                        }
                        className="btn btn-ghost px-2 py-1 text-(--muted)"
                      >
                        {expanded ? "Hide" : "Insights"}
                      </button>
                      {status === "approved" && (
                        <button
                          type="button"
                          onClick={() => setReportTarget(item)}
                          className="btn btn-ghost px-2 py-1 text-(--pastel-green-text)"
                        >
                          Report
                        </button>
                      )}
                      {status === "reported" && (
                        <button
                          type="button"
                          onClick={() => improveMutation.mutate(item.id)}
                          disabled={improveMutation.isPending}
                          className="btn btn-ghost px-2 py-1 text-(--pastel-blue-text) disabled:opacity-50"
                        >
                          Improve
                        </button>
                      )}
                    </td>
                  </tr>
                  {expanded && (
                    <tr key={`${item.id}-insights`} className="border-b border-(--border-subtle)">
                      <td
                        colSpan={status === "pending" ? 6 : 5}
                        className="p-0"
                      >
                        <SuggestionInsightPanel suggestion={item} />
                      </td>
                    </tr>
                  )}
                  </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {data && data.total > items.length && (
          <p className="mt-4 font-mono text-xs text-(--muted)">
            Showing {items.length} of {data.total}
          </p>
        )}
      </div>

      <RejectModal
        open={rejectOpen}
        count={selectedIds.length}
        onClose={() => setRejectOpen(false)}
        loading={rejectMutation.isPending}
        onConfirm={(reason, note) =>
          rejectMutation.mutate({
            keyword_ids: selectedIds,
            reason,
            note: note || undefined,
          })
        }
      />

      <ReportDialog
        suggestion={reportTarget}
        onClose={() => setReportTarget(null)}
        loading={reportMutation.isPending}
        onSubmit={(payload) => {
          if (reportTarget) {
            reportMutation.mutate({ id: reportTarget.id, payload });
          }
        }}
      />
    </div>
  );
}
