const STORAGE_KEY = "videoscout:active-discovery-job";

export interface ActiveDiscoveryJob {
  jobId: string;
}

export function isDiscoveryJobInProgress(status: string): boolean {
  return status === "started" || status === "running";
}

export function readActiveDiscoveryJob(): ActiveDiscoveryJob | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ActiveDiscoveryJob;
    if (!parsed?.jobId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeActiveDiscoveryJob(jobId: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ jobId }));
}

export function clearActiveDiscoveryJob(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
