# warning-agent architecture clarity target map

- status: `active-design-map`
- owner: `architecture-clarity pack`
- last_updated: `2026-04-20`
- source_pack: `docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_PLAN.md`

## 1. Purpose

本文把当前 repo 的 dependency/import hygiene concerns 和 runtime-vs-benchmark ownership concerns 收成一个可执行 target map。

目标不是一次性做大重构，而是给后续 slices 一个 deterministic move map。

## 2. Current runtime-ish dependency pressure

当前 runtime-ish family 里，最值得收口的依赖压力主要集中在：

- `packet -> receiver`
- `runtime_entry -> analyzer + investigator + receiver + delivery + integration_evidence + retrieval + storage`
- `investigator -> analyzer + packet + collectors`
- `analyzer` 中部分 training/corpus code 仍直接借用 `receiver + packet` glue

这说明当前 repo 的问题不是“没有模块”，而是：

- 概念边界比代码依赖图更清楚
- runtime / benchmark / training 的 ownership 还没完全收口

## 3. Runtime vs benchmark ownership inventory

### `app/analyzer/*`

| surface | intended owner | note |
|---|---|---|
| runtime scorer selection | `app/analyzer/runtime.py` | runtime-only |
| fast scorer runtime | `app/analyzer/fast_scorer.py` | runtime-only |
| trained scorer runtime artifact loading / scoring | runtime-focused module | `AC.S2a` 收口 |
| artifact training / corpus row assembly | training-focused module | `AC.S2a` 收口 |
| benchmark acceptance | `app/analyzer/benchmark.py` | benchmark-only |
| assist / audit groundwork | narrow internal module | `AC.S2b` 落地 |

### `app/investigator/*`

| surface | intended owner | note |
|---|---|---|
| route planning / budget policy | `app/investigator/router.py` | keep stable |
| execution spine | `app/investigator/runtime.py` | keep stable, narrow imports |
| local resident lifecycle / abnormal path | local-primary internal seam module | `AC.S3a` |
| local smoke provider behavior | local-primary provider-facing module | `AC.S3a` |
| cloud handoff / brief / request mapping | cloud-fallback brief module | `AC.S3b` |
| cloud transport client | `cloud_fallback_openai_responses.py` + narrow wrapper | keep bounded |
| cloud guard / fallback evaluation | cloud-fallback internal seam | `AC.S3b` |

### shared glue surfaces

| surface | target direction | note |
|---|---|---|
| normalized alert types | move to receiver/shared contract surface | `AC.S3c` |
| packet builder typing | should not depend on webhook implementation file | `AC.S3c` |
| package `__init__` exports | runtime APIs only by default | `AC.S1b` -> later slices |

## 4. Planned move map by slice

### `AC.S2a` — `3.5` runtime/training boundary cleanup

允许的 move：

- 将 trained scorer runtime 与 artifact training/corpus glue 分开
- 将 analyzer family 中直接依赖 replay/receiver/packet 的 training helpers 收到 training-focused module
- 保持 `TrainedScorer` runtime call shape 不变

不允许的 move：

- 重新设计 scorer contract
- 修改 `local-analyzer-decision.v1`

### `AC.S2b` — `3.5` assist/audit groundwork

允许的 move：

- 新增 `SidecarAssistPacket` / `DecisionAuditRecord` 的 narrow internal module
- 提供 builder / compare-friendly helpers

不允许的 move：

- 引入新的 chat-agent runtime
- 让 assist packet 变成 canonical output

### `AC.S3a` — `3.6` local-primary internal split

允许的 move：

- 将 resident lifecycle / abnormal path 从 `local_primary.py` 抽出
- 将 smoke provider behavior 与 lifecycle/control logic 分离
- 保持 `LocalPrimaryInvestigator` 对外入口稳定

不允许的 move：

- 改写 current resident/fallback semantics
- 把 repo 推向 model-serving platform

### `AC.S3b` — `3.6` cloud-fallback internal split

允许的 move：

- 将 handoff brief / request mapping / parsing 从 `cloud_fallback.py` 抽出
- 将 guard logic 收到更窄 seam
- 保持 bounded transport + result mapping truth

不允许的 move：

- 改变 cloud sparse-fallback role
- 抽成 generic vendor client framework

### `AC.S3c` — execution spine and normalized-alert dependency hygiene

允许的 move：

- 抽出 normalized-alert shared contracts
- 让 `packet` 不再直接依赖 webhook implementation module
- 收紧 `runtime_entry` / `receiver` / `packet` 的 import direction

不允许的 move：

- 在此 slice 混入 product behavior redesign
- 扩成 receiver/storage full rewrite

## 5. Export-surface policy

当前 pack 的 package export policy 应逐步收向：

- `app/analyzer/__init__.py`：优先 export runtime-stable APIs
- `app/investigator/__init__.py`：优先 export runtime-stable APIs
- benchmark/training helpers 应继续可导入，但不再作为默认 runtime barrel 的主要表面

## 6. Why this map is intentionally narrow

本 target map 故意不直接创建：

- `app/state/*`
- `app/policies/*`
- `app/runtime/*`

原因：

1. 当前 repo 还处在“先收清 ownership，再决定是否抽离”的阶段。
2. 现在先做大 tree，只会增加 import churn 与心理复杂度。
3. future note 已明确：
   - keep the shell
   - learn the policies
   - extract later

## 7. Done-when for `AC.S1b`

`AC.S1b` 只有在下面这些都成立时才算完成：

- 后续 slices 的 move target 已明确
- runtime vs benchmark ownership 已明确
- dependency hygiene target 已明确
- 没有把 target map 膨胀成 full redesign doc
