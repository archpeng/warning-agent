# warning-agent 三层 Investigator 路径

- 状态: `draft-analysis`
- 范围:
  - `local analyzer`
  - `local Gemma4 investigator`
  - `cloud final reviewer`
- 目标:
  - 明确三层调查链路何时触发
  - 明确本地 Gemma4 与云端模型各自的预算边界
  - 明确调查结果如何回流到本地判断系统

## 1. 为什么采用三层而不是两层

如果链路只有两层：

```text
local analyzer
  -> cloud model
```

会有两个问题：

1. 云端模型频率和成本会限制 deep investigation 的覆盖率
2. 本地无法形成高频 teacher 层

如果链路改成三层：

```text
local fast analyzer
  -> local Gemma4 investigator
  -> cloud final reviewer
```

就能同时得到：

- 高频 cheap first-pass
- 高频强一些的本地 deep investigation
- 极少量最强云端终审

这条路线比“纯云端 teacher”更适合第一阶段产品化。

## 2. 三层定义

### Layer 1: `local analyzer`

职责：

- 每条 packet 都处理
- retrieval + fast scorer
- 输出结构化 first-pass 决策

输出对象：

- `local-analyzer-decision.v1`

### Layer 2: `local Gemma4 investigator`

职责：

- 只处理被 first-pass 升级的样本
- 做 bounded 多步调查
- 使用较大 token budget
- 输出结构化 investigation result
- 产出压缩 handoff

输出对象：

- `cloud-investigation-result.v1`
- `investigator_tier = local_gemma4_investigator`

### Layer 3: `cloud final reviewer`

职责：

- 只处理最难、最重要、最昂贵的样本
- 复核本地 Gemma4 的调查结果
- 必要时补做极少量工具调用
- 生成最终终审结果

输出对象：

- `cloud-investigation-result.v1`
- `investigator_tier = cloud_final_reviewer`

## 3. 触发规则

### 3.1 `local analyzer -> local Gemma4 investigator`

当满足任一条件时触发：

- `confidence < 0.55`
- `novelty_score >= 0.75`
- `blast_radius_score >= 0.70`
- `severity_band in {P1, P2}` 且 `confidence < 0.75`
- `recommended_action = page_owner`
- 本地判断与 fired alerts / retrieval severe hits 冲突
- 关键 service / 关键 operation 被命中

### 3.2 `local Gemma4 investigator -> cloud final reviewer`

只有满足更严格条件才继续升级：

- 本地 Gemma4 investigation 后仍有关键未知项
- 本地 Gemma4 给出多个高置信冲突 hypothesis
- 涉及 `tier0/tier1` 服务且建议动作为 `page_owner`
- 涉及跨 repo / 跨依赖链路、影响面过大
- 本地 Gemma4 的 `confidence < 0.70`
- 本地 Gemma4 的 `compressed_handoff` 仍包含 high-risk unresolveds

### 3.3 明确不升级的情况

以下情况应停在本地 Gemma4：

- 故障链清晰
- owner / repo 候选清晰
- 建议动作明确
- 未知项不影响当下处置
- 属于重复出现且历史已知模式

## 4. 预算策略

### 4.1 Layer 1 预算

`local analyzer` 应该追求：

- 每 packet 低延迟
- 无 LLM 依赖
- 可并发

预算目标：

- 毫秒级到低秒级
- 高频运行

### 4.2 Layer 2 预算

`local Gemma4 investigator` 可以更贵，但必须 bounded。

建议预算字段：

- max prompt tokens
- max completion tokens
- max tool calls
- max repo search hits
- max trace refs
- max investigation wall time

建议第一版策略：

- 每次只看一个 packet
- 工具调用上限固定
- repo search 限定在 mapped repo candidates
- 超预算则直接输出部分结论和未知项

### 4.3 Layer 3 预算

`cloud final reviewer` 必须更稀疏、更严格。

建议策略：

- 只处理本地 Gemma4 过滤后的 top hard cases
- 输入优先使用 `compressed_handoff`
- 不再直接吃完整原始观测洪流
- 每次调用都应有明确升级理由

## 5. 数据回流方式

这是三层设计最关键的价值。

### 5.1 本地 analyzer 的回流

使用：

- `local-analyzer-decision.v1`
- 最终 outcome

来更新：

- retrieval 索引
- fast scorer 权重
- calibration thresholds

### 5.2 本地 Gemma4 的回流

使用：

- `cloud-investigation-result.v1`
- `investigator_tier = local_gemma4_investigator`

来沉淀：

- structured reason codes
- failure chain patterns
- owner / repo routing hints
- compressed handoff 模板

它的价值不只是“当前调查结果”，而是：

- 下一次相似样本的检索语料
- 未来 local small model 的 teacher supervision

### 5.3 云端 final review 的回流

使用：

- `cloud-investigation-result.v1`
- `investigator_tier = cloud_final_reviewer`

来沉淀：

- final teacher judgement
- 对本地 Gemma4 的偏差修正
- 更高质量的 training targets
- 更高质量的 escalation rules

## 6. 为什么这条路仍然符合 The Bitter Lesson

关键不是“有没有多一层模型”，而是：

- 热路径是否仍然是 `search + learning`
- investigator 结果是否被结构化沉淀
- 是否避免把经验写成越来越复杂的人工规则

这条路线符合它的地方在于：

1. first-pass 仍是 local search + learning
2. 本地 Gemma4 investigator 输出是结构化 supervision，不是一次性 prose
3. 云端 final reviewer 也输出同一结构化对象
4. 所有经验最终都能回流到 retrieval / scorer / future local model

所以这条路不是“模型堆叠”，而是：

**计算分层 + 结构化教师信号 + 统一反馈闭环**

## 7. 最终建议

`warning-agent` 的 investigator 路径应正式冻结为：

```text
incident packet
  -> local retrieval + local analyzer
  -> optional local Gemma4 investigator
  -> optional cloud final reviewer
  -> markdown alert report
  -> outcome feedback
```

其中：

- `local analyzer` 负责高频 first-pass
- `local Gemma4 investigator` 负责高频 hard-case 深挖
- `cloud final reviewer` 负责极少量终审

一句话总结：

> 让便宜计算处理所有样本，
> 让本地强模型处理大多数难样本，
> 让云端最强模型只处理最难的那一小撮，
> 并把每一层经验都变成结构化监督数据回流给系统。 
