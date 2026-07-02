import type { DiscoveryJobResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function parseDiscoveryEvent(data: string): DiscoveryJobResponse {
  return JSON.parse(data) as DiscoveryJobResponse;
}

function handleTerminal(
  job: DiscoveryJobResponse,
  onComplete: (job: DiscoveryJobResponse) => void,
  onError: (error: Error) => void,
): boolean {
  if (job.status === "completed") {
    onComplete(job);
    return true;
  }
  if (job.status === "failed") {
    onError(new Error(job.error_message ?? "Discovery failed"));
    return true;
  }
  return false;
}

export function subscribeDiscoveryJob(
  jobId: string,
  handlers: {
    onUpdate: (job: DiscoveryJobResponse) => void;
    onComplete: (job: DiscoveryJobResponse) => void;
    onError: (error: Error) => void;
    getDiscoveryJob: (jobId: string) => Promise<DiscoveryJobResponse>;
  },
): () => void {
  const source = new EventSource(
    `${API_BASE}/api/v1/discovery/jobs/${jobId}/stream`,
  );
  let closed = false;

  const close = () => {
    if (!closed) {
      closed = true;
      source.close();
    }
  };

  source.onmessage = (event) => {
    try {
      const job = parseDiscoveryEvent(event.data);
      handlers.onUpdate(job);
      if (handleTerminal(job, handlers.onComplete, handlers.onError)) {
        close();
      }
    } catch (error) {
      close();
      handlers.onError(
        error instanceof Error ? error : new Error("Invalid discovery event"),
      );
    }
  };

  source.onerror = () => {
    if (closed) return;
    close();
    void handlers
      .getDiscoveryJob(jobId)
      .then((job) => {
        handlers.onUpdate(job);
        if (handleTerminal(job, handlers.onComplete, handlers.onError)) {
          return;
        }
        handlers.onError(new Error("Lost connection to discovery stream"));
      })
      .catch((error) => {
        handlers.onError(
          error instanceof Error ? error : new Error("Discovery stream failed"),
        );
      });
  };

  return close;
}
