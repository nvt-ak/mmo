"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";

type Outcome = "success" | "neutral" | "failure";

interface PerformanceReportFormProps {
  onSubmitted?: () => void;
}

export function PerformanceReportForm({ onSubmitted }: PerformanceReportFormProps) {
  const [keyword, setKeyword] = useState("");
  const [views, setViews] = useState("0");
  const [likes, setLikes] = useState("0");
  const [comments, setComments] = useState("0");
  const [followersGained, setFollowersGained] = useState("0");
  const [outcome, setOutcome] = useState<Outcome>("neutral");
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
        followers_gained: Number(followersGained),
        outcome,
        suggestion_id: suggestionMap.get(keyword.trim()),
      }),
    onSuccess: () => {
      setMessage("Performance report submitted.");
      setViews("0");
      setLikes("0");
      setComments("0");
      setFollowersGained("0");
      setOutcome("neutral");
      setKeyword("");
      onSubmitted?.();
    },
    onError: (error: Error) => setMessage(error.message),
  });

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-zinc-900">Report performance</h2>
      <p className="mt-1 text-xs text-zinc-500">
        Pick an approved keyword or enter one manually.
      </p>

      {message && <p className="mt-3 rounded-lg bg-zinc-100 px-3 py-2 text-sm text-zinc-700">{message}</p>}
      {approvedSuggestions.isError && (
        <p className="mt-3 text-sm text-red-600">
          {(approvedSuggestions.error as Error).message}
        </p>
      )}

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="sm:col-span-2">
          <span className="mb-1 block text-xs font-medium uppercase text-zinc-500">Keyword</span>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            list="approved-keyword-options"
            placeholder="e.g. ai storytelling hooks"
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          />
          <datalist id="approved-keyword-options">
            {(approvedSuggestions.data?.items ?? []).map((item) => (
              <option key={item.id} value={item.keyword} />
            ))}
          </datalist>
        </label>

        <label>
          <span className="mb-1 block text-xs font-medium uppercase text-zinc-500">Views</span>
          <input
            type="number"
            min={0}
            value={views}
            onChange={(e) => setViews(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-medium uppercase text-zinc-500">Likes</span>
          <input
            type="number"
            min={0}
            value={likes}
            onChange={(e) => setLikes(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-medium uppercase text-zinc-500">Comments</span>
          <input
            type="number"
            min={0}
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          />
        </label>

        <label>
          <span className="mb-1 block text-xs font-medium uppercase text-zinc-500">Followers gained</span>
          <input
            type="number"
            min={0}
            value={followersGained}
            onChange={(e) => setFollowersGained(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          />
        </label>

        <label className="sm:col-span-2">
          <span className="mb-1 block text-xs font-medium uppercase text-zinc-500">Outcome</span>
          <select
            value={outcome}
            onChange={(e) => setOutcome(e.target.value as Outcome)}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          >
            <option value="success">Success</option>
            <option value="neutral">Neutral</option>
            <option value="failure">Failure</option>
          </select>
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
        className="mt-4 rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        {reportMutation.isPending ? "Submitting…" : "Submit report"}
      </button>
    </section>
  );
}
