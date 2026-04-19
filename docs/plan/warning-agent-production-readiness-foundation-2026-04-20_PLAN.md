# warning-agent production readiness foundation plan

- plan_id: `warning-agent-production-readiness-foundation-2026-04-20`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_wave: `closeout / W5 complete`
- last_updated: `2026-04-20`

## 1. Goal

在 `W4 compounding learning loop` honest closeout 之后，启动第一个 post-roadmap successor pack：

> 把当前 `warning-agent` 从“可试跑、可演示、tests/benchmarks 通过的 bounded MVP”
> 推进到“更接近 production 的 foundation state”，
> 但**不提前宣称 production rollout ready**。

本 plan 的主目标不是扩产品边界，而是收敛当前 capability audit 中最影响 production claim 的基础缺口：

```text
packaged CLI / operator entry
  -> normalized alert
  -> bounded evidence collection
  -> retrieval-informed analyzer
  -> local-first investigation
  -> markdown report
  -> durable delivery contract
```

当前 successor pack 重点收敛的是：

- packaged entrypoint correctness
- runtime metadata truth sync
- retrieval-informed runtime scoring wiring
- production-shaped admission baseline
- durable delivery adapter contract
- collector / provider config externalization
- safe provider boundary before later real vendor integration

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `docs/warning-agent-architecture.md`
- `docs/warning-agent-contract-inventory.md`
- `docs/warning-agent-feedback-governance.md`
- `docs/warning-agent-signoz-first-runbook.md`
- `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md`
- `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_STATUS.md`
- 当前 repo reality：
  - `app/main.py`
  - `app/runtime_entry.py`
  - `app/receiver/alertmanager_webhook.py`
  - `app/receiver/signoz_alert.py`
  - `app/investigator/*`
  - `app/collectors/*`
  - `app/reports/*`
  - `app/feedback/*`
  - `configs/*`
  - `tests/*`

## 3. Scope

### In scope

- packaged console-script entrypoint correctness
- runtime metadata drift resolution against active control-plane truth
- retrieval hits wiring into runtime first-pass scoring path
- production-shaped admission API baseline for current webhook/runtime path
- durable delivery adapter contract for report routing classes
- config-driven collector/provider endpoint loading
- explicit safe provider boundary for `local_primary` / `cloud_fallback`
- W5 closeout review and W6 replan input

### Out of scope

- full live vendor model integration
- automatic promotion / rollout of analyzer artifacts
- multi-environment secret manager / rollout orchestration
- unbounded observability exploration
- remediation / workflow engine / multi-agent runtime
- full incident management platform expansion
- production-ready claim before W5 reality audit and later successor work

## 4. Why this plan exists

当前 repo 已被代码、tests、artifacts、runbooks 证明具备 bounded MVP 主链，但 capability audit 也确认了几类阻断 production claim 的基础问题：

1. `uv run warning-agent ...` 当前不能正确执行 console-script runtime path，而 `python -m app.main ...` 可以。
2. runtime scoring path 当前仍调用 `score_packet(..., retrieval_hits=[])`，即检索基础设施已存在，但在线 first-pass 还未真正消费 retrieval 命中。
3. `Alertmanager webhook` 当前仍是 minimal stub，`outcome ingest` 仍是 repo-local function path，不是 production-shaped admission plane。
4. Markdown report 已能落盘，但 repo 还没有 durable external delivery contract。
5. collector/provider 配置仍 partly hard-coded 或 `*-pending`，与 production-safe externalization 仍有差距。
6. `local_primary` / `cloud_fallback` 当前仍保留 deterministic smoke provider 特征，需要更明确的 provider boundary 与 fail-closed rule。

W5 的目标不是一次性把上述所有问题都变成真实线上系统，而是先把它们收敛成**可持续推进的 foundation layer**，避免后续执行继续建立在带漂移或带隐式假设的 runtime 上。

## 5. Execution principles

1. **truth before claim**：优先修正 entrypoint / metadata / runtime wiring 的事实漂移，不先扩功能面。
2. **strict serial**：一次只允许一个 `active_slice`，避免 admission / delivery / provider 多线并发造成 scope 漂移。
3. **TDD-first**：每个 slice 先补 proof-carrying test，再落实现。
4. **fail closed over silent best-effort**：production-shaped surface 若不能满足 contract，优先显式 handoff 到 human review，而不是静默 pretend success。
5. **foundation before vendorization**：W5 先收敛 adapter/config/boundary，不把 live vendor integration 混入同一波。
6. **review-gated closeout**：W5 结束前必须做 reality audit；不得把 W5 直接宣称为 production rollout completed。

## 6. Wave decomposition

