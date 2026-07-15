import type {
  BatchListResponse,
  FinalVideoListResponse,
  FeedbackAccuracy,
  MergeEnqueueResponse,
  MergeJob,
  MergePoolResponse,
  BulkVideoReviewResponse,
  ChannelListResponse,
  ExperimentListResponse,
  LearningInsightsResponse,
  PoolListResponse,
  PendingFinalsResponse,
  ProfileStage,
  TikTokProfile,
  TikTokProfileListResponse,
  PerformanceReport,
  PerformanceReportPayload,
  RejectReason,
  DiscoveryRunResponse,
  DiscoveryJobResponse,
  KeywordType,
  KeywordTypeFilter,
  ScanProgressResponse,
  ScanRunResponse,
  SettingsResponse,
  UpdateSettingsPayload,
  LLMModelsRequest,
  LLMModelsResponse,
  WeightProposal,
  WeightProposalListResponse,
  SuggestionListResponse,
  SuggestionStatus,
  VideoReviewStatus,
} from "./types";
import { normalizeSettingsResponse } from "./normalize-settings";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public activeJobId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export { ApiError };

function formatApiErrorBody(body: unknown, status: number): { message: string; activeJobId?: string } {
  if (!body || typeof body !== "object") {
    return { message: `Request failed (${status})` };
  }
  const record = body as {
    error?: { message?: string; details?: { active_job_id?: string } };
    detail?: string | { message?: string; active_job_id?: string } | Array<{ message?: string; msg?: string }>;
  };
  if (record.error?.message) {
    return {
      message: record.error.message,
      activeJobId: record.error.details?.active_job_id,
    };
  }
  if (typeof record.detail === "string") return { message: record.detail };
  if (record.detail && typeof record.detail === "object" && !Array.isArray(record.detail)) {
    return {
      message: record.detail.message ?? `Request failed (${status})`,
      activeJobId: record.detail.active_job_id,
    };
  }
  if (Array.isArray(record.detail)) {
    return {
      message: record.detail
        .map((item) => item.message ?? item.msg ?? "Invalid request")
        .join("; "),
    };
  }
  return { message: `Request failed (${status})` };
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
    const { message, activeJobId } = formatApiErrorBody(body, res.status);
    throw new ApiError(message, res.status, activeJobId);
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
    keyword_type?: KeywordType;
    limit?: number;
    offset?: number;
    search?: string;
    sort?: string;
    order?: "asc" | "desc";
  }) => {
    const q = new URLSearchParams();
    if (params.status) q.set("status", params.status);
    if (params.keyword_type) q.set("keyword_type", params.keyword_type);
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.search) q.set("search", params.search);
    if (params.sort) q.set("sort", params.sort);
    if (params.order) q.set("order", params.order);
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
    apiFetch<ScanRunResponse>("/api/v1/scan/run", {
      method: "POST",
      body: JSON.stringify({ channel_ids: [], force }),
    }),

  getScanStatus: (jobId: string) =>
    apiFetch<ScanProgressResponse>(`/api/v1/scan/status/${jobId}`),

  runDiscovery: (keywordTypeFilter: KeywordTypeFilter = "both", force = false) =>
    apiFetch<DiscoveryRunResponse>("/api/v1/discovery/run", {
      method: "POST",
      body: JSON.stringify({
        keyword_type_filter: keywordTypeFilter,
        force,
      }),
    }),

  cancelDiscoveryJob: (jobId: string) =>
    apiFetch<DiscoveryJobResponse>(`/api/v1/discovery/jobs/${jobId}/cancel`, {
      method: "POST",
    }),

  getDiscoveryJob: (jobId: string) =>
    apiFetch<DiscoveryJobResponse>(`/api/v1/discovery/jobs/${jobId}`),

  getSettings: () =>
    apiFetch<SettingsResponse>("/api/v1/settings").then(normalizeSettingsResponse),

  updateSettings: (payload: UpdateSettingsPayload) =>
    apiFetch<{ message: string }>("/api/v1/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  listLlmModels: (payload: LLMModelsRequest = {}) =>
    apiFetch<LLMModelsResponse>("/api/v1/settings/llm/models", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getInsights: () =>
    apiFetch<LearningInsightsResponse>("/api/v1/learning/insights"),

  runLearningCycle: () =>
    apiFetch<{ report_id: string; adjustments_made: number; proposals_created: number }>(
      "/api/v1/learning/cycle",
      { method: "POST" },
    ),

  listWeightProposals: (status = "pending") =>
    apiFetch<WeightProposalListResponse>(
      `/api/v1/learning/weight-proposals?status=${encodeURIComponent(status)}`,
    ),

  approveWeightProposal: (proposalId: string) =>
    apiFetch<{ message: string; proposal: WeightProposal }>(
      `/api/v1/learning/weight-proposals/${proposalId}/approve`,
      { method: "POST" },
    ),

  rejectWeightProposal: (proposalId: string) =>
    apiFetch<{ message: string; proposal: WeightProposal }>(
      `/api/v1/learning/weight-proposals/${proposalId}/reject`,
      { method: "POST" },
    ),

  submitPerformanceReport: (payload: PerformanceReportPayload) =>
    apiFetch<PerformanceReport>("/api/v1/performance/reports", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listPerformanceReports: (params?: { keyword?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.keyword?.trim()) q.set("keyword", params.keyword.trim());
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<PerformanceReport[]>(
      `/api/v1/performance/reports${qs ? `?${qs}` : ""}`,
    );
  },

  getFeedbackAccuracy: () =>
    apiFetch<FeedbackAccuracy>("/api/v1/feedback/accuracy"),

  listPendingFinals: (limit = 20) =>
    apiFetch<PendingFinalsResponse>(`/api/v1/feedback/pending-finals?limit=${limit}`),

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

  listMergePool: (params?: { suggestion_id?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.suggestion_id) q.set("suggestion_id", params.suggestion_id);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<MergePoolResponse>(`/api/v1/merge/pool${qs ? `?${qs}` : ""}`);
  },

  enqueueManualMerge: (videoIds: [string, string]) =>
    apiFetch<MergeEnqueueResponse>("/api/v1/merge/manual", {
      method: "POST",
      body: JSON.stringify({ video_ids: videoIds }),
    }),

  enqueueRandomMerge: (suggestionId?: string) =>
    apiFetch<MergeEnqueueResponse>("/api/v1/merge/random", {
      method: "POST",
      body: JSON.stringify({ suggestion_id: suggestionId }),
    }),

  getMergeJob: (jobId: string) =>
    apiFetch<MergeJob>(`/api/v1/merge/jobs/${jobId}`),

  listFinals: (limit = 50) =>
    apiFetch<FinalVideoListResponse>(`/api/v1/finals?limit=${limit}`),

  listProfiles: (stage?: ProfileStage) => {
    const q = stage ? `?stage=${stage}` : "";
    return apiFetch<TikTokProfileListResponse>(`/api/v1/profiles${q}`);
  },

  createProfile: (payload: {
    label: string;
    handle: string;
    stage: ProfileStage;
    notes?: string;
  }) =>
    apiFetch<TikTokProfile>("/api/v1/profiles", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateProfile: (
    id: string,
    payload: Partial<{
      label: string;
      handle: string;
      beta_eligible: boolean;
      notes: string;
    }>,
  ) =>
    apiFetch<TikTokProfile>(`/api/v1/profiles/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  promoteProfile: (id: string) =>
    apiFetch<TikTokProfile>(`/api/v1/profiles/${id}/promote`, { method: "POST" }),

  deleteProfile: (id: string) =>
    apiFetch<void>(`/api/v1/profiles/${id}`, { method: "DELETE" }),

  listPoolMedia: (poolType: ProfileStage, poolStatus = "ready") =>
    apiFetch<PoolListResponse>(
      `/api/v1/pools?pool_type=${poolType}&pool_status=${poolStatus}`,
    ),
};
