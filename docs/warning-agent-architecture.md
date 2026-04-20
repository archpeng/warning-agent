# warning-agent 架构设计

- 状态: `active-ssot`
- 范围: `Prometheus + SigNoz` 智能分析-报警器
- 核心哲学: `The Bitter Lesson`
- last_updated: `2026-04-19`

## 1. 产品目标

`warning-agent` 的目标非常窄，只做一件事：

> 把 `Prometheus + SigNoz` 的告警与有界观测证据压成统一事件单元，
> 用本地高频 `search + learning` 做 first-pass 分诊，
> 对少量 unresolved case 进入单一 investigator 接口，
> investigator 默认走本地 provider，只在必要时才走 cloud fallback，
> 最终产出稳定、可回放、可追溯的 Markdown 警报报文。

它不是：

- observability UI
- 生产自动化执行器
- incident management platform
- workflow engine
- multi-agent 框架
- raw-log-first LLM 系统

## 2. The Bitter Lesson 约束

本产品下的可执行约束固定为：

1. 先建设统一表示与检索，不先建设复杂 prompt 树。
2. 高频路径优先 `search + learning`，不让大模型进入 every-alert 热路径。
3. investigator 是稀疏、bounded 的第二层，不是另一个常驻主判官。
4. cloud 是 fallback，不是默认推理平面。
5. 结构化对象是真相，Markdown 是投影。
6. 反馈应回流到本地 analyzer / investigator，而不是沉淀成人工 heuristics。

明确反模式：

- 每个 service 单独写一套 prompt
- 告警一来就让云端模型扫全量 logs / traces
- 把本地 analyzer 做成 free-form 聊天 agent
- 为 cloud 审核单独长出一个重量级 reviewer 子系统

## 3. SSOT 层级

当前仓库的 source-of-truth 层级固定为：

1. 本文档：产品与架构 SSOT
2. [warning-agent-schema-draft.md](./warning-agent-schema-draft.md)：runtime contract SSOT
3. [warning-agent-contract-inventory.md](./warning-agent-contract-inventory.md)：contract/path/module 映射 SSOT
4. `docs/plan/*`：交付控制面 SSOT
5. `docs/analyse/*`：派生分析，不允许覆盖 1-4

当前 architecture-clarity family 的结构优化 guardrail / target map 还额外由以下文档支配：

- [warning-agent-architecture-clarity-guardrails.md](./warning-agent-architecture-clarity-guardrails.md)
- [warning-agent-architecture-clarity-target-map.md](./warning-agent-architecture-clarity-target-map.md)

它们只定义 **当前代码结构优化边界与 move map**，不覆盖 canonical contracts 或产品边界。

## 4. 最小正确结构

最小正确系统现在理解为 6 个在线组件和 1 个反馈闭环。

| 层 | 组件 | 作用 | 是否热路径 |
|---|---|---|---|
| 输入层 | `Alert Receiver` | 接收 governed Signoz warning、Alertmanager webhook 或 replay 输入 | 是 |
| 采证层 | `Evidence Collector` | 用固定查询模板采集 `Prometheus` 与 `SigNoz` 证据 | 是 |
| 表示层 | `Incident Packet Builder` | 生成统一事件表示 `incident packet` | 是 |
| 本地计算层 | `Local Analyzer` | 本地检索与快速评分，给出结构化 first-pass 结论 | 是 |
| 调查层 | `Investigator Interface` | 默认 `local-first`；只在 unresolved case 才调用 cloud fallback | 否 |
| 输出层 | `Markdown Report Builder` | 产出标准化 `md` 警报报文 | 是 |
| 反馈层 | `Outcome Store + Replay` | 存储 packet / decision / investigation / report / outcome | 否 |

这里的关键是：

- 只有一个 investigator 接口
- local provider 是默认实现
- cloud provider 是 fallback 能力，不再被建模成独立 reviewer 系统

## 5. 唯一中间表示

系统只允许一个 canonical runtime unit：

- `incident packet`

任何下游模块都只能消费：

- `incident packet`
- `local analyzer decision`
- 可选 `investigation result`

不能直接消费：

- 全量日志流
- 任意原始 trace dump
- 任意自由拼接的上下文

这样做的原因：

- 检索、学习、调查共享同一输入
- replay 与 benchmark 可成立
- 避免系统退化成“大模型读一切”

