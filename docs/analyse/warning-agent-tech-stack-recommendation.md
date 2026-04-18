# warning-agent 技术栈建议

- 状态: `draft-recommendation`
- 范围: `warning-agent` 第一阶段实现所需的最小技术栈
- 目标:
  - 保证主路径简单、稳定、可 benchmark
  - 优先支持 `search + learning`
  - 避免过早平台化和过早模型化

## 1. 选型原则

技术栈选择必须服从产品主线：

```text
alert
  -> incident packet
  -> local retrieval + local analyzer
  -> optional cloud investigator
  -> markdown report
```

因此选型原则是：

1. 热路径优先确定性与可回放
2. 首版本地 analyzer 优先用轻量 `retrieval + scorer`
3. 云端 investigator 只占低频分支
4. 存储优先简单、可移植、便于离线 replay
5. schema 与报文渲染必须先冻结

## 2. 推荐技术栈总览

| 层 | 推荐技术 | 选择理由 |
|---|---|---|
| 开发语言 | `Python 3.12` | 当前本机已有，生态完整，最适合快速构建数据流与工具调用 |
| 包管理 | `uv` | 本机已安装，适合轻量项目和锁版本 |
| Web 接入 | `FastAPI + Uvicorn` | 简单稳定，适合 Alertmanager webhook 和内部 API |
| 配置与 schema | `Pydantic v2` + `JSON Schema` | 结构化契约清晰，方便校验和序列化 |
| HTTP 客户端 | `httpx` | 同时支持同步/异步，适合 Prometheus / SigNoz HTTP 调用 |
| 本地存储 | `SQLite 3.45` | 本机已有，足够支撑第一阶段 metadata 与 FTS |
| 本地检索 | `SQLite FTS5` | 无需额外依赖，足够支撑第一版 packet / report 检索 |
| 本地 scorer | `scikit-learn` | 先用 `LogisticRegression` / `CalibratedClassifierCV` 做稳健基线 |
| Artifact 存储 | `JSONL` | 简单、可 diff、可 replay、可直接进训练流 |
| Markdown 生成 | `Jinja2` + `PyYAML` | 模板清晰，frontmatter 与正文都容易固定 |
| 测试 | `pytest` | 足够覆盖 packet/schema/report/collector 主链路 |
| 代码质量 | `ruff` | 足够轻，适合小型 Python 仓 |

## 3. 第一阶段明确选择

### 3.1 Runtime

第一阶段建议直接固定为：

- `Python 3.12`
- `uv`
- `FastAPI`
- `Uvicorn`

原因：

- 当前环境已具备
- 写 webhook、collector、schema、report 都快
- 对 observability API 和本地训练流都友好

### 3.2 Storage

第一阶段建议：

- metadata: `SQLite`
- artifacts: `JSONL`

不要第一版就上：

- Postgres
- Elasticsearch / OpenSearch
- Kafka
- 各种 workflow state store

原因：

- `warning-agent` 当前不是大规模平台
- 先解决产品闭环，不先解决分布式系统问题

### 3.3 Retrieval

第一阶段建议：

- `SQLite FTS5`
- 以 packet render text、report text、outcome notes 建索引
- 结合 service / operation / severity 过滤字段

为什么不先上向量数据库：

- 第一版数据量不会很大
- BM25 / FTS 对事件检索往往已经足够
- 可以更快 benchmark
- 更符合“先用简单可扩展方法打底”

若后续检索 ceiling 明显，再考虑：

- `Qdrant`
- 或轻量 embedding + rerank

### 3.4 Local analyzer

第一阶段明确选择：

- `retrieval + Logistic Regression`
- 外加 calibration

建议具体实现：

- 特征:
  - Prometheus 数值特征
  - SigNoz top template / trace ratio 特征
  - blast radius / owner / repo mapping 特征
  - retrieval 命中摘要特征
- 输出:
  - `severity_band`
  - `severity_score`
  - `novelty_score`
  - `confidence`
  - `needs_cloud_investigation`
  - `recommended_action`
  - `reason_codes`

第一阶段不要把本地 analyzer 直接实现成：

- 本地 chat model
- prompt orchestration
- agent planner

### 3.5 Cloud investigator

第一阶段建议：

- Python investigator module
- cloud LLM client
- `SigNoz MCP` over HTTP
- bounded repo code search

这里的关键不是大模型 SDK 本身，而是 investigator 边界：

