# warning-agent 设计决策表

- 状态: `draft-analysis`
- 范围: `warning-agent` 在参考同类项目后，哪些设计应该借，哪些应该故意反着做
- 目标:
  - 为窄版智能分析-报警器建立清晰的产品边界
  - 防止 repo 演化成更大的 incident platform / AIOps platform
  - 保持实现路径符合 `The Bitter Lesson`

## 1. 背景

在对相邻项目与方向做广泛搜索后，可以确认：

- 已经有不少项目在做 `AI + observability + incident investigation`
- 但很少有项目严格等于 `warning-agent` 现在要做的极窄产品面：
  - `Prometheus/SigNoz` 告警驱动
  - 本地高频 `search + learning` 初筛
  - 少量样本升级给云端 investigator
  - 输出标准 Markdown 警报报文

因此，最重要的不是“完整照搬哪个项目”，而是明确：

1. 哪些设计值得借
2. 哪些设计必须故意反着做
3. `warning-agent` 最终要保持什么边界

## 2. 总设计原则

`warning-agent` 的设计原则应固定为：

1. 主路径必须是 `alert -> packet -> local analysis -> optional cloud investigation -> markdown report`
2. 高频路径优先 `search + learning`，而不是 prompt orchestration
3. 大模型只做 sparse investigation，不做 every-alert hot path
4. Markdown 报文是产品输出，不是调试副产物
5. outcome feedback 是唯一长期复利来源，不靠持续堆叠 heuristics

## 3. 设计决策表

| 设计问题 | 可参考方向 | 该借什么 | 该故意反着做什么 | 对 warning-agent 的结论 |
|---|---|---|---|---|
| 告警如何触发分析 | `IncidentFox`、`Grafana Sift`、`incident.io Investigations` | `alert-triggered investigation`，告警一到就启动 bounded analysis | 不做 `chat-first`，不把手工问答当主入口 | 主入口必须是告警驱动，不是对话驱动 |
| 观测数据如何进入系统 | `Robusta`、`Coroot`、`APO` | 先做 bounded evidence collection，把 logs/traces/metrics 压成有限上下文 | 不让 LLM 直接扫全量 raw logs / traces flood | 固定查询模板优先于自由探索 |
| 系统中间表示是什么 | `fixit` 的 `incident packet` 思路 | 用统一 `incident packet` 承接多源证据 | 不按 service / 场景写多套 prompt 或多套 schema | 一切下游都只消费 packet |
| 本地高频分析怎么做 | `The Bitter Lesson`、`fixit` 当前最优实践 | 先做 `search + learning`：本地检索 + 轻量 scorer | 不把本地 first-pass 做成小模型 agent 或 prose engine | MVP 的 local analyzer 应是 `retrieval + classifier/ranker` |
| 云端大模型做什么 | `IncidentFox`、`SigNoz MCP`、`incident.io` | 只做 sparse hard-case investigation，可调工具、多链路分析、repo 代码确认 | 不做 every-alert LLM，不做热路径主判官 | 云端模型是 investigator，不是 scorer |
| 产品输出是什么 | `IncidentFox`、`Robusta`、`incident.io` | 自动回写一个稳定输出物 | 不输出临时聊天结论，不让 prose 成唯一真相 | 输出必须是标准 Markdown 报文 |
| 结果如何持续提升系统 | `The Bitter Lesson`、`fixit` | 保存 `packet / decision / report / outcome`，回流到检索与本地模型 | 不靠持续加 heuristics、规则和 prompt patch | 复利来自 feedback，不来自手工规则 |
| 系统是否要平台化 | `Keep`、`Coroot` | 借 trigger / step / output 的边界感 | 不做 workflow engine，不做 observability suite，不做通用 AIOps platform | `warning-agent` 必须保持极窄 |
| 是否做自动执行 | `Robusta`、`Keep` 相邻方向 | 借 enrichment 与 routing hint | 不做 remediation，不做 autopilot，不做 action execution | 第一阶段止于“分析 + 报文” |
| 是否引入多 agent | `IncidentFox`、AI SRE 类平台 | 借 investigation / writeback 的产品价值 | 不做 multi-agent 编排，不做复杂自治 loop | 单 investigator + bounded tools 已足够 |

## 4. 项目逐项提炼

### 4.1 IncidentFox

#### 该借什么

- 告警驱动自动分析
- 自动聚合 observability 与代码上下文
- 自动把分析结果回写到协作流或告警上下文

#### 该故意反着做什么

- 不做大而全 AI SRE 平台
- 不做多 agent 社会
- 不做过宽的 incident management surface

#### 对 warning-agent 的结论

