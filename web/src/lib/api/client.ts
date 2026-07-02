import type {
  BatchListResponse,
  BulkVideoReviewResponse,
  ChannelListResponse,
  ExperimentListResponse,
  LearningInsightsResponse,
  PerformanceReport,
  PerformanceReportPayload,
  RejectReason,
  SettingsResponse,
  SuggestionListResponse,
  SuggestionStatus,
  VideoReviewStatus,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message =
      body?.error?.message ??
      body?.detail ??
      `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<{ status: string }>("/health"),

  listSuggestions: (params: {
    status?: SuggestionStatus;
    limit?: number;
    offset?: number;
    search?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.status) q.set("status", params.status);
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.search) q.set("search", params.search);
    const qs = q.toString();
    return apiFetch<SuggestionListResponse>(
      `/api/v1/suggestions${qs ? `?${qs}` : ""}`,
    );
  },

  bulkApprove: (keywordIds: string[]) =>
    apiFetch<{ approved_count: number }>("/api/v1/suggestions/bulk-approve", {
      method: "POST",
      body: JSON.stringify({ keyword_ids: keywordIds }),
    }),

  bulkReject: (payload: {
    keyword_ids: string[];
    reason: RejectReason;
    note?: string;
  }) =>
    apiFetch<{ rejected_count: number }>("/api/v1/suggestions/bulk-reject", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  reportSuggestion: (
    id: string,
    payload: {
      actual_views: number;
      actual_likes: number;
      actual_comments: number;
      actual_shares: number;
      outcome: "success" | "neutral" | "failure";
    },
  ) =>
    apiFetch<{ reported: boolean; engagement_rate: number; warning?: string }>(
      `/api/v1/suggestions/${id}/report`,
      { method: "POST", body: JSON.stringify(payload) },
    ),

  improveSuggestion: (keywordId: string, force = false) =>
    apiFetch<{ message: string; new_keywords_generated: number }>(
      "/api/v1/suggestions/improve",
      {
        method: "POST",
        body: JSON.stringify({ keyword_id: keywordId, force }),
      },
    ),

  listChannels: () =>
    apiFetch<ChannelListResponse>("/api/v1/sources/channels"),

  addChannel: (channel_id: string, scan_enabled = true) =>
    apiFetch<{ channel_id: string; name?: string }>("/api/v1/sources/channels", {
      method: "POST",
      body: JSON.stringify({ channel_id, scan_enabled }),
    }),

  updateChannelScan: (channelId: string, scan_enabled: boolean) =>
    apiFetch<{ scan_enabled: boolean }>(
      `/api/v1/sources/channels/${channelId}?scan_enabled=${scan_enabled}`,
      { method: "PUT" },
    ),

  deleteChannel: (channelId: string) =>
    apiFetch<void>(`/api/v1/sources/channels/${channelId}`, {
      method: "DELETE",
    }),

  runScan: (force = false) =>
    apiFetch<{ job_id: string; status: string }>("/api/v1/scan/run", {
      method: "POST",
      body: JSON.stringify({ channel_ids: [], force }),
    }),

  getSettings: () => apiFetch<SettingsResponse>("/api/v1/settings"),

  updateSettings: (payload: Partial<SettingsResponse>) =>
    apiFetch<{ message: string }>("/api/v1/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  getInsights: () =>
    apiFetch<LearningInsightsResponse>("/api/v1/learning/insights"),

  runLearningCycle: () =>
    apiFetch<{ report_id: string; adjustments_made: number }>(
      "/api/v1/learning/cycle",
      { method: "POST" },
    ),

  submitPerformanceReport: (payload: PerformanceReportPayload) =>
    apiFetch<PerformanceReport>("/api/v1/performance/reports", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listPerformanceReports: (keyword?: string) => {
    const q = new URLSearchParams();
    if (keyword?.trim()) q.set("keyword", keyword.trim());
    const qs = q.toString();
    return apiFetch<PerformanceReport[]>(
      `/api/v1/performance/reports${qs ? `?${qs}` : ""}`,
    );
  },

  listExperiments: (status?: string) => {
    const q = new URLSearchParams();
    if (status?.trim()) q.set("status", status.trim());
    const qs = q.toString();
    return apiFetch<ExperimentListResponse>(
      `/api/v1/experiments${qs ? `?${qs}` : ""}`,
    );
  },

  analyzeExperiments: () =>
    apiFetch<{
      total_experiments: number;
      patterns: Record<string, unknown>;
      weight_suggestions: Array<Record<string, unknown>>;
    }>("/api/v1/experiments/analyze", {
      method: "POST",
    }),

  listBatchVideos: (params?: { review_status?: VideoReviewStatus; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.review_status) q.set("review_status", params.review_status);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<BatchListResponse>(`/api/v1/batch${qs ? `?${qs}` : ""}`);
  },

  reviewVideo: (videoId: string, action: "keep" | "skip") =>
    apiFetch<{ id: string; review_status: VideoReviewStatus }>(
      `/api/v1/videos/${videoId}/review`,
      { method: "POST", body: JSON.stringify({ action }) },
    ),

  bulkReviewVideos: (videoIds: string[], action: "keep" | "skip") =>
    apiFetch<BulkVideoReviewResponse>("/api/v1/batch/review", {
      method: "POST",
      body: JSON.stringify({ video_ids: videoIds, action }),
    }),
};

export { ApiError };
