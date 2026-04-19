# warning-agent production integration bridge workset

- plan_id: `warning-agent-production-integration-bridge-2026-04-20`
- plan_class: `execution-plan`
- status: `ready`
- queue_mode: `strict-serial`
- active_wave: `wave-1 / W6 external outcome admission bridge`
- active_slice: `W6.S1a external outcome admission API baseline`
- last_updated: `2026-04-20`

## Active slice

### `W6.S1a` — external outcome admission API baseline

- owner: `execute-plan`
- state: `ready`
- goal:
  - 把 landed outcome ingest 收敛成 operator-facing external admission surface
  - 增加显式 success / error receipt contract
  - 让 outcome admission 不再只是 repo-local function call truth

### Primary surfaces

- `app/feedback/outcome_ingest.py`
- 必要时新：
  - `app/feedback/outcome_api.py`
  - app factory / router glue
- `tests/test_outcome_ingest.py`
- 新增 API tests（例如 `tests/test_outcome_admission_api.py`）
- 必要时：
  - `app/feedback/persistence.py`
  - `app/feedback/retrieval_refresh.py`

### Deliverable

一个最小但真实的 external outcome admission 修复包，满足：

1. operator-facing path 可以提交 landed outcome，而不仅是直接调用 `ingest_incident_outcome(...)`。
2. admission surface 返回显式 success / error receipt contract。
3. accepted outcome 会真实写入 artifacts / metadata，并给出 retrieval refresh evidence。
4. 仍保持 local-proof scope，不引入 auth、queue、deployment infra。

### Expected verification

1. targeted tests
   - `uv run pytest tests/test_outcome_ingest.py tests/test_feedback_persistence.py tests/test_feedback_retrieval_refresh.py`
   - 新增 outcome admission API tests
2. targeted smoke
   - `uv run python - <<'PY' ... TestClient(...) ... PY`
3. hygiene
   - `uv run ruff check app tests scripts`

### Done-when boundary

只有在以下同时成立时，`W6.S1a` 才能 claim done：

- external outcome admission surface 已 landed
- success / error receipt contract 已有 targeted proof
- admitted outcome 会真实 materialize artifact / metadata / retrieval refresh evidence
- targeted tests 与 targeted smoke 全部通过
- 没有把 work 扩张到 auth、queue、deployment infra 或 vendor delivery/provider surfaces

### Stop condition

命中以下任一项必须停止并回到 `plan-creator` 或至少暂停当前 slice：

- 为了验证最小 admission 正确性，必须先引入外部 auth / queue / deployment infra
- receipt contract 被证明需要跨服务 orchestration，而不是 repo-local API baseline
- 改动自然溢出到 vendor delivery、provider bridge 或 rollout hardening

### Next handoff after done

- `W6.S1b` — durable outcome receipt + feedback refresh glue

## Queued slices

| Order | Slice | Summary | State |
|---|---|---|---|
| 2 | `W6.S1b` | durable outcome receipt + feedback refresh glue | `queued` |
| 3 | `W6.S2a` | live delivery adapter contract + env config seam | `queued` |
| 4 | `W6.S2b` | first vendor delivery smoke bridge | `queued` |
| 5 | `W6.S3a` | real provider adapter contract freeze | `queued` |
| 6 | `W6.S3b` | provider runtime glue + fail-closed rollout gate | `queued` |
| 7 | `W6.S4a` | integration observability + rollout evidence baseline | `queued` |
| 8 | `W6.RV1` | reality audit + W7 replan input | `queued` |

## Boundary rule

- 当前 workset 只允许执行 `W6.S1a`。
- 若 execution 过程中出现多个同级主方案，必须先停下，不得让本 workset 退化成 changelog dump。
- 在 `W6.S1a` 完成前，不得提前 claim `W6.S1b` / `W6.S2*` / `W6.S3*` 已开始。
