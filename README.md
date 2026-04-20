# warning-agent

`warning-agent` 是一个极窄的智能分析-报警器。

它只做一件事：

> 接收 `Prometheus + SigNoz` 告警与有界观测证据，
> 先用本地 `retrieval + analyzer` 做高频 first-pass，
> 只有在需要时才进入单一 investigator 接口，
> investigator 默认 `local-first`，只有 unresolved case 才使用 cloud fallback，
> 最终输出稳定的 Markdown 警报报文。

## 当前统一主线

```text
Prometheus / Alertmanager alert
  -> bounded evidence collection
  -> incident packet
  -> local retrieval + local analyzer
  -> optional investigator (default local-first)
  -> optional cloud fallback
  -> markdown alert report
  -> outcome feedback
```

这条主线的重点是：

- 高频路径优先 `search + learning`
- investigator 只有一个接口，不再拆成两个重子系统
- cloud 只做 fallback，不做默认推理平面
- 结构化对象是真相，Markdown 是投影

## SSOT 约定

当前仓库的 source-of-truth 分层固定为：

- 产品 SSOT: [warning-agent 架构设计](./docs/warning-agent-architecture.md)
- 契约 SSOT: [schema 草案](./docs/warning-agent-schema-draft.md)
- 契约映射 SSOT: [contract inventory](./docs/warning-agent-contract-inventory.md)
- 交付控制面 SSOT:
  - [PLAN](./docs/plan/warning-agent-autopilot-delivery-2026-04-18_PLAN.md)
  - [STATUS](./docs/plan/warning-agent-autopilot-delivery-2026-04-18_STATUS.md)
  - [WORKSET](./docs/plan/warning-agent-autopilot-delivery-2026-04-18_WORKSET.md)
- `docs/analyse/*` 是派生分析，不允许覆盖以上文档

## 当前阶段模型

后续实现顺序现在统一为：

- `P1`: repo bootstrap + contract materialization
- `P2`: deterministic packet/report baseline
- `P3`: local analyzer baseline
- `P4`: 单一 investigator 接口，默认 `local-first`
- `P5`: cloud fallback only

`P5` 完成后才讨论更后的 benchmark hardening、shadow 或小模型替换；它们不再作为默认主线的一部分。

## 当前设计边界

这个项目明确不做：

- remediation / 自动执行
- workflow engine
- multi-agent orchestration
- observability UI / APM suite
- general agent runtime

项目只聚焦：

- 智能分析
- 精准升级
- 标准报文

## 当前仓库基线

当前仓库已经具备：

- `pyproject.toml`
- `app/` 最小 Python runtime 骨架
- `schemas/*.json` contract artifacts
- `configs/*.yaml` baseline 样例
- `tests/` smoke + contract harness

最小本地验证：

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
python3 -m compileall app
uv run warning-agent
```

如果要启用当前已经落地的 `adapter-feishu` notify-first live bridge：

```bash
cp .env.example .env
```

当前 `.env.example` 已包含本机 `adapter-feishu` 地址和已验证过的本地测试群目标：

- `WARNING_AGENT_ADAPTER_FEISHU_BASE_URL`
- `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID`

如果你要改成直接发给某个用户：

- 清空 `WARNING_AGENT_ADAPTER_FEISHU_CHAT_ID`
- 设置 `WARNING_AGENT_ADAPTER_FEISHU_OPEN_ID`

## 补充文档

- [integration rollout evidence baseline](./docs/warning-agent-integration-rollout-evidence.md)
- [本地 autopilot clean-start runbook](./docs/warning-agent-local-autopilot-clean-start-runbook.md)
- [最小 repo skeleton](./docs/warning-agent-minimal-repo-skeleton.md)
- [设计决策表](./docs/analyse/warning-agent-design-decision-table.md)
- [技术栈建议](./docs/analyse/warning-agent-tech-stack-recommendation.md)
- [local-first investigator path](./docs/analyse/warning-agent-local-first-investigation-path.md)
- [本地可用性检查](./docs/analyse/warning-agent-local-observability-status.md)

## 一句话总结

`warning-agent` 不是一个“大而全”的 AI 运维平台。

它是一个围绕下面这条主线构建的极窄产品：

> `incident packet -> local search + learning -> local-first investigation -> cloud fallback only when needed -> markdown alert report`