## 6. 运行时主路径

### 6.1 热路径

```text
Signoz warning / Alertmanager webhook / replay input
  -> bounded evidence collection
  -> incident packet
  -> local retrieval
  -> local scorer
  -> structured local decision
  -> markdown report
```

这个路径解决：

- 高频
- 低成本
- 可回放
- 可 benchmark

### 6.2 调查路径

```text
incident packet
  -> local analyzer says "needs investigation"
  -> investigator interface
  -> default local-primary investigation
  -> if unresolved or over-budget: cloud fallback
  -> enriched markdown report
```

这个路径解决：

- 高风险
- 高不确定性
- 跨 metrics / logs / traces 的综合定位
- 只把最难 case 升到更贵的计算层

### 6.3 反馈路径

```text
packet + local decision + investigation result + report + operator outcome
  -> outcome store
  -> retrieval refresh
  -> scorer recalibration
  -> later model replacement only if evidence supports it
```

## 7. 模块边界

### 7.1 `local analyzer`

输入：

- `incident packet`

输出：

- `local analyzer decision`

第一版推荐实现：

- 本地检索
- 轻量 scorer
- calibration / thresholding

第一版不做：

- 本地聊天 agent
- prompt orchestra
- 直接依赖 cloud LLM

### 7.2 `investigator interface`

这是单一接口，不是两套平行系统。

固定输入：

- 一个 `incident packet`
- 一个 `local analyzer decision`
- 少量 retrieval 摘要
- bounded 工具结果

固定输出：

- `investigation result`

接口行为：

1. 默认走 `local-primary` provider
2. 仅当本地结果 unresolved、冲突、超预算或工具上限命中时，才切到 `cloud-fallback`
3. cloud 只消费压缩 handoff 与少量 bounded refs，不重复读取完整原始洪流

### 7.3 `markdown report`

Markdown 报文就是产品输出，不是调试副产物。

正文 section order 固定为：

- `Executive Summary`
- `Why This Alert Exists`
- `Metric Signals`
- `Logs And Traces`
- `Investigation`
- `Impact And Routing`
- `Recommended Action`
- `Evidence Refs`
- `Unknowns`

## 8. 分阶段实现顺序

### P1. Repo bootstrap + contract materialization

目标：

- repo 可导入、可测试
- schema / contract / config 物化

### P2. Deterministic packet/report baseline

目标：

- replay 或 webhook stub 可生成合法 packet
- packet 可稳定渲染出合法 Markdown report

### P3. Local analyzer baseline

目标：

- 本地检索、feature/scorer、阈值与 decision contract 跑通
- 给出 `needs_investigation` 而不是 cloud-specific 决策

### P4. Single investigator interface, local-first

目标：

- 引入单一 investigator 接口
- 默认 `local-primary` provider
- bounded tools、structured result、report enrichment

### P5. Cloud fallback only

目标：

- 只在 unresolved case 上启用 cloud fallback
- 使用 compressed handoff
- 不单独扩成 reviewer 子系统

## 9. 明确简化规则

以下规则现在固定：

1. `P3` 完成前，不引入 investigator runtime。
2. `P4` 引入的是单一 investigator 接口，不再把 local investigator 和 cloud reviewer 当成两套一等系统。
3. `P5` 只加 cloud fallback，不允许把 cloud 层重新长成默认审查平面。
4. `P5` 完成前，不把 shadow-mode、runbook、复杂 rollout 作为主线目标。
5. 小模型替换只有在 replay / benchmark 证明优于 `retrieval + fast scorer` 后才讨论。

## 10. Current architecture-clarity rule

当前如果继续优化 `3.5 / 3.6`，优先遵守下面这条结构规则：

- keep the shell
- tighten module ownership
- add minimal internal objects only when they improve replay / compare / attribution
- extract later, not now

这意味着：

1. 先收紧 `3.5` runtime / benchmark / assist / audit 的 ownership。
2. 先收紧 `3.6` local resident lifecycle / abnormal path / cloud brief+transport seam 的 ownership。
3. 不要把当前结构优化 pack 漂移成 `warning-core` 抽离或 generic policy framework。

## 11. 一句话总结

`warning-agent` 的统一架构现在固定为：

```text
alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval + local analyzer
  -> optional investigator (default local-first)
  -> optional cloud fallback
  -> markdown report
  -> outcome feedback
```
