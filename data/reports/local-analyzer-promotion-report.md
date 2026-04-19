# warning-agent local analyzer promotion review

- compare summary: `/home/peng/dt-git/github/warning-agent/data/benchmarks/local-analyzer-feedback-compare-summary.json`
- current analyzer: `trained-scorer-2026-04-19`
- candidate analyzer: `trained-scorer-feedback-candidate-2026-04-19`
- final decision: `hold_current`

## Corpus contract
- replay cases: `30`
- landed outcomes: `1`
- total cases: `31`

## Current runtime metrics
- severe recall: `1.0`
- investigation precision: `1.0`
- brier score: `0.0`

## Candidate metrics
- severe recall: `1.0`
- investigation precision: `1.0`
- brier score: `0.0`
- candidate artifact path: `/home/peng/dt-git/github/warning-agent/data/models/local-analyzer-trained-scorer.candidate.json`

## Decision rationale
- landed_outcome_cases_below_promotion_minimum
- config_auto_promote_disabled

## Notes
- no automatic promotion occurred without an explicit decision artifact
- governance freeze and rollback policy remain a separate W4 step
