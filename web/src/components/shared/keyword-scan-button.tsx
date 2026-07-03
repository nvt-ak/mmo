"use client";

import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";
import { useDiscoveryJob } from "@/hooks/use-discovery-job";
import { DiscoveryProgressBar } from "@/components/shared/discovery-progress-bar";
import { isDiscoveryJobStale } from "@/lib/discovery/stale-job";
import type { KeywordTypeFilter } from "@/lib/api/types";

interface KeywordScanButtonProps {
  label?: string;
  keywordTypeFilter?: KeywordTypeFilter;
  onComplete?: () => void;
  showStatus?: boolean;
  variant?: "primary" | "secondary";
}

type ScanMutationInput = { force?: boolean } | undefined;

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
    mutationFn: async (input?: ScanMutationInput) => {
      const force = input?.force ?? false;
      clearStreamError();
      try {
        const { job_id } = await api.runDiscovery(keywordTypeFilter, force);
        return job_id;
      } catch (err) {
        if (err instanceof ApiError && err.status === 409 && err.activeJobId && !force) {
          const activeJob = await api.getDiscoveryJob(err.activeJobId);
          if (isDiscoveryJobStale(activeJob)) {
            const { job_id } = await api.runDiscovery(keywordTypeFilter, true);
            return job_id;
          }
          return err.activeJobId;
        }
        throw err;
      }
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
      <div className="flex justify-end gap-2">
        {showStatus && isTracking && (
          <button
            type="button"
            onClick={() => scanMutation.mutate({ force: true })}
            disabled={scanMutation.isPending}
            className="btn btn-secondary text-xs"
          >
            Start over
          </button>
        )}
        <button
          type="button"
          onClick={() => scanMutation.mutate(undefined)}
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
          {progress.keywords_generated > 0
            ? `Discovery complete — ${progress.keywords_generated} keyword${progress.keywords_generated === 1 ? "" : "s"}`
            : "Discovery complete — 0 keywords saved (TikTok gate blocked or no matches for this track)"}
        </p>
      )}
    </div>
  );
}
