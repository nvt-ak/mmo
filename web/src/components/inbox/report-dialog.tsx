"use client";

import type { Suggestion } from "@/lib/api/types";

interface ReportDialogProps {
  suggestion: Suggestion | null;
  onClose: () => void;
  onSubmit: (payload: {
    actual_views: number;
    actual_likes: number;
    actual_comments: number;
    actual_shares: number;
    outcome: "success" | "neutral" | "failure";
  }) => void;
  loading?: boolean;
}

export function ReportDialog({
  suggestion,
  onClose,
  onSubmit,
  loading,
}: ReportDialogProps) {
  if (!suggestion) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          onSubmit({
            actual_views: Number(fd.get("actual_views")),
            actual_likes: Number(fd.get("actual_likes")),
            actual_comments: Number(fd.get("actual_comments") || 0),
            actual_shares: Number(fd.get("actual_shares") || 0),
            outcome: fd.get("outcome") as "success" | "neutral" | "failure",
          });
        }}
      >
        <h2 className="text-lg font-semibold text-zinc-900">Report results</h2>
        <p className="mt-1 truncate text-sm text-zinc-500">{suggestion.keyword}</p>

        <div className="mt-4 grid grid-cols-2 gap-3">
          {[
            ["actual_views", "Views", "1500"],
            ["actual_likes", "Likes", "120"],
            ["actual_comments", "Comments", "15"],
            ["actual_shares", "Shares", "8"],
          ].map(([name, label, placeholder]) => (
            <label key={name} className="text-sm font-medium text-zinc-700">
              {label}
              <input
                name={name}
                type="number"
                min={0}
                required={name === "actual_views" || name === "actual_likes"}
                defaultValue={placeholder}
                className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              />
            </label>
          ))}
        </div>

        <label className="mt-3 block text-sm font-medium text-zinc-700">
          Outcome
          <select
            name="outcome"
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            defaultValue="success"
          >
            <option value="success">Success</option>
            <option value="neutral">Neutral</option>
            <option value="failure">Failure</option>
          </select>
        </label>

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm text-zinc-600 hover:bg-zinc-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {loading ? "Saving..." : "Save report"}
          </button>
        </div>
      </form>
    </div>
  );
}
