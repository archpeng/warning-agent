# warning-agent autopilot run prompt

- status: `active-helper`
- purpose: 用于在新会话里确认 `warning-agent` 当前 active pack 是否仍可执行；如果 active pack 已 terminal closeout，则明确转入 successor planning，而不是误继续旧 pack
- last_updated: `2026-04-20`

## How to use

在仓库根目录启动新会话后，直接粘贴下面整段提示词。

---

你现在在仓库 `/home/peng/dt-git/github/warning-agent` 中执行 `warning-agent` 的 autopilot run。

你的第一目标不是直接开始改代码，而是：

- 严格遵守 repo-local active control-plane
- 先确认当前 active pack 是否仍在 execution state
- 如果当前 pack 已 terminal closeout，就不要继续在旧 pack 中自动推进
- 而是转入 successor `plan-creator` boundary

## local extension mode 前置要求

1. repo-local active control-plane 以以下文件为机器真相：
   - `docs/plan/README.md`
   - `docs/plan/active_PLAN.md`
   - `docs/plan/active_STATUS.md`
   - `docs/plan/active_WORKSET.md`
2. richer human/source pack 仍是：
   - `docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_PLAN.md`
   - `docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_STATUS.md`
   - `docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_WORKSET.md`
3. local mode 的第一次 `/autopilot-run` 需要从 clean repo state 启动；如果 repo 在启动前已经 dirty，预期会命中 dirty-repo initial-run guard。

## 当前 terminal truth

当前 active pack 已在 `AC.RV1` closeout，状态为：

- verdict = `accept_with_residuals`
- next handoff = `plan-creator`
- current pack 不应再继续追加 execution slices

## 必须先读的 source-of-truth

1. `docs/plan/README.md`
2. `docs/plan/active_PLAN.md`
3. `docs/plan/active_STATUS.md`
4. `docs/plan/active_WORKSET.md`
5. `docs/plan/warning-agent-architecture-clarity-optimization-2026-04-20_CLOSEOUT.md`
6. `docs/plan/warning-agent-architecture-clarity-optimization-successor-replan-input-2026-04-20.md`

必要时再读：

- `README.md`
- `docs/warning-agent-architecture.md`
- `docs/warning-agent-architecture-clarity-guardrails.md`
- `docs/warning-agent-architecture-clarity-target-map.md`
- `docs/future/warning-agent-3.5-3.6-learning-optimization-minimal-engineering.md`

## 当前要求

完成 `AC.RV1` 后：

- 不要继续在当前 pack 中自动推进
- 如需继续推进，必须进入 successor replan
- 优先使用 `plan-creator`

## 推荐 next action

如果目标是继续改进 `3.5 / 3.6`：

- 读取 `docs/plan/warning-agent-architecture-clarity-optimization-successor-replan-input-2026-04-20.md`
- 新开 successor pack
- 不要 reopen 当前 architecture-clarity pack

---
