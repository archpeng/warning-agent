# warning-agent 最小 Repo Skeleton

- 状态: `draft`
- 范围: 仅服务于窄版智能分析-报警器
- 对齐文档:
  - `warning-agent-architecture.md`
  - `warning-agent-schema-draft.md`

## 1. 设计目标

这个 repo 的目标不是“容纳所有未来能力”，而是把主路径做得最清楚。

唯一主路径是:

```text
alert -> packet -> local analysis -> optional local Gemma4 investigation -> optional cloud final review -> markdown report
```

因此 repo 结构必须让这条路径直接可见。

## 2. 最小目录结构

```text
warning-agent/
  docs/
    warning-agent-architecture.md
    warning-agent-minimal-repo-skeleton.md
    warning-agent-schema-draft.md

  app/
    main.py

    receiver/
      alertmanager_webhook.py
      hot_window_scan.py

    collectors/
      prometheus.py
      signoz.py

    packet/
      builder.py
      render.py
      contracts.py

    retrieval/
      index.py
      search.py

    analyzer/
      base.py
      fast_scorer.py
      small_model.py
      calibrate.py

    investigator/
      local_gemma4_investigator.py
      cloud_final_reviewer.py
      handoff_builder.py
      signoz_tools.py
      prom_tools.py
      repo_locator.py

    reports/
      markdown_builder.py
      templates.py

    storage/
      sqlite_store.py
      artifact_store.py

    feedback/
      outcome_ingest.py
      retrain_jobs.py

  schemas/
    incident-packet.v1.json
    local-analyzer-decision.v1.json
    alert-report-frontmatter.v1.json

  configs/
    services.yaml
    thresholds.yaml
    escalation.yaml
    reports.yaml

  data/
    packets/
    decisions/
    investigations/
    reports/
    outcomes/
    retrieval/

  scripts/
    run_shadow_replay.py
    rebuild_retrieval_index.py
    train_fast_scorer.py
    train_small_model.py
    backfill_packets.py

  tests/
    test_packet_builder.py
    test_retrieval.py
    test_fast_scorer.py
    test_cloud_investigator.py
    test_markdown_builder.py
    test_end_to_end_shadow.py
```

## 3. 热路径模块

这些模块构成产品主路径，必须优先实现：

| 文件 | 作用 |
|---|---|
| `app/receiver/alertmanager_webhook.py` | 接收 Prometheus Alertmanager 事件 |
| `app/collectors/prometheus.py` | 拉取固定 Prometheus 指标窗口 |
| `app/collectors/signoz.py` | 拉取固定 SigNoz logs / traces / 聚合结果 |
| `app/packet/builder.py` | 构造 `incident packet` |
| `app/packet/render.py` | 把 packet 渲染成检索与模型输入文本 |
| `app/retrieval/search.py` | 本地历史检索 |
| `app/analyzer/fast_scorer.py` | 本地高频 structured scorer |
| `app/investigator/local_gemma4_investigator.py` | 本地 Gemma4 高频 hard-case 深挖 |
| `app/investigator/handoff_builder.py` | 把本地 investigator 结果压缩成下一层可消费 handoff |
| `app/investigator/cloud_final_reviewer.py` | 云端最强模型终审 top hard cases |
| `app/reports/markdown_builder.py` | 生成标准化 Markdown 报文 |

如果某个模块不直接服务这条链路，就不应该进入第一版 repo。

## 4. 冷路径模块

这些模块不是第一波必须完整实现，但必须保留位置：

| 文件 | 作用 |
|---|---|
| `app/retrieval/index.py` | 构建本地检索索引 |
| `app/analyzer/small_model.py` | 本地小模型版 analyzer |
| `app/analyzer/calibrate.py` | 校准与阈值更新 |
| `app/storage/sqlite_store.py` | metadata 存储 |
| `app/storage/artifact_store.py` | JSONL / Parquet artifact 存储 |
| `app/feedback/outcome_ingest.py` | outcome 写回 |
| `app/feedback/retrain_jobs.py` | 检索刷新与训练任务 |

## 5. 本地 analyzer 边界

本地 analyzer 必须永远被当成一个稳定接口，而不是一个具体模型。

统一 contract:

- 输入: `incident packet`
- 输出: `local analyzer decision`

内部可以有两种实现:

