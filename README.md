# warning-agent

`warning-agent` 是一个极窄的智能分析-报警器。

它只做一件事：

> 接收 `Prometheus + SigNoz` 告警与观测证据，
> 用本地高频分析器做 first-pass 分诊，
> 只把少量高风险问题升级给云端大模型深挖，
> 最终输出一份稳定的 Markdown 警报报文。

## 为什么这样设计

这个项目严格按 `The Bitter Lesson` 的方向来收缩：

- 高频路径优先 `search + learning`
- 不把复杂世界直接塞进 prompt
- 不让大模型进入 every-alert 热路径
- 不把系统做成更大的 AIOps 平台

这意味着：

- 先统一表示，再统一分析
- 先让本地 analyzer 快速、稳定、可回放
- 再让云端 investigator 只处理 hard cases

## 系统主路径

```text
Prometheus / Alertmanager alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval + local analyzer
  -> optional cloud investigator
  -> markdown alert report
  -> outcome feedback
```

## 四个核心模块

### 1. `incident packet`

这是系统唯一的 canonical unit。

它把一段 bounded 时间窗内的：

- 指标变化
- 日志异常
- traces 线索
- owner / repo / blast radius
- 历史相似问题

压成一个统一对象。

### 2. 本地 `local analyzer`

本地 analyzer 是高频路径核心。

它先做：

- 本地检索历史相似 packets / reports / outcomes

再做：

- 本地快速评分

输出固定结构结果，例如：

- `severity_band`
- `severity_score`
- `novelty_score`
- `confidence`
- `needs_cloud_investigation`
- `recommended_action`
- `reason_codes`

### 3. 云端 `cloud investigator`

云端大模型不是第一层判官，而是第二层专家。

它只在这些场景触发：

- 本地判断没把握
- 问题很新
- blast radius 很高
- 本地判断和历史/规则冲突

它会做：

- `SigNoz MCP` 深挖
- bounded Prometheus follow-up
- repo 代码确认

### 4. Markdown 报文

最终产品输出不是聊天记录，而是一份稳定的 Markdown 警报文档。

每条告警都会收敛成固定结构的报文，至少包括：

- Executive Summary
- Why This Alert Exists
- Metric Signals
- Logs And Traces
- Cloud Investigation
- Impact And Routing
- Recommended Action
- Evidence Refs
- Unknowns

## 当前设计边界

这个项目当前明确不做：

- 自动执行 / remediation
- autopilot
- promotion ladder
- workflow engine
- 多 agent 编排
- observability UI

项目只聚焦：

- 智能分析
- 精准升级
- 标准报文

## 当前文档

- [warning-agent 架构设计](./docs/warning-agent-architecture.md)
- [最小 repo skeleton](./docs/warning-agent-minimal-repo-skeleton.md)
- [schema 草案](./docs/warning-agent-schema-draft.md)
- [设计决策表](./docs/analyse/warning-agent-design-decision-table.md)
- [技术栈建议](./docs/analyse/warning-agent-tech-stack-recommendation.md)
- [本地可用性检查](./docs/analyse/warning-agent-local-observability-status.md)

## 一句话总结

`warning-agent` 不是一个“大而全”的 AI 运维平台。

它是一个围绕下面这条主线构建的极窄产品：

> `incident packet -> local search + learning -> sparse cloud investigation -> markdown alert report`