- 输入只看一个 packet
- 只允许 bounded tools
- 只在 escalation 条件满足时触发

### 3.6 Report generation

第一阶段建议：

- `Jinja2` 模板
- `PyYAML` 生成 frontmatter
- Markdown 正文固定 section order

不要用：

- 完全自由的 LLM prose 作为最终报文

## 4. 本地小模型的正确位置

本地小模型不是第一阶段主技术栈。

它的正确位置是第二阶段替换件：

- V1: `retrieval + fast scorer`
- V2: `retrieval + small model`

也就是说，`small_model.py` 应作为 `local analyzer` 的第二实现，而不是第一实现。

### 4.1 第二阶段推荐路线

当以下条件满足后，再引入本地小模型：

- packet contract 稳定
- replay 数据足够
- 本地 fast scorer 的 ceiling 看得见
- escalation rate 和误报率已有 baseline

### 4.2 第二阶段模型建议

若进入 small-model 阶段，推荐原则：

- text-first
- small parameter count
- easy-to-serve
- structured JSON outputs
- 只替换 local analyzer，不改变系统结构

对应实现形态：

- `small_model.py`
- 输出与 `fast_scorer.py` 完全一致

## 5. Prometheus / SigNoz 接入方式

### 5.1 热路径 collector

热路径应优先直接走确定性 API：

- `Prometheus HTTP API`
- `SigNoz HTTP / query API`

原因：

- collector 是固定采证，不需要 agent 化
- 直接 API 最稳、最便宜、最好 replay

### 5.2 深挖 investigator

investigator 层允许使用：

- `SigNoz MCP`
- bounded repo code search

原因：

- investigator 是低频路径
- 它需要多步调查和上下文切换
- MCP 在这个层面最有价值

结论：

- `collector` 用确定性 API
- `investigator` 用工具增强

### 5.3 当前默认 endpoint 建议

结合当前已确认的环境，第一阶段默认建议：

- Prometheus primary:
  - `http://192.168.33.16:9090`
- Prometheus secondary:
  - `http://10.10.32.206:31326`
- Prometheus optional / disabled by default:
  - `http://10.10.32.203:30223`
- SigNoz investigator endpoint:
  - `http://127.0.0.1:3104/mcp`

这样配置的原因：

- 两个 Prometheus 入口已经通过健康检查和查询验证
- temporal 专用入口当前不可达，不应作为 hard dependency
- `SigNoz MCP` 已注册且实测可调用，适合作为 investigator 工具层

## 6. 推荐目录与模块实现映射

| 模块 | 技术选择 |
|---|---|
| `receiver/alertmanager_webhook.py` | `FastAPI` |
| `collectors/prometheus.py` | `httpx` |
| `collectors/signoz.py` | `httpx` |
| `packet/builder.py` | `Pydantic` + Python dataclasses |
| `retrieval/index.py` | `sqlite3` + `FTS5` |
| `retrieval/search.py` | `sqlite3` |
| `analyzer/fast_scorer.py` | `scikit-learn` |
| `investigator/cloud_investigator.py` | Python + cloud LLM SDK + MCP client |
| `reports/markdown_builder.py` | `Jinja2` + `PyYAML` |
| `storage/sqlite_store.py` | `sqlite3` |
| `feedback/retrain_jobs.py` | Python scripts + `scikit-learn` |

## 7. 第一阶段依赖建议

建议第一版 Python 依赖只控制在下面这些：

- `fastapi`
- `uvicorn`
- `pydantic`
- `httpx`
- `jinja2`
- `pyyaml`
- `scikit-learn`
- `pytest`
- `ruff`

可选但不建议首版就加：

- `lightgbm`
- `duckdb`
- `qdrant-client`
- `langchain`
- `crewai`
- `autogen`

## 8. 最终建议

`warning-agent` 第一阶段最具体、最稳的技术栈建议是：

```text
Python 3.12
  + uv
  + FastAPI / Uvicorn
  + Pydantic v2
  + httpx
  + SQLite + FTS5
  + JSONL
  + scikit-learn
  + Jinja2 + PyYAML
  + pytest + ruff
```

并坚持下面这条实现策略：

- 先做 `packet-first`
- 再做 `retrieval-first`
- 再做 `fast-scorer`
- 再接 `cloud investigator`
- 最后才考虑 `local small model`

这条技术路径最符合当前产品边界，也最符合 `The Bitter Lesson`。
