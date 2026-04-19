# warning-agent 技术栈建议

- 状态: `aligned-recommendation`
- 范围: `warning-agent` 当前主线所需的最小技术栈
- 对齐文档:
  - `warning-agent-architecture.md`
  - `warning-agent-minimal-repo-skeleton.md`

## 1. 选型原则

技术栈选择必须服从当前统一主线：

```text
alert
  -> incident packet
  -> local retrieval + local analyzer
  -> optional investigator (default local-first)
  -> optional cloud fallback
  -> markdown report
```

因此当前原则固定为：

1. 热路径优先确定性、可回放、可 benchmark
2. `P3` 先把 `retrieval + scorer` 做稳
3. `P4` 引入单一 investigator interface
4. `P5` 只给 investigator 加 cloud fallback，不再独立长 reviewer 子系统
5. 存储、索引、artifact format 优先简单可移植

## 2. 推荐技术栈总览

| 层 | 推荐技术 | 选择理由 |
|---|---|---|
| 开发语言 | `Python 3.12` | 当前环境已具备，适合数据流、HTTP 调用、schema 与回放 |
| 包管理 | `uv` | 轻量、锁版本、适合小仓库 |
| Web 接入 | `FastAPI + Uvicorn` | 适合 Alertmanager webhook 与最小内部 API |
| 配置与 schema | `Pydantic v2` + `JSON Schema` | 结构化契约清晰，易于校验与序列化 |
| HTTP 客户端 | `httpx` | 适合 Prometheus / SigNoz API |
| 本地存储 | `SQLite` | 足够支撑第一阶段 metadata、FTS、索引状态 |
| 本地检索 | `SQLite FTS5` | 第一版无需额外基础设施 |
| 本地 scorer | `scikit-learn` | `LogisticRegression` + calibration 足够做基线 |
| Artifact 存储 | `JSONL` | 简单、可 diff、可 replay |
| Markdown 生成 | `Jinja2` + `PyYAML` | 模板清晰，frontmatter 与正文都容易固定 |
| 测试 | `pytest` | 足够覆盖 contract / packet / report / collector |
| 代码质量 | `ruff` | 足够轻、反馈快 |

## 3. 分阶段技术选择

### P1-P2

优先固定：

- `JSON Schema`
- `Pydantic`
- `FastAPI`
- `httpx`
- `Jinja2`

此时不需要：

- 本地小模型 serving
- 复杂 agent runtime
- vector DB

### P3

本地 analyzer 基线固定为：

- `SQLite FTS5`
- `scikit-learn`
- calibration / thresholds

输出重点：

- `severity_band`
- `severity_score`
- `novelty_score`
- `confidence`
- `needs_investigation`
- `recommended_action`
- `reason_codes`

### P4

investigator interface 固定为：

- Python module interface
- bounded tool wrappers
- default `local-primary` provider

这里的重点不是某个模型 SDK，而是边界：

- 输入只看一个 packet
- 工具调用有 hard cap
- 输出必须是结构化 `investigation result`

### P5

cloud 只作为 fallback：

- 只消费 compressed handoff + bounded refs
- 不重复读取完整原始观测洪流
- 不独立扩成 reviewer 子系统

## 4. 为什么先不用更重的东西

当前不建议第一版就引入：

- Postgres
- Elasticsearch / OpenSearch
- Kafka
- vector DB
- workflow state store
- 专门的 multi-agent runtime

原因很简单：

- 当前目标是验证窄产品闭环
- 不是先建设平台
- 不是先建设复杂 rollout / review / orchestration 层

## 5. Prometheus / SigNoz 接入方式

### 5.1 热路径 collector

热路径固定走确定性 API：

- `Prometheus HTTP API`
- `SigNoz HTTP / query API`

### 5.2 investigator tools

investigator 层允许使用：

- `SigNoz MCP`
- bounded repo code search
- bounded Prometheus follow-up

### 5.3 当前默认 endpoint 建议

- Prometheus primary: `http://192.168.33.16:9090`
- Prometheus secondary: `http://10.10.32.206:31326`
- Prometheus optional: `http://10.10.32.203:30223`
- SigNoz MCP: `http://127.0.0.1:3104/mcp`

## 6. 一句话结论

当前最稳的技术路径不是“先让模型看起来聪明”，而是：

> 先用 `SQLite FTS5 + fast scorer` 把 `P3` 做稳，
> 再把 investigator 收敛成一个 `local-first` 接口，
> 最后只给它补一个 cloud fallback。
