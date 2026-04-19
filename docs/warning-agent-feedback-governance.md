# warning-agent Feedback Governance

- 状态: `active-governance-ssot`
- scope:
  - W4 feedback loop cadence
  - retrain / compare / promotion guardrails
  - runtime artifact rollback policy
- config source:
  - `configs/feedback-governance.yaml`

## 1. Purpose

这份文档冻结 `W4` feedback loop 的最小治理规则，确保：

- outcome feedback 不会静默变成自动 promotion
- compare / promotion / rollback 都有 explicit artifact truth
- runtime artifact 更新仍受人工 review 与 evidence gate 约束

## 2. Cadence freeze

当前 cadence 固定为：

- retrieval refresh: `on_each_landed_outcome`
- corpus assembly: `on_compare_review_request`
- retrain / compare: `on_feedback_batch_review`
- promotion review: `explicit_manual_review_only`

含义：

1. landed outcome 到来后可以刷新 retrieval docs。
2. compare-ready corpus 只在需要 compare review 时组装。
3. retrain / compare 是 batch review 行为，不是热路径自动动作。
4. promotion 必须经过显式 review，不允许 silent auto-promotion。

## 3. Promotion gates

promotion policy 当前冻结为：

- `minimum_landed_outcome_cases = 3`
- `auto_promote = false`
- `require_candidate_not_worse = true`
- `require_manual_review_report = true`

因此：

- landed outcomes 少于 3 个时，默认 `hold_current`
- compare summary 未把 candidate 标成 `candidate_ready_for_review` 时，默认 `hold_current`
- 没有 explicit promotion decision artifact 时，不得切换 runtime artifact

## 4. Artifact truth

治理相关 artifact path 固定为：

- compare corpus: `data/feedback/feedback-compare-corpus.json`
- compare summary: `data/benchmarks/local-analyzer-feedback-compare-summary.json`
- candidate artifact: `data/models/local-analyzer-trained-scorer.candidate.json`
- promotion decision: `data/decisions/local-analyzer-promotion-decision.json`
- promotion report: `data/reports/local-analyzer-promotion-report.md`
- current runtime artifact: `data/models/local-analyzer-trained-scorer.v1.json`
- previous runtime artifact: `data/models/local-analyzer-trained-scorer.prev.json`

## 5. Rollback policy

当前 rollback policy 固定为：

- rollback enabled = `true`
- trigger rule = `regression_or_runtime_smoke_failure_after_manual_promotion`
- rollback target = `previous_runtime_artifact`

这意味着：

1. compare review 不是唯一 gate；promotion 后若 runtime smoke 或 regression 失败，允许显式回滚。
2. 回滚目标必须是上一版 runtime artifact，而不是临时重新训练的未审查候选。
3. governance freeze 只约束最小 loop，不引入 online learning 或 automatic rollback orchestration。

## 6. Boundary

当前文档不定义：

- online learning
- streaming feature infra
- automatic promotion
- multi-environment rollout policy

这些内容若要继续推进，必须新开后续 plan。
