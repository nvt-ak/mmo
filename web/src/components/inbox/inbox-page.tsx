"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { RejectReason, Suggestion, SuggestionStatus } from "@/lib/api/types";
import { ScoreBadge } from "@/components/shared/score-badge";
import { RejectModal } from "./reject-modal";
import { ReportDialog } from "./report-dialog";

const TABS: { status: SuggestionStatus; label: string }[] = [
  { status: "pending", label: "Pending" },
  { status: "approved", label: "Approved" },
  { status: "reported", label: "Reported" },
  { status: "rejected", label: "Rejected" },
];

export function InboxPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<SuggestionStatus>("pending");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reportTarget, setReportTarget] = useState<Suggestion | null>(null);

  const queryKey = ["suggestions", status, search];

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey,
    queryFn: () => api.listSuggestions({ status, limit: 100, search: search || undefined }),
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

  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-[var(--border)] bg-white px-8 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-zinc-900">Inbox</h1>
            <p className="mt-1 text-sm text-zinc-500">
              Review keyword suggestions from daily scans
              {isFetching && !isLoading ? " · refreshing…" : ""}
            </p>
          </div>
          <input
            type="search"
            placeholder="Search keywords…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full max-w-xs rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          />
        </div>
        <div className="mt-4 flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.status}
              type="button"
              onClick={() => {
                setStatus(tab.status);
                setSelected(new Set());
              }}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                status === tab.status
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-100"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {status === "pending" && selectedIds.length > 0 && (
        <div className="flex items-center gap-2 border-b border-[var(--border)] bg-zinc-50 px-8 py-3">
          <span className="text-sm text-zinc-600">{selectedIds.length} selected</span>
          <button
            type="button"
            onClick={() => approveMutation.mutate(selectedIds)}
            disabled={approveMutation.isPending}
            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            Approve
          </button>
          <button
            type="button"
            onClick={() => setRejectOpen(true)}
            className="rounded-lg border border-zinc-300 px-3 py-1.5 text-sm text-zinc-700 hover:bg-white"
          >
            Reject
          </button>
        </div>
      )}

      <div className="flex-1 overflow-auto px-8 py-4">
        {isLoading && (
          <p className="text-sm text-zinc-500">Loading suggestions…</p>
        )}
        {isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {(error as Error).message}. Is the API running on port 8000?
          </div>
        )}
        {!isLoading && !isError && items.length === 0 && (
          <p className="text-sm text-zinc-500">No {status} suggestions.</p>
        )}

        {items.length > 0 && (
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-xs uppercase tracking-wide text-zinc-500">
                {status === "pending" && (
                  <th className="w-10 py-3 pr-2">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={toggleAll}
                      aria-label="Select all"
                    />
                  </th>
                )}
                <th className="py-3 pr-4 font-medium">Keyword</th>
                <th className="py-3 pr-4 font-medium">Score</th>
                <th className="py-3 pr-4 font-medium">TikTok</th>
                <th className="py-3 pr-4 font-medium">Created</th>
                <th className="py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-zinc-100 hover:bg-zinc-50/80">
                  {status === "pending" && (
                    <td className="py-3 pr-2">
                      <input
                        type="checkbox"
                        checked={selected.has(item.id)}
                        onChange={() => toggleOne(item.id)}
                        aria-label={`Select ${item.keyword}`}
                      />
                    </td>
                  )}
                  <td className="max-w-md py-3 pr-4 font-medium text-zinc-900">
                    {item.keyword}
                  </td>
                  <td className="py-3 pr-4">
                    <ScoreBadge score={item.final_score} />
                  </td>
                  <td className="py-3 pr-4 capitalize text-zinc-600">
                    {item.tiktok_status ?? "—"}
                    {item.tiktok_count_at_suggest != null && (
                      <span className="text-zinc-400"> ({item.tiktok_count_at_suggest})</span>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-zinc-500">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3">
                    {status === "approved" && (
                      <button
                        type="button"
                        onClick={() => setReportTarget(item)}
                        className="text-sm font-medium text-emerald-700 hover:underline"
                      >
                        Report
                      </button>
                    )}
                    {status === "reported" && (
                      <button
                        type="button"
                        onClick={() => improveMutation.mutate(item.id)}
                        disabled={improveMutation.isPending}
                        className="text-sm font-medium text-indigo-700 hover:underline disabled:opacity-50"
                      >
                        Improve
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {data && data.total > items.length && (
          <p className="mt-4 text-xs text-zinc-400">
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
