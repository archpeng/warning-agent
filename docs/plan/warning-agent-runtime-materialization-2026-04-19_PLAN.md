# warning-agent runtime materialization plan

- plan_id: `warning-agent-runtime-materialization-2026-04-19`
- plan_class: `execution-plan`
- status: `completed`
- mode: `autopilot-control-plane`
- current_wave: `closeout / W2 complete`
- last_updated: `2026-04-19`

## 1. Goal

把已经 closeout 的 `local-first + bounded cloud-fallback` baseline，继续 materialize 成一个**真正可执行、可保存 artifacts、可索引检索、可 smoke proof** 的最小 runtime。

目标不是扩产品边界，而是把当前已存在的模块接成正式运行路径：

```text
replay/webhook input
  -> normalized alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval + local analyzer
  -> optional local-primary / cloud-fallback
  -> markdown report
  -> artifact writeback / metadata / retrieval refresh
```

## 2. Governing truth

本 plan 的 SSOT 输入固定为：

- `docs/warning-agent-architecture.md`
- `docs/future/README.md`
- `docs/future/warning-agent-local-trust-acceptance-and-minimal-upgrade.md`
- `docs/plan/warning-agent-autopilot-delivery-2026-04-18_CLOSEOUT.md`
- 当前代码 reality：
  - `app/main.py`
  - `app/receiver/alertmanager_webhook.py`
  - `app/packet/*`
  - `app/investigator/runtime.py`
  - `app/reports/markdown_builder.py`
  - `app/storage/*`
  - `app/retrieval/*`

## 3. Scope

### In scope
- replay / webhook runtime entrypoint materialization
- packet / decision / investigation / report active-path generation
- artifact writeback 与 metadata wiring
- retrieval index / search wiring on active path
- `LocalPrimaryInvestigator` 与 `BoundedInvestigatorTools` 的最小 evidence-driven materialization
- runtime smoke proof
- W2 closeout review and W3 replan handoff input

### Out of scope
- `W3` local trust upgrade implementation
- `W4` outcome ingest / learning loop implementation
- live vendor cloud integration
- contract-wide `packet.v2` migration
- richer corpora expansion beyond W2 needs
- rollout / shadow-mode / runbook hardening
- remediation / workflow / multi-agent / UI suite

## 4. Why this plan exists

当前 baseline 已 closeout，但 repo reality 仍显示：

- `app/main.py` 仍是 bootstrap banner
- artifact store / metadata store / retrieval index 仍未进入活路径
- `local_primary` 仍是 smoke synthesis，tool usage 未 materialize 到 runtime evidence

因此当前系统更像“可 benchmark 的模块集合”，而不是“正式可运行最小 runtime”。

## 5. Execution principles

1. **TDD-first**：每个 slice 先补或先改 proof-carrying test，再落实现。
2. **strict serial**：一次只允许一个 `active_slice`。
3. **runtime materialization before trust upgrade**：W2 不解决 W3/W4 的问题。
4. **review-gated closeout**：W2 完成后必须做 reality audit，再 replan W3；不得直接 auto-continue 到 W3 implementation。
5. **no scope drift**：不得把 W2 扩成 cloud hardening / training / data-program / governance 大包。

## 6. Wave decomposition

### wave-1 / W2 runtime materialization

| Slice | Main deliverable and surfaces | Validation proof | Stop boundary |
|---|---|---|---|
| `W2.S1a` replay runtime entrypoint skeleton | `app/main.py`、必要时最小 runtime helper；定义 replay-first entrypoint contract | targeted bootstrap/CLI tests pass | 不做 artifact writeback；不做 tool integration |
| `W2.S1b` replay execution path materialization | replay -> packet -> decision -> investigation/runtime -> report 走正式 entrypoint | targeted runtime path tests pass | 不做 persistence / retrieval wiring |
| `W2.S2a` artifact writeback materialization | `JSONLArtifactStore` 接入 packet / decision / investigation / report 活路径 | targeted persistence tests pass | 不做 retrieval index wiring |
| `W2.S2b` metadata + retrieval wiring | `MetadataStore` / `RetrievalIndex` 接入活路径；可从新生成 artifacts 检索 | targeted metadata/retrieval tests pass | 不做 trust upgrade |
| `W2.S3a` local-primary tool integration contract | `BoundedInvestigatorTools` 接入 `LocalPrimaryInvestigator` 的 contract / wiring | targeted investigator/tool tests pass | 不追求模型增强 |
| `W2.S3b` tool-driven local-primary proof | runtime / benchmark / smoke 证明 local-primary 已真实消费 bounded tools | targeted runtime + benchmark-adjacent proof pass | 不做 W3 metrics freeze |
| `W2.S4` runtime smoke and operator path proof | bounded replay / webhook-stub end-to-end smoke；report + artifacts + retrieval proof | full targeted smoke + full regression pass | 不做 W3 implementation |
| `W2.RV1` execution reality audit + W3 replan handoff | evidence-driven review，冻结真实 residuals 与 W3 replan input | reality-audit verdict=`accept` or `accept_with_residuals` | 不直接进入 W3 execution |

## 7. Validation ladder

W2 默认验证顺序：

1. targeted unit / contract tests
2. targeted runtime / replay tests
3. targeted artifact / retrieval tests
4. 必要时 rerun impacted benchmark or smoke script
5. `uv run pytest`
6. `uv run ruff check app tests scripts`

没有对应 evidence，不得 claim slice done。

## 8. W2 phase closeout rule

W2 只能在以下同时成立时 closeout：

- `warning-agent` 不再只是 banner bootstrap，而是存在正式 replay-first entrypoint
- packet / decision / investigation / report 会被活路径真实生成
- artifacts / metadata / retrieval 至少形成最小 write/read loop
- `local_primary` 不再只是完全零工具使用的 smoke path
- `W2.RV1` reality audit 通过
- `W3` 已被明确标记为 **next replan target**，而不是直接开始 execution

## 9. Mandatory replan triggers

命中任一项必须停下并 replan：

1. entrypoint shape 出现两个同级主方案且无法在当前 slice 内收敛（如 CLI-first vs API-first 同级冲突）。
2. 为继续 W2 必须做 `packet.v2` / contract family migration。
3. tool-driven local-primary materialization 明显改变当前 accepted P4/P5 baseline，且修复超出当前 slice。
4. retrieval / persistence wiring 暴露新的跨阶段目标，导致当前 slice 同时承担多个主目标。
5. W2 closeout review 发现 W3 需要重排顺序或新增 prerequisite wave。

## 10. Exit / successor rule

- `W2` 已在 `W2.RV1` 后 closeout completed。
- successor control plane 已生成：
  - `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_PLAN.md`
  - `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_STATUS.md`
  - `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_WORKSET.md`
- W2 pack 保留为 historical closeout truth，不得再次作为 active execution pack。
