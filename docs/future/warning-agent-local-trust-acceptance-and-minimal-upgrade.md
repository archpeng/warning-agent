# warning-agent Future Replan: Runtime Materialization, Local Trust Upgrade, And Compounding Learning

- 状态: `future-replan-closed / historical-roadmap`
- 范围:
  - post-closeout runtime materialization
  - local analyzer trust
  - local/cloud routing and handoff quality
  - feedback / learning loop
- 不覆盖:
  - `docs/warning-agent-architecture.md`
  - `docs/plan/*`
- 当前关系:
  - `docs/plan/*` 对当前 closeout truth 仍是唯一 SSOT
  - 本文档现主要保留为 **historical roadmap archive**
  - 本文列出的 `W2/W3/W4` 已分别由对应 control-plane pack closeout
  - 若要继续执行新的 future work，必须新开 explicit control plane

## 1. 目标

这份文档原本回答的是：

> 在 2026-04-19 closeout 之后，
> `warning-agent` 下一阶段最值得做什么、依赖顺序是什么、
> 哪些工作只是“已有模块的 runtime materialization”，
> 哪些工作才属于真正的 local trust / learning upgrade。

截至当前 closeout reality：

- `W1` — `P5 recovery`：已完成
- `W2` — runtime materialization baseline：已完成
- `W3` — local trust upgrade：已完成
- `W4` — compounding learning loop：已完成

因此本文后续章节现在主要保留为 **historical sequencing rationale**，不再代表 active workset。

## 2. Current closed reality

当前仓库已经被代码、tests、benchmark、artifacts 与 closeout 文档证明具备：

- replay / webhook -> packet -> retrieval -> analyzer -> investigator -> report 活路径
- local trust benchmark surface 与 trained scorer runtime truth
- outcome artifact / ingest / retrieval refresh / compare-ready corpus
- candidate retrain / compare summary
- promotion report + explicit hold decision
- cadence / rollback governance freeze

当前关键 closeout 证据：

- `docs/plan/warning-agent-runtime-materialization-2026-04-19_CLOSEOUT.md`
- `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_CLOSEOUT.md`
- `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md`

一句话：

> 本文所规划的 `W2 -> W4` 路线现在已经在对应 control-plane pack 中全部收口；
> 本文剩余内容应按 historical roadmap 理解，而不是当前缺口清单。

## 3. Planning Principles

future 规划必须继续服从当前架构 SSOT 与已 closeout 的 control plane。

固定原则：

1. 不能用 future doc 覆盖 `docs/plan/*` 的 closeout truth。
2. 不能把 historical completion 写回成 active workset。
3. 不能为了追求“看起来更聪明”而跳过 runtime materialization。
4. 不能把 post-closeout future work 静默塞回已完成的 `P5`。
5. 不能把 cloud fallback 重新长成默认审查平面。
6. 不能在 feedback loop 未建立时，把更多 heuristics 伪装成 learning。

## 4. Workstream Map

| Workstream | 目标 | 产出 | 当前角色 |
|---|---|---|---|
| `W1 P5 recovery` | historical prerequisite | cloud escalation policy 真正进入 runtime；cloud benchmark accepted；P5 closeout | 已完成，不再执行 |
| `W2 runtime materialization baseline` | 把现有模块接成真实入口与活路径 | entrypoint / artifact writeback / retrieval wiring / tool-driven local path | 已完成 |
| `W3 local trust upgrade` | 提升本地判断可信度 | temporal features、calibration、routing correctness、handoff quality | 已完成 |
| `W4 compounding learning loop` | 让 feedback / outcome 形成复利 | outcome ingest、retrieval refresh、retrain / compare / promote | 已完成 |

## 5. Strict Dependency Ladder

### 5.1 Recommended execution order

未来推荐顺序固定为：

1. `W2` 完成最小 runtime materialization
2. `W3` 完成 local trust upgrade
3. `W4` 建立最小 learning loop

说明：

- `W1` 已完成，只作为 prerequisite truth 保留
- 当前不应再把 `W1` 当 active queue claim

### 5.2 Research can start earlier

以下工作可在 `W2` 期间做研究，但不应 claim implementation done：

- trust metrics freeze
- temporal context / packet v2 设计
- corpora 设计
- calibration summary shape 设计
- richer cloud routing-eval corpus 设计

### 5.3 Why this order

原因：

- `W2` 不完成，系统仍更像“模块集合 + tests/scripts path”
- `W3` 不完成，local trust 仍主要停留在 baseline heuristics
- `W4` 不完成，The Bitter Lesson 里的 feedback compounding 仍不存在

## 6. W1 — Historical Prerequisite: P5 Recovery

### 6.1 Why W1 is retained here

保留 `W1` 不是为了继续执行，而是为了明确：

