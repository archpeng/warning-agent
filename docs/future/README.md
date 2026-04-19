# warning-agent Future Docs

- 状态: `future-index / roadmap-closed`
- 作用:
  - 作为 `docs/future/*` 的导航入口
  - 记录 closeout 之后的 future planning 顺序
- 不覆盖:
  - `docs/plan/*`

## 当前入口条件

当前真实前提已经不是“先完成 `P5 recovery`”，也不是“W4 仍待执行”。

当前真实前提是：

- `docs/plan/warning-agent-autopilot-delivery-2026-04-18_CLOSEOUT.md` 已 closeout
- `docs/plan/warning-agent-runtime-materialization-2026-04-19_CLOSEOUT.md` 已 closeout
- `docs/plan/warning-agent-local-trust-upgrade-2026-04-19_CLOSEOUT.md` 已 closeout
- `docs/plan/warning-agent-compounding-learning-loop-2026-04-19_CLOSEOUT.md` 已 closeout
- `docs/plan/*` 仍是当前边界与 closeout 事实的唯一 SSOT
- `docs/future/*` 当前主要作为 **historical roadmap archive** 保留
- 若要继续执行新的 future work，必须新开 explicit `PLAN / STATUS / WORKSET`

## 当前 future 主文档

- [warning-agent-local-trust-acceptance-and-minimal-upgrade.md](./warning-agent-local-trust-acceptance-and-minimal-upgrade.md)
  - 现已转为 historical roadmap document
  - 其中 `W1 -> W4` 已分别被下面 control-plane pack 收口：
    - `warning-agent-autopilot-delivery-2026-04-18`
    - `warning-agent-runtime-materialization-2026-04-19`
    - `warning-agent-local-trust-upgrade-2026-04-19`
    - `warning-agent-compounding-learning-loop-2026-04-19`

## 推荐阅读顺序

1. `docs/warning-agent-architecture.md`
2. `docs/plan/warning-agent-autopilot-delivery-2026-04-18_CLOSEOUT.md`
3. 当前 master plan 的 terminal state：
   - `docs/plan/warning-agent-autopilot-delivery-2026-04-18_PLAN.md`
   - `docs/plan/warning-agent-autopilot-delivery-2026-04-18_STATUS.md`
   - `docs/plan/warning-agent-autopilot-delivery-2026-04-18_WORKSET.md`
4. 本目录主文档

## 目录约束

`docs/future/*` 的用途固定为：

- historical roadmap archive
- post-closeout planning
- dependency analysis
- runtime materialization / trust / learning replan

不应用于：

- 覆盖当前 closeout truth
- 伪装已 closeout 的实现工作
- 引入未被架构 SSOT 接受的新产品方向
- 在没有新 control plane 的情况下 claim active execution
