# US-072 — Classifier v2 calibration from performance reports

## Status

implemented

## Lane

normal

## Product Contract

When enough linked performance reports exist, `classify_keyword_type` applies a
bucketed success-rate overlay on top of v1 heuristics. Without sufficient data,
behavior matches v1 exactly.

## Acceptance Criteria

- Calibration builds from `performance_reports` joined to `suggestions`.
- Overlay activates only when report count ≥ threshold.
- Bucket features: word length, discovery source, saturation tier.
- Discovery worker loads calibration once per job and passes to scorers.
- `run_classifier_experiment.py --db-calibrate` prints calibration summary.

## Validation

| Layer | Expected proof |
| --- | --- |
| unit | `videoscout/tests_api/test_classifier_calibration.py` |
| integration | existing `test_keyword_classifier.py` unchanged |
