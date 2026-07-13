"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { FinalVideo } from "@/lib/api/types";

type Outcome = "success" | "neutral" | "failure";

export interface PerformanceReportPrefill {
  keyword?: string;
  suggestionId?: string;
  finalVideoId?: string;
}

interface PerformanceReportFormProps {
  onSubmitted?: () => void;
  prefill?: PerformanceReportPrefill | null;
}

const OUTCOME_TAG: Record<Outcome, string> = {
  success: "tag-green",
  neutral: "tag-yellow",
  failure: "tag-red",
};

export function PerformanceReportForm({ onSubmitted, prefill }: PerformanceReportFormProps) {
  const [keyword, setKeyword] = useState(prefill?.keyword ?? "");
  const [views, setViews] = useState("0");
  const [likes, setLikes] = useState("0");
  const [comments, setComments] = useState("0");
  const [shares, setShares] = useState("0");
  const [followersGained, setFollowersGained] = useState("0");
  const [notes, setNotes] = useState("");
  const [outcome, setOutcome] = useState<Outcome>("neutral");
  const [finalVideoId, setFinalVideoId] = useState<string | undefined>(prefill?.finalVideoId);
  const [message, setMessage] = useState<string | null>(null);

  const approvedSuggestions = useQuery({
    queryKey: ["suggestions", "approved", 100],
    queryFn: () => api.listSuggestions({ status: "approved", limit: 100, offset: 0 }),
  });

  const suggestionMap = useMemo(
    () =>
      new Map(
        (approvedSuggestions.data?.items ?? []).map((item) => [item.keyword, item.id]),
      ),
    [approvedSuggestions.data?.items],
  );

  const reportMutation = useMutation({
    mutationFn: () =>
      api.submitPerformanceReport({
        keyword: keyword.trim(),
        actual_views: Number(views),
        actual_likes: Number(likes),
        actual_comments: Number(comments),
        actual_shares: Number(shares),
        followers_gained: Number(followersGained),
        outcome,
        notes: notes.trim() || undefined,
        suggestion_id: prefill?.suggestionId ?? suggestionMap.get(keyword.trim()),
        final_video_id: finalVideoId,
      }),
    onSuccess: () => {
      setMessage("Performance report submitted.");
      setViews("0");
      setLikes("0");
      setComments("0");
      setShares("0");
      setFollowersGained("0");
      setNotes("");
      setOutcome("neutral");
      setKeyword("");
      setFinalVideoId(undefined);
      onSubmitted?.();
    },
    onError: (error: Error) => setMessage(error.message),
  });

  return (
    <section className="panel-section">
      <h2 className="font-editorial text-xl text-(--foreground-strong)">
        Report performance
      </h2>
      <p className="mt-1 text-sm text-(--muted)">
        Tie TikTok results back to a keyword after upload.
      </p>

      {message && (
        <p className="mt-4 surface-card bg-(--pastel-green-bg) px-3 py-2 text-sm text-(--pastel-green-text)">
          {message}
        </p>
      )}
      {approvedSuggestions.isError && (
        <p className="mt-4 text-sm text-(--pastel-red-text)">
          {(approvedSuggestions.error as Error).message}
        </p>
      )}

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <label className="sm:col-span-2">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-(--muted)">
            Keyword
          </span>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            list="approved-keyword-options"
            placeholder="ai storytelling hooks"
            className="field-input"
          />
          <datalist id="approved-keyword-options">
            {(approvedSuggestions.data?.items ?? []).map((item) => (
              <option key={item.id} value={item.keyword} />
            ))}
          </datalist>
        </label>

        {(
          [
            ["Views", views, setViews],
            ["Likes", likes, setLikes],
            ["Comments", comments, setComments],
            ["Shares", shares, setShares],
            ["Followers gained", followersGained, setFollowersGained],
          ] as const
        ).map(([label, value, setter]) => (
          <label key={label}>
            <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-(--muted)">
              {label}
            </span>
            <input
              type="number"
              min={0}
              value={value}
              onChange={(e) => setter(e.target.value)}
              className="field-input"
            />
          </label>
        ))}

        <label className="sm:col-span-2">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-(--muted)">
            Outcome
          </span>
          <select
            value={outcome}
            onChange={(e) => setOutcome(e.target.value as Outcome)}
            className="field-input"
          >
            <option value="success">Success</option>
            <option value="neutral">Neutral</option>
            <option value="failure">Failure</option>
          </select>
          <span className={`tag-pill mt-2 inline-flex ${OUTCOME_TAG[outcome]}`}>{outcome}</span>
        </label>

        <label className="sm:col-span-2">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-(--muted)">
            Notes
          </span>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="field-input"
            placeholder="Hook timing, audience reaction, repost angle"
          />
        </label>
      </div>

      <button
        type="button"
        onClick={() => reportMutation.mutate()}
        disabled={
          reportMutation.isPending ||
          !keyword.trim() ||
          Number.isNaN(Number(views)) ||
          Number(views) < 0
        }
        className="btn btn-primary mt-5"
      >
        {reportMutation.isPending ? "Submitting" : "Submit report"}
      </button>
    </section>
  );
}

export function PendingFinalPicker({
  items,
  onSelect,
}: {
  items: FinalVideo[];
  onSelect: (final: FinalVideo) => void;
}) {
  if (items.length === 0) return null;

  return (
    <section className="panel-section">
      <h2 className="font-editorial text-xl text-(--foreground-strong)">
        Awaiting feedback
      </h2>
      <p className="mt-1 text-sm text-(--muted)">
        Finals without a performance report yet.
      </p>
      <ul className="mt-4 space-y-2">
        {items.map((final) => (
          <li key={final.id}>
            <button
              type="button"
              onClick={() => onSelect(final)}
              className="btn btn-secondary w-full justify-start text-left"
            >
              <span className="font-medium">{final.keyword ?? "Untitled final"}</span>
              <span className="ml-2 font-mono text-xs text-(--muted)">
                {final.file_path.split("/").pop()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
