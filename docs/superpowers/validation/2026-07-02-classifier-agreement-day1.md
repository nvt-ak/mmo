# Classifier Agreement Experiment — Day 1

**Date:** 2026-07-02  
**Protocol:** Dual-track spec Appendix B  
**Story:** US-051  
**Status:** Day 1 collected — **pending operator tags**

## Run

```bash
python scripts/run_classifier_experiment.py --day 1 --region DE --max-videos 25
```

**Output:** `docs/superpowers/validation/classifier-day1-2026-07-02.csv`

## Day 1 Summary

| Metric | Value |
| --- | --- |
| Candidates collected | 20 |
| Source | YouTube trending DE |
| `proposed_tag=nurture` | 20 (100%) |
| `proposed_tag=beta` | 0 (0%) |
| Operator tags filled | 0 |
| Agreement % | — (blocked on operator_tag) |

## Early Signal (pre-operator)

YouTube trending DE titles → extractor emits mostly **2–3 word phrases** → classifier §6.2 rules bias **nurture**.

**Risk:** YouTube-only R7a may miss bootstrap target (≥3 beta keywords) without niche_web source or length-4+ phrases from trending titles.

**Mitigations to test in days 2–7:**

1. Add niche topic seed list in Settings (manual `niche_web` source)
2. Extract 4–5 word phrases from descriptions, not just titles
3. Operator manual reclassify UI if beta inbox empty after discovery

## Operator Action Required

Fill `operator_tag` column in CSV (`nurture` or `beta`) for all 20 rows — blind, no peek at `proposed_tag` if possible.

Then score:

```bash
python scripts/run_classifier_experiment.py --score docs/superpowers/validation/classifier-day1-2026-07-02.csv
```

Repeat days 2–7 (target ≥140 total rows). Gate: ≥80% agreement → ship auto-classifier in R7a.

## Gate Decision (pending)

| Threshold | Action |
| --- | --- |
| ≥80% | `CLASSIFIER_MODE=auto` |
| 70–79% | Auto + one-click reclassify on inbox |
| <70% | Operator picks type at approve (R7a fallback) |

## Harness

Link validation evidence when operator tags complete:

```bash
scripts/bin/harness-cli story update --id US-051 --notes "Classifier day1: 20 rows, 100% proposed nurture, operator tags pending"
```