`IncidentFox` 证明“alert-triggered AI investigation”是有产品价值的；  
但 `warning-agent` 应保留更窄、更轻、更可 benchmark 的结构。

### 4.2 Sherlog Prometheus Agent

#### 该借什么

- 紧贴 `Prometheus/Loki/Grafana` 的观测分析思路
- 让系统直接服务 observability 数据分析而不是抽象平台

#### 该故意反着做什么

- 不把自然语言问答做成主入口
- 不把“会问答”当成核心价值

#### 对 warning-agent 的结论

应借它“贴着 observability 工作”的姿态，  
但 `warning-agent` 必须保持 `alert-driven` 而不是 `chat-driven`。

### 4.3 Keep

#### 该借什么

- trigger / step / output 的层次边界
- 清晰的输入输出设计

#### 该故意反着做什么

- 不做 workflow engine
- 不做 generic alert automation platform
- 不做 action marketplace

#### 对 warning-agent 的结论

借结构感，不借平台化。  
`warning-agent` 只需要一个单闭环产品，不需要通用编排系统。

### 4.4 Coroot

#### 该借什么

- 把 metrics/logs/traces 联合解释成 RCA 结果
- 让根因分析回到证据链，而不是抽象猜测

#### 该故意反着做什么

- 不把 `warning-agent` 做成 observability suite
- 不重复建设 dashboard / APM / profiling 面

#### 对 warning-agent 的结论

`warning-agent` 应消费 observability 平台，而不是取代 observability 平台。

### 4.5 Robusta

#### 该借什么

- alert enrichment 的设计直觉
- 先补证据，再做结论
- 对 owner / routing / diagnostics 的直接支持

#### 该故意反着做什么

- 不做 remediation
- 不做 Kubernetes-specialized automation 主线
- 不让 enrichment 继续膨胀成 execution layer

#### 对 warning-agent 的结论

告警 enrichment 很值得借，  
但产品终点应是 Markdown 报文，而不是自愈执行。

### 4.6 APO / 其他 LLM Troubleshooting Workflow

#### 该借什么

- 多信号交叉验证
- investigation 结果必须能回到 trace/log/metric 证据

#### 该故意反着做什么

- 不做重 workflow / heavy orchestration
- 不做复杂 planner / agent runtime

#### 对 warning-agent 的结论

要借“调查深度”，不要借“系统复杂度”。

### 4.7 SigNoz MCP Server

#### 该借什么

- 作为 cloud investigator 的工具基座
- 提供 logs / traces / metrics 的统一查询能力

#### 该故意反着做什么

- 不把 MCP 调用带进 every-alert 热路径
- 不把工具层误当产品本身

#### 对 warning-agent 的结论

`SigNoz MCP` 很适合作为 investigator 的基础设施，  
但必须保持稀疏调用。

## 5. warning-agent 应坚持的设计选择

综合所有参考方向，`warning-agent` 应明确坚持下面这些选择：

### 5.1 要坚持的

1. `alert-triggered investigation`
2. `incident packet` 作为唯一中间表示
3. 本地 `retrieval + fast scorer` 做 high-frequency first-pass
4. 云端 investigator 只处理 hard cases
5. Markdown 报文作为稳定产品输出
6. outcome feedback 回流到本地 analyzer

### 5.2 不要偏离到的方向

1. 不做多 agent incident platform
2. 不做通用 alert workflow engine
3. 不做 full observability suite
4. 不做 remediation / autopilot
5. 不做 raw-log-first LLM 设计
6. 不做“本地小模型聊天代理”热路径

## 6. 最终产品边界

`warning-agent` 最终应被定义为：

> 一个消费 `Prometheus + SigNoz` 告警与观测数据的窄版智能分析-报警器，
> 通过 `incident packet`、本地高频 `search + learning`、稀疏云端调查与标准 Markdown 报文，
> 为 on-call / owner 提供更及时、更清晰、更可追溯的告警分析结果。

它不应该被定义为：

- observability platform
- incident management platform
- AIOps orchestration platform
- autonomous remediation system

## 7. 一句话结论

对 `warning-agent` 来说，最值得借的是：

- `alert-triggered investigation`
- `bounded evidence collection`
- `evidence-backed RCA`
- `stable writeback`

最应该故意反着做的是：

- 平台化
- workflow 化
- 多 agent 化
- 自动执行化
- raw-log-first LLM 化

最终正确主线应保持为：

```text
Prometheus/SigNoz alert
  -> incident packet
  -> local retrieval + local analyzer
  -> optional cloud investigator
  -> markdown alert report
  -> outcome feedback
```