- `P5` closeout gap 已经如何被 honest 修补
- 为什么未来 work 不需要再回头做 `P5 recovery`

### 6.2 What W1 completed

#### `W1.S1`
- `cloud escalation routing / invocation materialization`
- 当前已 landed：
  - `app/investigator/runtime.py`
  - `app/investigator/router.py`
  - `configs/escalation.yaml`
  - `tests/test_investigation_runtime.py`

#### `W1.S2`
- `cloud benchmark freeze / acceptance`
- 当前已 landed：
  - `app/investigator/cloud_benchmark.py`
  - `scripts/run_cloud_fallback_benchmark.py`
  - `fixtures/evidence/cloud-fallback-routing-eval-corpus.json`
  - `data/benchmarks/cloud-fallback-baseline-summary.json`

#### `W1.S3`
- `P5 closeout summary`
- 当前已 landed：
  - `docs/plan/warning-agent-autopilot-delivery-2026-04-18_CLOSEOUT.md`

#### `W1.S4`
- `explicit policy decision`
- 当前状态：`not-needed`

### 6.3 Current W1 verdict

`W1` 已完成，不再是 future blocker。

需要保留的 residual 只有：

- richer cloud-routed corpus 仍可继续扩充
- 这属于 future confidence / hardening，不属于 `P5` 未闭合

## 7. W2 — Runtime Materialization Baseline

### 7.1 Why W2 exists now

当前代码已经拥有：

- packet builder
- local analyzer
- investigator runtime path
- report builder
- artifact store primitives
- metadata store primitives

但仍缺少 **面向产品运行的正式 glue**：

- `app/main.py` 不是活路径
- artifact writeback 没进入主执行路径
- retrieval render / index refresh 没进入主执行路径
- operator-facing replay / webhook execution path 仍未 materialize

因此 `W2` 的任务不是“增加新模块”，而是：

> 把已经存在的能力接成真正能运行、能保存、能索引的最小 runtime。

### 7.2 W2 slices

#### `W2.S1`
名称：
- `entrypoint and execution path materialization`

目标：
- 提供最小 runnable path：

```text
replay/webhook input
  -> normalized alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval
  -> local analyzer
  -> optional local-primary / cloud fallback
  -> markdown report
```

交付物：
- `app/main.py` 不再只是 bootstrap banner
- replay execution helper 或最小 CLI / API wiring
- 最小可执行入口 proof

#### `W2.S2`
名称：
- `artifact writeback and retrieval wiring`

目标：
- packet / decision / investigation / report 走真实 artifact writeback
- retrieval index / refresh 不再只是 isolated primitive

交付物：
- `JSONLArtifactStore` 接入活路径
- `MetadataStore` 接入活路径
- retrieval render / index refresh 接入活路径

#### `W2.S3`
名称：
- `local-primary evidence-driven materialization`

目标：
- 让 `local_primary` 真正消费 bounded tools，而不是仅做 smoke synthesis

交付物：
- `BoundedInvestigatorTools` 接入 `LocalPrimaryInvestigator`
- tool usage 真正反映在 investigation result / benchmark 中

说明：
- 当前 `local-primary` benchmark 中 `average_tool_calls_per_investigation = 0.0`
- 这说明 smoke baseline 成立，但不代表“真实本地深挖能力”已经成立

#### `W2.S4`
名称：
- `runtime smoke and operator path proof`

目标：
- 用 replay 或 stub webhook 证明整条最小产品路径能跑通

交付物：
- bounded end-to-end smoke
- artifact persistence proof
- stable report rendering proof

### 7.3 W2 done_when

`W2` 完成时，系统应至少能诚实说：

- 它不只是 tests / scripts 中成立的模块集合
- 它已有正式 entrypoint / execution path
- packet / decision / investigation / report 会被真实生成、保存、索引
- local/cloud 两条调查路径都可被 entrypoint 间接触发

## 8. W3 — Local Trust Upgrade

### 8.1 Why W3 exists

`W2` 解决的是“系统是否真正运行”。

`W3` 解决的是“本地判断是否足够可信”。

当前 local trust 的主要限制仍是：

- local analyzer 仍是 baseline fast scorer
- 特征更多是单点 snapshot，而不是 richer temporal structure
- scorer 还没有显式 learned calibration surface
- routing / handoff correctness 的 corpus 仍偏薄
- current cloud benchmark 是 zero-cloud baseline，不足以代表 richer routing reality

### 8.2 Planning note on gates

本节所有指标当前都只是 **future planning targets**。

它们不是当前 control plane 的 active numeric gates，
在新 plan 明确前，不应把它们当作已经冻结的 acceptance policy。

### 8.3 Local trust 的五个验收维度（planning targets）

#### Calibration

