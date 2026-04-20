# warning-agent architecture clarity guardrails

- status: `active-design-guardrail`
- owner: `architecture-clarity pack`
- last_updated: `2026-04-20`
- source_pack: `docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_PLAN.md`

## 1. Purpose

本文是当前 architecture-clarity pack 的 governing design guardrail。

它回答的不是“下一步怎么写更多能力”，而是：

- 当前到底在优化什么
- 哪些 surfaces 可以动
- 哪些 surfaces 必须保护
- `3.5` / `3.6` 的代码清晰度优化应停在什么边界内

这份文档必须让后续 `execute-plan` 在不依赖会话记忆的情况下继续推进。

## 2. One-sentence boundary

当前 pack 的核心边界固定为：

> 在 **不改变 canonical contracts、不改变现有 provider topology、不重开 shell、不引入过度工程化 framework** 的前提下，收紧 `3.5` 与 `3.6` 的代码模块边界，并为 future learning optimization 做最小必要 groundwork。

## 3. What this pack is optimizing

当前 pack 优化的对象不是“更多模型能力”，而是：

- 文件职责清晰度
- import direction 清晰度
- runtime / benchmark / training ownership 清晰度
- `3.5` 的 triage / assist / audit seam 清晰度
- `3.6` 的 resident local / abnormal path / cloud brief+transport seam 清晰度
- minimal internal learning object groundwork

## 4. Protected surfaces

以下 surfaces 在本 pack 中默认视为 **protected**：

### 4.1 Canonical contracts

不得修改：

- `incident-packet.v1`
- `local-analyzer-decision.v1`
- `investigation-result.v1`
- `alert-report.v1`
- `incident-outcome.v1`

### 4.2 Runtime shell

默认保持不重开：

- ingress
- packet
- report
- delivery
- feedback governance shell
- warning-plane queue / worker shell

注意：

- 允许做 narrow dependency hygiene
- 不允许顺手重构成新的 runtime platform

### 4.3 Provider topology

当前角色分工保持不变：

- `local_primary` = default `3.6` provider
- `cloud_fallback` = sparse fallback only
- `local_primary` resident lifecycle / fallback-or-queue semantics 保持现有 truth

## 5. Hard anti-overengineering rules

以下规则在当前 pack 中是硬边界：

1. **keep the shell**：不要借结构优化之名重开 packet / ingress / delivery / feedback 外壳。
2. **no generic framework jump**：不要提前引入完整 `app/state/*`、`app/policies/*`、`app/runtime/*` 新框架树。
3. **no warning-core extraction**：当前 pack 不是 `warning-core` 抽离 pack。
4. **no contract churn**：不能靠改 canonical schema 来“让结构更清楚”。
5. **no platform creep**：不能把当前工作演变成 multi-provider SDK / workflow engine / orchestration platform。
6. **passive groundwork first**：future-learning groundwork 优先做 passive internal objects / builders / compare surfaces，不要直接长成 online policy runtime。
7. **proof-carrying only**：任何模块拆分都必须有 targeted validation，而不是纯审美重排。

## 6. Current hotspot inventory

当前最需要 architecture-clarity 收口的 hotspot 已明确为：

| file | current issue | pack intent |
|---|---|---|
| `app/collectors/evidence_bundle.py` | evidence shaping + collector glue 过厚 | 目前只记录为 hotspot，不在本 pack 主线优先切分 |
| `app/investigator/local_primary.py` | resident lifecycle、abnormal path、provider materialization、smoke investigation 责任混杂 | 在 `AC.S3a` 中切分内部 seam |
| `app/investigator/cloud_fallback.py` | handoff/brief、guards、client mapping、fallback execution 责任混杂 | 在 `AC.S3b` 中切分内部 seam |
| `app/runtime_entry.py` | runtime spine 聚合过多 family 依赖 | 在 `AC.S3c` 中做 narrow dependency hygiene |
| `app/storage/signoz_warning_store.py` | warning-plane durable state 管理过厚 | 本 pack 只记录热点，不扩成 storage redesign |
| `app/analyzer/trained_scorer.py` | runtime scorer + artifact training + replay/corpus glue 混杂 | 在 `AC.S2a` 中收成 clearer ownership |
| `app/analyzer/calibrate.py` | calibration logic 与 corpus materialization 耦合 | 在 `AC.S2a` 中收成 clearer ownership |

## 7. `3.5` clarity target

当前 pack 对 `3.5` 的目标不是“做更聪明的 first-pass”，而是先让后续优化有清晰落点：

- runtime scorer surface
- training / benchmark surface
- minimal assist seam
- minimal decision-audit seam

在当前 pack 内，`3.5` 只允许新增最小 internal objects，例如：

- `SidecarAssistPacket`
- `DecisionAuditRecord`

这些对象必须：

- non-canonical
- bounded
- passive-first
- 不改变 `local-analyzer-decision.v1`

## 8. `3.6` clarity target

当前 pack 对 `3.6` 的目标不是“换模型策略”，而是让代码分层更贴近既有 truth：

- local resident lifecycle seam
- abnormal-path policy seam
- local smoke / real-adapter provider seam
- cloud brief / guard / transport / mapping seam
- execution-spine imports 更干净

在当前 pack 内，`3.6` 只允许新增最小 internal objects，例如：

- `ActionTrace`
- `InvestigationEvidencePack`
- `CompressedInvestigationBrief`

这些对象必须：

- non-canonical
- serve replay / compare / attribution first
- 不能演化成新的 general runtime protocol

## 9. Allowed move types

当前 pack 中允许的 move type 仅限：

1. extract helper / internal record modules
2. split thick provider files by responsibility
3. reduce cross-layer import coupling
4. narrow package export surfaces
5. align docs / benchmarks / runbooks to the clearer ownership map

## 10. Explicit non-goals for this pack

本 pack 明确不做：

- external live rollout proof
- queue infra / lease / distributed orchestration
- warning-core extraction
- online learning runtime
- auto-promotion
- generic state/policy framework
- shell replatform

## 11. Done-when for the family

本 pack 只有在下面这些都成立时才算 honest closeout：

- `3.5` 与 `3.6` 的模块边界明显比当前更清楚
- hotspot files 的职责混杂得到收口或明确 split
- future note 中最关键的 minimal internal objects 已有安全的代码落点
- targeted proofs + full regression 通过
- 当前 repo 仍然保持“窄产品 + bounded runtime + no overengineering”