1. `fast_scorer.py`
   - 当前默认实现
   - retrieval + feature scorer
2. `small_model.py`
   - 后续替代候选
   - 使用相同输出 schema

这样做的原因是:

- 产品不绑定某个模型家族
- benchmark 与 rollback 更简单
- Bitter Lesson 下，系统结构优先于具体模型

## 6. investigator 三层边界

### 6.1 `local_gemma4_investigator.py`

作用：

- 处理被 first-pass 升级的 hard cases
- 允许较大 token budget
- 做 bounded observability deep analysis
- 输出结构化 investigation result
- 生成压缩 handoff

允许：

- 读一个 `incident packet`
- 读一个 `local analyzer decision`
- 调 `SigNoz MCP`
- 补 Prometheus 查询
- 在映射 repo 中做代码确认

不允许：

- 参与 every-alert 热路径
- 无边界工具调用
- 直接决定系统 schema
- 取代 local analyzer

### 6.2 `handoff_builder.py`

作用：

- 把本地 Gemma4 investigation result 压缩成更短的 handoff
- 供 cloud final reviewer 使用

允许：

- 提炼关键 hypothesis
- 提炼 reason codes
- 提炼证据引用
- 估算 handoff token 规模

不允许：

- 替代 investigator 本身
- 直接做最终判决

### 6.3 `cloud_final_reviewer.py`

作用：

- 只处理最难、最重要的 top hard cases
- 复核本地 Gemma4 的结论
- 输出 final review result

允许：

- 读 packet
- 读 local decision
- 读 local Gemma4 investigation result
- 读 compressed handoff
- 必要时补充极少量高价值工具调用

不允许：

- 参与 every-alert 热路径
- 重复做完整本地调查
- 读取原始观测洪流
- 直接决定系统 schema

## 7. 推荐实现顺序

按下面顺序实现最稳：

1. `schemas/`
2. `packet/`
3. `collectors/`
4. `reports/`
5. `retrieval/`
6. `analyzer/fast_scorer.py`
7. `investigator/local_gemma4_investigator.py`
8. `investigator/handoff_builder.py`
9. `investigator/cloud_final_reviewer.py`
10. `storage/`
11. `feedback/`
12. `analyzer/small_model.py`

这个顺序的意义是：

- 先固定表示
- 再固定采证
- 再固定输出
- 再引入 search
- 再引入 local learning
- 再引入本地 Gemma4 investigator
- 再引入云端终审
- 最后才引入 local small model

## 8. 最小配置文件

### `configs/services.yaml`

只放:

- service canonical names
- operation allowlists
- owner hints
- repo hints

### `configs/thresholds.yaml`

只放:

- 本地 severity thresholds
- novelty threshold
- cloud escalation threshold
- false-page ceiling

### `configs/escalation.yaml`

只放:

- local Gemma4 investigation trigger rules
- cloud final review trigger rules
- max concurrent local investigations
- max concurrent cloud reviews
- report delivery routes

### `configs/reports.yaml`

只放:

- Markdown section order
- severity -> delivery class mapping
- optional labels

## 9. 推荐最小存储

一开始不要上复杂数据库与事件总线。

推荐最小存储：

- `SQLite` 存 metadata
- `JSONL` 存 packet / decision / investigation / outcome artifacts
- 本地检索索引文件

最小表集合：

- `packets`
- `local_decisions`
- `investigations`
- `alert_reports`
- `outcomes`

## 10. 第一版不要引入的东西

下面这些都应明确排除在最小 repo 外：

- action autopilot
- promotion ladder
- runtime action admission
- temporal sidecar
- multi-lane governance
- UI dashboard
- workflow engine
- general agent runtime

如果未来真的需要，也必须在产品证据基础上再引入。

## 11. 最终建议

这个 skeleton 的目的只有一个：

> 让 `warning-agent` 只围绕“本地高频分析 + 稀疏云端深挖 + Markdown 报文”这条产品主线生长，
> 不让 repo 在第一阶段长成更大的 incident platform。

在三层 investigator 版本下，更精确的表述应是：

> 让 `warning-agent` 只围绕“本地高频分析 + 本地 Gemma4 深挖 + 稀疏云端终审 + Markdown 报文”这条产品主线生长，
> 不让 repo 在第一阶段长成更大的 incident platform。