| Metric | 定义 | 最低 gate | Stretch |
|---|---|---|---|
| `brier_score` | `needs_investigation` 概率的 Brier score | `<= 0.16` | `<= 0.12` |
| `ece_10bin` | 10-bin expected calibration error | `<= 0.10` | `<= 0.06` |
| `severe_confidence_gap` | severe case 平均 confidence - benign case 平均 confidence | `>= 0.12` | `>= 0.20` |
| `top_decile_precision` | confidence 最高 10% case 的 severe / investigate precision | `>= 0.75` | `>= 0.85` |

#### False Escalation

| Metric | 定义 | 最低 gate | Stretch |
|---|---|---|---|
| `false_investigation_rate_on_benign` | benign case 中被标记 `needs_investigation = true` 的比例 | `<= 0.15` | `<= 0.08` |
| `false_local_primary_invocation_rate_on_benign` | benign case 中实际进入 `local_primary` 的比例 | `<= 0.08` | `<= 0.05` |
| `investigation_candidate_rate` | 全 replay corpus 上 `needs_investigation = true` 的比例 | `<= 0.30` | `<= 0.22` |
| `local_primary_invocation_rate` | 全 replay corpus 上进入 `local_primary` 的比例 | `<= 0.20` | `<= 0.15` |

#### Temporal Robustness

| Metric | 定义 | 最低 gate | Stretch |
|---|---|---|---|
| `window_jitter_flip_rate` | 同一 case 在 `window +/- 5m` 变体上 `needs_investigation` 翻转比例 | `<= 0.12` | `<= 0.06` |
| `severity_band_drift_rate` | 同一 case 在时间抖动变体上 severity band 漂移超过 1 档的比例 | `<= 0.08` | `<= 0.03` |
| `persistent_anomaly_recall` | 持续型异常样本中被保留为 investigate 的比例 | `>= 0.85` | `>= 0.92` |
| `seasonal_benign_suppression_precision` | 周期性 benign 样本被正确压制的比例 | `>= 0.75` | `>= 0.85` |

#### Routing Correctness

| Metric | 定义 | 最低 gate | Stretch |
|---|---|---|---|
| `local_primary_routing_alignment_rate` | 与 routing-eval corpus 的 expected local label 一致的比例 | `>= 0.95` | `>= 0.98` |
| `missed_local_primary_rate` | 应进入 `local_primary` 却未进入的比例 | `<= 0.10` | `<= 0.05` |
| `unnecessary_local_primary_rate` | 不应进入 `local_primary` 却进入的比例 | `<= 0.05` | `<= 0.03` |
| `cloud_fallback_alignment_rate` | 与 fallback-eval corpus 的 expected cloud label 一致的比例 | `>= 0.90` | `>= 0.95` |

#### Handoff Quality

| Metric | 定义 | 最低 gate | Stretch |
|---|---|---|---|
| `handoff_required_fields_completeness` | `compressed_handoff` 必需字段完整率 | `= 1.0` | `= 1.0` |
| `handoff_token_budget_pass_rate` | `handoff_tokens_estimate <= 1200` 的比例 | `>= 0.95` | `>= 0.99` |
| `handoff_reason_retention_rate` | handoff 中保留 top reason codes 的比例 | `>= 0.90` | `>= 0.97` |
| `handoff_routing_retention_rate` | 仅消费 handoff 时，最终 escalation target / recommended action 与 full local result 一致的比例 | `>= 0.85` | `>= 0.92` |

### 8.4 W3 benchmark surface

建议新增：

1. `data/benchmarks/local-analyzer-calibration-summary.json`
2. `data/benchmarks/local-analyzer-temporal-robustness-summary.json`
3. `data/benchmarks/local-routing-correctness-summary.json`
4. `data/benchmarks/local-handoff-quality-summary.json`

要求：

- 可重复生成
- 明确 corpus schema version
- 明确 analyzer / feature / routing / handoff version
- 可被 future `STATUS` 直接引用

### 8.5 W3 slices

#### `W3.S1`
- `metrics freeze and benchmark surface`

交付物：
- 上述四类 summary schema + runner
- `feature_set_version`
- `analyzer_version`

#### `W3.S2`
- `packet temporal context v2`

交付物：
- richer packet contract
- 推荐采用显式 `packet v2` / temporal context surface，而不是继续偷塞到 `history`

建议字段：
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

#### `W3.S3`
- `temporal feature extraction`

交付物：
- 多窗口时序特征
- `delta_of_delta`
- anomaly duration
- deploy timing / rollback signal
- error template 新增率

#### `W3.S4`
- `learned scorer with calibration`

交付物：
- `trained_scorer`
- 离线训练脚本
- probability calibration
- model artifact versioning

建议最小方案：
- `LogisticRegression`
- `Platt scaling` 或 `isotonic calibration`

#### `W3.S5`
- `routing and handoff upgrade`

交付物：
- routing 使用 calibrated probability / confidence margin
- richer `handoff-eval-corpus`
- cloud routing correctness benchmark

