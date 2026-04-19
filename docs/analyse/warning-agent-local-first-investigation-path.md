# warning-agent local-first Investigator Path

- 状态: `aligned-analysis`
- 范围:
  - `local analyzer`
  - `investigator interface`
  - `local-primary provider`
  - `cloud-fallback provider`
- 对齐文档:
  - `warning-agent-architecture.md`
  - `warning-agent-schema-draft.md`

## 1. 为什么不再保留“三层叙事”

旧叙事的问题不是“多一层模型”本身，而是：

- `local investigator` 和 `cloud reviewer` 都被写成一等系统
- 文档里容易形成两套模块、两套 gate、两套心智模型
- cloud 层容易重新长成默认审查面

现在的简化方式是：

- 保留计算分层
- 但只保留一个 investigator interface
- default provider 是 `local-primary`
- cloud 只做 fallback

## 2. 当前 canonical 路径

```text
incident packet
  -> local retrieval + local analyzer
  -> if needs_investigation:
       investigator interface
         -> local-primary provider
         -> if unresolved / over-budget: cloud-fallback provider
  -> markdown report
```

## 3. 各层职责

### 3.1 `local analyzer`

职责：

- 每条 packet 都处理
- retrieval + fast scorer
- 输出结构化 `local-analyzer-decision.v1`
- 决定 `needs_investigation`

### 3.2 `investigator interface`

职责：

- 吃一个 packet 和一个 local decision
- 调 bounded tools
- 输出结构化 `investigation-result.v1`
- 路由 local-primary 与 cloud-fallback

### 3.3 `local-primary provider`

职责：

- 处理绝大多数 hard cases
- 在 bounded 预算内完成深挖
- 生成结构化 investigation result
- 尽量在本地收敛，不把 token 推给 cloud

### 3.4 `cloud-fallback provider`

职责：

- 只处理 unresolved / over-budget / conflicting hypothesis cases
- 只消费 compressed handoff 与少量 bounded refs
- 不重新读取完整原始观测洪流

## 4. 触发规则

### 4.1 `local analyzer -> investigator interface`

当满足任一条件时触发：

- `confidence < threshold`
- `novelty_score` 高
- `blast_radius_score` 高
- `recommended_action = page_owner`
- retrieval 与当前判断冲突

### 4.2 `local-primary -> cloud-fallback`

只有满足更严格条件才触发：

- 本地调查后仍有关键未知项
- 多个高置信冲突 hypothesis 无法收敛
- 命中 token / tool / wall-time budget
- 需要更强模型做最终压缩判断

## 5. 为什么这更符合 Bitter Lesson

这套路径保留了真正重要的东西：

1. 热路径仍然是 `search + learning`
2. investigator 输出仍是结构化监督数据
3. cloud 只做稀疏 fallback
4. 经验仍然回流到 retrieval / scorer / future model replacement

它去掉的是不必要的系统复杂度：

- 独立 reviewer 子系统
- 两套并行 investigator 叙事
- cloud-first 心智模型

## 6. 一句话结论

当前正确说法不是“三层系统”，而是：

> 一个 `local-first` 的 investigator interface，
> 必要时才使用 cloud fallback。
