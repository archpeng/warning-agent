# warning-agent 最小 Repo Skeleton

- 状态: `derived-design`
- 范围: 仅服务于窄版智能分析-报警器
- 对齐文档:
  - `warning-agent-architecture.md`
  - `warning-agent-schema-draft.md`

## 1. 设计目标

这个 repo 的目标不是“预留所有未来能力”，而是把 MVP 主路径做得最清楚。

当前唯一主路径是：

```text
alert -> packet -> local analysis -> optional investigator (default local-first) -> optional cloud fallback -> markdown report
```

因此 repo 结构必须直接暴露下面三件事：

- 热路径是 deterministic packet + local analyzer
- investigator 是一个接口，不是两个平行子系统
- cloud 是 fallback，不是默认模块中心

## 2. 最小目录结构

```text
warning-agent/
  docs/
    warning-agent-architecture.md
    warning-agent-schema-draft.md
    warning-agent-contract-inventory.md

  app/
    main.py

    receiver/
      alertmanager_webhook.py

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
      calibrate.py
      contracts.py

    investigator/
      base.py
      router.py
      local_primary.py
      cloud_fallback.py
      tools.py
      contracts.py

    reports/
      markdown_builder.py
      contracts.py

    storage/
      sqlite_store.py
      artifact_store.py

    feedback/
      outcome_ingest.py
      replay.py

  schemas/
    incident-packet.v1.json
    local-analyzer-decision.v1.json
    investigation-result.v1.json
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
    run_replay.py
    rebuild_retrieval_index.py
    train_fast_scorer.py

  tests/
    test_contracts.py
    test_configs.py
    test_packet_builder.py
    test_retrieval.py
    test_fast_scorer.py
    test_markdown_builder.py
```

## 3. 热路径模块

这些模块构成第一版真正需要优先实现的链路：

| 文件 | 作用 |
|---|---|
| `app/receiver/alertmanager_webhook.py` | 接收 Alertmanager 事件或 replay 输入 |
| `app/collectors/prometheus.py` | 拉取固定 Prometheus 指标窗口 |
| `app/collectors/signoz.py` | 拉取固定 SigNoz logs / traces / 聚合结果 |
| `app/packet/builder.py` | 构造 `incident packet` |
| `app/packet/render.py` | 把 packet 渲染成检索文本 |
| `app/retrieval/search.py` | 本地历史检索 |
| `app/analyzer/fast_scorer.py` | 本地高频 structured scorer |
| `app/reports/markdown_builder.py` | 生成标准化 Markdown 报文 |

在 `P3` 之前，不需要 investigator runtime。

## 4. P4/P5 的最小 investigator 结构

investigator 层现在只保留一个接口家族：

| 文件 | 作用 |
|---|---|
| `app/investigator/base.py` | investigator interface 定义 |
| `app/investigator/router.py` | local-first 路由逻辑 |
| `app/investigator/local_primary.py` | 默认本地调查 provider |
| `app/investigator/cloud_fallback.py` | unresolved case 的 cloud fallback provider |
| `app/investigator/tools.py` | bounded observability / repo tools 包装 |

当前不再把下面这些当成第一版独立中心模块：

- `handoff_builder.py`
- `cloud_final_reviewer.py`
- model-specific `local_gemma4_investigator.py`

压缩 handoff 仍然保留，但它是 `cloud_fallback.py` 的内部能力，不再单独长成一个重模块。

## 5. 冷路径模块

这些模块不是第一波必须完整实现，但保留清晰位置：

| 文件 | 作用 |
|---|---|
| `app/retrieval/index.py` | 构建本地检索索引 |
| `app/analyzer/calibrate.py` | 校准与阈值更新 |
| `app/storage/sqlite_store.py` | metadata 存储 |
| `app/storage/artifact_store.py` | JSONL artifact 存储 |
| `app/feedback/outcome_ingest.py` | outcome 写回 |
| `app/feedback/replay.py` | 存量 artifacts 回放 |

当前不再把下面这些当作最小 skeleton 的默认部分：

- `small_model.py`
- `train_small_model.py`
- `hot_window_scan.py`
- `run_shadow_replay.py`

## 6. 模块边界

### 6.1 `local analyzer`

- 输入：`incident packet`
- 输出：`local analyzer decision`
- 责任：高频 first-pass

### 6.2 `investigator interface`

- 输入：`incident packet` + `local analyzer decision`
- 输出：`investigation result`
- 默认 provider：`local-primary`
- fallback provider：`cloud-fallback`

### 6.3 `reports`

- 输入：结构化对象
- 输出：稳定 Markdown 报文
- 不依赖自由生成 prose

## 7. 推荐实现顺序

当前统一顺序固定为：

1. `schemas/` + `contracts.py`
2. `packet/`
3. `collectors/`
4. `reports/`
5. `retrieval/`
6. `analyzer/fast_scorer.py`
7. `investigator/base.py` + `router.py`
8. `investigator/local_primary.py`
9. `investigator/cloud_fallback.py`
10. `storage/` + `feedback/`

## 8. 一句话结论

repo skeleton 的目标不是提前为“大系统”铺路，而是：

> 先把 packet、local analyzer 和 report 做稳；
> 再在同一 investigator 接口下引入 `local-first` 与 `cloud fallback`；
> 不再让两套 investigator 子系统并行生长。
