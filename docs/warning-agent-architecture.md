# warning-agent 架构设计

- 状态: `draft-ssot`
- 范围: `Prometheus + SigNoz` 智能分析-报警器
- 核心哲学: `The Bitter Lesson`
- 目标形态:
  - 接收实时告警
  - 进行高频本地分析
  - 先把少量高风险样本升级给本地 `Gemma4` investigator 深挖
  - 再只把极少量 top hard cases 升级给云端更强模型终审
  - 输出稳定的 Markdown 警报报文

## 1. 产品目标

`warning-agent` 的目标非常窄，只做一件事:

> 把 `Prometheus + SigNoz` 的告警与观测证据压成统一事件单元，
> 用本地高频 `search + learning` 做 first-pass 智能分诊，
> 对少量疑似高风险样本调用本地 `Gemma4` investigator 做深挖，
> 再把极少量 top hard cases 升级给云端更强模型终审，
> 最终产出稳定、可读、可追溯的 Markdown 警报报文。

它不是:

- observability UI
- 生产自动化执行器
- 全量 incident 管理平台
- 多 agent 协作框架
- 全量 raw logs 的大模型阅读器

## 2. `The Bitter Lesson` 对本产品的直接约束

`The Bitter Lesson` 的可执行含义很明确:

1. 优先建设 `search` 与 `learning`，不要优先建设复杂规则树。
2. 优先建设统一表示，避免把世界复杂性直接塞进 prompt 或 service-specific 逻辑。
3. 大模型只做稀疏高价值推理，不做高频热路径。
4. 产品输出必须结构化、可回放、可校准，而不是一次一变的 prose。
5. 反馈应回流到本地分析器，而不是不断叠加人工 heuristics。

本产品下的明确反模式:

- 每个 service 单独写一套 prompt
- 告警来了就直接让大模型扫日志
- 把本地分析器做成 free-form 聊天 agent
- 让 Markdown 报文成为唯一真相
- 把“看起来聪明”的手工逻辑堆成主路径

## 3. 最小正确结构

最小正确系统现在应理解为 7 个在线组件和 2 个离线闭环。

| 层 | 组件 | 作用 | 是否热路径 |
|---|---|---|---|
| 输入层 | `Alert Receiver` | 接收 Alertmanager webhook 或少量热点窗口扫描 | 是 |
| 采证层 | `Evidence Collector` | 用固定查询模板采集 `Prometheus` 与 `SigNoz` 证据 | 是 |
| 表示层 | `Incident Packet Builder` | 生成统一事件表示 `incident packet` | 是 |
| 本地计算层 | `Local Analyzer` | 做本地检索与快速评分，给出结构化 first-pass 结论 | 是 |
| 本地深挖层 | `Local Gemma4 Investigator` | 调查升级样本，做高 token 深挖与压缩 handoff | 否 |
| 云端终审层 | `Cloud Final Reviewer` | 只终审最难样本，复核本地 investigator 结论 | 否 |
| 输出层 | `Markdown Report Builder` | 产出标准化 `md` 警报报文 | 是 |
| 反馈层 | `Outcome Store` | 存储 packet / decision / report / outcome | 否 |
| 学习层 | `Retrain / Recalibrate Jobs` | 刷新检索索引与本地分析器 | 否 |

这就是产品的最小可行结构。

## 4. 唯一中间表示: `incident packet`

系统只允许一个 canonical runtime unit:

- `incident packet`

为什么必须这么做:

- 它让本地检索和本地学习共享同一输入
- 它让云端 investigator 只看 bounded context
- 它让 replay 与 benchmark 成为可能
- 它防止系统退化成“大模型读一切”

任何下游模块都只能消费:

- `incident packet`
- `local analyzer decision`
- 可选的 `cloud investigation result`

不能直接消费:

- 全量日志流
- 任意原始 trace dump
- 任意自由拼接的上下文

## 5. 运行时数据流

### 5.1 本地热路径

```text
Alertmanager webhook
  -> bounded evidence collection
  -> incident packet
  -> local retrieval
  -> local scorer
  -> structured local decision
  -> markdown report
```

这个路径解决的是:

- 高频
- 低成本
- 高吞吐
- 可回放

### 5.2 三层 investigator 路径

```text
incident packet
  -> local analyzer says "needs investigation"
  -> local Gemma4 investigator
  -> compressed handoff
  -> optional cloud final reviewer
  -> SigNoz MCP deep analysis
  -> bounded Prometheus follow-up
  -> repo code confirmation
  -> enriched markdown report
```

这个路径解决的是:

- 高风险
- 高不确定性
- 跨 metrics/logs/traces 的综合定位
- code-level 佐证
- 计算分层后的高频深挖
- 只把极少数样本交给最昂贵模型

### 5.3 反馈学习路径

```text
packet + local decision + local/cloud investigation result + report + operator outcome
  -> outcome store
  -> retrieval refresh
  -> local scorer recalibration
  -> later local Gemma4 distillation / fine-tuning
  -> later small-model fine-tuning
```

这条路径才是 Bitter Lesson 下真正有复利的部分。

## 6. 本地分析器的正确角色

### 6.1 不应该是什么

本地分析器不应该一开始就是:

- 本地聊天 agent
- 自由输出 prose 的小模型
- service-aware prompt orchestra

这些都不够稳定，也不够容易 benchmark。

### 6.2 应该是什么

本地分析器应先定义成一个稳定接口:

- 输入: `incident packet`
- 输出: `local analyzer decision`

第一版推荐实现:

1. `local retrieval`
   - 搜索历史 packets
   - 搜索历史 alert reports
   - 搜索历史 outcomes
