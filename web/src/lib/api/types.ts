export type SuggestionStatus = "pending" | "approved" | "rejected" | "reported";

export interface ComponentScores {
  relevance: number;
  specificity: number;
  saturation: number;
  trend: number;
  video_performance: number;
}

export interface PlatformAgentSignals {
  scored_with?: string;
  rationale?: string;
  confidence?: number;
  risk_flags?: string[];
  component_scores?: ComponentScores;
  component_reasons?: Record<string, string>;
}

export interface PlatformSignals {
  tiktok?: {
    status?: string;
    unverified?: boolean;
    gate_score?: number;
    stats?: {
      video_count_7d: number;
      avg_views: number;
      avg_likes: number;
      avg_comments: number;
      saturation_tier?: string;
    };
  };
  youtube?: {
    discovery_source?: string;
    source_title?: string;
    video_id?: string;
    channel_id?: string;
  };
  agent?: PlatformAgentSignals;
}

export type KeywordType = "nurture" | "beta";

export interface Suggestion {
  id: string;
  keyword: string;
  status: SuggestionStatus;
  keyword_type?: KeywordType;
  discovery_source?: string;
  gate_profile?: string;
  tiktok_unverified?: boolean;
  final_score: number;
  component_scores: ComponentScores;
  platform_signals?: PlatformSignals;
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

export interface ScoringRubricField {
  text: string;
  custom_text: string | null;
  default_text: string;
  is_custom: boolean;
}

export interface ScoringRubricsConfig {
  nurture: ScoringRubricField;
  beta: ScoringRubricField;
}

export interface SettingsResponse {
  weights: ScoringWeights;
  filters: Record<string, number>;
  niche: {
    topics: string[];
    preferred_language: string;
    target_audience?: string;
  };
  llm: { model: string; temperature: number; base_url: string; api_key_set: boolean };
  tiktok: { api_key_set: boolean; check_enabled: boolean };
  scoring_rubrics: ScoringRubricsConfig;
  /** False when API response omits rubrics (old server or pending restart). */
  rubrics_available?: boolean;
}

export interface UpdateSettingsPayload {
  weights?: ScoringWeights;
  filters?: Record<string, number>;
  niche?: {
    topics?: string[];
    preferred_language?: string;
    target_audience?: string;
  };
  llm?: {
    model?: string;
    temperature?: number;
    base_url?: string;
    api_key?: string;
  };
  tiktok?: { check_enabled?: boolean };
  scoring_rubrics?: {
    nurture?: string | null;
    beta?: string | null;
  };
}

export interface LLMModelsResponse {
  models: string[];
}

export interface LLMModelsRequest {
  base_url?: string;
  api_key?: string;
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
  final_video_id?: string;
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
  final_video_id?: string;
}

export interface WeightProposal {
  id: string;
  factor: string;
  old_value: number;
  new_value: number;
  reason?: string;
  confidence: number;
  status: string;
  keyword_type: string;
  created_at: string;
  resolved_at?: string;
}

export interface WeightProposalListResponse {
  items: WeightProposal[];
  total: number;
}

export interface FeedbackAccuracy {
  total_reports: number;
  linked_suggestions: number;
  success_rate: number;
  avg_views: number;
  high_score_success_rate: number;
  pending_finals: number;
}

export interface PendingFinalsResponse {
  items: FinalVideo[];
  total: number;
}

export interface ScanRunResponse {
  job_id: string;
  status: string;
  estimated_duration_seconds?: number;
}

export interface ScanProgress {
  channels_processed?: number;
  videos_processed?: number;
  suggestions_generated?: number;
}

export interface ScanProgressResponse {
  job_id: string;
  status: string;
  progress: ScanProgress;
  error?: string;
}

export type KeywordTypeFilter = "nurture" | "beta" | "both";

export interface DiscoveryRunResponse {
  job_id: string;
  status: string;
  estimated_duration_seconds?: number;
  max_keywords?: number;
}

export interface DiscoveryJobResponse {
  id: string;
  status: string;
  job_type: string;
  keyword_type_filter: string;
  sources_scanned: number;
  videos_scanned: number;
  candidates_checked: number;
  keywords_generated: number;
  max_keywords?: number;
  max_videos?: number;
  progress_percent: number;
  progress_phase: string;
  progress_label: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
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

export type ProfileStage = "nurture" | "beta";

export interface TikTokProfile {
  id: string;
  label: string;
  handle: string;
  stage: ProfileStage;
  beta_eligible: boolean;
  promoted_at?: string;
  notes?: string;
  created_at: string;
}

export interface TikTokProfileListResponse {
  items: TikTokProfile[];
  total: number;
}

export interface PoolMediaItem {
  id: string;
  kind: "video_asset" | "final_video";
  pool_type: ProfileStage;
  pool_status: string;
  title: string;
  keyword?: string;
  file_path: string;
  duration_sec?: number;
  created_at: string;
}

export interface PoolListResponse {
  items: PoolMediaItem[];
  total: number;
  limit: number;
}

export type RejectReason =
  | "too_broad"
  | "too_competitive"
  | "off_topic"
  | "poor_quality"
  | "other";
