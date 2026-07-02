"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/lib/api/client";
import type { DiscoveryJobResponse, KeywordTypeFilter } from "@/lib/api/types";

interface KeywordScanButtonProps {
  label?: string;
  keywordTypeFilter?: KeywordTypeFilter;
  onComplete?: () => void;
  showStatus?: boolean;
  variant?: "primary" | "secondary";
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function KeywordScanButton({
  label = "Run trend discovery",
  keywordTypeFilter = "both",
  onComplete,
  showStatus = true,
  variant = "primary",
}: KeywordScanButtonProps) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState<DiscoveryJobResponse | null>(null);

  const scanMutation = useMutation({
    mutationFn: async () => {
      setProgress(null);
      const { job_id } = await api.runDiscovery(keywordTypeFilter);
      for (;;) {
        const status = await api.getDiscoveryJob(job_id);
        setProgress(status);
        if (status.status === "completed") return status;
        if (status.status === "failed") {
          throw new Error(status.error_message ?? "Discovery failed");
        }
        await sleep(2000);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["suggestions"] });
      onComplete?.();
    },
  });

  const statusMessage = useMemo(() => {
    const cap = progress?.max_keywords ?? 10;
    if (scanMutation.isError) return (scanMutation.error as Error).message;
    if (!scanMutation.isPending && progress?.status === "completed") {
      const count = progress.keywords_generated ?? 0;
      return `Discovery complete — ${count} keyword${count === 1 ? "" : "s"}`;
    }
    if (scanMutation.isPending && progress) {
      if (progress.status === "running" && (progress.keywords_generated ?? 0) > 0) {
        return `Discovering… ${progress.keywords_generated}/${cap} keywords`;
      }
      if (
        progress.status === "running" ||
        (progress.status === "started" && (progress.sources_scanned ?? 0) >= 1)
      ) {
        return "Checking TikTok gates…";
      }
      if (progress.status === "started") {
        return "Fetching YouTube trends…";
      }
    }
    if (scanMutation.isPending) return "Starting discovery…";
    return null;
  }, [scanMutation.isError, scanMutation.error, scanMutation.isPending, progress]);

  const busy = scanMutation.isPending;
  const btnClass = variant === "secondary" ? "btn btn-secondary" : "btn btn-primary";

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={() => scanMutation.mutate()}
        disabled={busy}
        className={btnClass}
      >
        {busy ? "Discovering…" : label}
      </button>
      {showStatus && statusMessage && (
        <p className="max-w-xs text-right text-xs text-(--muted)">{statusMessage}</p>
      )}
    </div>
  );
}
