# warning-agent Schema Draft

- 状态: `active-contract-ssot`
- 范围:
  - `incident packet`
  - `local analyzer decision`
  - `investigation result`
  - `alert report` Markdown contract
  - `incident outcome`
- last_updated: `2026-04-19`

## 1. 设计原则

1. 所有 runtime contract 都版本化。
2. 所有时间使用 `RFC3339 UTC`。
3. 结构化对象是真相，Markdown 是投影。
4. 所有对象都必须支持 replay、diff、benchmark。
5. 热路径先产出结构化字段，再生成 prose。
6. cloud fallback 不能反向塑造热路径 contract。

## 2. 当前命名冻结

- `incident-packet.v1` 保持不变
- `local-analyzer-decision.v1` 保持不变
- `investigation-result.v1` 保持不变
- `alert-report.v1` 仍是最终 Markdown 契约
- 可执行 report schema 只物化 frontmatter，文件名固定为 `alert-report-frontmatter.v1.json`

从现在起不再使用：

- `cloud-investigation-result.v1`
- `needs_cloud_investigation`
- `cloud_trigger_reasons`
- `Cloud Investigation`

## 3. `incident-packet.v1`

### 3.1 作用

`incident packet` 是系统唯一 canonical runtime unit。

它连接：

- evidence collection
- local retrieval
- local analyzer
- investigator
- report generation

### 3.2 语义要求

它必须足够承载：

- 当前 alert / evidence window
- bounded metrics / logs / traces 摘要
- topology / owner / repo 候选
- 历史上下文
- evidence refs

但它不能退化成：

- 原始日志洪流
- 任意自由拼接的 prompt payload
- investigator 专用上下文缓存

### 3.3 当前物化文件

- `schemas/incident-packet.v1.json`
- `schemas/incident-packet.v2.json`（`W3` contract-prep；当前活路径仍保持 `v1`）

### 3.4 `incident-packet.v2`（W3-prep contract）

`incident-packet.v2` 当前只冻结 contract surface，不改变 `W2` 活路径。

新增字段固定收敛在：

- `temporal_context`
  - `error_rate_1h`
  - `error_rate_24h`
  - `error_rate_7d_p95`
  - `latency_p95_1h`
  - `latency_p95_24h`
  - `qps_1h`
  - `qps_24h`
  - `anomaly_duration_sec`
  - `deploy_age_sec`
  - `rollback_recent`
  - `new_error_template_ratio`

边界：

- `v2` 目前只作为 `W3` 的 temporal contract surface
- `W2` runtime path 继续使用 `incident-packet.v1`
- 在 learned scorer / temporal feature 真正落地前，不得把 `v2` 误写成 active runtime truth

## 4. `local-analyzer-decision.v1`

### 4.1 作用

这是本地高频分析器的唯一输出契约。

无论底层实现是：

- `fast_scorer`
- `hybrid`
- future replacement

都必须输出同一结构。

### 4.2 当前关键字段

必须包含：

- `severity_band`
- `severity_score`
- `novelty_score`
- `confidence`
- `needs_investigation`
- `recommended_action`
- `reason_codes`
- `risk_flags`
- `retrieval_hits`
- `investigation_trigger_reasons`

### 4.3 字段语义

`needs_investigation` 的语义是：

- 是否进入 investigator interface

它不是：

- 是否直接进 cloud

`investigation_trigger_reasons` 的语义是：

- 为什么当前样本需要第二层调查

它不是：

- cloud-only escalation reasons

### 4.4 当前物化文件

- `schemas/local-analyzer-decision.v1.json`

## 5. `investigation-result.v1`

### 5.1 作用

这是 investigator 层的统一输出契约。

它同时服务：

- `local-primary` provider
- `cloud-fallback` provider

### 5.2 当前关键字段

必须包含：

- `investigator_tier`
- `model_provider`
- `model_name`
- `summary`
- `hypotheses`
- `analysis_updates`
- `routing`
- `evidence_refs`
- `unknowns`

可选包含：

- `compressed_handoff`

### 5.3 `investigator_tier`

当前 canonical 允许值固定为：

- `local_primary_investigator`
- `cloud_fallback_investigator`

这反映的是单一 investigator interface 下的不同 provider，不再代表两套独立系统。

### 5.4 `compressed_handoff`

`compressed_handoff` 只服务一个目的：

- 当 `local-primary` 无法收敛时，把 case 压缩后交给 `cloud-fallback`

它不是独立 contract family，也不是独立模块中心。

### 5.5 当前物化文件

- `schemas/investigation-result.v1.json`

## 6. `alert-report.v1`

### 6.1 作用

最终产品输出仍然是稳定 Markdown 报文。

它由：

- `incident packet`
- `local analyzer decision`
- 可选 `investigation result`

共同渲染得到。

### 6.2 report section order

当前 section order 固定为：

1. `Executive Summary`
2. `Why This Alert Exists`
3. `Metric Signals`
4. `Logs And Traces`
5. `Investigation`
6. `Impact And Routing`
7. `Recommended Action`
8. `Evidence Refs`
9. `Unknowns`

### 6.3 frontmatter

当前 frontmatter 记录调查状态时统一使用：

- `investigation_stage`

允许值为：

- `none`
- `local_primary`
- `cloud_fallback`

### 6.4 当前物化文件

- `schemas/alert-report-frontmatter.v1.json`

## 7. `incident-outcome.v1`

### 7.1 作用

`incident outcome` 是反馈层的 canonical artifact。

它连接：

- `incident packet`
- `local analyzer decision`
- 可选 `investigation result`
- `alert report`
- landed operator / replay / postmortem outcome truth

### 7.2 当前关键字段

必须包含：

- `outcome_id`
- `source`
- `recorded_at`
- `service`
- `operation`
- `environment`
- `input_refs`
- `summary`
- `notes`

其中 `summary` 当前最小冻结为：

- `known_outcome`
- `final_severity_band`
- `final_recommended_action`
- `resolution_summary`

### 7.3 边界

`incident outcome` 当前只承担两类职责：

1. 形成稳定、可回放、可检索的 outcome artifact
2. 为后续 retrieval refresh / corpus assembly / retrain compare 提供 landed truth link

当前不承担：

- retrieval refresh 逻辑本身
- corpus assembly 逻辑本身
- auto promotion 决策本身

### 7.4 当前物化文件

- `schemas/incident-outcome.v1.json`

## 8. 当前 contract 边界

这些边界现在固定：

1. `incident packet` 是唯一 runtime unit。
2. `local analyzer decision` 决定是否进入 investigator，而不是是否直接进 cloud。
3. `investigation result` 是单一 investigator interface 的统一输出。
4. `alert report` 的 JSON schema 只覆盖 frontmatter；正文结构由 report contract 固定。
5. `incident outcome` 是反馈层 canonical artifact，但在 `W4.S1a` 仍不承担 retrieval refresh / compare 逻辑。

## 9. 一句话结论

当前 contract SSOT 的核心是：

> packet 统一输入，
> decision 决定是否调查，
> investigation result 统一承载 local-first 与 cloud-fallback，
> report 固定输出，
> outcome 承载 landed feedback truth。