### wave-1 / W5 runtime truth hardening

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W5.S1a` packaged entrypoint correctness + metadata truth | `app/main.py`、`tests/test_bootstrap.py`、必要时 README/runbook truth sync | `uv run warning-agent replay ...` 成功；module mode 与 console-script mode 行为一致；targeted tests pass | 不改 admission plane；不改 delivery contract |
| `W5.S1b` retrieval-informed runtime scoring contract | `app/runtime_entry.py`、`app/retrieval/*`、相关 tests | runtime path 对 replay/live path 能传递非空 retrieval hits；targeted runtime/retrieval tests pass | 不 retrain model；不改阈值 policy |

### wave-2 / W5 operator plane baseline

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W5.S2a` admission API hardening baseline | `app/receiver/alertmanager_webhook.py`、必要时新 runtime service glue、API tests | health/readiness + explicit runtime error surface + durable receipt contract 有 targeted tests 与 TestClient smoke | 不接外部 auth/provider；不引入分布式队列 |
| `W5.S2b` delivery adapter contract + durable local route | 新 `app/delivery/*`、`configs/delivery.yaml`、report/runtime wiring、tests | `page_owner` / `open_ticket` / `send_to_human_review` 至少映射到 durable adapter outputs；targeted delivery tests pass | 不接 PagerDuty/Jira/Slack live vendor integration |

### wave-3 / W5 config + provider hardening

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W5.S3a` collector/provider config externalization | `app/collectors/*`、`app/investigator/*`、`configs/*`、tests | runtime 不再依赖隐藏 hard-coded endpoints；targeted config tests + grep/probe proof | 不做 secret manager / multi-env rollout |
| `W5.S3b` safe provider boundary + human-review fallback rule | `app/investigator/*`、runbook/docs、tests | deterministic smoke path 与 future real adapter boundary 被显式区分；provider unavailable 时 fail closed 到 human review | 不做 live vendor model integration |
| `W5.RV1` execution reality audit + W6 replan input | evidence-driven audit + residual freeze | reality audit verdict=`accept` or `accept_with_residuals`；W6 replan input written | 不 claim production-ready |

## 7. Validation ladder

W5 默认验证顺序固定为：

1. targeted unit / contract tests
2. targeted runtime / API / delivery smoke
3. direct probe for the affected surface
4. `uv run pytest`
5. `uv run ruff check app tests scripts`

slice-specific notes：

- `W5.S1a` 必须同时验证 `python -m app.main ...` 与 `uv run warning-agent ...`
- `W5.S1b` 必须证明 runtime scorer 输入已不再固定为 `retrieval_hits=[]`
- `W5.S2a` 必须证明 admission API 失败时返回显式 operator-facing contract，而不是 silent pass
- `W5.S2b` 必须证明 delivery class 至少进入 durable adapter output，而不只是 Markdown 落盘
- `W5.S3a` 若改 collector/provider config，必须给出 config-driven probe 或 targeted grep evidence
- `W5.S3b` 必须证明 provider unavailable 时进入明确的 human-review / fallback boundary

没有对应 evidence，不得 claim slice done。

## 8. W5 closeout rule

W5 只能在以下同时成立时 closeout：

- packaged console-script 与 module mode 均可稳定触发 runtime path
- runtime scoring path 已显式消费 retrieval hits
- admission surface 不再只是 minimal normalization stub，而具有 production-shaped contract baseline
- delivery class 至少存在一个 durable adapter layer
- collector/provider endpoints 已外置到 config，不再隐含在 runtime code 默认值中
- provider boundary 与 fail-closed rule 已明确 landed
- `W5.RV1` reality audit 通过
- remaining residuals 已明确路由到 W6，而不是继续混在 W5 中

## 9. Mandatory replan triggers

命中任一项必须停下并 replan：

1. retrieval-informed runtime scoring 需要修改 analyzer contract/schema version，而不只是 wiring。
2. admission baseline 要求引入外部 auth、message queue 或 deployment infra 才能继续。
3. delivery adapter contract 被证明离不开 live vendor credential / SaaS API 才能验证最小正确性。
4. config externalization 需要 multi-env secret management，超出本 pack 的 local-proof 范围。
5. provider boundary work 变成真实 vendor SDK integration / serving deployment 项目。
6. W5 reality audit 发现 foundation 目标仍混入了 rollout-ready claim，导致 scope 失真。

## 10. Exit / successor rule

- 本 pack 是 `W4` closeout 之后的第一个 successor control plane。
- W5 完成后，若继续推进，下一 pack 应聚焦：
  - real provider integration
  - external outcome admission
  - live vendor delivery integration
  - rollout / observability hardening
- 在这些 successor work 完成前，repo 不得诚实声称 `production-ready`。
