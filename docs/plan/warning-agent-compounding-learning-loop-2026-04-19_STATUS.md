# warning-agent compounding learning loop status

- plan_id: `warning-agent-compounding-learning-loop-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- current_wave: `closeout / W4 complete`
- current_step: `closeout complete`
- last_updated: `2026-04-19`

## 1. Current truth

- `W4` 已完成并 closeout。
- closeout verdict：`accept_with_residuals`
- closeout doc：`docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md`
- `docs/future/*` 当前 roadmap 已在 W2/W3/W4 边界内全部收口。

## 2. Recently completed

### `W4.S2b` — corpus assembly surface

landed truth：

- 新增 `app/feedback/corpus.py`
- 新增 `scripts/assemble_feedback_compare_corpus.py`
- 新增 `tests/test_feedback_corpus.py`
- 生成 `data/feedback/feedback-compare-corpus.json`
- compare-ready corpus truth：
  - `replay_case_count = 30`
  - `landed_outcome_case_count = 1`
  - `unknown_outcome_skipped_count = 0`
  - `total_cases = 31`

review verdict：
- `accept`

### `W4.S3a` — retrain / evaluate / compare scaffold

landed truth：

- 新增 `app/feedback/compare.py`
- 新增 `scripts/run_feedback_retrain_compare.py`
- 新增 `tests/test_feedback_compare.py`
- 生成 `data/benchmarks/local-analyzer-feedback-compare-summary.json`
- 生成 `data/models/local-analyzer-trained-scorer.candidate.json`
- compare summary truth：
  - `current_runtime.analyzer_version = trained-scorer-2026-04-19`
  - `candidate_retrained.analyzer_version = trained-scorer-feedback-candidate-2026-04-19`
  - current / candidate 在 compare corpus 上均保持：
    - `severe_recall = 1.0`
    - `investigation_precision = 1.0`
    - `investigation_candidate_rate = 0.29`
  - provisional decision：`candidate_ready_for_review`

review verdict：
- `accept`

### `W4.S3b` — promotion report + gated decision

landed truth：

- 新增 `app/feedback/promotion.py`
- 新增 `scripts/run_feedback_promotion_review.py`
- 新增 `tests/test_feedback_promotion.py`
- 生成 `data/decisions/local-analyzer-promotion-decision.json`
- 生成 `data/reports/local-analyzer-promotion-report.md`
- explicit decision truth：
  - `final_decision = hold_current`
  - rationale：`landed_outcome_cases_below_promotion_minimum`, `config_auto_promote_disabled`

review verdict：
- `accept`

### `W4.S4a` — refresh cadence and governance freeze

landed truth：

- 新增 `app/feedback/governance.py`
- 新增 `configs/feedback-governance.yaml`
- 新增 `docs/warning-agent-feedback-governance.md`
- 新增 `tests/test_feedback_governance.py`
- 更新 `app/main.py`
- 更新 `tests/test_bootstrap.py`

freeze truth：

- retrieval refresh cadence：`on_each_landed_outcome`
- corpus assembly cadence：`on_compare_review_request`
- retrain / compare cadence：`on_feedback_batch_review`
- promotion review cadence：`explicit_manual_review_only`
- rollback target：`data/models/local-analyzer-trained-scorer.prev.json`
- runtime metadata 现为：`phase = feedback-governance`, `active_slice = none`

review verdict：
- `accept`

### `W4.RV1` — execution reality audit + roadmap closeout

landed truth：

- `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md` 已生成
- W4 pack 已切到 terminal completed state
- `docs/future/*` 当前 roadmap 已切到 historical closed state

review verdict：
- `accept_with_residuals`
- residuals 已明确留在 successor replan boundary，而不是当前 W4 blocker

## 3. Next step

- 当前 roadmap 已完成
- 若要继续推进新的 external admission / richer outcome batch / real promotion / rollout 工作，必须新开 plan

## 4. Blockers / risks

1. 当前只有 `1` 个 landed outcome case，因此 explicit decision 仍是 `hold_current`，不是 promotion。
2. current ingest surface 是 repo-local function path，不是外部生产 admission plane。
3. compare summary 当前仍主要服务 repo-local feedback bootstrap；更丰富 landed outcomes 仍需后续新 plan。

## 5. Gate state

| gate | state | evidence |
|---|---|---|
| W4.S1a | pass | `incident-outcome.v1` contract + persistence landed |
| W4.S1b | pass | outcome ingest entrypoint landed |
| W4.S2a | pass | outcome-driven retrieval refresh landed |
| W4.S2b | pass | compare-ready corpus assembled |
| W4.S3a | pass | retrain / compare summary + candidate artifact landed |
| W4.S3b | pass | explicit promote-or-hold decision landed |
| W4.S4a | pass | governance config + docs freeze landed |
| W4.RV1 | pass | closeout review complete |
| W4 closeout | pass | `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md` |

## 6. Latest evidence

- `uv run pytest tests/test_feedback_contracts.py tests/test_feedback_persistence.py tests/test_outcome_ingest.py tests/test_feedback_retrieval_refresh.py tests/test_feedback_corpus.py tests/test_feedback_compare.py tests/test_feedback_promotion.py tests/test_feedback_governance.py`
- `uv run python scripts/assemble_feedback_compare_corpus.py`
- `uv run python scripts/run_feedback_retrain_compare.py`
- `uv run python scripts/run_feedback_promotion_review.py`
- `uv run pytest` → `85 passed`
- `uv run ruff check app tests scripts` → pass
