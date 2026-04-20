# warning-agent autopilot run prompt

- status: `active-helper`
- purpose: 说明当前 repo-local active pack 已停在 `W7.RV1` terminal truth，后续应进入 successor planning，而不是继续在 W7 内执行
- last_updated: `2026-04-20`

## Current machine truth

当前 repo-local machine control-plane 以以下文件为机器真相：

- `docs/plan/README.md`
- `docs/plan/active_PLAN.md`
- `docs/plan/active_STATUS.md`
- `docs/plan/active_WORKSET.md`

当前 richer source pack 为：

- `docs/plan/warning-agent-signoz-warning-production-2026-04-20_PLAN.md`
- `docs/plan/warning-agent-signoz-warning-production-2026-04-20_STATUS.md`
- `docs/plan/warning-agent-signoz-warning-production-2026-04-20_WORKSET.md`

## Current active slice

- `W7.RV1`
- state: `completed`
- intended handoff: `plan-creator`

## What this means

- W7 已完成 closeout；不要继续在当前 W7 pack 内追加实现
- 若要继续推进，必须从：
  - `docs/plan/warning-agent-w8-successor-replan-input-2026-04-20.md`
  出发创建 successor pack
- 若是新 local autopilot session，仍需遵守 clean-start rule；但当前 pack 本身不再是可继续 execution 的 active implementation slice

## Required next move

下一步默认不是 `execute-plan`，而是：

- `plan-creator`

目标：

- 基于 `docs/plan/warning-agent-w8-successor-replan-input-2026-04-20.md`
- 创建新的 successor pack
- 再让新的 machine/source control-plane 指向下一条可执行 active slice