2. `fast scorer`
   - numeric features
   - categorical features
   - retrieval features
   - calibration layer

这比直接上本地生成式小模型更符合 `The Bitter Lesson`。

### 6.3 后续小模型升级位置

本地小模型应作为:

- `local analyzer` 的第二实现

而不是整个系统的中心。

正确顺序是:

1. 先有 packet
2. 先有 retrieval
3. 先有 fast scorer
4. 再把 scorer 背后的模型替换成 small model

而不是:

1. 先上本地 chat model
2. 再想办法让它看起来可控

## 7. investigator 分层的正确角色

### 7.1 本地 `Gemma4` investigator 的正确角色

本地 `Gemma4` investigator 负责第二层调查。

它的输入应被严格压缩为:

- 一个 `incident packet`
- 一个 `local analyzer decision`
- 少量 retrieval 摘要
- 有界的 observability tool 结果
- 少量 repo 候选

允许它做的事:

- 多步读取 packet 与 retrieval 结果
- 调 `SigNoz MCP`
- 补充有限的 Prometheus 查询
- 在 repo 候选上做本地代码确认
- 生成结构化 `investigation result`
- 生成压缩 handoff 给云端 reviewer

不允许它做的事:

- 处理 every-alert 热路径
- 无边界调用工具
- 读取原始日志洪流
- 直接改变系统契约

### 7.2 云端 `final reviewer` 的正确角色

云端更强模型只负责第三层终审。

它的输入应该被严格压缩为:

- 一个 `incident packet`
- 一个 `local analyzer decision`
- 一个本地 `Gemma4` investigation result
- 一个压缩 handoff
- 少量最终补充工具结果

允许它做的事:

- 复核本地 investigator 的故障链判断
- 在必要时补做极少量高价值工具查询
- 生成 final review 结果
- 提升最终报文质量与置信度标注

不允许它做的事:

- 全量读取原始日志
- 替代本地 first-pass scorer
- 替代本地 Gemma4 承担高频深挖
- 自己决定系统契约

## 8. 技术路径分阶段

### Stage A: packet-first baseline

先做:

- Alertmanager 接入
- Prometheus 固定查询模板
- SigNoz 固定查询模板
- `incident packet` 契约
- Markdown 报文模板

此时不需要:

- 本地小模型
- investigator 分层

### Stage B: search-first local analyzer

加上:

- packet render
- 本地检索索引
- 轻量 scorer
- 校准与阈值

推荐起步实现:

- `SQLite FTS5 / BM25` 检索
- `Logistic Regression / LightGBM` 评分

### Stage C: local Gemma4 investigator

再加上:

- escalation gates
- 本地 `Gemma4` investigator
- bounded `SigNoz MCP` / Prometheus follow-up
- repo 映射与代码确认
- structure investigation result
- compressed handoff generation

### Stage D: sparse cloud final review

再加上:

- second-stage escalation gates
- cloud final reviewer
- final review result
- enriched alert report

### Stage E: local small model upgrade

最后才考虑:

- text-first local small model
- 替换 fast scorer
- 保持相同输出 contract
- 用 outcome-backed 数据蒸馏和微调

## 9. 本地模型与云端模型分工

当前推荐的最小正确分工是:

| 层 | 角色 | 特征 |
|---|---|---|
| 本地 analyzer | dense first-pass triage | 快、便宜、结构化、可回滚 |
| 本地 `Gemma4` investigator | high-frequency deep investigation | 更强、可高频、bounded tools、可沉淀 teacher 经验 |
| 云端 final reviewer | sparse final review | 最贵、最强、只终审 top hard cases |

本地输出必须是:

- `severity_band`
- `severity_score`
- `novelty_score`
- `confidence`
- `needs_cloud_investigation`
- `recommended_action`
- `reason_codes`

investigator 输出必须是结构化 `investigation result`，至少包含:

- suspected failure chain
- key supporting evidence
- likely owner / repo / component
- recommended next checks
- unknowns
- compressed handoff（若要升级给下一层）

## 10. 产品输出: Markdown 报文

Markdown 报文不是附属物，它就是产品输出。

每条告警都必须收敛成一份稳定结构的文档，至少包含:

- `Executive Summary`
- `Why This Alert Exists`
- `Metric Signals`
- `Logs And Traces`
- `Cloud Investigation`
- `Impact And Routing`
- `Recommended Action`
- `Evidence Refs`
- `Unknowns`

报文应由结构化字段渲染，不允许把最终输出建立在不稳定的自然语言生成上。

## 11. 最小评测面

产品最小评测指标应只围绕窄目标：

- severe recall
- top-K precision
- cloud escalation rate
- false-page rate
- local analyzer latency
- report completeness rate

若未来本地小模型在这些指标的组合上不优于 `retrieval + fast scorer`，则不应替换更简单的实现。

对于三层 investigator，还应额外观察：

- local Gemma4 escalation rate
- cloud final review rate
- local Gemma4 -> cloud final review 的压缩保真度
- 每层 investigator 的平均 token / 时间成本

## 12. 最终建议

如果只做这个窄产品，当前最合理且最符合 `The Bitter Lesson` 的结构是：

```text
alert receiver
  -> evidence collector
  -> incident packet
  -> local retrieval + local analyzer
  -> optional local Gemma4 investigator
  -> optional cloud final reviewer
  -> markdown report
  -> outcome feedback
```

核心原则只有一句:

> 把高频路径做成 `search + learning`，
> 把 investigator 路径拆成“本地高频深挖 + 云端稀疏终审”，
> 把 Markdown 报文做成稳定产品输出，
> 把 outcome 回流做成唯一长期复利来源。
