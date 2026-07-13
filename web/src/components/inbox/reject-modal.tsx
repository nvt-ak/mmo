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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <form
        className="surface-card w-full max-w-md p-6"
        onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData(e.currentTarget);
          onConfirm(
            fd.get("reason") as RejectReason,
            String(fd.get("note") ?? ""),
          );
        }}
      >
        <h2 className="font-editorial text-2xl text-(--foreground-strong)">
          Reject {count} keyword{count !== 1 ? "s" : ""}
        </h2>
        <p className="mt-2 text-sm text-(--muted)">
          Reason is stored for the learning agent.
        </p>
        <label className="mt-5 block text-sm font-medium text-(--foreground)">
          Reason
          <select
            name="reason"
            className="field-input mt-1.5"
            defaultValue="too_broad"
          >
            {REASONS.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-sm font-medium text-(--foreground)">
          Note (optional)
          <textarea
            name="note"
            rows={3}
            className="field-input mt-1.5"
            placeholder="Why these keywords do not fit"
          />
        </label>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="btn btn-ghost">
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? "Rejecting" : "Reject"}
          </button>
        </div>
      </form>
    </div>
  );
}
