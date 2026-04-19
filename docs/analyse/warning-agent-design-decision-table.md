# warning-agent 设计决策表

- 状态: `aligned-analysis`
- 范围: `warning-agent` 在参考相邻项目后，哪些设计应该借，哪些必须故意反着做
- 对齐文档:
  - `warning-agent-architecture.md`
  - `warning-agent-schema-draft.md`

## 1. 总设计原则

`warning-agent` 现在固定坚持下面五条：

1. 主路径必须是 `alert -> packet -> local analysis -> optional investigator -> optional cloud fallback -> markdown report`
2. 高频路径优先 `search + learning`，而不是 prompt orchestration
3. investigator 只有一个接口，默认 `local-first`
4. cloud 只做 fallback，不单独扩成 reviewer 子系统
5. outcome feedback 是唯一长期复利来源，不靠持续堆叠 heuristics

## 2. 设计决策表

| 设计问题 | 该借什么 | 该故意反着做什么 | 当前结论 |
|---|---|---|---|
| 告警如何触发分析 | `alert-triggered investigation` | 不做 `chat-first` 主入口 | 主入口必须是告警驱动，不是对话驱动 |
| 观测数据如何进入系统 | bounded evidence collection | 不让 LLM 直接扫全量 raw logs / traces | 固定查询模板优先于自由探索 |
| 系统中间表示是什么 | `incident packet` | 不按 service / 场景写多套 prompt / schema | 一切下游都只消费 packet |
| 本地高频分析怎么做 | 本地检索 + 轻量 scorer | 不把 first-pass 做成小模型 agent | `P3` 的 analyzer 是 `retrieval + classifier/ranker` |
| 调查层如何实现 | 单一 investigator interface | 不再保留两套平行 investigator 子系统 | `P4` 是 local-first；`P5` 只加 cloud fallback |
| 云端模型做什么 | unresolved case fallback | 不做 every-alert LLM，不做默认审查面 | cloud 是 fallback provider，不是中心模块 |
| 产品输出是什么 | 稳定 Markdown 报文 | 不输出临时聊天结论 | 输出必须是结构化对象渲染结果 |
| 结果如何回流 | 保存 `packet / decision / investigation / report / outcome` | 不靠持续加 heuristics | 复利来自 feedback，不来自规则补丁 |
| 系统是否要平台化 | 借输入输出边界感 | 不做 workflow engine / AIOps platform | 保持极窄单闭环 |
| 是否做自动执行 | 借 enrichment / routing hint | 不做 remediation / autopilot runtime | 第一阶段止于“分析 + 报文” |

## 3. 现在明确不做的事

- multi-agent orchestration
- workflow engine
- observability suite
- action marketplace
- autonomous remediation
- raw-log-first cloud analysis

## 4. 为什么改成 local-first investigator

旧叙事的问题是：

- 文档里同时存在“两层版”和“三层版”
- local investigator 与 cloud reviewer 都被写成一等系统
- cloud 容易重新长成默认审查面

改成现在这套叙事的原因是：

- 更符合 `P3 -> P4 -> P5` 的渐进实现顺序
- 更贴近 Bitter Lesson：先把 cheap computation 做满
- 更容易控制 token、成本、路由和验证面

## 5. 一句话结论

当前正确主线固定为：

```text
Prometheus/SigNoz alert
  -> incident packet
  -> local retrieval + local analyzer
  -> optional investigator (default local-first)
  -> optional cloud fallback
  -> markdown alert report
  -> outcome feedback
```
