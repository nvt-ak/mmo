"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import { subscribeDiscoveryJob } from "@/lib/api/discovery-stream";
import {
  clearActiveDiscoveryJob,
  isDiscoveryJobInProgress,
  readActiveDiscoveryJob,
  writeActiveDiscoveryJob,
} from "@/lib/discovery/active-job";
import type { DiscoveryJobResponse } from "@/lib/api/types";

interface UseDiscoveryJobOptions {
  onComplete?: () => void;
}

export function useDiscoveryJob({ onComplete }: UseDiscoveryJobOptions = {}) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState<DiscoveryJobResponse | null>(null);
  const [isTracking, setIsTracking] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const cleanupStream = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
  }, []);

  const finishSuccess = useCallback(
    (job: DiscoveryJobResponse) => {
      setProgress(job);
      setIsTracking(false);
      setStreamError(null);
      clearActiveDiscoveryJob();
      cleanupStream();
      void queryClient.invalidateQueries({ queryKey: ["suggestions"] });
      onComplete?.();
    },
    [cleanupStream, onComplete, queryClient],
  );

  const finishError = useCallback(
    (error: Error) => {
      setIsTracking(false);
      setStreamError(error.message);
      clearActiveDiscoveryJob();
      cleanupStream();
    },
    [cleanupStream],
  );

  const attachToJob = useCallback(
    (jobId: string, persist: boolean) => {
      cleanupStream();
      setStreamError(null);
      if (persist) writeActiveDiscoveryJob(jobId);
      setIsTracking(true);
      unsubscribeRef.current = subscribeDiscoveryJob(jobId, {
        onUpdate: setProgress,
        onComplete: finishSuccess,
        onError: finishError,
        getDiscoveryJob: api.getDiscoveryJob,
      });
    },
    [cleanupStream, finishError, finishSuccess],
  );

  useEffect(() => {
    let cancelled = false;

    const resume = async () => {
      const active = readActiveDiscoveryJob();
      if (!active) return;

      try {
        const job = await api.getDiscoveryJob(active.jobId);
        if (cancelled) return;
        if (isDiscoveryJobInProgress(job.status)) {
          setProgress(job);
          attachToJob(active.jobId, false);
        } else {
          clearActiveDiscoveryJob();
        }
      } catch {
        if (!cancelled) clearActiveDiscoveryJob();
      }
    };

    void resume();

    return () => {
      cancelled = true;
      cleanupStream();
    };
  }, [attachToJob, cleanupStream]);

  return {
    progress,
    isTracking,
    streamError,
    attachToJob,
    clearStreamError: () => setStreamError(null),
  };
}
