"use client";

import type { RejectReason } from "@/lib/api/types";

const REASONS: { value: RejectReason; label: string }[] = [
  { value: "too_broad", label: "Too broad" },
  { value: "too_competitive", label: "Too competitive" },
  { value: "off_topic", label: "Off topic" },
  { value: "poor_quality", label: "Poor quality" },
  { value: "other", label: "Other" },
];

interface RejectModalProps {
  open: boolean;
  count: number;
  onClose: () => void;
  onConfirm: (reason: RejectReason, note: string) => void;
  loading?: boolean;
}

export function RejectModal({
  open,
  count,
  onClose,
  onConfirm,
  loading,
}: RejectModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          onConfirm(
            fd.get("reason") as RejectReason,
            String(fd.get("note") ?? ""),
          );
        }}
      >
        <h2 className="text-lg font-semibold text-zinc-900">
          Reject {count} keyword{count !== 1 ? "s" : ""}
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Feedback trains the learning agent immediately.
        </p>
        <label className="mt-4 block text-sm font-medium text-zinc-700">
          Reason
          <select
            name="reason"
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            defaultValue="too_broad"
          >
            {REASONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-sm font-medium text-zinc-700">
          Note (optional)
          <textarea
            name="note"
            rows={3}
            className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            placeholder="Why these keywords don't fit..."
          />
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
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? "Rejecting..." : "Reject"}
          </button>
        </div>
      </form>
    </div>
  );
}
