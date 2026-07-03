import type { DiscoveryJobResponse } from "@/lib/api/types";

const NEVER_STARTED_STALE_MS = 5 * 60 * 1000;
const ACTIVE_JOB_STALE_MS = 30 * 60 * 1000;

export function isDiscoveryJobStale(job: DiscoveryJobResponse): boolean {
  if (job.status !== "started" && job.status !== "running") {
    return false;
  }

  const activityAt = new Date(job.started_at ?? job.created_at).getTime();
  const ageMs = Date.now() - activityAt;

  if (job.status === "started" && !job.started_at) {
    return ageMs >= NEVER_STARTED_STALE_MS;
  }

  return ageMs >= ACTIVE_JOB_STALE_MS;
}
