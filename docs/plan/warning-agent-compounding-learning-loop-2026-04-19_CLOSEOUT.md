# warning-agent compounding learning loop closeout

- plan_id: `warning-agent-compounding-learning-loop-2026-04-19`
- closeout_date: `2026-04-19`
- verdict: `accept_with_residuals`
- next_handoff: `replan-required`

## 1. Scope audited

审计对象：`W4 compounding learning loop`

claimed outcomes：

- outcome artifact / ingest / metadata / retrieval refresh 已 materialize
- replay + landed outcome compare corpus 已可重复生成
- candidate retrain / compare 已有 explicit summary artifact
- promotion report + explicit promote-or-hold decision 已落地
- cadence / rollback governance 已冻结
- `docs/future/*` 当前 roadmap 已在 W2/W3/W4 边界内 honest 收口

## 2. Findings

### confirmed

1. feedback layer 已形成最小闭环：
   - `incident-outcome.v1` contract
   - `ingest_incident_outcome(...)`
   - `refresh_outcome_retrieval_docs(...)`
   - `assemble_feedback_compare_corpus(...)`
   - `run_feedback_retrain_compare(...)`
   - `run_feedback_promotion_review(...)`
2. landed outcome 已真实进入 artifact / metadata / retrieval truth：
   - `data/outcomes/outcomes.jsonl`
   - `data/metadata.sqlite3` 中 `outcomes` table
   - `data/retrieval/retrieval.sqlite3` 中 `outcome` docs
3. compare-ready corpus 已真实 materialize：
   - `data/feedback/feedback-compare-corpus.json`
   - `replay_case_count = 30`
   - `landed_outcome_case_count = 1`
4. candidate retrain / compare 已真实 materialize：
   - `data/benchmarks/local-analyzer-feedback-compare-summary.json`
   - `data/models/local-analyzer-trained-scorer.candidate.json`
5. explicit decision 已真实 materialize：
   - `data/decisions/local-analyzer-promotion-decision.json`
   - `final_decision = hold_current`
6. governance freeze 已真实 materialize：
   - `configs/feedback-governance.yaml`
   - `docs/warning-agent-feedback-governance.md`
7. runtime metadata drift 已修正：
   - `app/main.py` 现返回 `phase = feedback-governance`
   - `active_slice = none`
8. full regression 通过：
   - `uv run pytest` → `85 passed`
   - `uv run ruff check app tests scripts` → pass

### drift fixed

1. 原先 repo 只在 storage 层预留 `outcomes` plumbing；当前已补齐 contract / ingest / refresh / compare / decision / governance 真正闭环。
2. 原先 `app.main` metadata 仍停在 `W2.S1a`；当前已修正到 terminal `feedback-governance / none`。

### uncertain

none remaining inside current W4 scope.

## 3. Evidence added / reused

### targeted evidence

- `uv run pytest tests/test_feedback_contracts.py tests/test_feedback_persistence.py tests/test_outcome_ingest.py tests/test_feedback_retrieval_refresh.py tests/test_feedback_corpus.py tests/test_feedback_compare.py tests/test_feedback_promotion.py tests/test_feedback_governance.py`

### script / artifact evidence

- `uv run python scripts/assemble_feedback_compare_corpus.py`
- `uv run python scripts/run_feedback_retrain_compare.py`
- `uv run python scripts/run_feedback_promotion_review.py`

### full gates

- `uv run pytest` → `85 passed`
- `uv run ruff check app tests scripts` → pass

## 4. Fixes landed during W4

- outcome contract + persistence surface
- outcome ingest entrypoint
- outcome-driven retrieval refresh helper
- replay + landed outcome corpus assembly
- candidate retrain / compare scaffold
- promotion report + explicit hold decision
- cadence / rollback governance freeze
- runtime metadata sync to terminal state

## 5. Successor residuals

1. landed outcome corpus 目前仍只有 `1` 个 case，因此 explicit decision 只能 honest 地保持 `hold_current`。
2. ingest surface 当前是 repo-local function path；若要接真实外部 operator / postmortem admission，需要新 plan。
3. richer promotion confidence、real rollout、多环境 artifact promotion 仍不在当前 roadmap closeout 范围内。

## 6. Closeout verdict

`W4` 可以 honest closeout 为 `completed`，并带 successor residuals。

理由：

- 当前 roadmap 要求的 feedback -> retrieval -> retrain compare -> explicit decision -> governance freeze 已全部有代码、tests、artifacts、scripts、control-plane 共同支撑。
- 当前 scope 内已无未证实 claim。
- 剩余缺口均属于后续 successor work，而不是 W4 未闭合 implementation。

## 7. Successor handoff

- 当前停止在 `review / replan` boundary。
- `docs/future/*` 当前 roadmap 已完成；若要继续推进新的 learning / rollout / external admission work，必须新开 successor `PLAN / STATUS / WORKSET`。
