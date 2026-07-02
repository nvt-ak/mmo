"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useDiscoveryJob } from "@/hooks/use-discovery-job";
import { DiscoveryProgressBar } from "@/components/shared/discovery-progress-bar";
import type { KeywordTypeFilter } from "@/lib/api/types";

interface KeywordScanButtonProps {
  label?: string;
  keywordTypeFilter?: KeywordTypeFilter;
  onComplete?: () => void;
  showStatus?: boolean;
  variant?: "primary" | "secondary";
}

export function KeywordScanButton({
  label = "Run trend discovery",
  keywordTypeFilter = "both",
  onComplete,
  showStatus = true,
  variant = "primary",
}: KeywordScanButtonProps) {
  const { progress, isTracking, streamError, attachToJob, clearStreamError } =
    useDiscoveryJob({ onComplete });

  const scanMutation = useMutation({
    mutationFn: async () => {
      clearStreamError();
      const { job_id } = await api.runDiscovery(keywordTypeFilter);
      return job_id;
    },
    onSuccess: (jobId) => {
      attachToJob(jobId, true);
    },
  });

  const busy = isTracking || scanMutation.isPending;
  const btnClass = variant === "secondary" ? "btn btn-secondary" : "btn btn-primary";
  const errorMessage =
    streamError ??
    (scanMutation.isError ? (scanMutation.error as Error).message : null);

  return (
    <div className="flex w-full min-w-[260px] max-w-sm flex-col items-stretch gap-2.5">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => scanMutation.mutate()}
          disabled={busy}
          className={btnClass}
        >
          {busy ? "Discovering…" : label}
        </button>
      </div>
      {showStatus && busy && progress && !errorMessage && (
        <DiscoveryProgressBar progress={progress} />
      )}
      {showStatus && errorMessage && (
        <p className="text-right text-xs text-(--muted)">{errorMessage}</p>
      )}
      {showStatus && !busy && progress?.status === "completed" && !errorMessage && (
        <p className="text-right text-xs text-(--muted)">
          {progress.progress_label}
          {progress.keywords_generated > 0
            ? ` — ${progress.keywords_generated} keyword${progress.keywords_generated === 1 ? "" : "s"}`
            : ""}
        </p>
      )}
    </div>
  );
}
