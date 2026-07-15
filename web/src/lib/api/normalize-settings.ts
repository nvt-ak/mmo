import type { ScoringRubricField, ScoringRubricsConfig, SettingsResponse } from "./types";
import { BETA_RUBRIC_DEFAULT, NURTURE_RUBRIC_DEFAULT } from "../scoring-rubric-defaults";

function fallbackField(defaultText: string): ScoringRubricField {
  return {
    text: defaultText,
    custom_text: null,
    default_text: defaultText,
    is_custom: false,
  };
}

const FALLBACK_RUBRICS: ScoringRubricsConfig = {
  nurture: fallbackField(NURTURE_RUBRIC_DEFAULT),
  beta: fallbackField(BETA_RUBRIC_DEFAULT),
};

function mergeRubricField(
  fromApi: ScoringRubricField | undefined,
  fallback: ScoringRubricField,
): ScoringRubricField {
  if (!fromApi?.default_text) {
    return fallback;
  }
  return {
    text: fromApi.text || fromApi.default_text,
    custom_text: fromApi.custom_text,
    default_text: fromApi.default_text,
    is_custom: fromApi.is_custom,
  };
}

/** Backfill scoring_rubrics when API is pre-US-061 or server not restarted. */
export function normalizeSettingsResponse(raw: SettingsResponse): SettingsResponse {
  const nurture = mergeRubricField(raw.scoring_rubrics?.nurture, FALLBACK_RUBRICS.nurture);
  const beta = mergeRubricField(raw.scoring_rubrics?.beta, FALLBACK_RUBRICS.beta);
  const rubricsAvailable = Boolean(
    raw.scoring_rubrics?.nurture?.default_text && raw.scoring_rubrics?.beta?.default_text,
  );
  const regions = Array.isArray(raw.discovery_region_codes)
    ? raw.discovery_region_codes
    : ["US"];

  return {
    ...raw,
    discovery_region_codes: regions.length > 0 ? regions : ["US"],
    rubrics_available: rubricsAvailable,
    scoring_rubrics: { nurture, beta },
  };
}