### 8.6 W3 data prerequisites

| Corpus | Planning minima | 用途 |
|---|---|---|
| `accepted labeled replay corpus` | `>= 30` case，`>= 8` severe | 训练与 calibration |
| `temporal-robustness-corpus` | `>= 12` 原始 case，每个至少 `3` 个时间变体 | temporal robustness |
| `local-primary-routing-eval-corpus` | `>= 20` case，`>= 4` expected invocation | routing correctness |
| `cloud-fallback-routing-eval-corpus` | `>= 12` case，`>= 3` expected fallback | fallback correctness |
| `handoff-eval-corpus` | `>= 12` case | handoff quality |

说明：
- 当前 `10` case / `3` severe 的 accepted baseline 够 closeout，不够 strong trust upgrade

## 9. W4 — Compounding Learning Loop

### 9.1 Why W4 exists

如果没有 `W4`，`warning-agent` 仍只是：

- 有结构化对象
- 有 replay / benchmark
- 但没有真正的结果回流复利

而 The Bitter Lesson 最终要求的是：

- search
- learning
- feedback

一起形成长期增长路径。

### 9.2 Current reality before W4

当前与 `W4` 最相关的现实是：

- `app/feedback/` 目录存在
- 但真正的 `outcome ingest` 路径尚未 materialize
- retrieval refresh / corpus assembly / retrain compare 还不存在活链路

所以 `W4` 是合理 future roadmap，
但不是当前 repo 中已经半实现、只差一刀的工作。

### 9.3 W4 slices

#### `W4.S1`
- `outcome ingest path`

目标：
- 把 operator outcome / replay label / postmortem outcome 变成可存储 artifact

交付物：
- `outcomes` artifact schema / ingest path
- metadata writeback

#### `W4.S2`
- `retrieval refresh and corpus assembly`

目标：
- outcome 到来后能刷新 retrieval 文本与训练 corpus

交付物：
- retrieval refresh helper
- corpus assembler

#### `W4.S3`
- `offline retrain / compare / promote`

目标：
- 对比 `fast_scorer` 与 `trained_scorer`
- 只在 evidence 优于 baseline 时才 promote

交付物：
- train / evaluate / compare script
- promotion report

#### `W4.S4`
- `refresh cadence and governance`

目标：
- 冻结 retrain cadence、artifact versioning、回滚策略

### 9.4 W4 stop boundary

`W4` 期间不做：

- online learning serving
- feature store
- streaming infra
- automatic promotion without evidence review

## 10. Tech Stack Reality And Future Use

### 10.1 Already present and should stay

继续保留：

- `Python 3.12`
- `uv`
- `httpx`
- `SQLite + FTS5`
- `JSONL`
- `JSON Schema`
- `FastAPI`（依赖已在 repo 中）
- `scikit-learn`（依赖已在 repo 中）

### 10.2 Materialize Rather Than Expand

以下能力优先“真正用起来”，而不是先引入新平台：

- `FastAPI`
  - 当前应先 materialize 到 runtime entrypoint / webhook glue
- `scikit-learn`
  - 当前应留给 `W3.S4`

### 10.3 Optional, Not Mandatory

以下技术当前不是 future plan 的必要前提：

- `Pydantic`
- `Jinja2`

只有当 runtime ingest / report complexity 明显逼迫时再引入。

### 10.4 Explicitly Not Needed Now

当前不建议新增：

- vector DB
- Kafka
- Elasticsearch / OpenSearch
- feature store
- workflow engine
- multi-agent runtime

原因：

- 当前瓶颈不是 infra scale
- 当前瓶颈是 runtime glue、signal quality、benchmark surface、feedback loop

## 11. Recommended Future Execution Order

future execution order 建议固定为：

1. `W2.S1`
2. `W2.S2`
3. `W2.S3`
4. `W2.S4`
5. `W3.S1`
6. `W3.S2`
7. `W3.S3`
8. `W3.S4`
9. `W3.S5`
10. `W4.S1`
11. `W4.S2`
12. `W4.S3`
13. `W4.S4`

前提：
- `W1` 已完成，无需重新执行

## 12. Done When

这个 future replan 的总体方向可视为闭合，当且仅当：

- 系统存在真实 runnable execution path，而不只是 tests / scripts path
- packet / decision / investigation / report 会被 entrypoint 真实生成、保存、索引
- `local_primary` 不再只是 smoke synthesis
- local trust 五组指标拥有 repeatable benchmark surface
- outcome feedback / retrieval refresh / retrain compare 已形成最小闭环

一句话总结：

> `warning-agent` 的下一阶段主线不应再是“继续堆更多模块”，
> 而应是：
> 先把 baseline 真正接成产品运行路径，
> 再提升 local trust，
> 最后把 feedback 变成 search + learning 的复利闭环。
