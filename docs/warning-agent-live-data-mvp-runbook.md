# warning-agent Live-Data MVP Runbook

- 状态: `historical-runbook-superseded-for-source-priority`
- note: `source-priority truth has moved to docs/warning-agent-signoz-first-runbook.md`
- scope:
  - live runtime smoke
  - fixture-vs-live execution mode
  - honest claim boundary for current MVP

## 0. Historical scope note

本文件仍描述 predecessor pack 的 live-data MVP truth，
但对“谁是 primary warning input / primary severity evidence”的问题，
它已被 `docs/warning-agent-signoz-first-runbook.md` supersede。

在当前 successor workstream 中：

- SigNoz = primary warning input and primary severity/investigation evidence
- Prometheus = optional infra corroboration only

## 1. What this MVP now does

当前 live-data MVP 已具备：

1. 从 replay / webhook 入口进入主运行链路
2. 在 `live` mode 下从 Prometheus / SigNoz collector surface 组装 packet-compatible evidence bundle
3. 运行 local analyzer 自动分析
4. 在需要 investigation 时，对 live refs 做 bounded Prometheus / SigNoz follow-up
5. 生成 Markdown report，并写入 artifacts / metadata / retrieval sidecars

## 2. What it does **not** claim

当前 MVP **不宣称**：

- production rollout ready
- external operator admission plane
- unbounded logs/traces root-cause exploration
- guaranteed real promotion / rollout
- perfect root-cause certainty

当前最诚实的 claim 是：

> `warning-agent` 现在已具备一个可演示、可试跑的 live-data MVP：
> 它可以从真实 Prometheus / SigNoz collector surface 自动取数、自动分析，
> 并在 bounded investigation 阶段做初步定位。

## 3. Execution modes

### fixture mode

适用：
- benchmark
- deterministic tests
- replay regression

路径：
- `warning-agent replay <fixture-path>`

### live mode

适用：
- live smoke
- demo / try-run
- bounded runtime validation against current Prometheus/SigNoz interfaces

路径：
- `warning-agent replay --live <fixture-path>`
- webhook app 可通过 `create_app(..., evidence_source="live")` 启动 live mode

## 4. Smoke command

当前最小 smoke：

```bash
uv run python scripts/run_live_runtime_smoke.py
```

预期：
- entrypoint summary 显示 `evidence_source = live`
- 产出 packet / decision / optional investigation / report ids
- artifacts / metadata / retrieval sidecars 正常落盘

## 5. Honest boundaries on live evidence

当前 live evidence 采用：

- bounded config-driven Prometheus query surface
- bounded SigNoz MCP wrappers
- query failure tolerant packet assembly

这意味着：

1. 如果当前环境 Prometheus metric naming 与默认 config 不完全匹配，packet 仍可 best-effort materialize。
2. 如果 SigNoz 某个 bounded call 失败，packet/report 仍可 fallback，而不是整条路径崩溃。
3. 当前 MVP 目标是 live auto-analysis + initial localization，不是 full production certainty。

## 6. When to replan instead of extending this pack

需要 replan 的情形：

- 要接真实 external outcome admission
- 要做更大规模 landed outcome batch / promotion
- 要做 multi-env rollout / canary / rollback orchestration
- 要做更深、无边界的 observability exploration
