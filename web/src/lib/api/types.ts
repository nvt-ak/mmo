export type SuggestionStatus = "pending" | "approved" | "rejected" | "reported";

export interface ComponentScores {
  relevance: number;
  specificity: number;
  saturation: number;
  trend: number;
  video_performance: number;
}

export interface Suggestion {
  id: string;
  keyword: string;
  status: SuggestionStatus;
  final_score: number;
  component_scores: ComponentScores;
  suggested_by: Array<{
    source: string;
    video_id?: string;
    channel_id?: string;
    score: number;
    timestamp: string;
  }>;
  tiktok_status?: string;
  tiktok_count_at_suggest?: number;
  created_at: string;
  approved_at?: string;
  rejected_at?: string;
  reject_reason?: string;
  reject_note?: string;
  reported_at?: string;
  actual_views?: number;
  actual_likes?: number;
  outcome?: string;
}

export interface SuggestionListResponse {
  items: Suggestion[];
  total: number;
  limit: number;
  offset: number;
}

export interface Channel {
  id: string;
  channel_id: string;
  name?: string;
  scan_enabled: boolean;
  last_scan_at?: string;
  video_count: number;
  suggestion_count: number;
  created_at: string;
}

export interface ChannelListResponse {
  items: Channel[];
  total: number;
}

export interface ScoringWeights {
  relevance: number;
  specificity: number;
  saturation: number;
  trend: number;
  video_performance: number;
}

export interface SettingsResponse {
  weights: ScoringWeights;
  filters: Record<string, number>;
  niche: {
    topics: string[];
    preferred_language: string;
    target_audience?: string;
  };
  llm: { model: string; temperature: number; api_key_set: boolean };
  tiktok: { api_key_set: boolean; check_enabled: boolean };
}

export interface LearningInsightsResponse {
  timestamp: string;
  rejection_patterns?: Array<{
    reason: string;
    frequency: number;
    suggested_action: string;
  }>;
  success_patterns?: Array<{
    keyword_example: string;
    avg_views: number;
    avg_engagement_rate: number;
    replication_strategy: string;
  }>;
  summary_metrics?: Record<string, number>;
  new_keywords_generated: number;
}

export interface PerformanceReport {
  id: string;
  keyword: string;
  suggestion_id?: string;
  actual_views: number;
  actual_likes?: number;
  actual_comments?: number;
  actual_shares?: number;
  followers_gained?: number;
  engagement_rate?: number;
  outcome?: string;
  notes?: string;
  reported_at: string;
}

export interface PerformanceReportPayload {
  keyword: string;
  actual_views: number;
  actual_likes?: number;
  actual_comments?: number;
  actual_shares?: number;
  followers_gained?: number;
  outcome?: string;
  notes?: string;
  suggestion_id?: string;
}

export interface Experiment {
  id: string;
  keyword: string;
  channel_id?: string;
  channel_subscribers?: number;
  creator_avg_views?: number;
  views_vs_baseline?: number;
  suggestion_source: string;
  agent_suggested_score?: number;
  predicted_score: number;
  prediction_reasoning?: string;
  actual_views?: number;
  actual_engagement?: number;
  actual_retention?: number;
  test_status: string;
  user_rating?: number;
  user_comments?: string;
  accuracy?: number;
  outcome_type?: string;
  reported_at?: string;
  created_at: string;
}

export interface ExperimentListResponse {
  items: Experiment[];
  total: number;
}

export type VideoReviewStatus = "pending" | "in_pool" | "skipped" | "merged";

export interface VideoAsset {
  id: string;
  youtube_video_id: string;
  channel_id: string;
  suggestion_id?: string;
  title: string;
  view_count?: number;
  duration_sec?: number;
  youtube_url: string;
  file_path: string;
  status: string;
  review_status: VideoReviewStatus;
  downloaded_at: string;
  metadata?: Record<string, unknown>;
}

export interface BatchVideoAsset extends VideoAsset {
  channel_name?: string;
  keyword?: string;
  thumbnail_url?: string;
}

export interface BatchListResponse {
  items: BatchVideoAsset[];
  total: number;
  limit: number;
  pending_count: number;
  in_pool_count: number;
  skipped_count: number;
}

export interface BulkVideoReviewResponse {
  updated_count: number;
  review_status: VideoReviewStatus;
}

export interface MergePoolResponse {
  items: BatchVideoAsset[];
  total: number;
  limit: number;
}

export interface MergeJob {
  id: string;
  job_type: string;
  status: string;
  video_a_id?: string;
  video_b_id?: string;
  suggestion_id?: string;
  error_message?: string;
  final_video_id?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface MergeEnqueueResponse {
  job_id: string;
  video_ids: string[];
  status: string;
}

export interface FinalVideo {
  id: string;
  merge_job_id?: string;
  file_path: string;
  keyword?: string;
  suggestion_id?: string;
  source_video_ids: string[];
  duration_sec?: number;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface FinalVideoListResponse {
  items: FinalVideo[];
  total: number;
  limit: number;
}

export type RejectReason =
  | "too_broad"
  | "too_competitive"
  | "off_topic"
  | "poor_quality"
  | "other";
